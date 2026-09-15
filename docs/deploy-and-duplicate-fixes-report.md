# Deploy-Blocker and Duplicate-Submission Fixes Report

Project: NAZ Order Papers System

Branch: `feature-daliD`

Report date: 2026-09-15

## 1. Outcome

The project would not start locally or deploy reliably: `/readyz` failed the
whole stack when Ollama/qwen wasn't provisioned, the Sessions page had no
working activate/close/delete, submission errors (including duplicate
detection) were silently swallowed by the frontend, and a stray editor file
was left in the repo. All of these are fixed, plus two environment-level
issues that were separately blocking the stack from actually running were
diagnosed and resolved. Everything below was verified against the real
running Docker stack, not just builds.

Work was split into two tracks so it could be parallelized; both tracks are
now complete.

## 2. Track 1 — Deployment and Sessions

### 2.1 AI/Ollama made non-blocking for readiness

- `backend/app/config.py` — new `AI_REQUIRED` setting (env `AI_REQUIRED`,
  default `false`).
- `backend/app/services/readiness.py` — `/readyz` no longer returns `503`
  when Ollama/qwen is missing unless `AI_REQUIRED=true` is explicitly set.
  `ollama_llm_model` (qwen) was dropped from the required-models check
  entirely; only the embedding model is checked now.
- `docs/ai-explanation.html` — documented the new setting (an existing test
  asserts every AI/Ollama env setting is documented).

### 2.2 Session activate/close/delete

The ticket for this assumed the backend already supported session
PATCH/DELETE and only a frontend proxy route was missing. That wasn't the
case: the backend had a GET-only `/sessions` endpoint and the Sessions page
was entirely local mock state with no working Edit/Close buttons. Built the
full path instead of just the proxy:

- `backend/app/routers/sessions.py`, `backend/app/schemas/session.py` — new
  `PATCH /sessions/{id}` and `DELETE /sessions/{id}`, gated by the existing
  `manage_sessions` permission, audit-logged, returning a clean `409` (not a
  raw DB error) if a session with linked records is deleted.
- `frontend/src/app/api/sessions/[id]/route.js` (new) — PATCH/DELETE proxy.
- `frontend/src/app/(dashboard)/sessions/page.jsx` — rewired from mock data
  to the real API with working Edit/Activate/Close/Delete actions. The old
  "Add Session" button was removed since it never persisted anything; session
  creation is still not implemented (see Limits).

### 2.3 Housekeeping

- Removed the stray `.docker-compose.yml.swp` (confirmed a stale Vim swap
  file from a different user/host, not in-progress work).

## 3. Track 2 — Submissions and Duplicate Detection

### 3.1 Silent submission failures

The stated bug ("`onSubmit` discards the result") wasn't quite the root
cause. The actual chain:

- `useSubmit.js`'s `submitSubmission` never returned anything, so there was
  nothing to read.
- More importantly, the backend returns duplicate-detection results as a
  structured object inside a `409`'s `detail` field. The generic frontend
  proxy's error handler only knew how to stringify `detail` when it was a
  string or a validation-error array; an object fell through to a hardcoded
  `"Backend request failed"` — so the duplicate payload was being discarded
  before it ever reached the UI, regardless of how `onSubmit` used the
  result.

Fixed: `frontend/src/app/api/submissions/route.js` now preserves the
structured duplicate payload instead of collapsing it, and
`useSubmit.js`'s `submitSubmission` returns `{ duplicate }` or
`{ success }` for the caller to act on.

### 3.2 Duplicate-submission popup and "view document"

- `backend/app/schemas/similarity.py`, `backend/app/similarity/presentation.py`
  — `SimilarityMatchOut`/`SimilarityDisplayMatch` now include `subject` and a
  ~240-character `snippet` of the matched record's text, so the popup doesn't
  need a second round trip.
- `frontend/src/components/submit/SubmitForm.jsx` — on a duplicate result,
  opens a confirmation modal listing each match's session, member, score,
  subject, and snippet, with a "View document" link to
  `/results/{source_record}` and a "Submit anyway" action that resubmits with
  `confirm_duplicate: true` (an existing backend capability).

