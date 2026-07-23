# NAZ Order Papers File-by-File Guide

This guide covers every tracked file in the repository. Generated runtime folders
such as `.git`, `.next`, `node_modules`, `.venv`, caches, Playwright results, and
local `.env` files are intentionally not tracked and are not application source.

## 1. Repository Root

| File | Responsibility |
| --- | --- |
| `.gitignore` | Excludes dependencies, builds, local secrets, virtual environments, caches, logs, and test artifacts. |
| `.vscode/settings.json` | Legacy workspace test-runner preferences for VS Code. Command-line pytest is the authoritative backend test path. |
| `README.md` | Primary setup, service, credential, testing, architecture, and documentation entry point. |
| `docker-compose.yml` | Defines PostgreSQL/pgvector, FastAPI, Next.js, Portainer, networking, ports, mounts, health checks, and persistent volumes. |
| `pyrightconfig.json` | Configures Python static-analysis roots, virtual environment, exclusions, and Python version. |

## 2. Documentation

| File | Responsibility |
| --- | --- |
| `docs/implementation-baseline.md` | Pre-change assessment of styling, RBAC, functional requirements, tests, and implementation gaps. |
| `docs/visual-regression-checklist.md` | Manual/automated visual checks used during Tailwind-to-plain-CSS migration. |
| `docs/system-specification.md` | Normative functional, security, data, API, operational, and limitation specification. |
| `docs/system-architecture.md` | Graphical Mermaid architecture, workflow, state, data, and deployment diagrams. |
| `docs/file-guide.md` | This exhaustive source and artifact catalog. |
| `docs/implementation-report.md` | Final requirement disposition, change summary, verification results, and residual risks. |

## 3. Backend Packaging and Configuration

| File | Responsibility |
| --- | --- |
| `backend/.dockerignore` | Keeps local caches, virtual environments, and irrelevant files out of the backend image context. |
| `backend/Dockerfile` | Builds the Python image, installs requirements, copies source, and starts Uvicorn. |
| `backend/README.md` | Backend-specific local setup and endpoint notes. |
| `backend/requirements.txt` | Pins FastAPI, Uvicorn, SQLAlchemy, psycopg, dotenv, bcrypt, and PyJWT runtime dependencies. |
| `backend/requirements-dev.txt` | Extends runtime requirements with pytest and HTTPX for API testing. |

## 4. Backend Application Core

| File | Responsibility |
| --- | --- |
| `backend/app/config.py` | Loads environment variables and provides cached database/CORS settings. |
| `backend/app/database.py` | Creates the SQLAlchemy engine, session factory, declarative base, and request-scoped DB dependency. |
| `backend/app/db_compat.py` | Applies idempotent compatibility DDL, maps legacy statuses/columns, seeds RBAC, and assigns legacy users to data roles. |
| `backend/app/deps.py` | Implements current-user resolution, revocable-session validation, permission dependencies, request IP extraction, and audit-row creation. |
| `backend/app/main.py` | Creates FastAPI, configures CORS, registers every router, runs schema compatibility, seeds data, and triggers archival at startup. |

## 5. Backend Authentication Library

| File | Responsibility |
| --- | --- |
| `backend/app/lib/__init__.py` | Marks the authentication helper package. |
| `backend/app/lib/auth.py` | Hashes/verifies bcrypt passwords and creates/verifies eight-hour HS256 JWTs with JTI claims. |

## 6. Backend Models

| File | Responsibility |
| --- | --- |
| `backend/app/models/__init__.py` | Re-exports ORM models for concise imports elsewhere. |
| `backend/app/models/models.py` | Defines Permission, Role, User, UserSession, ParliamentarySession, ParliamentaryRecord, SearchLog, ReviewDecision, WorkflowDecision, AuditLog, and RBAC join tables. |

## 7. Backend Retrieval

| File | Responsibility |
| --- | --- |
| `backend/app/retrieval/__init__.py` | Marks the retrieval package. |
| `backend/app/retrieval/bm25.py` | Tokenizes searchable text, computes BM25 relevance, records matched terms, sorts, limits, and normalizes scores. |

## 8. Backend Routers

