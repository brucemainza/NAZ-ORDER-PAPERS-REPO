# TDD Implementation and Verification Report

Project: NAZ Order Papers System

Team: CMZ

Report date: 2026-07-24
Branch: `main`

## 1. Outcome

The requested Tailwind migration, configurable permissions foundation, and listed
functional requirements are implemented or explicitly verified with automated
coverage. The application builds, its backend test suite passes, and all defined
browser visual/smoke scenarios pass against the Docker stack.

No listed functional requirement was silently skipped. Product and operational
limits that could not be inferred from the repository, such as an official print
template, are stated in the specification rather than invented.

## 2. What Already Existed

Before this work, the repository already contained:

- Docker Compose services for PostgreSQL/pgvector, FastAPI, and Next.js.
- Employee-ID/password authentication with bcrypt.
- JWT creation, HTTP-only cookie handling, and database-backed session revocation.
- Basic users, sessions, parliamentary records, search logs, review decisions, and
  audit models.
- Session and record-list/detail endpoints.
- BM25 keyword ranking.
- Optional pgvector similarity SQL.
- Initial submission, similarity review, report, and audit endpoints.
- A Next.js App Router UI with dashboard, submission, search, result, reports,
  audit, sessions, and users pages.
- Tailwind-based styling mixed with frontend mock/demo data.
- Seed users, sessions, and historical records.

The pre-change state and gaps are recorded in
[implementation-baseline.md](implementation-baseline.md).

## 3. What Was Changed

### 3.1 Styling

- Established Playwright desktop/mobile visual baselines.
- Migrated all pages, components, controls, responsive rules, and states from
  Tailwind utility classes to plain CSS.
- Removed Tailwind directives, config, dependencies, and class merging.
- Added a source guard that fails if Tailwind is reintroduced.
- Stabilized screenshots with a fixed Playwright browser clock.

### 3.2 Authorization

- Replaced legacy role-name authorization with data-driven Permission, Role,
  role_permissions, and user_roles relationships.
- Seeded Administrator, Clerk, Member of Parliament, and Viewer roles.
- Exposed role and permission arrays to frontend auth state.
- Converted backend guards and frontend conditional navigation/actions to
  permission checks.
- Proved custom roles work without business-logic changes.
- Enforced `view_reports`, `view_audit`, `manage_users`, `schedule_item`,
  submission/review permissions, and archive permissions at API boundaries.

### 3.3 Submission and Review Model

- Replaced legacy record status meanings with the exact seven-state lifecycle.
- Centralized valid state transitions.
- Separated similarity decisions from workflow approval decisions.
- Added submission ownership, draft visibility, editing, and resubmission.
- Added question answer type.
- Added scheduling date.
- Updated seed/runtime compatibility rules for legacy statuses.

## 4. What Was Newly Implemented

- Five-failure account lockout and permission-protected unlock.
- Oral/written question authorization and validation.
- Notice-of-motion authorization.
- Exhaustive required-field API coverage and readable BFF error formatting.
- Clerk review queue.
- Approve, reject, and request-changes workflow history.
- Owned-submission status tracking.
- Exact lifecycle state machine and database constraint.
- Approved-only sitting scheduling.
- Deterministic sitting-date Order Paper JSON.
- Automatic startup archival for ended/closed sessions.
- Independent archive list/detail/search permissions.
- Complete session/date/member/ministry/status/type filters.
- Explicit subject/full-text keyword-search verification.
- Connected the Submissions page to filtered, paginated BM25 ranking with
  full-text match context.
- CSV importer status normalization.
- Topbar date hydration correction.
- Full system specification, architecture diagrams, and file catalog.

## 5. Requirement Disposition

| Requirement | Status | Implemented/verified behavior |
| --- | --- | --- |
| Part A: Tailwind to CSS | Complete | Plain CSS only, source guard, build, and visual baselines. |
| Part B: Configurable RBAC | Complete | Permission/Role/User data model, four seeded roles, custom-role tests, permission guards. |
| FR-001 Login | Verified | Valid succeeds; invalid ID/password fail with identical non-leaking message. |
| FR-002 Roles | Complete | Administrator, Clerk, Member of Parliament, Viewer seeded as configurable data. |
| FR-003 Lockout | Complete | Fifth failure locks; correct password remains rejected; administrator unlock restores access. |
| FR-005 Questions | Complete | Oral/written questions, permission checks, persistence. |
| FR-006 Motions | Complete | Notice-of-motion creation and permission checks. |
| FR-007 Validation | Complete | Existing required schema fields exhaustively tested and normalized. |
| FR-009 Clerk queue | Complete | New items reach Under Review and permission-protected oldest-first queue. |
| FR-010 Review actions | Complete | Approve, reject, request changes; separate action permissions and history. |
| FR-019 Status tracking | Complete | `/submissions/mine`, owner visibility, non-owner draft protection. |
| FR-020 Status set | Complete | Exact seven values, transition graph, invalid jump rejection. |
| FR-022 Scheduling | Complete | Approved-only, permission-protected, sitting date stored, status Scheduled. |
| FR-023 Order Paper | Complete with format caveat | Exact-date scheduled items, Questions/Motions grouping, stable order, JSON output. |
| FR-025 Auto-archive | Complete with operational caveat | Startup archives closed/date-ended sessions idempotently; active sessions untouched. |
| FR-026 Archive access | Complete | `view_archive` for list/detail and `search_archive` for keyword results. |
| FR-028 Keyword search | Complete | The visible Submissions page uses BM25 for usable keywords; subject/full-text matches, filters, pagination, scores, and matched terms are verified. |
| FR-029 Filters | Complete | Session/date/member/ministry/status/type independent and combined behavior. |

