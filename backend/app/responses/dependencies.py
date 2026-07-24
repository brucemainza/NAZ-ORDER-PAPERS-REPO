from fastapi import BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.notifications.dependencies import get_status_change_notifier
from app.notifications.service import StatusChangeNotifier
from app.responses.service import ResponseRecorder, ResponseRecordingService
from app.services.status_transition import (
    StatusTransitioner,
    get_status_transitioner,
)


def get_response_recorder(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    status_transitioner: StatusTransitioner = Depends(get_status_transitioner),
    notifier: StatusChangeNotifier = Depends(get_status_change_notifier),
) -> ResponseRecorder:
    return ResponseRecordingService(
        db,
        status_transitioner=status_transitioner,
        notifier=notifier,
        task_scheduler=background_tasks,
    )
