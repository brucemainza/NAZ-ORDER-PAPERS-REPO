# NAZ Order Papers TDD Implementation Baseline

Recorded: 2026-07-23

This document captures the repository state before the TDD implementation
directive is applied. It is intentionally descriptive: no production behavior has
been changed at this point.

## Verification Baseline

- `npm run build` succeeds for the Next.js frontend.
- `python3 -m compileall -q backend/app backend/scripts` succeeds.
- Docker services for PostgreSQL, FastAPI, and Next.js start successfully.
- `GET http://localhost:8080/health` returns `{"status":"ok"}`.
- `GET http://localhost:3000/login` returns HTTP 200.
- No backend or frontend automated test suite is currently configured.
- Google Chrome is available for browser screenshots, but no browser automation
  package is currently installed.

## Part A: Styling

### What exists

- Tailwind CSS 3 is configured through `tailwind.config.js` and
  `postcss.config.js`.
- `globals.css` contains Tailwind's base, components, and utilities directives.
- The frontend has 244 `className` uses and approximately 207 distinct utility
  class strings across the root layout, two application layouts, eight pages,
  and 23 shared components.
- `tailwind-merge` is used by the `cn()` helper to merge utility classes.
- A small amount of custom CSS exists for theme variables, striped tables, and
  two-line clamping.

### What is missing

- There is no visual regression or component snapshot suite.
- There are no plain CSS modules or component stylesheets.
- The current UI cannot run without Tailwind-generated CSS.

### Smallest correct change

1. Add a Playwright smoke/visual baseline that uses the existing Chrome
   installation and exercises all application routes at desktop and mobile
   widths.
2. Migrate one component or page at a time to a colocated CSS module, keeping
   existing component APIs and exact Tailwind-computed values.
3. Run the build and relevant browser checks after every migration.
4. Remove Tailwind, its PostCSS plugin, directives, and `tailwind-merge` only
   after a repository-wide utility-class check is clean.

## Part B: Authorization

### What exists

- A user has one required text `role`.
- The database limits roles to `Admin`, `Senior Clerk`, or `Clerk`.
- API authorization uses `require_roles()` and currently protects only audit-log
  access.
- Most authenticated endpoints allow every active user.
- The frontend checks the literal `Admin` role for the Sessions and Users pages
  and for sidebar navigation.
- JWTs include the role name, while `/auth/me` reloads the current user from the
  database.

### What is missing

- Permission and role tables, role-permission mappings, and user-role mappings.
- The required Administrator, Clerk, Member of Parliament, and Viewer roles.
- Permission-aware API dependencies and UI guards.
- Configurable custom roles.

### Smallest correct change

Add `permissions`, `roles`, `role_permissions`, and `user_roles`; keep the legacy
`users.role` column temporarily for compatibility while all reads move to role
relationships. Expose a flat permission list in authenticated user responses and
JWTs, replace business-logic role checks with permission checks, then remove
reliance on the legacy value.

## Part C: Functional Requirements

| Requirement | Existing behavior | Gap and smallest correct change |
| --- | --- | --- |
| FR-001 Login | Employee ID/password login, bcrypt verification, generic invalid-credential response, JWT session, and logout exist. | Add tests for valid and invalid cases; preserve the non-leaking error. |
| FR-002 Roles | Admin, Senior Clerk, and Clerk are text values. | Seed the four required roles as data with capability mappings. |
| FR-003 Lockout | No failed-attempt tracking or unlock behavior exists. | Add failed-attempt/lock fields, lock on the fifth failure, and provide a `manage_users`-protected administrator unlock endpoint. |
| FR-005 Questions | Any authenticated user can create a generic Question. | Require `submit_question`; add an oral/written answer type. |
| FR-006 Motions | Any authenticated user can create a Motion. | Require `submit_motion`. |
| FR-007 Validation | Session, member, subject, text, and question ministry validation exist; Pydantic reports errors. | Test every existing required field and normalize clear API error responses. |
| FR-009 Review queue | New records receive `Pending Review`. | Adopt the required lifecycle and expose `Under Review` records to `review_submission` holders. |
| FR-010 Review actions | Reviews record duplicate-detection decisions: Clear, Duplicate, or Substantially Similar. Any authenticated user can review. | Separate lifecycle review actions (approve, reject, request changes) from similarity classification and guard them by permission. |
| FR-019 Status tracking | Records contain no submitter/owner identifier, and all authenticated users can read all records. | Add `submitted_by`, an own-submissions query, and draft visibility rules. |
| FR-020 Status model | Free-text statuses include Historical, Pending Review, Clear, Duplicate, and Substantially Similar. | Introduce exactly Draft, Submitted, Under Review, Approved, Rejected, Scheduled, and Archived plus an explicit transition service. Migrate legacy data to valid lifecycle values while retaining similarity decisions separately. |
| FR-022 Scheduling | Absent. | Add sitting date and a permission-protected schedule action that only accepts Approved records. |
| FR-023 Order Paper | Absent; no existing template or ordering format is present in the repository. | Generate a deterministic data representation grouped Questions then Motions and ordered by creation time for a sitting date. This is the minimal format derivable from the current domain model. |
| FR-025 Auto-archive | Absent. Sessions use Active, Closed, and Upcoming. | Add an idempotent archive service/endpoint that archives records belonging to Closed or ended sessions and leaves active sessions unchanged. |
| FR-026 Archive access | Historical records are readable by every authenticated user. | Require `view_archive` for archived lists/details and `search_archive` for archive search. |
| FR-028 Keyword search | BM25 search covers subject and full text; record list text filtering also covers member and ministry. | Test subject/full-text matching and clear non-matches while preserving BM25 ranking. |
| FR-029 Filters | Record list supports session, item type, status, and a broad text query. | Add independent date, member, and ministry filters and test combinations. |

## Data and Compatibility Risks

- Existing databases are upgraded at startup by `db_compat.py`; schema changes
  must be idempotent because Docker persists the PostgreSQL volume.
- Seed records use legacy `Historical`, `Pending Review`, and `Duplicate` statuses.
  They must be migrated before a strict lifecycle constraint can be applied.
- The Sessions and Users pages currently modify local mock arrays only. They are
  not reliable evidence of backend administration behavior.
- pgvector embeddings are not populated for seed data, so BM25 remains the
  available similarity fallback.
- No official Order Paper template exists in this repository. The initial API
  format must therefore be deterministic and domain-minimal rather than claiming
  fidelity to an unavailable external document layout.

## Default Permission Set

| Permission | Administrator | Clerk | Member of Parliament | Viewer |
| --- | ---: | ---: | ---: | ---: |
| `submit_question` | Yes | No | Yes | No |
| `submit_motion` | Yes | No | Yes | No |
| `review_submission` | Yes | Yes | No | No |
| `approve_motion` | Yes | Yes | No | No |
| `reject_submission` | Yes | Yes | No | No |
| `schedule_item` | Yes | Yes | No | No |
| `view_reports` | Yes | Yes | No | Yes |
| `manage_users` | Yes | No | No | No |
| `manage_roles` | Yes | No | No | No |
| `manage_sessions` | Yes | Yes | No | No |
| `search_archive` | Yes | Yes | Yes | Yes |
| `view_archive` | Yes | Yes | Yes | Yes |

Administrator receives every seeded permission. A custom role is represented by
database rows and mappings only; business logic checks permission names rather
than role names.
