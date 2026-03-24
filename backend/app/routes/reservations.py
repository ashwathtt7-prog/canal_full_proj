import json
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.slot import Slot, SlotStatus
from app.models.vessel import Vessel
from app.models.reservation import Reservation, ReservationStatus, ReservationOrigin
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.schemas import (
    ReservationCreate, ReservationResponse, ChangeDateRequest,
    SubstitutionRequest, SwapRequest, CancellationRequest, VoidRequest,
    DaylightTransitRequest, TIARequest, LastMinuteRequest, SDTRRequest,
    VesselCreate, VesselResponse
)
from app.services.slot_engine import SlotEngine
from app.services.rules_engine import RulesEngine
from app.services.pricing_service import PricingService
from app.services.billing_service import BillingService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/api/reservations", tags=["Reservations"])
pricing = PricingService()

# ───────── Vessels ─────────
@router.post("/vessels", response_model=VesselResponse)
def create_vessel(data: VesselCreate, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    vessel = Vessel(
        name=data.name, imo_number=data.imo_number, category=data.category,
        hml_flag=data.hml_flag, segment=data.segment,
        loa=data.loa, beam=data.beam, draft=data.draft,
        customer_id=current_user.id, is_lotsa=data.is_lotsa,
    )
    db.add(vessel)
    db.commit()
    db.refresh(vessel)
    return VesselResponse.model_validate(vessel)

@router.get("/vessels", response_model=list[VesselResponse])
def list_vessels(db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.CUSTOMER:
        vessels = db.query(Vessel).filter(Vessel.customer_id == current_user.id).all()
    else:
        vessels = db.query(Vessel).all()
    return [VesselResponse.model_validate(v) for v in vessels]

# ───────── Reservations CRUD ─────────
@router.post("/", response_model=ReservationResponse)
def create_reservation(data: ReservationCreate, db: Session = Depends(get_db),
                        current_user: User = Depends(require_role(UserRole.CUSTOMER))):
    engine = SlotEngine(db)
    vessel = db.query(Vessel).filter(Vessel.id == data.vessel_id).first()
    if not vessel:
        raise HTTPException(status_code=404, detail="Vessel not found")

    # Check restrictions
    restrictions = engine.check_restrictions(
        data.category, data.direction, data.transit_date,
        vessel=vessel, customer_id=current_user.id
    )
    if not restrictions["allowed"]:
        raise HTTPException(status_code=400, detail=restrictions["violations"])

    # Find available slot
    available = engine.get_availability(data.transit_date, data.category, data.direction)
    if not available:
        raise HTTPException(status_code=400, detail="No slots available for this date/category/direction")

    slot = available[0]
    period = engine.determine_period(data.transit_date)
    base_price = pricing.get_base_price(data.category, period.value, slot.is_high_demand)

    reservation = Reservation(
        slot_id=slot.id, vessel_id=data.vessel_id,
        customer_id=current_user.id,
        origin=ReservationOrigin.REGULAR,
        status=ReservationStatus.BOOKED,
        transit_date=data.transit_date,
        direction=data.direction,
        booking_fee=base_price, total_fees=base_price,
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)

    engine.allocate_slot(slot.id, reservation.id, base_price)

    # Record billing
    billing = BillingService(db)
    billing.record_booking_charge(slot.id, current_user.id, data.vessel_id, base_price)

    resp = ReservationResponse.model_validate(reservation)
    resp.vessel_name = vessel.name
    resp.customer_name = current_user.full_name
    resp.category = data.category
    return resp

@router.get("/", response_model=list[ReservationResponse])
def list_reservations(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Reservation)
    if current_user.role == UserRole.CUSTOMER:
        query = query.filter(Reservation.customer_id == current_user.id)
    if status:
        query = query.filter(Reservation.status == status)
    reservations = query.order_by(Reservation.created_at.desc()).all()

    result = []
    for r in reservations:
        data = ReservationResponse.model_validate(r)
        vessel = db.query(Vessel).filter(Vessel.id == r.vessel_id).first()
        customer = db.query(User).filter(User.id == r.customer_id).first()
        slot = db.query(Slot).filter(Slot.id == r.slot_id).first()
        data.vessel_name = vessel.name if vessel else None
        data.customer_name = customer.full_name if customer else None
        data.category = slot.category if slot else None
        result.append(data)
    return result

@router.get("/{reservation_id}", response_model=ReservationResponse)
def get_reservation(reservation_id: str, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    r = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")
    data = ReservationResponse.model_validate(r)
    vessel = db.query(Vessel).filter(Vessel.id == r.vessel_id).first()
    customer = db.query(User).filter(User.id == r.customer_id).first()
    slot = db.query(Slot).filter(Slot.id == r.slot_id).first()
    data.vessel_name = vessel.name if vessel else None
    data.customer_name = customer.full_name if customer else None
    data.category = slot.category if slot else None
    return data

# ───────── Transaction Endpoints (9 types) ─────────

@router.post("/{reservation_id}/change-date")
def request_change_date(reservation_id: str, data: ChangeDateRequest,
                         db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    r = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")

    vessel = db.query(Vessel).filter(Vessel.id == r.vessel_id).first()
    rules = RulesEngine(db)
    validation = rules.validate_change_date(r, data.new_date, vessel)

    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["messages"])

    engine = SlotEngine(db)
    slot = db.query(Slot).filter(Slot.id == r.slot_id).first()
    availability = engine.get_availability(data.new_date, slot.category, r.direction)
    validation["availability"] = len(availability) > 0

    tx_status = TransactionStatus.PLANNER_REVIEW if validation.get("requires_planner") else TransactionStatus.PENDING

    tx = Transaction(
        reservation_id=reservation_id,
        type=TransactionType.CHANGE_DATE,
        status=tx_status,
        requested_by=current_user.id,
        details=json.dumps({"new_date": str(data.new_date), "old_date": str(r.transit_date)}),
        system_validation=json.dumps(validation),
    )
    db.add(tx)
    db.commit()
    return {"transaction_id": tx.id, "status": tx.status.value, "validation": validation}

@router.post("/{reservation_id}/substitution")
def request_substitution(reservation_id: str, data: SubstitutionRequest,
                          db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    r = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")

    old_vessel = db.query(Vessel).filter(Vessel.id == r.vessel_id).first()
    new_vessel = db.query(Vessel).filter(Vessel.id == data.new_vessel_id).first()
    if not new_vessel:
        raise HTTPException(status_code=404, detail="New vessel not found")

    rules = RulesEngine(db)
    validation = rules.validate_substitution(r, old_vessel, new_vessel)

    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["messages"])

    fee = pricing.calculate_substitution_fee(r.booking_fee)
    tx_status = TransactionStatus.PLANNER_REVIEW if validation.get("requires_planner") else TransactionStatus.PENDING

    tx = Transaction(
        reservation_id=reservation_id,
        type=TransactionType.SUBSTITUTION,
        status=tx_status,
        requested_by=current_user.id,
        details=json.dumps({"old_vessel_id": r.vessel_id, "new_vessel_id": data.new_vessel_id}),
        system_validation=json.dumps(validation),
        fees=fee,
    )
    db.add(tx)
    db.commit()
    return {"transaction_id": tx.id, "status": tx.status.value, "fee": fee, "validation": validation}

@router.post("/{reservation_id}/swap")
def request_swap(reservation_id: str, data: SwapRequest,
                  db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    r_a = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    r_b = db.query(Reservation).filter(Reservation.id == data.other_reservation_id).first()
    if not r_a or not r_b:
        raise HTTPException(status_code=404, detail="Reservation not found")

    v_a = db.query(Vessel).filter(Vessel.id == r_a.vessel_id).first()
    v_b = db.query(Vessel).filter(Vessel.id == r_b.vessel_id).first()

    rules = RulesEngine(db)
    validation = rules.validate_swap(r_a, r_b, v_a, v_b)

    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["messages"])

    fee = pricing.calculate_swap_fee(r_a.booking_fee)
    tx_status = TransactionStatus.PLANNER_REVIEW if validation.get("requires_planner") else TransactionStatus.PENDING

    tx = Transaction(
        reservation_id=reservation_id,
        type=TransactionType.SWAP,
        status=tx_status,
        requested_by=current_user.id,
        details=json.dumps({"other_reservation_id": data.other_reservation_id}),
        system_validation=json.dumps(validation),
        fees=fee,
    )
    db.add(tx)
    db.commit()
    return {"transaction_id": tx.id, "status": tx.status.value, "fee": fee, "validation": validation}

@router.post("/{reservation_id}/tia")
def request_tia(reservation_id: str, data: TIARequest,
                 db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    r = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")

    vessel = db.query(Vessel).filter(Vessel.id == r.vessel_id).first()
    rules = RulesEngine(db)
    validation = rules.validate_tia(vessel, data.new_date, r.transit_date)

    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["messages"])

    slot = db.query(Slot).filter(Slot.id == r.slot_id).first()
    fee = pricing.calculate_tia_fee(slot.category, vessel.is_lotsa)

    tx = Transaction(
        reservation_id=reservation_id,
        type=TransactionType.TIA,
        status=TransactionStatus.PLANNER_REVIEW,
        requested_by=current_user.id,
        details=json.dumps({"new_date": str(data.new_date), "old_date": str(r.transit_date)}),
        system_validation=json.dumps(validation),
        fees=fee,
    )
    db.add(tx)
    db.commit()
    return {"transaction_id": tx.id, "status": tx.status.value, "fee": fee, "validation": validation}

@router.post("/{reservation_id}/daylight")
def request_daylight_transit(reservation_id: str, data: DaylightTransitRequest,
                              db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    r = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")

    vessel = db.query(Vessel).filter(Vessel.id == r.vessel_id).first()
    rules = RulesEngine(db)
    validation = rules.validate_daylight_transit(vessel)

    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["messages"])

    slot = db.query(Slot).filter(Slot.id == r.slot_id).first()
    fee = pricing.calculate_daylight_transit_fee(slot.category)

    tx = Transaction(
        reservation_id=reservation_id,
        type=TransactionType.DAYLIGHT_TRANSIT,
        status=TransactionStatus.PENDING,
        requested_by=current_user.id,
        details=json.dumps({"reason": data.reason}),
        system_validation=json.dumps(validation),
        fees=fee,
    )
    db.add(tx)
    db.commit()
    return {"transaction_id": tx.id, "status": tx.status.value, "fee": fee}

@router.post("/{reservation_id}/last-minute")
def request_last_minute(reservation_id: str, data: LastMinuteRequest,
                         db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    vessel = db.query(Vessel).filter(Vessel.id == data.vessel_id).first()
    if not vessel:
        raise HTTPException(status_code=404, detail="Vessel not found")

    rules = RulesEngine(db)
    validation = rules.validate_last_minute(vessel, current_user.id, data.transit_date)

    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["messages"])

    fee = pricing.calculate_last_minute_fee(vessel.category.value if hasattr(vessel.category, 'value') else vessel.category)

    tx = Transaction(
        reservation_id=reservation_id,
        type=TransactionType.LAST_MINUTE,
        status=TransactionStatus.PLANNER_REVIEW,
        requested_by=current_user.id,
        details=json.dumps({"vessel_id": data.vessel_id, "direction": data.direction, "transit_date": str(data.transit_date)}),
        system_validation=json.dumps(validation),
        fees=fee,
    )
    db.add(tx)
    db.commit()
    return {"transaction_id": tx.id, "status": tx.status.value, "fee": fee}

@router.post("/{reservation_id}/sdtr")
def request_sdtr(reservation_id: str, data: SDTRRequest,
                  db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    r = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")

    slot = db.query(Slot).filter(Slot.id == r.slot_id).first()
    penalty = pricing.calculate_sdtr_penalty(slot.category)

    # Auto-set status to forfeit_request
    r.status = ReservationStatus.FORFEIT_REQUEST
    db.commit()

    tx = Transaction(
        reservation_id=reservation_id,
        type=TransactionType.SDTR,
        status=TransactionStatus.PENDING,
        requested_by=current_user.id,
        details=json.dumps({"reason": data.reason}),
        penalties=penalty,
    )
    db.add(tx)
    db.commit()
    return {"transaction_id": tx.id, "status": tx.status.value, "penalty": penalty}

@router.post("/{reservation_id}/cancel")
def request_cancellation(reservation_id: str, data: CancellationRequest,
                          db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    r = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")

    days_before = (r.transit_date - date.today()).days
    rules = RulesEngine(db)
    penalty_rate = rules.get_cancellation_penalty_rate(days_before, r.origin.value)
    penalty = pricing.calculate_cancellation_penalty(r.booking_fee, penalty_rate)

    tx = Transaction(
        reservation_id=reservation_id,
        type=TransactionType.CANCELLATION,
        status=TransactionStatus.PENDING,
        requested_by=current_user.id,
        details=json.dumps({"reason": data.reason, "days_before": days_before, "penalty_rate": penalty_rate}),
        penalties=penalty,
    )
    db.add(tx)
    db.commit()
    return {"transaction_id": tx.id, "status": tx.status.value, "penalty": penalty, "penalty_rate": penalty_rate}

@router.post("/{reservation_id}/void")
def request_void(reservation_id: str, data: VoidRequest,
                  db: Session = Depends(get_db),
                  current_user: User = Depends(require_role(UserRole.COORDINATOR, UserRole.PLANNER))):
    r = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")

    r.status = ReservationStatus.VOID_REQUEST

    tx = Transaction(
        reservation_id=reservation_id,
        type=TransactionType.VOID,
        status=TransactionStatus.PLANNER_REVIEW,
        requested_by=current_user.id,
        details=json.dumps({"new_slot_reservation_id": data.new_slot_reservation_id, "reason": data.reason}),
        fees=0, penalties=0,
    )
    db.add(tx)
    db.commit()
    return {"transaction_id": tx.id, "status": tx.status.value, "note": "No charges for VOID transactions"}
