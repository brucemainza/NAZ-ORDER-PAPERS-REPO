# NAZ Order Papers System Architecture

This document presents the implemented architecture. Mermaid-capable Markdown
viewers render each diagram graphically.

## 1. System Context

```mermaid
flowchart LR
    MP[Member of Parliament]
    CLERK[Clerk]
    ADMIN[Administrator]
    VIEWER[Viewer]
    SYSTEM[NAZ Order Papers System]
    DB[(Parliamentary Records)]

    MP -->|Submit and track questions/motions| SYSTEM
    CLERK -->|Review, decide, schedule| SYSTEM
    ADMIN -->|Administer, audit, report| SYSTEM
    VIEWER -->|Read reports and archive| SYSTEM
    SYSTEM -->|Persist and retrieve| DB
```

## 2. Container Architecture

```mermaid
flowchart TB
    subgraph Browser["User Browser"]
        UI["React 18 UI\nNext.js App Router pages"]
        STORE["Zustand auth state\nReact context"]
    end

    subgraph Next["Next.js 14 Container :3000"]
        MW["JWT middleware\nRoute navigation guard"]
        SSR["Server layouts/pages"]
        BFF["/api/* route handlers\nBackend-for-frontend proxy"]
        COOKIE["HTTP-only naz_token cookie"]
    end

    subgraph API["FastAPI Container :8000 / host :8080"]
        ROUTERS["API routers\nAuth, records, submissions,\nreviews, reports, audit"]
        DEPS["Auth and permission dependencies"]
        SERVICES["Domain services\nStatus, visibility, RBAC,\nsimilarity, archiving"]
        SCHEMAS["Pydantic request/response schemas"]
        ORM["SQLAlchemy ORM"]
    end

    subgraph Data["PostgreSQL 16 + pgvector :5432 / host :5433"]
        REL[(Relational tables)]
        VECTOR[(vector(384) + cosine index)]
    end

    UI <--> STORE
    UI -->|Same-origin fetch /api/*| BFF
    MW <--> COOKIE
    SSR <--> COOKIE
    BFF <--> COOKIE
    BFF -->|JSON + Bearer JWT| ROUTERS
    ROUTERS --> DEPS
    ROUTERS --> SCHEMAS
    ROUTERS --> SERVICES
    SERVICES --> ORM
    ROUTERS --> ORM
    ORM --> REL
    SERVICES --> VECTOR
```

## 3. Layer Responsibilities

| Layer | Implemented responsibility |
| --- | --- |
| Browser pages/components | Forms, tables, filters, permission-aware controls, feedback, and navigation. |
| Next.js middleware | Fast local JWT check before protected page navigation. |
| Next.js BFF | Reads HTTP-only cookie, forwards Bearer JWT, normalizes backend errors. |
| FastAPI routers | HTTP contracts, dependency injection, orchestration, status codes, audit calls. |
| Domain services | Status transitions, record visibility, RBAC seed/mapping, similarity merge, archiving. |
| Pydantic schemas | Input validation and typed response serialization. |
| SQLAlchemy models | Entity mappings and relationships. |
| PostgreSQL | Durable users, sessions, records, workflow, search, review, and audit data. |
| pgvector | Optional semantic similarity storage and cosine matching. |

## 4. Authentication Sequence

```mermaid
sequenceDiagram
    actor U as User
    participant F as LoginForm
    participant N as Next.js /api/auth/login
    participant A as FastAPI /auth/login
    participant D as PostgreSQL

    U->>F: Enter employee ID and password
    F->>N: POST credentials
    N->>N: Validate payload with Zod
    N->>A: POST employee_id and password
    A->>D: Load active user
    D-->>A: User, hash, lock state
    A->>A: Check lock and bcrypt password

    alt Invalid password
        A->>D: Increment failed attempts
        A->>D: Set locked_at on fifth failure
        A-->>N: 401 generic credential error
        N-->>F: 401 message
    else Valid password
        A->>A: Create 8-hour HS256 JWT and JTI
        A->>D: Persist user_sessions and login audit
        A-->>N: Token plus user permissions
        N->>N: Set HTTP-only naz_token cookie
        N-->>F: Authenticated user
        F-->>U: Navigate to dashboard
    end
```

## 5. Protected Request Sequence

```mermaid
sequenceDiagram
    actor U as Authenticated User
    participant P as React Page
    participant B as Next.js BFF
    participant R as FastAPI Router
    participant G as Auth/Permission Guard
    participant D as PostgreSQL

    U->>P: Perform action
    P->>B: Same-origin /api request
    B->>B: Read HTTP-only cookie
    B->>R: Forward JSON + Authorization Bearer
    R->>G: Resolve current user
    G->>D: Validate JTI, expiry, revocation, account
    G->>G: Check atomic permission if required

    alt Unauthorized
        G-->>B: 401 or 403
        B-->>P: Normalized JSON message
    else Authorized
        R->>D: Query/update transaction
        R->>D: Add audit log where applicable
        D-->>R: Persisted result
        R-->>B: Typed JSON response
        B-->>P: Same-origin JSON response
    end
```

