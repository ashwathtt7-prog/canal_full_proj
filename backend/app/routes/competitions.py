from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.competition import Competition, CompetitionApplication, CompetitionStatus
from app.models.vessel import Vessel
from app.schemas import (
    CompetitionResponse, CompetitionApplyRequest,
    CompetitionApplicationResponse, SelectWinnerRequest
)
from app.services.competition_service import CompetitionService

router = APIRouter(prefix="/api/competitions", tags=["Competitions"])

@router.get("/", response_model=list[CompetitionResponse])
def list_competitions(
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Competition)
    if status:
        query = query.filter(Competition.status == status)
    comps = query.order_by(Competition.created_at.desc()).all()

    result = []
    for c in comps:
        data = CompetitionResponse.model_validate(c)
        app_count = db.query(CompetitionApplication).filter(
            CompetitionApplication.competition_id == c.id
        ).count()
        data.application_count = app_count
        if c.winner_customer_id:
            winner = db.query(User).filter(User.id == c.winner_customer_id).first()
            data.winner_name = winner.full_name if winner else None
        result.append(data)
    return result

@router.get("/{competition_id}")
def get_competition(competition_id: str, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    comp = db.query(Competition).filter(Competition.id == competition_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Competition not found")

    data = CompetitionResponse.model_validate(comp)
    data.application_count = db.query(CompetitionApplication).filter(
        CompetitionApplication.competition_id == comp.id
    ).count()
    return data

@router.post("/{competition_id}/validate")
def validate_competition(
    competition_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COORDINATOR))
):
    service = CompetitionService(db)
    comp = service.validate_competition(competition_id, current_user.id)
    return {"message": "Competition validated", "status": comp.status.value}

@router.post("/{competition_id}/open")
def open_competition(
    competition_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COORDINATOR))
):
    service = CompetitionService(db)
    comp = service.open_competition(competition_id)
    return {"message": "Competition opened for applications", "status": comp.status.value}

@router.post("/{competition_id}/apply")
def apply_to_competition(
    competition_id: str,
    data: CompetitionApplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CUSTOMER))
):
    service = CompetitionService(db)
    app = service.submit_application(competition_id, current_user.id, data.vessel_id)
    return {"message": "Application submitted", "application_id": app.id, "status": app.status.value}

@router.get("/{competition_id}/applications", response_model=list[CompetitionApplicationResponse])
def get_applications(
    competition_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COORDINATOR, UserRole.PLANNER))
):
    service = CompetitionService(db)
    apps_data = service.get_applications(competition_id)

    result = []
    for item in apps_data:
        app = item["application"]
        data = CompetitionApplicationResponse.model_validate(app)
        data.customer_name = item["customer_name"]
        data.vessel_name = item["vessel_name"]
        result.append(data)
    return result

@router.post("/{competition_id}/select-winner")
def select_winner(
    competition_id: str,
    data: SelectWinnerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COORDINATOR))
):
    service = CompetitionService(db)
    comp = service.select_winner(competition_id, data.application_id)
    return {"message": "Winner selected", "winner_customer_id": comp.winner_customer_id}

@router.post("/{competition_id}/publish")
def publish_results(
    competition_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COORDINATOR))
):
    service = CompetitionService(db)
    comp = service.publish_results(competition_id)
    return {"message": "Results published", "status": comp.status.value}
