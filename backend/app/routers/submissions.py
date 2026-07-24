from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import add_audit_log, get_current_user, request_ip, require_permission
from app.models import ParliamentaryRecord, ParliamentarySession, User
from app.notifications.dependencies import get_status_change_notifier
from app.notifications.service import StatusChangeNotifier
from app.notifications.tasks import enqueue_status_change_notification
from app.schemas.search import SearchResultOut
from app.schemas.similarity import (
    SimilarityCheckRequest,
    SimilarityCheckResponse,
)
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionDraftUpdate,
    SubmissionRecordOut,
    SubmissionResponse,
)
from app.similarity.dependencies import (
    get_duplicate_checker,
    get_embedding_generator,
    get_previously_addressed_checker,
    get_related_item_linker,
    get_similarity_result_formatter,
)
from app.similarity.duplicate_detection import (
    DUPLICATE_SIMILARITY_THRESHOLD,
    DuplicateChecker,
    DuplicateMatch,
    build_similarity_text,
)
from app.similarity.embeddings import EmbeddingGenerator
from app.similarity.presentation import SimilarityResultFormatter
from app.similarity.previously_addressed import PreviouslyAddressedChecker
from app.similarity.related_items import RelatedItemLinker
from app.services.similarity import find_previously_addressed_candidates
from app.services.submission_status import (
    InvalidStatusTransition,
    SubmissionStatus,
    transition_submission,
)

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.get("/mine", response_model=list[SubmissionRecordOut])
def my_submissions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ParliamentaryRecord]:
    return list(
        db.scalars(
            select(ParliamentaryRecord)
            .where(ParliamentaryRecord.submitted_by == user.id)
            .order_by(ParliamentaryRecord.created_at.desc())
        ).all()
    )


@router.get("/review-queue", response_model=list[SubmissionRecordOut])
def review_queue(
    db: Session = Depends(get_db),
    reviewer: User = Depends(require_permission("review_submission")),
) -> list[ParliamentaryRecord]:
    return list(
        db.scalars(
            select(ParliamentaryRecord)
            .where(
                ParliamentaryRecord.status == SubmissionStatus.UNDER_REVIEW.value
            )
            .order_by(ParliamentaryRecord.created_at.asc())
        ).all()
    )


@router.post(
    "/check-similarity",
    response_model=SimilarityCheckResponse,
)
def check_submission_similarity(
    check: SimilarityCheckRequest,
    user: User = Depends(get_current_user),
    duplicate_checker: DuplicateChecker = Depends(get_duplicate_checker),
    addressed_checker: PreviouslyAddressedChecker = Depends(
        get_previously_addressed_checker
    ),
    result_formatter: SimilarityResultFormatter = Depends(
        get_similarity_result_formatter
    ),
) -> SimilarityCheckResponse:
    required_permission = (
        "submit_question"
        if check.item_type == "Question"
        else "submit_motion"
    )
    if not user.has_permission(required_permission):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    result = duplicate_checker.check(
        subject=check.subject,
        full_text=check.full_text,
        item_type=check.item_type,
    )
    addressed_matches = []
    if check.session_id is not None:
        addressed_result = addressed_checker.check(
            subject=check.subject,
            full_text=check.full_text,
            item_type=check.item_type,
            current_session_id=check.session_id,
        )
        addressed_matches = result_formatter.format(
            [
                DuplicateMatch(
                    source_id=match.source_id,
                    score=match.score,
                    match_type="previously_addressed",
                )
                for match in addressed_result.matches
            ]
        )
    return SimilarityCheckResponse(
        possible_duplicate=result.is_duplicate,
        threshold=DUPLICATE_SIMILARITY_THRESHOLD,
        matches=result_formatter.format(result.matches),
        previously_addressed=addressed_matches,
    )


