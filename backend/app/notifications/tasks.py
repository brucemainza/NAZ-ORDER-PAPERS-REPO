from uuid import UUID
from collections.abc import Callable
from typing import Any, Protocol

from app.notifications.service import StatusChangeNotifier


class TaskScheduler(Protocol):
    def add_task(
        self,
        function: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Schedule callable execution after the current unit of work."""


def enqueue_status_change_notification(
    background_tasks: TaskScheduler,
    notifier: StatusChangeNotifier,
    *,
    recipient: str | None,
    record_id: UUID,
    item_type: str,
    subject: str,
    old_status: str,
    new_status: str,
) -> None:
    if not recipient or old_status == new_status:
        return
    background_tasks.add_task(
        notifier.notify_status_change,
        recipient=recipient,
        record_id=record_id,
        item_type=item_type,
        subject=subject,
        old_status=old_status,
        new_status=new_status,
    )