| File | Responsibility |
| --- | --- |
| `backend/app/routers/__init__.py` | Imports all router modules for registration in the application. |
| `backend/app/routers/health.py` | Public `GET /health` liveness endpoint. |
| `backend/app/routers/auth.py` | Login, generic credential errors, five-attempt lockout, JWT/session creation, current-user lookup, logout, revocation, and auth audit events. |
| `backend/app/routers/users.py` | Permission-protected administrator account unlock endpoint. |
| `backend/app/routers/sessions.py` | Lists parliamentary sessions newest first. |
| `backend/app/routers/submissions.py` | Creates questions/motions, exposes owner tracking and Clerk queue, edits returned drafts, and resubmits drafts. |
| `backend/app/routers/workflow_reviews.py` | Applies Approve, Reject, and Request Changes actions with action-specific permissions and workflow history. |
| `backend/app/routers/scheduling.py` | Schedules approved records for a sitting date with state validation and audit. |
| `backend/app/routers/order_papers.py` | Generates deterministic sitting-date Order Paper JSON grouped into Questions and Notices of Motion. |
| `backend/app/routers/records.py` | Lists, filters, paginates, retrieves, and similarity-checks records while enforcing draft/archive visibility. |
| `backend/app/routers/search.py` | Runs permission-aware BM25 keyword search and records search/audit logs. |
| `backend/app/routers/reviews.py` | Lists and records similarity/duplicate decisions separately from workflow status. |
| `backend/app/routers/reports.py` | Produces permission-protected session, match-rate, member, and department aggregates. |
| `backend/app/routers/audit.py` | Returns permission-protected, filterable audit history and audits audit-trail access. |

## 9. Backend Schemas

| File | Responsibility |
| --- | --- |
| `backend/app/schemas/__init__.py` | Marks the Pydantic schema package. |
| `backend/app/schemas/auth.py` | Login request, current-user output, and login response contracts. |
| `backend/app/schemas/session.py` | Parliamentary session output contract. |
| `backend/app/schemas/submission.py` | Create/edit/schedule validation plus record and similarity-bearing submission responses. |
| `backend/app/schemas/record.py` | Record list/detail serialization including session name and sitting date. |
| `backend/app/schemas/search.py` | BM25 request, record, ranked result, and response contracts. |
| `backend/app/schemas/review.py` | Similarity decision and workflow-review request/response validation. |
| `backend/app/schemas/order_paper.py` | Order Paper document and section response contracts. |
| `backend/app/schemas/report.py` | Session, match-rate, activity, and complete report response contracts. |
| `backend/app/schemas/audit.py` | Audit-log output contract with optional actor and entity metadata. |

## 10. Backend Services

| File | Responsibility |
| --- | --- |
| `backend/app/services/__init__.py` | Marks the domain-service package. |
| `backend/app/services/permissions.py` | Defines atomic capabilities, default role matrices, data seeding, legacy role mapping, and custom-role-compatible authorization data. |
| `backend/app/services/submission_status.py` | Defines the exact seven statuses, transition graph, transition validation, and status mutation boundary. |
| `backend/app/services/record_visibility.py` | Centralizes draft ownership, reviewer visibility, archive listing/search permissions, and direct detail visibility. |
| `backend/app/services/similarity.py` | Combines BM25 and optional pgvector matches, deduplicates candidates, and falls back safely when vector search is unavailable. |
| `backend/app/services/archiving.py` | Idempotently moves records from ended/closed sessions to Archived through the status service. |

## 11. Backend Database and Data Tools

| File | Responsibility |
| --- | --- |
| `backend/db/schema.sql` | First-volume PostgreSQL schema, constraints, pgcrypto/pgvector extensions, foreign keys, and indexes. |
| `backend/db/seed.sql` | Initial permissions, default roles, role mappings, users, sessions, and sample parliamentary records. |
| `backend/scripts/ingest_csv.py` | Command-line CSV importer that maps session codes and normalizes legacy/blank statuses to supported lifecycle values. |

## 12. Backend Tests