@router.post("", response_model=SubmissionResponse, status_code=201)
def create_submission(
    submission: SubmissionCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    duplicate_checker: DuplicateChecker = Depends(get_duplicate_checker),
    addressed_checker: PreviouslyAddressedChecker = Depends(
        get_previously_addressed_checker
    ),
    related_item_linker: RelatedItemLinker = Depends(get_related_item_linker),
    embedding_generator: EmbeddingGenerator = Depends(get_embedding_generator),
    result_formatter: SimilarityResultFormatter = Depends(
        get_similarity_result_formatter
    ),
) -> SubmissionResponse:
    if submission.item_type == "Question" and not user.has_permission("submit_question"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if submission.item_type == "Motion" and not user.has_permission("submit_motion"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    session = db.execute(
        select(ParliamentarySession).where(ParliamentarySession.id == submission.session_id)
    ).scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Parliamentary session not found")
    if session.status not in {"Active", "Upcoming"}:
        raise HTTPException(status_code=400, detail="Submissions can only be added to active or upcoming sessions")

    duplicate_result = duplicate_checker.check(
        subject=submission.subject,
        full_text=submission.full_text,
        item_type=submission.item_type,
    )
    addressed_result = addressed_checker.check(
        subject=submission.subject,
        full_text=submission.full_text,
        item_type=submission.item_type,
        current_session_id=submission.session_id,
    )
    addressed_matches = result_formatter.format(
        [
            DuplicateMatch(
                source_id=match.source_id,
                score=match.score,
                match_type="previously_addressed",
            )
            for match in addressed_result.matches
        ]
    )
    if duplicate_result.is_duplicate and not submission.confirm_duplicate:
        check_response = SimilarityCheckResponse(
            possible_duplicate=True,
            threshold=DUPLICATE_SIMILARITY_THRESHOLD,
            matches=result_formatter.format(duplicate_result.matches),
            previously_addressed=addressed_matches,
        )
        raise HTTPException(
            status_code=409,
            detail={
                "code": "possible_duplicate",
                **check_response.model_dump(mode="json"),
            },
        )

    record = ParliamentaryRecord(
        item_type=submission.item_type,
        session_id=submission.session_id,
        member=submission.member.strip(),
        ministry=submission.ministry.strip() if submission.ministry else None,
        answer_type=submission.answer_type,
        subject=submission.subject.strip(),
        full_text=submission.full_text.strip(),
        status=SubmissionStatus.SUBMITTED.value,
        submitted_by=user.id,
        embedding=embedding_generator.embed(
            build_similarity_text(submission.subject, submission.full_text)
        ),
    )
    transition_submission(record, SubmissionStatus.UNDER_REVIEW)
    db.add(record)
    db.flush()
    related_item_linker.link(record, addressed_result.matches)
    add_audit_log(
        db,
        user_id=user.id,
        action="record_submission",
        entity_type="parliamentary_record",
        entity_id=str(record.id),
        details=f"{record.item_type}: {record.subject}",
        ip_address=request_ip(request),
    )
    db.commit()
    db.refresh(record)

    candidates = find_previously_addressed_candidates(db, record=record, limit=5)
    return SubmissionResponse(
        record=record,
        candidates=[
            SearchResultOut(
                rank=index + 1,
                score=match.score,
                matched_terms=match.matched_terms,
                record=match.record,
            )
            for index, match in enumerate(candidates)
        ],
        previously_addressed=addressed_matches,
    )


@router.post("/{record_id}/submit", response_model=SubmissionRecordOut)
def resubmit_draft(
    record_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    notifier: StatusChangeNotifier = Depends(get_status_change_notifier),
) -> ParliamentaryRecord:
    record = db.get(ParliamentaryRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if record.submitted_by != user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the submission owner can resubmit a draft",
        )

    required_permission = (
        "submit_question"
        if record.item_type == "Question"
        else "submit_motion"
    )
    if not user.has_permission(required_permission):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    old_status = record.status
    try:
        transition_submission(record, SubmissionStatus.SUBMITTED)
        transition_submission(record, SubmissionStatus.UNDER_REVIEW)
    except InvalidStatusTransition as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    add_audit_log(
        db,
        user_id=user.id,
        action="record_resubmission",
        entity_type="parliamentary_record",
        entity_id=str(record.id),
        details=record.subject,
        ip_address=request_ip(request),
    )
    db.commit()
    db.refresh(record)
    enqueue_status_change_notification(
        background_tasks,
        notifier,
        recipient=record.submitter.email if record.submitter else None,
        record_id=record.id,
        item_type=record.item_type,
        subject=record.subject,
        old_status=old_status,
        new_status=record.status,
    )
    return record


@router.patch("/{record_id}", response_model=SubmissionRecordOut)
def update_draft(
    record_id: UUID,
    update: SubmissionDraftUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ParliamentaryRecord:
    record = db.get(ParliamentaryRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if record.submitted_by != user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the submission owner can edit a draft",
        )
    if record.status != SubmissionStatus.DRAFT.value:
        raise HTTPException(
            status_code=409,
            detail="Only Draft submissions can be edited",
        )

    required_permission = (
        "submit_question"
        if record.item_type == "Question"
        else "submit_motion"
    )
    if not user.has_permission(required_permission):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    changes = update.model_dump(exclude_unset=True)
    for required_field in ("member", "subject", "full_text"):
        if required_field in changes and changes[required_field] is None:
            raise HTTPException(
                status_code=422,
                detail=f"{required_field} cannot be null",
            )

    proposed_ministry = changes.get("ministry", record.ministry)
    proposed_answer_type = changes.get("answer_type", record.answer_type)
    if record.item_type == "Question":
        if not (proposed_ministry or "").strip():
            raise HTTPException(
                status_code=422,
                detail="Ministry or department is required for questions",
            )
        if proposed_answer_type is None:
            raise HTTPException(
                status_code=422,
                detail="Oral or written answer type is required for questions",
            )
    elif proposed_answer_type is not None:
        raise HTTPException(
            status_code=422,
            detail="Answer type only applies to questions",
        )

    for field, value in changes.items():
        setattr(record, field, value)

    add_audit_log(
        db,
        user_id=user.id,
        action="draft_update",
        entity_type="parliamentary_record",
        entity_id=str(record.id),
        details=", ".join(sorted(changes)),
        ip_address=request_ip(request),
    )
    db.commit()
    db.refresh(record)
    return record
