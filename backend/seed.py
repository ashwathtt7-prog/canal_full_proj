"""
Database seeding script — creates demo users, vessels, slots, and sample data.
"""
from datetime import date, timedelta, datetime
from app.database import engine, SessionLocal, Base
from app.models import *
from app.auth import hash_password
from app.services.slot_engine import SlotEngine
from app.services.pricing_service import PricingService

def seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    pricing = PricingService()

    # ── Users ──
    planner = User(
        email="planner@panama-canal.com", password_hash=hash_password("planner123"),
        full_name="Carlos Mendez", role="planner",
        company_name="Panama Canal Authority", is_active=True
    )
    coordinator = User(
        email="coordinator@panama-canal.com", password_hash=hash_password("coordinator123"),
        full_name="Maria Rodriguez", role="coordinator",
        company_name="Panama Canal Authority", is_active=True
    )
    customers = []
    customer_data = [
        ("customer1@oceanline.com", "customer123", "James Wilson", "OceanLine Corp.", "OLC-001"),
        ("customer2@globalmar.com", "customer123", "Sarah Chen", "Global Maritime Ltd.", "GML-002"),
        ("customer3@bluewave.com", "customer123", "Robert Kim", "BlueWave Carriers", "BWC-003"),
        ("customer4@pacificship.com", "customer123", "Ana Torres", "Pacific Shipping Co.", "PSC-004"),
        ("customer5@atlfreight.com", "customer123", "Michael Brown", "Atlantic Freight Inc.", "AFI-005"),
    ]
    for email, pwd, name, company, code in customer_data:
        c = User(email=email, password_hash=hash_password(pwd), full_name=name,
                 role="customer", company_name=company, customer_code=code)
        customers.append(c)

    db.add_all([planner, coordinator] + customers)
    db.commit()

    # ── Vessels ──
    vessel_data = [
        ("MV PACIFIC STAR", "IMO9100001", "regular", "none", "general_cargo", False, customers[0].id),
        ("MV ATLANTIC MOON", "IMO9100002", "neopanamax", "C", "full_container", False, customers[0].id),
        ("MV OCEAN BREEZE", "IMO9100003", "supers", "none", "full_container", False, customers[1].id),
        ("MV GLOBAL PIONEER", "IMO9100004", "neopanamax", "none", "full_container", False, customers[1].id),
        ("MV SEA GUARDIAN", "IMO9100005", "neopanamax", "C", "lng", True, customers[2].id),
        ("MV HORIZON TRADER", "IMO9100006", "supers", "none", "tanker", False, customers[2].id),
        ("MV CORAL NAVIGATOR", "IMO9100007", "neopanamax", "none", "lpg", False, customers[3].id),
        ("MV NORTHERN WAVE", "IMO9100008", "supers", "D", "roro", False, customers[3].id),
        ("MV SOUTHERN CROSS", "IMO9100009", "regular", "none", "general_cargo", False, customers[4].id),
        ("MV EAGLE SPIRIT", "IMO9100010", "neopanamax", "M", "lng", False, customers[4].id),
        ("MV DRAGON PEARL", "IMO9100011", "supers", "none", "vehicle_carrier", False, customers[0].id),
        ("MV LIBERTY BRIDGE", "IMO9100012", "supers", "C", "full_container", True, customers[1].id),
        ("MV GOLDEN GATE", "IMO9100013", "neopanamax", "none", "full_container", False, customers[2].id),
        ("MV SILVER STREAM", "IMO9100014", "regular", "none", "tanker", False, customers[3].id),
        ("MV CRYSTAL BAY", "IMO9100015", "supers", "none", "bulk", False, customers[4].id),
    ]
    vessels = []
    for name, imo, cat, hml, seg, lotsa, cust_id in vessel_data:
        v = Vessel(name=name, imo_number=imo, category=cat, hml_flag=hml,
                   segment=seg, loa=round(200 + len(name)*5, 1),
                   beam=round(30 + len(name)*0.5, 1), draft=round(10 + len(name)*0.2, 1),
                   customer_id=cust_id, is_lotsa=lotsa)
        vessels.append(v)
    db.add_all(vessels)
    db.commit()

    # ── Generate Slots for 30 days ──
    se = SlotEngine(db)
    start = date.today() + timedelta(days=2)
    for i in range(30):
        se.generate_daily_slots(start + timedelta(days=i))

    # ── Sample Reservations ──
    from app.models.slot import Slot, SlotStatus
    from app.models.reservation import Reservation, ReservationStatus, ReservationOrigin
    from app.models.slot_history import SlotHistory

    sample_dates = [start + timedelta(days=d) for d in [0, 2, 5, 7, 10]]
    for idx, (vessel, customer) in enumerate(zip(vessels[:5], customers)):
        td = sample_dates[idx % len(sample_dates)]
        slot = db.query(Slot).filter(
            Slot.transit_date == td, Slot.category == vessel.category,
            Slot.status == "available"
        ).first()
        if slot:
            bp = pricing.get_base_price(vessel.category, "standard")
            r = Reservation(
                slot_id=slot.id, vessel_id=vessel.id, customer_id=customer.id,
                origin="regular", status="booked",
                transit_date=td, direction=slot.direction.value,
                booking_fee=bp, total_fees=bp,
            )
            db.add(r)
            db.commit()
            slot.status = "booked"
            slot.reservation_id = r.id
            slot.current_price = bp
            db.commit()
            db.add(SlotHistory(
                slot_id=slot.id, customer_id=customer.id, vessel_id=vessel.id,
                event_type="booking", price=bp, total=bp,
                description=f"Initial booking: {vessel.name} on {td}"
            ))
            db.commit()

    # ── Sample Competition ──
    comp_slot = db.query(Slot).filter(Slot.status == "available", Slot.category == "supers").first()
    if comp_slot:
        from app.services.competition_service import CompetitionService
        cs = CompetitionService(db)
        comp = cs.create_competition(comp_slot.id, "cancellation")
        cs.validate_competition(comp.id, coordinator.id)
        cs.open_competition(comp.id)

    # ── Sample Auction ──
    auc_slot = db.query(Slot).filter(
        Slot.status == "available", Slot.category == "neopanamax", Slot.is_auction_slot == True
    ).first()
    if auc_slot:
        from app.services.auction_service import AuctionService
        aus = AuctionService(db)
        auction = aus.create_auction(auc_slot.id, "regular")
        aus.planner_approve(auction.id, planner.id)
        aus.coordinator_publish(auction.id, coordinator.id)

    # ── Notifications ──
    from app.services.notification_service import NotificationService
    ns = NotificationService(db)
    ns.create(planner.id, "system", "Welcome", "Welcome to the Panama Canal Booking System", "/dashboard")
    ns.create(coordinator.id, "system", "Welcome", "Welcome to the Panama Canal Booking System", "/dashboard")
    for c in customers:
        ns.create(c.id, "system", "Welcome", "Welcome to the Panama Canal Booking System", "/dashboard")

    db.close()
    print("Database seeded successfully!")
    print(f"  Planner: planner@panama-canal.com / planner123")
    print(f"  Coordinator: coordinator@panama-canal.com / coordinator123")
    print(f"  Customer 1: customer1@oceanline.com / customer123")
    print(f"  Customer 2: customer2@globalmar.com / customer123")
    print(f"  Customer 3: customer3@bluewave.com / customer123")

if __name__ == "__main__":
    seed()