| File | Responsibility |
| --- | --- |
| `backend/tests/conftest.py` | Creates the isolated PostgreSQL test database, rebuilds schema per test, overrides request DB sessions, and exposes TestClient fixtures. |
| `backend/tests/test_health.py` | Verifies API liveness. |
| `backend/tests/test_authentication.py` | Verifies valid login, invalid ID/password behavior, and non-leaking messages. |
| `backend/tests/test_account_lockout.py` | Covers four/five failures, locked correct-password rejection, permission-protected unlock, and post-unlock login. |
| `backend/tests/test_permissions.py` | Covers default role seeding, inheritance, custom roles, and route-level permission checks. |
| `backend/tests/test_report_permissions.py` | Verifies report permission enforcement and MP dashboard-report capability. |
| `backend/tests/test_question_submissions.py` | Covers oral/written questions and `submit_question` authorization. |
| `backend/tests/test_motion_submissions.py` | Covers notice-of-motion creation and `submit_motion` authorization. |
| `backend/tests/test_submission_validation.py` | Exercises every required field, type-specific validation, trimming, and clear errors. |
| `backend/tests/test_review_queue.py` | Verifies Under Review routing, queue contents/order, and Clerk permission. |
| `backend/tests/test_workflow_reviews.py` | Covers approve/reject/request changes, permission separation, history, and invalid transitions. |
| `backend/tests/test_submission_ownership.py` | Covers owned submission tracking, non-owner draft hiding, and owner detail. |
| `backend/tests/test_submission_status.py` | Verifies exact lifecycle values, transition graph, draft edit/resubmit, and rejected invalid jumps. |
| `backend/tests/test_scheduling.py` | Covers approved-only scheduling, sitting date persistence, permission checks, and conflict behavior. |
| `backend/tests/test_order_papers.py` | Verifies exact sitting membership, fixed grouping, deterministic order, and empty documents. |
| `backend/tests/test_auto_archiving.py` | Covers ended/closed session archival, active-session preservation, idempotency, and startup triggering. |
| `backend/tests/test_archive_access.py` | Verifies independent `view_archive` and `search_archive` behavior using custom roles. |
| `backend/tests/test_keyword_search.py` | Proves subject/full-text keyword matches and clear non-match exclusion. |
| `backend/tests/test_record_filters.py` | Covers each required filter, combined filters, and contradictory empty results. |
| `backend/tests/test_csv_ingestion.py` | Verifies CSV lifecycle-status normalization. |

## 13. Frontend Packaging and Configuration

| File | Responsibility |
| --- | --- |
| `frontend/.dockerignore` | Reduces frontend Docker build context. |
| `frontend/.env.local.example` | Documents local frontend/backend/JWT/database environment values. |
| `frontend/Dockerfile` | Builds the Node image, installs packages, copies source, and defines the frontend runtime. |
| `frontend/package.json` | Declares Next/React runtime packages, source/build/Playwright scripts, and development dependencies. |
| `frontend/package-lock.json` | Reproducibly locks the full npm dependency graph. |
| `frontend/jsconfig.json` | Configures `@/*` imports to resolve from `src`. |
| `frontend/next.config.js` | Enables React strict mode. |
| `frontend/postcss.config.js` | Runs Autoprefixer only; Tailwind is fully removed. |
| `frontend/playwright.config.js` | Configures serial Chrome E2E tests, Lusaka locale/timezone, screenshots, traces, and development web server. |

## 14. Frontend Public Assets

| File | Responsibility |
| --- | --- |
| `frontend/public/naz.jpg` | National Assembly image asset retained for the UI/public asset set. |
| `frontend/public/naz_logo2.jpg` | Alternate National Assembly logo asset retained for the UI/public asset set. |

## 15. Frontend App Shell and Pages

