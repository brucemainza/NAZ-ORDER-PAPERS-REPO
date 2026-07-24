from datetime import date

from pydantic import BaseModel

from app.schemas.submission import SubmissionRecordOut


class OrderPaperSection(BaseModel):
    heading: str
    item_type: str
    items: list[SubmissionRecordOut]


class OrderPaperOut(BaseModel):
    title: str
    sitting_date: date
    total_items: int
    sections: list[OrderPaperSection]