## 6. Submission and Review Flow

```mermaid
sequenceDiagram
    actor MP as Member
    participant UI as Submit UI
    participant API as FastAPI
    participant SM as Status Service
    participant SIM as Similarity Service
    participant DB as PostgreSQL
    actor C as Clerk

    MP->>UI: Enter question or motion
    UI->>UI: Zod field validation
    UI->>API: POST /submissions
    API->>API: Pydantic validation + permission check
    API->>DB: Verify Active/Upcoming session
    API->>SM: Submitted -> Under Review
    API->>DB: Save record, owner, audit
    API->>SIM: Find related historical records
    SIM->>DB: Load non-draft candidates
    SIM->>SIM: BM25 rank
    opt Embeddings are available
        SIM->>DB: pgvector cosine query
        SIM->>SIM: Merge BM25/vector matches
    end
    API-->>UI: Record + candidate matches

    C->>API: GET /submissions/review-queue
    API-->>C: Oldest Under Review items
    C->>API: Record similarity decision
    API->>DB: Save review_decisions + audit
    C->>API: Approve / Reject / Request Changes
    API->>SM: Validate transition
    API->>DB: Save workflow_decisions + audit
```

## 7. Submission State Machine

```mermaid
stateDiagram-v2
    [*] --> Submitted: Valid new submission
    Draft --> Submitted: Owner resubmits
    Submitted --> UnderReview: Queue for Clerk
    UnderReview --> Draft: Request Changes
    UnderReview --> Approved: Approve
    UnderReview --> Rejected: Reject
    Approved --> Scheduled: Assign sitting date

    Draft --> Archived: Session ended
    Submitted --> Archived: Session ended
    UnderReview --> Archived: Session ended
    Approved --> Archived: Session ended
    Rejected --> Archived: Session ended
    Scheduled --> Archived: Session ended

    Archived --> [*]
```

`UnderReview` in the diagram corresponds to the stored value `Under Review`.
Transitions not shown are rejected.

## 8. Scheduling and Order Paper Flow

```mermaid
flowchart LR
    A["Approved record"]
    P{"Has schedule_item?"}
    DATE["Specific sitting date"]
    S["Scheduled record"]
    QUERY["GET /order-papers/{date}"]
    Q["QUESTIONS\noldest first"]
    M["NOTICES OF MOTION\noldest first"]
    PAPER["Structured Order Paper JSON"]

    A --> P
    P -->|No| DENY["403"]
    P -->|Yes| DATE
    DATE --> S
    S --> QUERY
    QUERY --> Q
    QUERY --> M
    Q --> PAPER
    M --> PAPER
```

## 9. Search Architecture

```mermaid
flowchart TB
    UI["Submissions search UI"]
    LENGTH{"Trimmed keyword\nat least 3 chars?"}
    BROWSE["GET /api/records\nSQL browse/filter path"]
    BFF["POST /api/search\nNext.js BFF"]
    INPUT["Keyword + optional session/date/member/\nministry/status/type + offset/limit"]
    VIS["Draft and archive\nvisibility filters"]
    FILTERS["Apply structured filters\nbefore relevance scoring"]
    CANDIDATES["Candidate records"]
    TOKEN["Lowercase, remove punctuation,\nignore tokens under 3 chars"]
    BM25["BM25 term-frequency /\ninverse-frequency scoring"]
    NORMALIZE["Sort and normalize top score to 100"]
    PAGE["Paginate ranked results\nwith stable rank numbers"]
    LOG["search_logs + audit_logs"]
    RESULTS["Cards with full text,\nscore, and matched terms"]

    UI --> LENGTH
    LENGTH -->|No| BROWSE
    LENGTH -->|Yes| BFF
    BFF --> INPUT
    INPUT --> VIS
    VIS --> FILTERS
    FILTERS --> CANDIDATES
    CANDIDATES --> TOKEN
    TOKEN --> BM25
    BM25 --> NORMALIZE
    NORMALIZE --> PAGE
    PAGE --> RESULTS
    INPUT --> LOG
    RESULTS --> LOG
```

The record-list endpoint uses SQL filters and partial text matching for blank or
short-keyword browsing. Usable keywords take the BM25 branch so matching content,
not only record metadata, determines relevance.

## 10. Archive Flow

```mermaid
flowchart TD
    START["FastAPI startup"]
    SCHEMA["Apply compatibility DDL"]
    RBAC["Seed roles/permissions\nand map legacy users"]
    FIND{"Session Closed OR\nend_date before today?"}
    RECORDS["Load every non-Archived record"]
    TRANSITION["Status service -> Archived"]
    COMMIT["Commit transaction"]
    KEEP["Leave active/future records unchanged"]

    START --> SCHEMA
    SCHEMA --> RBAC
    RBAC --> FIND
    FIND -->|Yes| RECORDS
    RECORDS --> TRANSITION
    TRANSITION --> COMMIT
    FIND -->|No| KEEP
```

