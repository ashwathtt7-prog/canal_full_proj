"""
Notification Service
Manages in-app notifications and would integrate with email in production.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.notification import Notification
from app.models.user import User

class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: str, notif_type: str, title: str,
               message: str, link: Optional[str] = None) -> Notification:
        notif = Notification(
            user_id=user_id,
            type=notif_type,
            title=title,
            message=message,
            link=link,
        )
        self.db.add(notif)
        self.db.commit()
        return notif

    def get_user_notifications(self, user_id: str, unread_only: bool = False) -> List[Notification]:
        query = self.db.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            query = query.filter(Notification.is_read == False)
        return query.order_by(Notification.created_at.desc()).limit(50).all()

    def mark_read(self, notification_id: str, user_id: str) -> bool:
        notif = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        if notif:
            notif.is_read = True
            self.db.commit()
            return True
        return False

    def mark_all_read(self, user_id: str) -> int:
        count = self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).update({"is_read": True})
        self.db.commit()
        return count

    def get_unread_count(self, user_id: str) -> int:
        return self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).count()

    def notify_role(self, role: str, notif_type: str, title: str,
                     message: str, link: Optional[str] = None):
        users = self.db.query(User).filter(User.role == role).all()
        for user in users:
            self.create(user.id, notif_type, title, message, link)
