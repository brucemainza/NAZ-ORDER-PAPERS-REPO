from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.responses.service import ResponseRecorder, ResponseRecordingService
from app.services.status_transition import (
    StatusTransitioner,
    get_status_transitioner,
)


def get_response_recorder(
    db: Session = Depends(get_db),
    status_transitioner: StatusTransitioner = Depends(get_status_transitioner),
) -> ResponseRecorder:
    return ResponseRecordingService(
        db,
        status_transitioner=status_transitioner,
    )
