import json
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.models.reservation import Reservation, ReservationStatus
from app.models.slot import Slot
from app.models.vessel import Vessel
from app.schemas import TransactionResponse, TransactionAction
from app.services.slot_engine import SlotEngine
from app.services.billing_service import BillingService
from app.services.competition_service import CompetitionService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])

@router.get("/", response_model=list[TransactionResponse])
def list_transactions(
    status: str = None,
    type: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Transaction)
    if current_user.role == UserRole.CUSTOMER:
        query = query.filter(Transaction.requested_by == current_user.id)
    if status:
        query = query.filter(Transaction.status == status)
    if type:
        query = query.filter(Transaction.type == type)

    txs = query.order_by(Transaction.created_at.desc()).all()
    result = []
    for tx in txs:
        data = TransactionResponse.model_validate(tx)
        r = db.query(Reservation).filter(Reservation.id == tx.reservation_id).first()
        if r:
            v = db.query(Vessel).filter(Vessel.id == r.vessel_id).first()
            c = db.query(User).filter(User.id == r.customer_id).first()
            data.vessel_name = v.name if v else None
            data.customer_name = c.full_name if c else None
            data.reservation_status = r.status.value if hasattr(r.status, 'value') else r.status
        result.append(data)
    return result

@router.get("/pending", response_model=list[TransactionResponse])
def pending_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COORDINATOR, UserRole.PLANNER))
):
    pending_statuses = [TransactionStatus.PENDING, TransactionStatus.UNDER_REVIEW,
                        TransactionStatus.PLANNER_REVIEW, TransactionStatus.LOTSA_REVIEW]

    if current_user.role == UserRole.COORDINATOR:
        query = db.query(Transaction).filter(
            Transaction.status.in_([TransactionStatus.PENDING, TransactionStatus.UNDER_REVIEW])
        )
    else:
        query = db.query(Transaction).filter(
            Transaction.status.in_([TransactionStatus.PLANNER_REVIEW, TransactionStatus.LOTSA_REVIEW])
        )

    txs = query.order_by(Transaction.created_at).all()
    result = []
    for tx in txs:
        data = TransactionResponse.model_validate(tx)
        r = db.query(Reservation).filter(Reservation.id == tx.reservation_id).first()
        if r:
            v = db.query(Vessel).filter(Vessel.id == r.vessel_id).first()
            c = db.query(User).filter(User.id == r.customer_id).first()
            data.vessel_name = v.name if v else None
            data.customer_name = c.full_name if c else None
            data.reservation_status = r.status.value if hasattr(r.status, 'value') else r.status
        result.append(data)
    return result

