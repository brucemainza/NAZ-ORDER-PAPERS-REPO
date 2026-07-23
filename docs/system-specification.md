# NAZ Order Papers System Specification

Document status: Implemented system baseline

System owner: National Assembly of Zambia

Implementation team: Team CMZ
Specification date: 2026-07-23

## 1. Purpose

The NAZ Order Papers System is an internal parliamentary records application for:

- authenticating authorized staff;
- recording questions and notices of motion;
- validating and reviewing submissions;
- detecting potentially repeated parliamentary matters;
- approving, rejecting, returning, and scheduling submissions;
- generating a structured Order Paper for a sitting date;
- retaining and searching historical records;
- reporting operational activity; and
- maintaining an auditable history of important actions.

The system is a browser application backed by a JSON API and PostgreSQL database.
It is not a public parliamentary website.

## 2. Scope

### 2.1 In scope

- Employee-ID and password authentication.
- Revocable eight-hour user sessions.
- Account lockout after five failed logins and administrator unlock.
- Configurable permission-based RBAC.
- Question submission for oral or written answer.
- Notice-of-motion submission.
- Submission ownership and draft recovery.
- Clerk review queue and workflow decisions.
- Duplicate/similarity review decisions.
- Sitting-date scheduling.
- Structured JSON Order Paper generation.
- Session-end archival.
- Archive access controls.
- Keyword search and record filtering.
- Operational reports and audit trail.
- Docker-based local deployment.

### 2.2 Outside the implemented scope

- Official typeset or PDF Order Paper publication.
- Electronic signatures.
- Email/SMS notifications.
- Password reset or user-driven password change.
- A persistent user/session administration CRUD API.
- A persistent parliamentary-session administration CRUD API.
- Automatic embedding generation.
- Production-grade migrations managed by Alembic or another migration framework.
- High-availability, backup, disaster-recovery, and external identity-provider setup.

## 3. Actors

| Actor | Primary responsibilities |
| --- | --- |
| Administrator | Full platform administration, audit, reporting, review, scheduling, role management, and account unlock. |
| Clerk | Reviews submitted items, records similarity decisions, approves/rejects/returns items, schedules approved items, manages sessions, and accesses reports/audit/archive. |
| Member of Parliament | Submits questions and motions, edits returned drafts, tracks owned submissions, and reads reports/archive. |
| Viewer | Read-only reports and archive access. |
| System process | Seeds RBAC data, applies compatibility schema changes, archives ended sessions at startup, and records system data. |

Roles are data records. Business logic authorizes atomic permission codes, not role
name strings. A custom role can be introduced or changed without altering route
logic.

## 4. Permissions

### 4.1 Atomic permissions

| Permission | Meaning |
| --- | --- |
| `submit_question` | Create and resubmit questions. |
| `submit_motion` | Create and resubmit notices of motion. |
| `review_submission` | See the Clerk review queue and similarity decision history. |
| `approve_motion` | Approve a submission in workflow review. |
| `reject_submission` | Reject a submission in workflow review. |
| `request_changes` | Return a submission to its owner as an editable draft. |
| `schedule_item` | Assign an approved item to a sitting date. |
| `view_reports` | Read aggregate operational reports. |
| `view_audit` | Read and filter the audit trail. |
| `manage_users` | Perform account-management operations such as unlock. |
| `manage_roles` | Manage role/permission configuration in principle. |
| `manage_sessions` | Access session-management functions. |
| `search_archive` | Include archived records in keyword search. |
| `view_archive` | List and open archived records. |

### 4.2 Default role matrix

| Permission | Administrator | Clerk | Member of Parliament | Viewer |
| --- | :---: | :---: | :---: | :---: |
| `submit_question` | Yes | No | Yes | No |
| `submit_motion` | Yes | No | Yes | No |
| `review_submission` | Yes | Yes | No | No |
| `approve_motion` | Yes | Yes | No | No |
| `reject_submission` | Yes | Yes | No | No |
| `request_changes` | Yes | Yes | No | No |
| `schedule_item` | Yes | Yes | No | No |
| `view_reports` | Yes | Yes | Yes | Yes |
| `view_audit` | Yes | Yes | No | No |
| `manage_users` | Yes | No | No | No |
| `manage_roles` | Yes | No | No | No |
| `manage_sessions` | Yes | Yes | No | No |
| `search_archive` | Yes | Yes | Yes | Yes |
| `view_archive` | Yes | Yes | Yes | Yes |