| File | Responsibility |
| --- | --- |
| `frontend/src/app/layout.jsx` | Root HTML metadata, global CSS import, and AuthProvider wrapper. |
| `frontend/src/app/page.jsx` | Redirects the root path to dashboard or login based on the auth cookie. |
| `frontend/src/app/globals.css` | Entire plain-CSS design system, page layouts, states, responsive rules, and migrated component styling. |
| `frontend/src/app/(auth)/login/page.jsx` | Public login route and LoginForm composition. |
| `frontend/src/app/(dashboard)/layout.jsx` | Server-validates the backend session and composes protected Sidebar/Topbar/main layout. |
| `frontend/src/app/(dashboard)/dashboard/page.jsx` | Loads reports, records, sessions, aggregate cards, and recent activity. |
| `frontend/src/app/(dashboard)/submit/page.jsx` | Loads sessions, derives permitted item types, and renders the submission form or access states. |
| `frontend/src/app/(dashboard)/search/page.jsx` | Paginates and filters record browsing by text/session/date/member/ministry/status/type. |
| `frontend/src/app/(dashboard)/results/[id]/page.jsx` | Loads record/similarity/history and provides similarity decisions, workflow actions, draft recovery, and scheduling controls. |
| `frontend/src/app/(dashboard)/reports/page.jsx` | Renders summary cards and session/match/member/department report tables. |
| `frontend/src/app/(dashboard)/audit/page.jsx` | Filters audit data and provides browser-generated CSV export. |
| `frontend/src/app/(dashboard)/sessions/page.jsx` | Permission-gated demonstrative session table/modal backed by local mock state, not persistent APIs. |
| `frontend/src/app/(dashboard)/users/page.jsx` | Permission-gated demonstrative user table/modal backed by local mock state, not persistent user CRUD. |

## 16. Frontend BFF API Routes

| File | Responsibility |
| --- | --- |
| `frontend/src/app/api/auth/login/route.js` | Validates login input, calls FastAPI, and sets the HTTP-only auth cookie. |
| `frontend/src/app/api/auth/me/route.js` | Validates the cookie against FastAPI, returns the current user, and clears invalid cookies. |
| `frontend/src/app/api/auth/logout/route.js` | Calls backend logout and expires the auth cookie. |
| `frontend/src/app/api/sessions/route.js` | Proxies session listing; implemented separately from the shared proxy helper. |
| `frontend/src/app/api/records/route.js` | Forwards all record-list query parameters. |
| `frontend/src/app/api/records/[id]/route.js` | Proxies record detail. |
| `frontend/src/app/api/records/[id]/similar/route.js` | Proxies similarity candidates. |
| `frontend/src/app/api/records/[id]/reviews/route.js` | Proxies similarity-decision GET and POST. |
| `frontend/src/app/api/search/route.js` | Proxies BM25 keyword-search POST. |
| `frontend/src/app/api/submissions/route.js` | Proxies new submission POST. |
| `frontend/src/app/api/submissions/mine/route.js` | Proxies current-user submission tracking. |
| `frontend/src/app/api/submissions/review-queue/route.js` | Proxies the permission-protected Clerk queue. |
| `frontend/src/app/api/submissions/[id]/route.js` | Proxies draft PATCH. |
| `frontend/src/app/api/submissions/[id]/submit/route.js` | Proxies draft resubmission. |
| `frontend/src/app/api/submissions/[id]/workflow-review/route.js` | Proxies approve/reject/request-changes decisions. |
| `frontend/src/app/api/submissions/[id]/schedule/route.js` | Proxies sitting-date scheduling. |
| `frontend/src/app/api/order-papers/[date]/route.js` | Proxies generated Order Papers by sitting date. |
| `frontend/src/app/api/audit/route.js` | Proxies audit filters and result data. |
| `frontend/src/app/api/reports/route.js` | Proxies operational reports. |

## 17. Frontend Authentication, State, and Middleware

| File | Responsibility |
| --- | --- |
| `frontend/src/middleware.js` | Verifies JWT signature/expiry for protected paths and redirects valid login sessions or invalid protected sessions. |
| `frontend/src/context/AuthContext.jsx` | Loads current user, exposes login/logout/refresh, and reacts to API session-expiry events. |
| `frontend/src/hooks/useAuth.js` | Thin public hook over AuthContext. |
| `frontend/src/store/authStore.js` | Zustand store for current user and auth loading state. |

## 18. Frontend Feature Hooks

| File | Responsibility |
| --- | --- |
| `frontend/src/hooks/useSubmit.js` | Maps form values to submission API fields, tracks submission state/errors, and navigates to the result record. |
| `frontend/src/hooks/useSearch.js` | Runs BM25 search requests, normalizes ranked results, and tracks loading/search/error state. |

## 19. Frontend Libraries

