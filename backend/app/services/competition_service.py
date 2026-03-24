"""
Competition Service
Manages the Special Competition lifecycle from trigger to award.
"""
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from app.models.competition import Competition, CompetitionApplication, CompetitionStatus, ApplicationStatus
from app.models.slot import Slot, SlotStatus
from app.models.vessel import Vessel
from app.models.user import User
from app.models.notification import Notification

class CompetitionService:
    def __init__(self, db: Session):
        self.db = db

    def create_competition(self, slot_id: str, trigger_reason: str = "cancellation") -> Competition:
        """Auto-create a special competition when a slot is released."""
        slot = self.db.query(Slot).filter(Slot.id == slot_id).first()
        if not slot:
            raise ValueError("Slot not found")

        slot.status = SlotStatus.COMPETITION

        competition = Competition(
            slot_id=slot_id,
            trigger_reason=trigger_reason,
            status=CompetitionStatus.PENDING,
            category=slot.category,
            direction=slot.direction.value if hasattr(slot.direction, 'value') else slot.direction,
            transit_date=str(slot.transit_date),
        )
        self.db.add(competition)
        self.db.commit()

        # Notify coordinator
        self._notify_coordinators(competition, "New Special Competition requires validation")

        return competition

    def validate_competition(self, competition_id: str, coordinator_id: str) -> Competition:
        """Coordinator validates the competition."""
        comp = self.db.query(Competition).filter(Competition.id == competition_id).first()
        if not comp:
            raise ValueError("Competition not found")

        comp.status = CompetitionStatus.VALIDATED
        comp.validated_by = coordinator_id
        self.db.commit()
        return comp

    def open_competition(self, competition_id: str) -> Competition:
        """Open the competition for customer applications."""
        comp = self.db.query(Competition).filter(Competition.id == competition_id).first()
        if not comp:
            raise ValueError("Competition not found")

        comp.status = CompetitionStatus.OPEN
        comp.opened_at = datetime.utcnow()
        self.db.commit()

        # Notify all customers
        self._notify_customers(comp, "Special Competition now open for applications")
        return comp

    def submit_application(self, competition_id: str, customer_id: str,
                            vessel_id: str) -> CompetitionApplication:
        """Customer submits an application."""
        comp = self.db.query(Competition).filter(
            Competition.id == competition_id,
            Competition.status == CompetitionStatus.OPEN
        ).first()
        if not comp:
            raise ValueError("Competition not found or not open")

        # Check if already applied
        existing = self.db.query(CompetitionApplication).filter(
            CompetitionApplication.competition_id == competition_id,
            CompetitionApplication.customer_id == customer_id
        ).first()
        if existing:
            raise ValueError("Already applied to this competition")

        # Validate vessel
        vessel = self.db.query(Vessel).filter(Vessel.id == vessel_id).first()
        if not vessel:
            raise ValueError("Vessel not found")

        hml_valid = "passed"  # Simplified — full HML validation in production
        dir_valid = "passed"

        # Calculate ranking score (simplified — customer ranking in production)
        customer = self.db.query(User).filter(User.id == customer_id).first()
        ranking = hash(customer_id) % 100  # Simplified ranking

        app = CompetitionApplication(
            competition_id=competition_id,
            customer_id=customer_id,
            vessel_id=vessel_id,
            status=ApplicationStatus.VALIDATED,
            ranking_score=ranking,
            hml_validated=hml_valid,
            direction_validated=dir_valid,
        )
        self.db.add(app)
        self.db.commit()
        return app

    def get_applications(self, competition_id: str) -> List[Dict]:
        """Get consolidated application list with recommendations."""
        apps = self.db.query(CompetitionApplication).filter(
            CompetitionApplication.competition_id == competition_id
        ).order_by(CompetitionApplication.ranking_score.desc()).all()

        result = []
        for i, app in enumerate(apps):
            customer = self.db.query(User).filter(User.id == app.customer_id).first()
            vessel = self.db.query(Vessel).filter(Vessel.id == app.vessel_id).first()
            result.append({
                "application": app,
                "customer_name": customer.full_name if customer else "Unknown",
                "vessel_name": vessel.name if vessel else "Unknown",
                "is_recommended": i == 0  # Highest ranking is recommended
            })

        # Set recommended winner on competition
        if apps:
            comp = self.db.query(Competition).filter(
                Competition.id == competition_id).first()
            comp.recommended_winner_id = apps[0].customer_id
            self.db.commit()

        return result

    def select_winner(self, competition_id: str, application_id: str) -> Competition:
        """Coordinator selects the winner."""
        comp = self.db.query(Competition).filter(Competition.id == competition_id).first()
        if not comp:
            raise ValueError("Competition not found")

        winning_app = self.db.query(CompetitionApplication).filter(
            CompetitionApplication.id == application_id
        ).first()
        if not winning_app:
            raise ValueError("Application not found")

        # Mark winner
        winning_app.status = ApplicationStatus.WINNER
        comp.winner_customer_id = winning_app.customer_id
        comp.status = CompetitionStatus.CLOSED
        comp.closed_at = datetime.utcnow()

        # Reject all other applications
        other_apps = self.db.query(CompetitionApplication).filter(
            CompetitionApplication.competition_id == competition_id,
            CompetitionApplication.id != application_id
        ).all()
        for app in other_apps:
            app.status = ApplicationStatus.REJECTED

        self.db.commit()
        return comp

    def publish_results(self, competition_id: str) -> Competition:
        """Publish competition results."""
        comp = self.db.query(Competition).filter(Competition.id == competition_id).first()
        if not comp:
            raise ValueError("Competition not found")

        comp.status = CompetitionStatus.AWARDED
        self.db.commit()

        # Notify winner
        self._notify_user(comp.winner_customer_id,
                          "Competition Won",
                          f"You have won the Special Competition for slot on {comp.transit_date}",
                          "competition_won")

        return comp

    def _notify_coordinators(self, competition: Competition, message: str):
        coordinators = self.db.query(User).filter(User.role == "coordinator").all()
        for coord in coordinators:
            notif = Notification(
                user_id=coord.id,
                type="competition_pending",
                title="Special Competition Created",
                message=message,
                link=f"/competitions/{competition.id}"
            )
            self.db.add(notif)
        self.db.commit()

    def _notify_customers(self, competition: Competition, message: str):
        from app.models.user import UserRole
        customers = self.db.query(User).filter(User.role == UserRole.CUSTOMER).all()
        for cust in customers:
            notif = Notification(
                user_id=cust.id,
                type="competition_open",
                title="Special Competition Open",
                message=f"{message} — Category: {competition.category}, Direction: {competition.direction}",
                link=f"/competitions/{competition.id}"
            )
            self.db.add(notif)
        self.db.commit()

    def _notify_user(self, user_id: str, title: str, message: str, notif_type: str):
        notif = Notification(
            user_id=user_id,
            type=notif_type,
            title=title,
            message=message,
        )
        self.db.add(notif)
        self.db.commit()