## 11. Entity Relationship Diagram

```mermaid
erDiagram
    USERS ||--o{ USER_SESSIONS : owns
    USERS }o--o{ ROLES : assigned
    ROLES }o--o{ PERMISSIONS : grants
    USERS ||--o{ PARLIAMENTARY_RECORDS : submits
    PARLIAMENTARY_SESSIONS ||--o{ PARLIAMENTARY_RECORDS : contains
    USERS ||--o{ SEARCH_LOGS : performs
    PARLIAMENTARY_SESSIONS ||--o{ SEARCH_LOGS : scopes
    PARLIAMENTARY_RECORDS ||--o{ REVIEW_DECISIONS : reviewed_record
    PARLIAMENTARY_RECORDS ||--o{ REVIEW_DECISIONS : similar_record
    USERS ||--o{ REVIEW_DECISIONS : reviewer
    PARLIAMENTARY_RECORDS ||--o{ WORKFLOW_DECISIONS : receives
    USERS ||--o{ WORKFLOW_DECISIONS : reviewer
    USERS ||--o{ AUDIT_LOGS : actor

    USERS {
        uuid id PK
        text employee_id UK
        text name
        text role
        text status
        text password_hash
        int failed_login_attempts
        timestamptz locked_at
    }

    USER_SESSIONS {
        uuid id PK
        uuid user_id FK
        text jti UK
        timestamptz expires_at
        timestamptz revoked_at
    }

    ROLES {
        uuid id PK
        text name UK
    }

    PERMISSIONS {
        uuid id PK
        text code UK
    }

    PARLIAMENTARY_SESSIONS {
        uuid id PK
        text code UK
        date start_date
        date end_date
        text status
    }

    PARLIAMENTARY_RECORDS {
        uuid id PK
        text item_type
        uuid session_id FK
        uuid submitted_by FK
        text member
        text ministry
        text answer_type
        text subject
        text full_text
        text status
        date sitting_date
        vector embedding
    }

    REVIEW_DECISIONS {
        uuid id PK
        uuid record_id FK
        uuid similar_record_id FK
        uuid reviewer_id FK
        text decision
        boolean is_duplicate
    }

    WORKFLOW_DECISIONS {
        uuid id PK
        uuid record_id FK
        uuid reviewer_id FK
        text action
    }

    SEARCH_LOGS {
        uuid id PK
        uuid user_id FK
        uuid session_id FK
        text query_text
        uuid_array top_result_ids
    }

    AUDIT_LOGS {
        uuid id PK
        uuid user_id FK
        text action
        text entity_type
        text entity_id
    }
```

The physical join tables `user_roles` and `role_permissions` implement the two
many-to-many relationships.

## 12. Docker Deployment

```mermaid
flowchart LR
    HOST["Developer workstation"]

    subgraph COMPOSE["Docker Compose network"]
        FRONT["naz_order_papers_frontend\nNext.js dev server\n3000"]
        BACK["naz_order_papers_backend\nUvicorn/FastAPI\n8000"]
        PG["naz_order_papers_db\nPostgreSQL + pgvector\n5432"]
        PORT["naz_portainer\nPortainer CE\n9000 / 8000"]
        VOL1[("pgdata")]
        VOL2[("portainer_data")]

        FRONT -->|http://backend:8000| BACK
        BACK -->|psycopg| PG
        PG --- VOL1
        PORT --- VOL2
    end

    HOST -->|localhost:3000| FRONT
    HOST -->|localhost:8080| BACK
    HOST -->|localhost:5433| PG
    HOST -->|localhost:9000/9001| PORT
```

## 13. Trust Boundaries

```mermaid
flowchart LR
    USER["Untrusted browser input"]
    EDGE["Next.js validation and\nHTTP-only cookie boundary"]
    AUTH["FastAPI authentication and\npermission boundary"]
    DOMAIN["Validated domain operations"]
    DATA["Trusted database transaction"]

    USER --> EDGE
    EDGE --> AUTH
    AUTH --> DOMAIN
    DOMAIN --> DATA
```

Important controls at the boundaries:

- Zod validates login and forms in the browser/BFF.
- Pydantic is authoritative for API payload validation.
- The BFF prevents direct browser access to the JWT.
- FastAPI revalidates JWT session state and permissions.
- SQLAlchemy uses parameterized statements.
- PostgreSQL constraints protect core enumerations and references.

## 14. Source Map

- Full behavioral contract: [system-specification.md](system-specification.md)
- Every tracked file: [file-guide.md](file-guide.md)
- Delivery and verification status: [implementation-report.md](implementation-report.md)
- Local startup: [../README.md](../README.md)
