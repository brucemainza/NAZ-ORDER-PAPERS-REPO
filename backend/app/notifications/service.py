import logging
from abc import ABC, abstractmethod
from uuid import UUID

from app.email.base import EmailProvider

logger = logging.getLogger(__name__)


class StatusChangeNotifier(ABC):
    @abstractmethod
    async def notify_status_change(
        self,
        *,
        recipient: str,
        record_id: UUID,
        item_type: str,
        subject: str,
        old_status: str,
        new_status: str,
    ) -> bool:
        """Notify one recipient of a persisted lifecycle change."""


class NotificationService(StatusChangeNotifier):
    """Builds status messages and delegates delivery to EmailProvider."""

    def __init__(self, email_provider: EmailProvider) -> None:
        self._email_provider = email_provider

    async def notify_status_change(
        self,
        *,
        recipient: str,
        record_id: UUID,
        item_type: str,
        subject: str,
        old_status: str,
        new_status: str,
    ) -> bool:
        if old_status == new_status:
            return True

        email_subject = f"{item_type} status changed to {new_status}"
        body = (
            f'Your {item_type.lower()} "{subject}" changed from '
            f"{old_status} to {new_status}.\n\n"
            f"Reference: {record_id}"
        )
        html_body = (
            f"<p>Your {item_type.lower()} <strong>{subject}</strong> changed "
            f"from {old_status} to <strong>{new_status}</strong>.</p>"
            f"<p>Reference: {record_id}</p>"
        )
        try:
            sent = await self._email_provider.send_email(
                recipient,
                email_subject,
                body,
                html_body,
            )
        except Exception:
            logger.exception(
                "status-change email failed for record %s",
                record_id,
            )
            return False
        if not sent:
            logger.warning(
                "status-change email failed for record %s",
                record_id,
            )
        return sent
