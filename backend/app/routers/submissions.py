from hashlib import sha256
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.deps import add_audit_log, get_current_user, request_ip, require_permission
from app.jobs.queue import enqueue_outbox_job
from app.models import ParliamentaryRecord, ParliamentarySession, User
from app.schemas.search import SearchResultOut
from app.schemas.similarity import (
    SimilarityCheckRequest,
    SimilarityCheckResponse,
)
from app.schemas.submission import (
    DocumentUploadResponse,
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
    DuplicateChecker,
    DuplicateMatch,
    build_similarity_text,
)
from app.similarity.embeddings import EmbeddingGenerator
from app.similarity.presentation import SimilarityResultFormatter
from app.similarity.previously_addressed import PreviouslyAddressedChecker
from app.similarity.related_items import RelatedItemLinker
from app.services.document_parser import bounded_upload_file, parse_document_safely
from app.services.idempotency import (
    IdempotencyConflict,
    IdempotencyInProgress,
    cached_idempotency_response,
    claim_idempotency_key,
    complete_idempotency_key,
)
from app.services.similarity import find_previously_addressed_candidates
from app.services.submission_status import (
    InvalidStatusTransition,
    SubmissionStatus,
    transition_submission,
)
from app.services.transactions import (
    DatabaseConflict,
    commit_transaction,
    flush_transaction,
)

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.get("/mine", response_model=list[SubmissionRecordOut])
def my_submissions(
    cursor: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ParliamentaryRecord]:
    query = (
        select(ParliamentaryRecord)
        .where(ParliamentaryRecord.submitted_by == user.id)
        .order_by(
            ParliamentaryRecord.created_at.desc(),
            ParliamentaryRecord.id.desc(),
        )
        .limit(limit)
    )
    if cursor is not None:
        cursor_record = db.scalar(
            select(ParliamentaryRecord).where(
                ParliamentaryRecord.id == cursor,
                ParliamentaryRecord.submitted_by == user.id,
            )
        )
        if cursor_record is None:
            raise HTTPException(status_code=404, detail="Submission cursor not found")
        query = query.where(
            or_(
                ParliamentaryRecord.created_at < cursor_record.created_at,
                and_(
                    ParliamentaryRecord.created_at == cursor_record.created_at,
                    ParliamentaryRecord.id < cursor_record.id,
                ),
            )
        )
    return list(
        db.scalars(query).all()
    )


@router.get("/review-queue", response_model=list[SubmissionRecordOut])
def review_queue(
    cursor: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    reviewer: User = Depends(require_permission("review_submission")),
) -> list[ParliamentaryRecord]:
    query = (
        select(ParliamentaryRecord)
        .where(ParliamentaryRecord.status == SubmissionStatus.UNDER_REVIEW.value)
        .order_by(
            ParliamentaryRecord.created_at.asc(),
            ParliamentaryRecord.id.asc(),
        )
        .limit(limit)
    )
    if cursor is not None:
        cursor_record = db.scalar(
            select(ParliamentaryRecord).where(
                ParliamentaryRecord.id == cursor,
                ParliamentaryRecord.status == SubmissionStatus.UNDER_REVIEW.value,
            )
        )
        if cursor_record is None:
            raise HTTPException(status_code=404, detail="Review cursor not found")
        query = query.where(
            or_(
                ParliamentaryRecord.created_at > cursor_record.created_at,
                and_(
                    ParliamentaryRecord.created_at == cursor_record.created_at,
                    ParliamentaryRecord.id > cursor_record.id,
                ),
            )
        )
    return list(
        db.scalars(query).all()
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
                    ranking_score=match.score,
                    cosine_similarity=match.score,
                )
                for match in addressed_result.matches
            ]
        )
    return SimilarityCheckResponse(
        possible_duplicate=result.is_duplicate,
        threshold=result.threshold,
        threshold_version=result.threshold_version,
        matches=result_formatter.format(result.matches),
        previously_addressed=addressed_matches,
    )


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_200_OK,
)
def upload_submission_document(
    file: UploadFile = File(..., description="PDF, DOCX or TXT parliamentary document"),
    item_type: str | None = Form(default=None, pattern="^(Question|Motion)?$"),
    user: User = Depends(get_current_user),
) -> DocumentUploadResponse:
    """Extract submission fields from an uploaded document.

    The returned subject and full text can be used to pre-fill the submission
    form. The caller is still responsible for selecting the parliamentary
    session, member and any question-specific fields before creating the
    submission.
    """
    required_permission = (
        "submit_question" if item_type == "Question" else "submit_motion"
    )
    if item_type is not None and not user.has_permission(required_permission):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if item_type is None and not any(
        user.has_permission(permission)
        for permission in ("submit_question", "submit_motion")
    ):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    settings = get_settings()
    try:
        with bounded_upload_file(
            file.file,
            temp_directory=settings.upload_temp_directory,
        ) as path:
            result = parse_document_safely(
                path,
                filename=file.filename,
                content_type=file.content_type,
                item_type=item_type,
                timeout_seconds=settings.upload_parse_timeout_seconds,
                memory_mb=settings.upload_parse_memory_mb,
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document parsing is temporarily unavailable",
        ) from exc

    return DocumentUploadResponse(
        item_type=result["item_type"],
        subject=result["subject"],
        full_text=result["full_text"],
    )