@router.post("/{transaction_id}/approve")
def approve_transaction(
    transaction_id: str,
    action: TransactionAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COORDINATOR, UserRole.PLANNER))
):
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    r = db.query(Reservation).filter(Reservation.id == tx.reservation_id).first()
    slot = db.query(Slot).filter(Slot.id == r.slot_id).first()
    engine = SlotEngine(db)
    billing = BillingService(db)
    notif = NotificationService(db)

    # Process based on transaction type
    if tx.type == TransactionType.CHANGE_DATE:
        details = json.loads(tx.details) if tx.details else {}
        new_date = date.fromisoformat(details.get("new_date", str(r.transit_date)))

        # Release old slot and allocate new
        old_slot_routing = engine.release_slot(slot.id)
        available = engine.get_availability(new_date, slot.category, r.direction)
        if available:
            new_slot = available[0]
            engine.allocate_slot(new_slot.id, r.id, r.booking_fee)
            r.slot_id = new_slot.id
            r.transit_date = new_date
            r.status = ReservationStatus.CHANGED

            # Trigger competition/auction for released slot
            if old_slot_routing == "competition":
                comp_service = CompetitionService(db)
                comp_service.create_competition(slot.id, "date_change")

    elif tx.type == TransactionType.SUBSTITUTION:
        details = json.loads(tx.details) if tx.details else {}
        new_vessel_id = details.get("new_vessel_id")
        r.vessel_id = new_vessel_id
        billing.record_substitution_charge(slot.id, r.customer_id, new_vessel_id, r.booking_fee)
        r.total_fees += tx.fees

    elif tx.type == TransactionType.SWAP:
        details = json.loads(tx.details) if tx.details else {}
        other_id = details.get("other_reservation_id")
        r_b = db.query(Reservation).filter(Reservation.id == other_id).first()
        if r_b:
            # Swap dates and slots
            r.transit_date, r_b.transit_date = r_b.transit_date, r.transit_date
            r.slot_id, r_b.slot_id = r_b.slot_id, r.slot_id
            billing.record_swap_charge(slot.id, r.customer_id, r.vessel_id, r.booking_fee)
            r.total_fees += tx.fees

    elif tx.type == TransactionType.CANCELLATION:
        r.status = ReservationStatus.CANCELLED
        r.penalties += tx.penalties
        billing.record_cancellation_charge(
            slot.id, r.customer_id, r.vessel_id,
            r.booking_fee,
            json.loads(tx.details).get("penalty_rate", 0.5) if tx.details else 0.5
        )
        routing = engine.release_slot(slot.id)
        if routing == "competition":
            comp_service = CompetitionService(db)
            comp_service.create_competition(slot.id, "cancellation")

    elif tx.type == TransactionType.VOID:
        r.status = ReservationStatus.VOIDED
        billing.record_void(slot.id, r.customer_id, r.vessel_id)
        engine.release_slot(slot.id)

    elif tx.type == TransactionType.TIA:
        details = json.loads(tx.details) if tx.details else {}
        new_date = date.fromisoformat(details.get("new_date", str(r.transit_date)))
        r.transit_date = new_date
        r.total_fees += tx.fees

    elif tx.type == TransactionType.SDTR:
        r.status = ReservationStatus.BOOKED
        r.penalties += tx.penalties

    elif tx.type == TransactionType.DAYLIGHT_TRANSIT:
        r.total_fees += tx.fees

    elif tx.type == TransactionType.LAST_MINUTE:
        r.total_fees += tx.fees

    tx.status = TransactionStatus.APPROVED
    tx.reviewed_by = current_user.id
    tx.reviewed_at = datetime.utcnow()
    tx.completed_at = datetime.utcnow()
    tx.form_generated = "yes"
    if action.notes:
        tx.notes = action.notes

    db.commit()

    # Notify requestor
    notif.create(tx.requested_by, "transaction_approved",
                 f"{tx.type.value.replace('_', ' ').title()} Approved",
                 f"Your {tx.type.value.replace('_', ' ')} request has been approved.",
                 f"/reservations/{r.id}")

    return {"message": "Transaction approved", "transaction_id": tx.id}

@router.post("/{transaction_id}/reject")
def reject_transaction(
    transaction_id: str,
    action: TransactionAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COORDINATOR, UserRole.PLANNER))
):
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx.status = TransactionStatus.REJECTED
    tx.reviewed_by = current_user.id
    tx.reviewed_at = datetime.utcnow()
    if action.notes:
        tx.notes = action.notes
    db.commit()

    # Restore SDTR forfeit request status
    r = db.query(Reservation).filter(Reservation.id == tx.reservation_id).first()
    if tx.type == TransactionType.SDTR and r:
        r.status = ReservationStatus.FORFEITED
        db.commit()

    notif = NotificationService(db)
    notif.create(tx.requested_by, "transaction_rejected",
                 f"{tx.type.value.replace('_', ' ').title()} Rejected",
                 f"Your {tx.type.value.replace('_', ' ')} request has been rejected. {action.notes or ''}",
                 f"/reservations/{tx.reservation_id}")

    return {"message": "Transaction rejected", "transaction_id": tx.id}
