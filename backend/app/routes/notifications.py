from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.schemas import NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

@router.get("/", response_model=list[NotificationResponse])
def get_notifications(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = NotificationService(db)
    notifs = service.get_user_notifications(current_user.id, unread_only)
    return [NotificationResponse.model_validate(n) for n in notifs]

@router.get("/count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = NotificationService(db)
    return {"unread_count": service.get_unread_count(current_user.id)}

@router.post("/{notification_id}/read")
def mark_read(notification_id: str,
              db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    service = NotificationService(db)
    service.mark_read(notification_id, current_user.id)
    return {"message": "Marked as read"}

@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    service = NotificationService(db)
    count = service.mark_all_read(current_user.id)
    return {"message": f"{count} notifications marked as read"}