### 3.3 Paragraph formatting

- `frontend/src/app/globals.css` — `.result-detail__body` now uses
  `white-space: pre-line`, matching the convention already used by
  `.result-card__text`, so paragraph breaks in `full_text` render instead of
  collapsing into one run-on block. No backend/storage change was needed;
  `document_parser.py` already newline-joins paragraphs.
- Documented limit: bold/italic/tables/lists from the original DOCX/PDF are
  not recoverable, since formatting is stripped at parse time. True
  "looks like the original" rendering is out of scope unless the original
  file is stored alongside the extracted text.

## 4. Environment Issues Found and Fixed

Two problems unrelated to application code were separately preventing the
stack from running at all:

1. **Host disk space.** The development machine's C: drive filled
   completely (down to 0 bytes free at one point), which crashed Docker
   Desktop mid-build and made its daemon unresponsive. Recovered via a full
   WSL2/Docker Desktop reset, `docker system prune`, and (at the user's
   request) deleting an unused 46.6GB game install. Not a code issue, but it
   fully blocked `docker compose up --build` until resolved.
2. **Stale local database volume.** The local Postgres volume
   (`naz-order-papers-repo_pgdata`) held a `review_decisions` table from a
   much older schema version (`decided_by`/`decided_at` columns) that
   predated the current baseline migration. Because the baseline migration
   uses `CREATE TABLE IF NOT EXISTS`, it silently skipped fixing that table,
   and migration `20260805_0010` then crashed trying to add a constraint on
   a column that was never added to it. Dropped and recreated the volume
   (local dev data only); migrations now run clean to head.

## 5. Verification

### 5.1 Backend test suite

```bash
cd backend
.venv/Scripts/python -m pytest -q
```

Result: **227 passed, 0 failed** (last full run, against the live
Postgres/pgvector test database).

### 5.2 Frontend build

```bash
cd frontend
npm run build
```

Result: production build, type checking, and static generation all succeed.

### 5.3 Live end-to-end verification (Docker stack, not just builds)

Ran against the actual running containers on `localhost`:

- `/readyz` returns `"ready"` with Ollama reachable but `required: false`,
  confirming the stack starts clean without Ollama being mandatory.
- Login (`EMP-001` / `Password123!`) → JWT cookie flow works.
- Session **Activate** (`PATCH`), **Close** (`PATCH`), and **Delete**
  (`DELETE`) all confirmed via the real API, including a clean `409` when
  deleting a session with linked records.
- Submitted a record, resubmitted identical content → received the full
  structured duplicate payload (`possible_duplicate`, `matches` with
  `subject`/`snippet`/`source_record`), then confirmed the `confirm_duplicate:
  true` override creates the record anyway (`201`).

### 5.4 Not verified

No browser was available in this environment, so the Sessions page's
Edit modal and the new duplicate-submission modal were verified at the API
level (the data they render was checked directly) but not click-tested
visually. Worth a manual pass before considering the UI work fully signed
off.

## 6. Residual Risks / Follow-ups

- Session **creation** (the old "Add Session" modal) is still not backed by
  a real API — only activate/close/delete were in scope for this round.
- The Users management page is still local mock state (unchanged, out of
  scope here).
- `C:\3uToolsV3` (5.91GB, unused iOS tool cache) is still on the dev
  machine; its deletion was blocked by a tool-level safety protection and
  needs to be removed manually if desired.
- The local Ollama installation crashed once during testing
  (`llama-server process has terminated: ... stack-based buffer overrun`)
  under disk-space stress; it recovered on its own and hasn't recurred, but
  it's worth keeping an eye on since the readiness fix (Section 2.1) is
  exactly what stops that kind of flakiness from taking down the whole
  stack.

## 7. Documentation Set

- [System specification](system-specification.md)
- [TDD implementation and verification report](implementation-report.md)
- [Production AI implementation (offline HTML)](ai-explanation.html)
- This report supersedes the "Users and Sessions management pages currently
  change local demo state" limit for Sessions (see README's Current Product
  Limits).