The legacy `users.role` field remains for compatibility. Runtime authorization uses
the many-to-many `users -> roles -> permissions` relationships.

## 5. Authentication Specification

### 5.1 Login

1. The user enters an employee ID and password.
2. The Next.js login route validates the payload.
3. FastAPI normalizes the employee ID to uppercase.
4. FastAPI finds an active, unlocked account.
5. bcrypt verifies the password hash using cost factor 12.
6. On success, failed-attempt state is reset and last-login time is updated.
7. FastAPI issues an HS256 JWT with an expiry, issue time, and unique `jti`.
8. A matching `user_sessions` row is persisted.
9. Next.js stores the JWT in the `naz_token` HTTP-only cookie.

Invalid user IDs and invalid passwords return the same message:
`Invalid employee ID or password.` This prevents account enumeration.

### 5.2 Lockout

- Failed passwords increment `failed_login_attempts`.
- The fifth failure sets `locked_at`.
- A locked account rejects a correct password with the same generic credential
  message.
- A user with `manage_users` can call the unlock endpoint.
- Unlock resets the failure count and clears `locked_at`.

### 5.3 Session validation

- JWT lifetime is eight hours.
- Browser middleware validates signature/expiry before protected navigation.
- Backend protected routes validate the JWT and a non-revoked, non-expired
  `user_sessions` row.
- Logout marks the row revoked and clears the browser cookie.
- The cookie is HTTP-only, `SameSite=Lax`, path `/`, and `Secure` in production.

## 6. Submission Specification

### 6.1 Question input

Required:

- item type `Question`;
- parliamentary session;
- member name, 3 to 255 characters;
- ministry/department;
- answer type `Oral` or `Written`;
- subject, 5 to 500 characters; and
- full text, at least 40 characters.

The caller must hold `submit_question`.

### 6.2 Motion input

Required:

- item type `Motion`;
- parliamentary session;
- member name, 3 to 255 characters;
- subject, 5 to 500 characters; and
- full text, at least 40 characters.

Motions do not accept an answer type. Ministry is optional. The caller must hold
`submit_motion`.

### 6.3 Session eligibility

New submissions can target only sessions with status `Active` or `Upcoming`.
Unknown sessions return `404`; closed sessions reject new submissions.

### 6.4 Initial processing

A valid new item is persisted with its owner and enters `Submitted`, then
immediately transitions through the state service to `Under Review`. The response
also contains up to five previously addressed candidates.

## 7. Status Lifecycle

The database and application support exactly:

1. `Draft`
2. `Submitted`
3. `Under Review`
4. `Approved`
5. `Rejected`
6. `Scheduled`
7. `Archived`

Allowed transitions:

| From | Allowed next states |
| --- | --- |
| `Draft` | `Submitted`, `Archived` |
| `Submitted` | `Under Review`, `Archived` |
| `Under Review` | `Draft`, `Approved`, `Rejected`, `Archived` |
| `Approved` | `Scheduled`, `Archived` |
| `Rejected` | `Archived` |
| `Scheduled` | `Archived` |
| `Archived` | None |

All normal production status changes use the centralized transition service.
Invalid jumps return conflict status `409`.

## 8. Ownership and Visibility

- `GET /submissions/mine` returns only records owned by the authenticated user.
- Drafts are visible to their owner and users with `review_submission`.
- Other users cannot open or discover another owner's draft.
- Only the owner can edit or resubmit a returned draft.
- Only a record in `Draft` can be edited.
- Draft edits revalidate question/motion-specific rules.
- Archived records are omitted from ordinary lists unless the user has
  `view_archive`.
- Direct archived detail returns `403` without `view_archive`.
- Archived records are omitted from keyword search unless the user has
  `search_archive`.

Unauthorized list/search queries hide restricted rows rather than revealing that
they exist.

## 9. Review Specification

