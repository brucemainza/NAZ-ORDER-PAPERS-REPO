from datetime import date

from app.main import startup
from app.models import ParliamentaryRecord, ParliamentarySession
from app.services.archiving import archive_ended_session_records


def add_session(db_session, *, code, end_date, status):
    session = ParliamentarySession(
        code=code,
        name=f"{code} Session",
        start_date=date(2025, 1, 1),
        end_date=end_date,
        status=status,
    )
    db_session.add(session)
    db_session.flush()
    return session


def add_record(db_session, session, *, subject, status):
    record = ParliamentaryRecord(
        item_type="Question",
        session=session,
        member="Hon. Archive Tester",
        ministry="Ministry of Testing",
        answer_type="Written",
        subject=subject,
        full_text=(
            f"This is the complete text for {subject}, used to verify "
            "automatic parliamentary session archiving."
        ),
        status=status,
    )
    db_session.add(record)
    db_session.flush()
    return record


def test_records_in_ended_sessions_are_archived(db_session):
    ended_by_date = add_session(
        db_session,
        code="ENDED-BY-DATE",
        end_date=date(2026, 6, 30),
        status="Active",
    )
    marked_closed = add_session(
        db_session,
        code="MARKED-CLOSED",
        end_date=date(2027, 12, 31),
        status="Closed",
    )
    submitted = add_record(
        db_session,
        ended_by_date,
        subject="Past Session Question",
        status="Submitted",
    )
    scheduled = add_record(
        db_session,
        marked_closed,
        subject="Closed Session Question",
        status="Scheduled",
    )
    db_session.commit()

    archived_count = archive_ended_session_records(
        db_session,
        as_of=date(2026, 7, 1),
    )
    db_session.commit()

    assert archived_count == 2
    assert submitted.status == "Archived"
    assert scheduled.status == "Archived"


def test_active_session_records_are_untouched_and_archiving_is_idempotent(
    db_session,
):
    active = add_session(
        db_session,
        code="CURRENT-SESSION",
        end_date=date(2026, 12, 31),
        status="Active",
    )
    record = add_record(
        db_session,
        active,
        subject="Current Session Question",
        status="Under Review",
    )
    db_session.commit()

    first_count = archive_ended_session_records(
        db_session,
        as_of=date(2026, 7, 1),
    )
    second_count = archive_ended_session_records(
        db_session,
        as_of=date(2026, 7, 1),
    )

    assert first_count == 0
    assert second_count == 0
    assert record.status == "Under Review"


def test_application_startup_automatically_archives_ended_sessions(db_session):
    ended = add_session(
        db_session,
        code="STARTUP-ARCHIVE",
        end_date=date(2020, 12, 31),
        status="Closed",
    )
    record = add_record(
        db_session,
        ended,
        subject="Startup Archive Question",
        status="Approved",
    )
    db_session.commit()

    startup()
    db_session.expire_all()

    assert record.status == "Archived"
