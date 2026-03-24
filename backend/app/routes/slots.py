from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.slot import Slot, SlotStatus
from app.models.slot_history import SlotHistory
from app.models.vessel import Vessel
from app.schemas import SlotResponse, SlotConfigRequest, SlotHistoryResponse
from app.services.slot_engine import SlotEngine

router = APIRouter(prefix="/api/slots", tags=["Slots"])

@router.get("/", response_model=list[SlotResponse])
def list_slots(
    transit_date: Optional[str] = None,
    category: Optional[str] = None,
    direction: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Slot)
    if transit_date:
        query = query.filter(Slot.transit_date == date.fromisoformat(transit_date))
    if category:
        query = query.filter(Slot.category == category)
    if direction:
        query = query.filter(Slot.direction == direction)
    if status:
        query = query.filter(Slot.status == status)
    slots = query.order_by(Slot.transit_date, Slot.category, Slot.slot_number).all()
    return [SlotResponse.model_validate(s) for s in slots]

@router.get("/availability")
def check_availability(
    transit_date: str,
    category: Optional[str] = None,
    direction: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    engine = SlotEngine(db)
    td = date.fromisoformat(transit_date)
    return engine.get_slot_summary(td)

@router.post("/configure")
def configure_daily_slots(
    data: SlotConfigRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLANNER, UserRole.COORDINATOR))
):
    engine = SlotEngine(db)
    engine.generate_daily_slots(data.transit_date)

    if data.is_high_demand:
        slots = db.query(Slot).filter(
            Slot.transit_date == data.transit_date,
            Slot.category == "neopanamax"
        ).all()
        for s in slots:
            s.is_high_demand = True
        db.commit()

    return engine.get_slot_summary(data.transit_date)

@router.post("/generate-range")
def generate_slot_range(
    start_date: str,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PLANNER, UserRole.COORDINATOR))
):
    engine = SlotEngine(db)
    sd = date.fromisoformat(start_date)
    generated = 0
    for i in range(days):
        d = sd + timedelta(days=i)
        existing = db.query(Slot).filter(Slot.transit_date == d).first()
        if not existing:
            engine.generate_daily_slots(d)
            generated += 1
    return {"message": f"Generated slots for {generated} days", "start": start_date, "days": days}

@router.get("/{slot_id}")
def get_slot(slot_id: str, db: Session = Depends(get_db),
             current_user: User = Depends(get_current_user)):
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    return SlotResponse.model_validate(slot)

@router.get("/{slot_id}/history")
def get_slot_history(slot_id: str, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    entries = db.query(SlotHistory).filter(
        SlotHistory.slot_id == slot_id
    ).order_by(SlotHistory.timestamp).all()

    result = []
    for e in entries:
        data = SlotHistoryResponse.model_validate(e)
        customer = db.query(User).filter(User.id == e.customer_id).first()
        vessel = db.query(Vessel).filter(Vessel.id == e.vessel_id).first()
        data.customer_name = customer.full_name if customer else None
        data.vessel_name = vessel.name if vessel else None
        result.append(data)
    return result

@router.get("/distribution/table")
def get_distribution_table(
    current_user: User = Depends(get_current_user)
):
    from app.services.slot_engine import SLOT_DISTRIBUTION, RESTRICTIONS
    return {
        "distribution": SLOT_DISTRIBUTION,
        "restrictions": RESTRICTIONS
    }