## 6. TDD Evidence

Feature work followed red-green verification:

- missing endpoint tests returned `404` before implementation;
- missing service imports failed collection before service creation;
- permissionless custom roles exposed access before guards were added;
- missing filters returned unfiltered rows before query clauses were added;
- frontend source guards failed before BFF routes/controls existed;
- hydration and clock guards failed before deterministic rendering fixes; and
- focused tests were followed by full-suite checks before commits.

Representative atomic commits:

| Commit | Change |
| --- | --- |
| `3366625` | Configurable permissions RBAC. |
| `9f9a92f` | Tailwind removal. |
| `2fa1c16` | FR-003 lockout. |
| `d956fdd` | FR-005 questions. |
| `984f9ef` | FR-006 motions. |
| `de9c599` | FR-007 validation. |
| `8fab65b` | FR-009 review queue. |
| `25b3a1d` | FR-010 workflow actions. |
| `33d6bce` | FR-019 ownership. |
| `3e9b545` | FR-020 lifecycle. |
| `54f99dc` | FR-022 scheduling. |
| `2ac726e` | FR-023 Order Paper. |
| `6d861e6` | FR-025 archival. |
| `b24bd17` | FR-026 archive access. |
| `f968aaf` | FR-028 verification. |
| `b21993f` | FR-029 filters. |
| `d875028` | Hydration correction. |
| `525b0c6` | Report permission enforcement. |
| `1497074` | Import status normalization. |
| `416d2bf` | MP dashboard reporting integration. |
| `b9bafc5` | Deterministic visual test clock. |

## 7. Final Verification

### 7.1 Backend

Command:

```bash
PYTHONPATH=backend .venv/bin/pytest -q backend/tests
```

Result:

- 83 tests passed.
- No failures.
- Warnings are framework/runtime deprecations, primarily FastAPI/Starlette
  coroutine detection under Python 3.14 and the legacy FastAPI startup hook.

### 7.2 Frontend source guards

Command:

```bash
cd frontend
npm run test:source
```

Result:

- 17 source tests passed.
- No failures.

### 7.3 Production build

Command:

```bash
cd frontend
npm run build
```

Result:

- Next.js production compilation succeeded.
- Lint/type checking succeeded.
- All page and API routes were generated.

### 7.4 Browser E2E and visual tests

Command:

```bash
cd frontend
npm run test:e2e
```

Result:

- 11 Playwright scenarios passed against the approved snapshots.
- Covered login desktop/mobile, dashboard, submit, search, reports, sessions,
  users, result detail, audit, mobile dashboard, and a content-only BM25 match.
- Authenticated tests use a fixed browser time to prevent daily snapshot drift.

### 7.5 Docker smoke

Verified services:

- PostgreSQL health check;
- FastAPI health endpoint;
- Next.js login route;
- frontend-to-backend authenticated behavior; and
- live runtime schema compatibility.

## 8. Deliberate Non-Implementations

### 8.1 Official print/PDF format

No official Order Paper template or sample was in the repository. The implementation
therefore generates a deterministic structured document and does not invent
procedural headings, typography, numbering, or publication signatures.

### 8.2 Persistent user/session management screens

The existing users and sessions pages remain demonstrative local-state interfaces.
Building full CRUD was not part of the listed FR acceptance criteria. The backend
currently supports account unlock and session listing.

### 8.3 Continuous scheduler

Archiving runs automatically at API startup. No worker/scheduler dependency was
introduced because the repository had no background-job infrastructure. A
production deployment should schedule a daily restart/job or add a supported
worker.

## 9. Residual Risks

- The development JWT fallback must be replaced in production.
- A versioned migration tool should replace runtime compatibility DDL before
  controlled production releases.
- `/sessions` is publicly readable at the backend API.
- No rate limiting, MFA, password reset, or CSRF token framework is present.
- No embedding generation pipeline populates `vector(384)`.
- No backup/restore, retention, or disaster-recovery policy is encoded in this
  repository.
- Frontend `lib/db.js`, empty type placeholders, and mock data are retained legacy
  artifacts and can be removed after persistent admin UI work is designed.

## 10. Documentation Set

- [System specification](system-specification.md)
- [Graphical system architecture](system-architecture.md)
- [File-by-file guide](file-guide.md)
- [Visual regression checklist](visual-regression-checklist.md)
- [Original implementation baseline](implementation-baseline.md)