### 9.1 Clerk queue

`GET /submissions/review-queue`:

- requires `review_submission`;
- contains only `Under Review` items; and
- orders oldest submissions first.

### 9.2 Workflow decisions

| Action | Required permission | Resulting status |
| --- | --- | --- |
| Approve | `approve_motion` | `Approved` |
| Reject | `reject_submission` | `Rejected` |
| Request Changes | `request_changes` | `Draft` |

Each action creates a `workflow_decisions` row and an audit event. State-machine
rules still apply.

### 9.3 Similarity decisions

Similarity review is separate from workflow approval. A user with
`review_submission` can record:

- `Clear (New)`;
- `Duplicate`; or
- `Substantially Similar`.

Duplicate and substantially-similar decisions set `is_duplicate=true` on the
decision record. They do not directly mutate the parliamentary record's workflow
status.

## 10. Search and Similarity

### 10.1 Record browsing

`GET /records` supports:

- `session_id`: exact UUID;
- `date`: exact calendar date of `created_at`;
- `member`: case-insensitive partial text;
- `ministry`: case-insensitive partial text;
- `status`: case-insensitive lifecycle status;
- `item_type`: case-insensitive `Question` or `Motion`;
- `query_text`: case-insensitive partial match across subject, member, ministry,
  and full text;
- `limit`: 1 to 100; and
- `offset`: non-negative.

Filters are combined with logical AND. Contradictory filters return an empty list,
not an error.

### 10.2 Keyword search

`POST /search` performs in-process BM25 ranking over:

- subject;
- full text;
- member; and
- ministry.

Archive/draft visibility and optional session, date, member, ministry, status, and
item-type filters are applied before BM25 scoring. The complete eligible result
set is ranked first and then paginated with `offset` and `limit`, preserving stable
rank numbers across pages. The response distinguishes filtered candidates from
positive-score results.

Search is case-insensitive, strips punctuation, ignores tokens shorter than three
characters, excludes zero-score rows, normalizes the best score to 100, and returns
each record's full text, rank, score, and matched terms. Searches and returned
result IDs are logged.

The Submissions page sends trimmed keywords of at least three characters to the
BM25 endpoint through `POST /api/search`. It displays relevance, matched terms,
and expandable full-text context. Blank, one-character, two-character, and
filter-only requests continue to use `GET /records` for deterministic SQL
browsing.

### 10.3 Similarity candidates

For a submitted or selected record:

1. BM25 ranks non-draft historical candidates.
2. If source and candidate embeddings exist, pgvector cosine distance adds vector
   candidates.
3. Results are merged by record ID.
4. The higher score is retained for duplicate candidates.
5. A vector query failure falls back to BM25 rather than failing submission.

Seed data does not currently contain generated embeddings, so BM25 is the normal
active path.

## 11. Scheduling and Order Papers

### 11.1 Scheduling

- Requires `schedule_item`.
- Only an `Approved` record can be scheduled.
- The request records a required sitting date.
- Success transitions the item to `Scheduled`.
- Rescheduling a scheduled item through the same transition is rejected.

### 11.2 Generated Order Paper

`GET /order-papers/{sitting_date}` returns a deterministic structured document:

- title `NATIONAL ASSEMBLY OF ZAMBIA ORDER PAPER`;
- requested sitting date;
- total item count;
- a `QUESTIONS` section; and
- a `NOTICES OF MOTION` section.

Only records with status `Scheduled` and the exact sitting date are included.
Within each section, records are ordered by `created_at`, then UUID to break ties.
Both sections are present even when empty.

The current output is JSON. No official print/PDF template was present in the
repository, so print typography, numbering, procedural headings, and publication
approval are not specified or implemented.

## 12. Archiving

At API startup, the system archives every non-archived record belonging to a
session that:

- has `end_date` before the current date; or
- is marked `Closed`.

The operation:

- uses the normal status state machine;
- handles records in any non-archived lifecycle state;
- is idempotent; and
- leaves current/future active sessions untouched.

Operational limitation: the check runs at process startup. A continuously running
instance that crosses a session end date needs a restart or an external scheduled
restart/job to invoke the startup process.

