from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.responses.service import ResponseRecorder, ResponseRecordingService


def get_response_recorder(
    db: Session = Depends(get_db),
) -> ResponseRecorder:
    return ResponseRecordingService(db)
