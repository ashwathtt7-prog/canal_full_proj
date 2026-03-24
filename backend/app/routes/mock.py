"""
Mock VUMPA & EVTMS data routes + real-time simulators
"""
import random
import math
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/mock", tags=["Mock Systems"])

# Panama Canal coordinates
CANAL_LAT = 9.08
CANAL_LNG = -79.68

def generate_vessel_positions(count=15):
    vessels = []
    statuses = ["approaching", "waiting", "in_transit", "completed", "anchored"]
    names = [
        "MV PACIFIC STAR", "MV ATLANTIC MOON", "MV OCEAN BREEZE",
        "MV GLOBAL PIONEER", "MV SEA GUARDIAN", "MV HORIZON TRADER",
        "MV CORAL NAVIGATOR", "MV NORTHERN WAVE", "MV SOUTHERN CROSS",
        "MV EAGLE SPIRIT", "MV DRAGON PEARL", "MV LIBERTY BRIDGE",
        "MV GOLDEN GATE", "MV SILVER STREAM", "MV CRYSTAL BAY"
    ]
    categories = ["neopanamax", "supers", "regular"]

    for i in range(min(count, len(names))):
        lat = CANAL_LAT + random.uniform(-0.5, 0.5)
        lng = CANAL_LNG + random.uniform(-0.5, 0.5)
        vessels.append({
            "id": f"vessel_{i+1}",
            "name": names[i],
            "imo": f"IMO{9100000 + i}",
            "category": random.choice(categories),
            "latitude": round(lat, 6),
            "longitude": round(lng, 6),
            "speed_knots": round(random.uniform(0, 12), 1),
            "heading": random.randint(0, 359),
            "status": random.choice(statuses),
            "eta": str(datetime.utcnow() + timedelta(hours=random.randint(1, 48))),
            "draft_meters": round(random.uniform(8, 15), 1),
            "last_updated": str(datetime.utcnow()),
        })
    return vessels

def generate_traffic_events(count=20):
    events = []
    event_types = [
        "vessel_approaching", "lock_entry", "transit_in_progress",
        "lock_exit", "transit_completed", "anchorage_assigned",
        "pilot_boarded", "tugs_assigned", "clearance_granted"
    ]
    locks = ["Gatun Locks", "Pedro Miguel Locks", "Miraflores Locks",
             "Agua Clara Locks (Neo)", "Cocoli Locks (Neo)"]

    for i in range(count):
        events.append({
            "id": f"evt_{i+1}",
            "type": random.choice(event_types),
            "vessel_name": f"MV {random.choice(['PACIFIC','ATLANTIC','INDIAN','ARCTIC'])} {random.choice(['STAR','MOON','BREEZE','PIONEER'])}",
            "location": random.choice(locks),
            "direction": random.choice(["northbound", "southbound"]),
            "timestamp": str(datetime.utcnow() - timedelta(minutes=random.randint(0, 120))),
            "details": f"Event {i+1} — operational update",
            "priority": random.choice(["normal", "high", "urgent"]),
        })
    events.sort(key=lambda x: x["timestamp"], reverse=True)
    return events

@router.get("/vumpa/vessels")
def get_vumpa_vessels(current_user: User = Depends(get_current_user)):
    return {
        "system": "VUMPA",
        "timestamp": str(datetime.utcnow()),
        "vessel_count": 15,
        "vessels": generate_vessel_positions(15),
        "canal_zone": {
            "center_lat": CANAL_LAT,
            "center_lng": CANAL_LNG,
            "radius_nm": 30
        }
    }

@router.get("/evtms/traffic")
def get_evtms_traffic(current_user: User = Depends(get_current_user)):
    return {
        "system": "EVTMS",
        "timestamp": str(datetime.utcnow()),
        "event_count": 20,
        "events": generate_traffic_events(20),
        "operational_summary": {
            "vessels_in_transit": random.randint(3, 8),
            "vessels_waiting": random.randint(5, 15),
            "locks_active": random.randint(3, 5),
            "avg_transit_time_hours": round(random.uniform(8, 12), 1)
        }
    }

@router.get("/vumpa/vessel/{vessel_id}")
def get_vessel_detail(vessel_id: str, current_user: User = Depends(get_current_user)):
    positions = generate_vessel_positions(1)
    if positions:
        vessel = positions[0]
        vessel["id"] = vessel_id
        vessel["track_history"] = [
            {"lat": CANAL_LAT + random.uniform(-0.3, 0.3),
             "lng": CANAL_LNG + random.uniform(-0.3, 0.3),
             "time": str(datetime.utcnow() - timedelta(hours=i))}
            for i in range(24)
        ]
        return vessel
    return {"error": "Vessel not found"}

@router.get("/billing/summary")
def get_billing_summary(current_user: User = Depends(get_current_user)):
    return {
        "system": "Billing",
        "timestamp": str(datetime.utcnow()),
        "total_invoices": random.randint(50, 200),
        "total_revenue": random.randint(5000000, 20000000),
        "pending_payments": random.randint(10, 30),
        "recent_invoices": [
            {
                "id": f"INV-{2024}-{str(i).zfill(4)}",
                "customer": f"Customer {chr(65+i)}",
                "amount": random.randint(12000, 250000),
                "type": random.choice(["booking_fee", "cancellation_penalty", "auction_payment", "substitution_fee"]),
                "status": random.choice(["paid", "pending", "overdue"]),
                "date": str(datetime.utcnow() - timedelta(days=random.randint(0, 30)))
            }
            for i in range(10)
        ]
    }