## 13. Reports and Audit

### 13.1 Reports

`GET /reports` requires `view_reports` and returns:

- submissions by session;
- question and motion counts;
- under-review and duplicate counts;
- similarity match rate by review date;
- top member activity; and
- top ministry/department activity.

Reading reports writes a `report_access` audit event.

### 13.2 Audit

`GET /audit` requires `view_audit` and supports:

- partial user-name filter;
- partial action filter;
- entity ID/detail filter; and
- a 1 to 500 row limit.

The frontend can export the returned rows to CSV. Reading the audit trail itself
creates an `audit_read` event.

Audited actions include login, logout, unlock, submission, draft update,
resubmission, workflow review, scheduling, similarity decision, search, record
retrieval, report access, and audit access.

## 14. API Contract

All backend paths are relative to the FastAPI service.

| Method | Path | Authentication/permission | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | Public | Liveness response. |
| `POST` | `/auth/login` | Public | Authenticate and issue JWT. |
| `GET` | `/auth/me` | JWT session | Return current user, roles, and permissions. |
| `POST` | `/auth/logout` | Optional JWT | Revoke current session when present. |
| `POST` | `/users/{user_id}/unlock` | `manage_users` | Unlock an account. |
| `GET` | `/sessions` | Public backend route | List sessions newest first. |
| `POST` | `/submissions` | Item-specific submit permission | Create and queue an item. |
| `GET` | `/submissions/mine` | Authenticated | List owned submissions. |
| `GET` | `/submissions/review-queue` | `review_submission` | List review queue. |
| `PATCH` | `/submissions/{record_id}` | Owner plus submit permission | Edit draft. |
| `POST` | `/submissions/{record_id}/submit` | Owner plus submit permission | Resubmit draft. |
| `POST` | `/submissions/{record_id}/workflow-review` | Action-specific permission | Approve, reject, or return. |
| `POST` | `/submissions/{record_id}/schedule` | `schedule_item` | Schedule approved item. |
| `GET` | `/records` | Authenticated plus row visibility | Browse/filter records. |
| `GET` | `/records/{record_id}` | Authenticated plus row visibility | Read detail and audit access. |
| `GET` | `/records/{record_id}/similar` | Authenticated plus row visibility | Find related records. |
| `GET` | `/records/{record_id}/reviews` | `review_submission` | List similarity decisions. |
| `POST` | `/records/{record_id}/reviews` | `review_submission` | Record similarity decision. |
| `POST` | `/search` | Authenticated plus archive visibility | BM25 keyword search. |
| `GET` | `/order-papers/{sitting_date}` | Authenticated | Generate sitting Order Paper. |
| `GET` | `/reports` | `view_reports` | Aggregate reports. |
| `GET` | `/audit` | `view_audit` | Filtered audit trail. |

FastAPI also exposes `/openapi.json`, `/docs`, and `/redoc`.

## 15. Data Specification

### 15.1 Core entities

| Entity | Important fields | Purpose |
| --- | --- | --- |
| Permission | code, description | Atomic capability. |
| Role | name, description | Configurable permission collection. |
| User | employee ID, name, compatibility role, status, password hash, lock state | Staff identity. |
| UserSession | user, JTI, issue/expiry/revocation, IP, user agent | Revocable JWT session. |
| ParliamentarySession | code, name, start/end dates, status | Assembly/session boundary. |
| ParliamentaryRecord | type, session, member, ministry, answer type, subject, text, owner, status, sitting date, embedding | Question/motion record. |
| SearchLog | query, optional session, result IDs | Search history. |
| ReviewDecision | source/related records, decision, duplicate flag, reviewer, notes | Similarity decision. |
| WorkflowDecision | record, action, reviewer, notes | Approval workflow history. |
| AuditLog | actor, action, entity, details, IP, timestamp | Accountability trail. |

### 15.2 Database constraints

- PostgreSQL UUID primary keys.
- Unique permission code, role name, employee ID, session code, and session JTI.
- Session status: `Active`, `Closed`, or `Upcoming`.
- Record type: `Question` or `Motion`.
- Answer type: `Oral` or `Written` when present.
- Record status restricted to the seven lifecycle values.
- Review and workflow actions restricted to supported values in first-run SQL.
- `vector(384)` embedding storage and cosine IVFFlat index.