| File | Responsibility |
| --- | --- |
| `frontend/src/lib/auth.js` | Defines cookie name/options, verifies JWTs with JOSE, and checks user permission arrays. |
| `frontend/src/lib/backendProxy.js` | Shared cookie-to-Bearer forwarding, backend-unavailable handling, and structured error normalization. |
| `frontend/src/lib/api.js` | Axios same-origin client, direct backend client, credentials behavior, and 401 event dispatch. |
| `frontend/src/lib/db.js` | Creates a direct PostgreSQL pool; currently retained but not used by the implemented BFF routes. |
| `frontend/src/lib/records.js` | Converts backend snake_case record/search responses into frontend view models. |
| `frontend/src/lib/utils.js` | Class joining, date/time formatting, and text truncation helpers. |
| `frontend/src/lib/mockData.js` | Legacy/demo sessions, users, submissions, decisions, audit entries, and in-memory search/similarity helpers; production records use APIs. |

## 20. Frontend Layout and Feature Components

| File | Responsibility |
| --- | --- |
| `frontend/src/components/auth/LoginForm.jsx` | Zod/react-hook-form login validation, API call, errors, and redirect. |
| `frontend/src/components/layout/Sidebar.jsx` | Permission-filtered navigation, identity display, active route, and logout. |
| `frontend/src/components/layout/Topbar.jsx` | Assembly title, current role/session label, and hydration-safe client date. |
| `frontend/src/components/layout/PageHeader.jsx` | Breadcrumbs, title, description, and route-specific actions. |
| `frontend/src/components/dashboard/StatCard.jsx` | Dashboard metric card. |
| `frontend/src/components/dashboard/RecentActivity.jsx` | Recent record table/cards with lifecycle badges and session labels. |
| `frontend/src/components/submit/SubmitForm.jsx` | Permission-constrained type choices, conditional question fields, Zod validation, and submission hook integration. |
| `frontend/src/components/submit/SubmissionCard.jsx` | Browse-list card with type/status/session metadata and detail navigation. |
| `frontend/src/components/search/SearchBar.jsx` | Debounced text/session/date/member/ministry/status/type filter form. |
| `frontend/src/components/search/ResultCard.jsx` | Ranked similarity result, score, metadata, and expandable text. |
| `frontend/src/components/shared/SessionBadge.jsx` | Session-label badge wrapper. |
| `frontend/src/components/shared/SimilarityScore.jsx` | Score display with level-specific styling. |

## 21. Frontend UI Primitives

| File | Responsibility |
| --- | --- |
| `frontend/src/components/ui/Badge.jsx` | Semantic status/type/role badges. |
| `frontend/src/components/ui/Button.jsx` | Shared button variants, sizes, widths, and link-compatible class builder. |
| `frontend/src/components/ui/Card.jsx` | Shared bordered content container. |
| `frontend/src/components/ui/EmptyState.jsx` | Empty/error/access-denied presentation with optional action. |
| `frontend/src/components/ui/Input.jsx` | Labeled input with hint/error support and forwarded ref. |
| `frontend/src/components/ui/Modal.jsx` | Accessible modal structure, backdrop, close control, content, and footer. |
| `frontend/src/components/ui/Select.jsx` | Labeled select with icon/error/hint and forwarded ref. |
| `frontend/src/components/ui/Spinner.jsx` | Shared loading indicator. |
| `frontend/src/components/ui/Table.jsx` | Configurable columns, row keys, responsive wrapper, and empty state. |
| `frontend/src/components/ui/Textarea.jsx` | Labeled multiline control with hint/error and forwarded ref. |
| `frontend/src/components/ui/Toast.jsx` | Success/error/info notification styling and icon selection. |

## 22. Frontend Type Placeholders

| File | Responsibility |
| --- | --- |
| `frontend/src/types/auth.js` | Empty compatibility placeholder for former/generated auth types. |
| `frontend/src/types/search.js` | Empty compatibility placeholder for former/generated search types. |
| `frontend/src/types/submission.js` | Empty compatibility placeholder for former/generated submission types. |

## 23. Frontend E2E Tests and Snapshots

