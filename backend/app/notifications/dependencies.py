from fastapi import Depends

from app.email.base import EmailProvider
from app.email.factory import get_email_provider
from app.notifications.service import NotificationService, StatusChangeNotifier


def get_status_change_notifier(
    email_provider: EmailProvider = Depends(get_email_provider),
) -> StatusChangeNotifier:
    return NotificationService(email_provider)