## 16. Error Behavior

| HTTP status | Meaning |
| --- | --- |
| `400` | Business input rejected, such as a closed target session. |
| `401` | Missing, invalid, expired, revoked, inactive, locked, or bad credentials. |
| `403` | Authenticated but lacks permission/ownership/row visibility. |
| `404` | Requested user, session, record, or related record does not exist. |
| `409` | Invalid lifecycle operation or edit in the wrong state. |
| `422` | Schema or field validation failure. |
| `502` | Next.js BFF cannot reach FastAPI. |

The BFF converts structured FastAPI validation errors into readable `message`
strings for browser clients.

## 17. Frontend Specification

### 17.1 Routes

| Route | Function |
| --- | --- |
| `/login` | Employee-ID/password login. |
| `/dashboard` | Aggregate counts and recent activity. |
| `/submit` | Permission-aware question/motion form. |
| `/search` | Browse and filter submissions. |
| `/results/{id}` | Record detail, similarity, review, draft recovery, and scheduling actions. |
| `/sessions` | Permission-gated demonstrative session management UI. |
| `/users` | Permission-gated demonstrative user management UI. |
| `/audit` | Audit filters, table, and CSV export. |
| `/reports` | Aggregate operational tables. |

### 17.2 BFF behavior

Browser components call same-origin `/api/*` routes. The Next.js BFF reads the
HTTP-only cookie server-side, forwards it as a Bearer token, and returns normalized
JSON errors. Browser JavaScript never needs to read the JWT.

### 17.3 Styling

- Plain CSS only.
- No Tailwind dependency, directives, config, or runtime class merger.
- Responsive desktop/mobile layouts.
- Shared CSS variables and component classes in `globals.css`.
- Playwright pixel snapshots protect current appearance.

## 18. Runtime and Deployment

Docker Compose starts:

| Service | Container port | Host port | Purpose |
| --- | ---: | ---: | --- |
| PostgreSQL/pgvector | 5432 | 5433 | Persistent relational/vector data. |
| FastAPI | 8000 | 8080 | Business API and OpenAPI docs. |
| Next.js | 3000 | 3000 | Browser UI and BFF. |
| Portainer | 9000/8000 | 9000/9001 | Local container administration. |

Database schema and seed SQL run when a new PostgreSQL volume is initialized.
FastAPI startup also applies idempotent compatibility DDL, seeds default RBAC, maps
legacy roles, and archives ended-session records.

Required production configuration:

- change `JWT_SECRET`;
- provide `DATABASE_URL`;
- set `FRONTEND_ORIGIN`;
- set `BACKEND_INTERNAL_URL` for the BFF;
- use HTTPS so the auth cookie is secure; and
- establish backup/restore and migration processes.

## 19. Quality and Verification

Automated verification consists of:

- isolated PostgreSQL-backed pytest API tests;
- Node source-level architecture/feature guards;
- Next.js production compilation;
- Playwright authenticated end-to-end visual tests;
- Docker health and HTTP smoke checks; and
- Git whitespace/diff validation.

See [implementation-report.md](implementation-report.md) for the final results and
[system-architecture.md](system-architecture.md) for graphical views.

## 20. Known Limitations and Risks

- Order Paper output is structured JSON, not an official publication artifact.
- Archival is startup-triggered rather than continuously scheduled.
- User and session management pages mutate local mock state; only account unlock
  and session listing have corresponding backend APIs.
- `manage_roles` is modeled and seeded, but no role-management API/UI is present.
- Embedding generation is absent, so pgvector generally has no vectors to compare.
- Runtime compatibility DDL is practical for this codebase but not a substitute
  for versioned production migrations.
- Backend `/sessions` is public even though the dashboard page is protected.
- API rate limiting, CSRF tokens, MFA, password reset, and centralized security
  monitoring are not implemented.
- The default JWT fallback secret is suitable only for local development.
- FastAPI startup hooks emit deprecation warnings and should eventually migrate to
  lifespan handlers.