@router.post("", response_model=SubmissionResponse, status_code=201)
def create_submission(
    submission: SubmissionCreate,
    request: Request,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=1,
        max_length=200,
    ),
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
    if submission.item_type == "Question" and not user.has_permission(
        "submit_question"
    ):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if submission.item_type == "Motion" and not user.has_permission("submit_motion"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        idempotency = claim_idempotency_key(
            db,
            scope=f"submission:create:{user.id}",
            key=idempotency_key,
            payload=submission.model_dump(mode="json"),
            user_id=user.id,
        )
    except (IdempotencyConflict, IdempotencyInProgress) as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    cached_response = cached_idempotency_response(idempotency)
    if cached_response is not None:
        return SubmissionResponse.model_validate(cached_response)

    session = db.execute(
        select(ParliamentarySession).where(
            ParliamentarySession.id == submission.session_id
        )
    ).scalars().first()
    if not session:
        db.rollback()
        raise HTTPException(status_code=404, detail="Parliamentary session not found")
    if session.status not in {"Active", "Upcoming"}:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Submissions can only be added to active or upcoming sessions",
        )

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
                ranking_score=match.score,
                cosine_similarity=match.score,
            )
            for match in addressed_result.matches
        ]
    )
    if duplicate_result.is_duplicate and not submission.confirm_duplicate:
        check_response = SimilarityCheckResponse(
            possible_duplicate=True,
            threshold=duplicate_result.threshold,
            threshold_version=duplicate_result.threshold_version,
            matches=result_formatter.format(duplicate_result.matches),
            previously_addressed=addressed_matches,
        )
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={
                "code": "possible_duplicate",
                **check_response.model_dump(mode="json"),
            },
        )

    search_text = build_similarity_text(submission.subject, submission.full_text)
    embedding = None
    embedding_model = None
    ai_warnings: list[str] = []
    try:
        embedding = embedding_generator.embed(search_text)
        embedding_model = embedding_generator.model_name
    except RuntimeError:
        ai_warnings.append(
            "Semantic indexing is queued because the AI service is unavailable."
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
        embedding=embedding,
        embedding_model=embedding_model,
    )
    transition_submission(record, SubmissionStatus.UNDER_REVIEW)
    db.add(record)
    try:
        flush_transaction(
            db,
            conflict_message="The submission conflicts with another committed change",
        )
    except DatabaseConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    content_hash = sha256(search_text.encode("utf-8")).hexdigest()
    enqueue_outbox_job(
        db,
        job_type="embed_record",
        payload={
            "record_id": str(record.id),
            "content_hash": content_hash,
            "model": embedding_generator.model_name,
        },
        deduplication_key=(
            f"embed_record:{record.id}:{content_hash}:"
            f"{embedding_generator.model_name}"
        ),
        aggregate_type="parliamentary_record",
        aggregate_id=str(record.id),
        event_type="record.indexing_requested",
    )
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
    candidates = find_previously_addressed_candidates(db, record=record, user=user, limit=5)
    response = SubmissionResponse(
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
        ai_degraded=bool(ai_warnings),
        warnings=ai_warnings,
    )
    complete_idempotency_key(
        idempotency,
        response_status=status.HTTP_201_CREATED,
        response_body=response.model_dump(mode="json"),
        resource_type="parliamentary_record",
        resource_id=str(record.id),
    )
    try:
        commit_transaction(
            db,
            conflict_message="The submission conflicts with another committed change",
        )
    except DatabaseConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return response


@router.post("/{record_id}/submit", response_model=SubmissionRecordOut)
def resubmit_draft(
    record_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ParliamentaryRecord:
    record = db.scalar(
        select(ParliamentaryRecord)
        .where(ParliamentaryRecord.id == record_id)
        .with_for_update()
    )
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
    return record


@router.patch("/{record_id}", response_model=SubmissionRecordOut)
def update_draft(
    record_id: UUID,
    update: SubmissionDraftUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    embedding_generator: EmbeddingGenerator = Depends(get_embedding_generator),
) -> ParliamentaryRecord:
    record = db.scalar(
        select(ParliamentaryRecord)
        .where(ParliamentaryRecord.id == record_id)
        .with_for_update()
    )
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

    if "subject" in changes or "full_text" in changes:
        search_text = build_similarity_text(record.subject, record.full_text)
        try:
            record.embedding = embedding_generator.embed(search_text)
            record.embedding_model = embedding_generator.model_name
        except RuntimeError:
            record.embedding = None
            record.embedding_model = None
        content_hash = sha256(search_text.encode("utf-8")).hexdigest()
        enqueue_outbox_job(
            db,
            job_type="embed_record",
            payload={
                "record_id": str(record.id),
                "content_hash": content_hash,
                "model": embedding_generator.model_name,
            },
            deduplication_key=(
                f"embed_record:{record.id}:{content_hash}:"
                f"{embedding_generator.model_name}"
            ),
            aggregate_type="parliamentary_record",
            aggregate_id=str(record.id),
            event_type="record.indexing_requested",
        )

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