| File | Responsibility |
| --- | --- |
| `frontend/tests/e2e/visual-baseline.spec.js` | Authenticated route smoke tests and exact desktop/mobile screenshots using seeded login data. |
| `frontend/tests/e2e/visual-baseline.spec.js-snapshots/login-desktop-linux.png` | Approved desktop login rendering. |
| `frontend/tests/e2e/visual-baseline.spec.js-snapshots/login-mobile-linux.png` | Approved mobile login rendering. |
| `frontend/tests/e2e/visual-baseline.spec.js-snapshots/dashboard-linux.png` | Approved desktop dashboard rendering. |
| `frontend/tests/e2e/visual-baseline.spec.js-snapshots/dashboard-mobile-linux.png` | Approved mobile dashboard rendering. |
| `frontend/tests/e2e/visual-baseline.spec.js-snapshots/submit-linux.png` | Approved desktop submission page rendering. |
| `frontend/tests/e2e/visual-baseline.spec.js-snapshots/search-linux.png` | Approved desktop record-search/filter page rendering. |
| `frontend/tests/e2e/visual-baseline.spec.js-snapshots/reports-linux.png` | Approved desktop reports page rendering. |
| `frontend/tests/e2e/visual-baseline.spec.js-snapshots/sessions-linux.png` | Approved desktop sessions page rendering. |
| `frontend/tests/e2e/visual-baseline.spec.js-snapshots/users-linux.png` | Approved desktop users page rendering. |
| `frontend/tests/e2e/visual-baseline.spec.js-snapshots/result-detail-linux.png` | Approved record detail/review page rendering. |
| `frontend/tests/e2e/visual-baseline.spec.js-snapshots/audit-linux.png` | Approved audit-page frame; dynamic table content is masked. |

## 24. Frontend Source Guards

| File | Responsibility |
| --- | --- |
| `frontend/tests/source/no-tailwind.test.cjs` | Proves Tailwind dependencies/config/directives/classes are absent. |
| `frontend/tests/source/no-role-authorization.test.cjs` | Guards against role-name authorization logic in frontend source. |
| `frontend/tests/source/submission-permissions.test.cjs` | Verifies submission types derive from permission checks. |
| `frontend/tests/source/question-submission.test.cjs` | Verifies oral/written answer field and API payload mapping. |
| `frontend/tests/source/submission-validation.test.cjs` | Verifies readable formatting of structured backend validation errors. |
| `frontend/tests/source/review-queue.test.cjs` | Verifies Clerk queue BFF exposure. |
| `frontend/tests/source/workflow-review.test.cjs` | Verifies BFF and permission-aware workflow actions. |
| `frontend/tests/source/my-submissions.test.cjs` | Verifies authenticated owner-tracking BFF exposure. |
| `frontend/tests/source/draft-recovery.test.cjs` | Verifies draft edit and resubmission proxies. |
| `frontend/tests/source/submission-statuses.test.cjs` | Guards the exact seven status filter values. |
| `frontend/tests/source/scheduling.test.cjs` | Verifies sitting-date scheduling UI and BFF. |
| `frontend/tests/source/order-paper.test.cjs` | Verifies sitting-date Order Paper BFF route. |
| `frontend/tests/source/record-filters.test.cjs` | Verifies date/member/ministry UI controls and query forwarding. |
| `frontend/tests/source/topbar-hydration.test.cjs` | Prevents direct server rendering of timezone-dependent current date. |
| `frontend/tests/source/visual-clock.test.cjs` | Keeps authenticated Playwright snapshots on a deterministic browser date. |

## 25. How Files Work Together

Typical record creation path:

1. `SubmitForm.jsx` validates input and calls `useSubmit.js`.
2. `useSubmit.js` posts to `app/api/submissions/route.js`.
3. The BFF uses `backendProxy.js` to add the cookie token.
4. `routers/submissions.py` authorizes and validates with
   `schemas/submission.py`.
5. `services/submission_status.py` moves the record into review.
6. `models/models.py` persists through `database.py`.
7. `services/similarity.py` and `retrieval/bm25.py` produce candidates.
8. The browser navigates to `results/[id]/page.jsx`.

Typical protected read path:

1. `middleware.js` checks the JWT before navigation.
2. The dashboard layout confirms the session against FastAPI.
3. A page calls a same-origin BFF route.
4. `backendProxy.js` forwards the Bearer token.
5. `deps.py` validates JWT, JTI, expiry, revocation, account, and permission.
6. A router queries records while `record_visibility.py` enforces row rules.
