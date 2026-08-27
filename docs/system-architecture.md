# NAZ Order Papers System Architecture

This document describes the implemented prototype as of 5 August 2026. It has
two authoritative views:

1. the complete application and container architecture; and
2. the hybrid retrieval-augmented generation (RAG) architecture.

The diagrams use Mermaid. A PlantUML component definition is also included for
teams that maintain UML documentation separately.

## 1. System context

```mermaid
flowchart LR
    MP[Member of Parliament]
    CLERK[Clerk]
    ADMIN[Administrator]
    SYSTEM[NAZ Order Papers prototype]

    MP -->|Submit and track questions or motions| SYSTEM
    CLERK -->|Review, search, explain and schedule| SYSTEM
    ADMIN -->|Manage access, audit and reports| SYSTEM
```

The AI layer is advisory. It retrieves evidence and can generate a grounded
explanation, but a human clerk retains every procedural decision.

## 2. Full system UML component architecture

```mermaid
flowchart TB
    ACTORS[Parliamentary staff]

    subgraph HOST[Developer workstation]
        BROWSER[Web browser]
        OLLAMA[Ollama service\nembeddinggemma:300m + qwen3.5:4b\nDocker bridge 172.17.0.1:11434]
    end

    subgraph COMPOSE[Docker Compose network]
        subgraph FRONTEND[Next.js 15 frontend :3000]
            UI[React pages & components]
            MW[JWT navigation middleware]
            BFF[Same-origin /api BFF routes]
            COOKIE[HTTP-only naz_token cookie]
        end

        subgraph BACKEND[FastAPI backend :8000 / host :8080]
            ROUTES[API routers\n/auth /submissions /records\n/search /reviews /scheduling\n/reports /ai]
            ACCESS[JWT session, permissions\nand record visibility]
            DOMAIN[Workflow & domain services]
            HYBRID[Hybrid retrieval service\nlexical + semantic + RRF]
            READY[Readiness & liveness checks]
            LOGS[Structured request logs]
            SCHEMAS[Pydantic schemas & validation]
        end

        MIGRATE[One-shot Alembic migrator\nadvisory lock + transaction]
        WORKER[Durable background worker\nleases + retry backoff + dead letter]

        subgraph POSTGRES[PostgreSQL 16 + pgvector :5432 / host :5433]
            DOMAINDB[(Domain, auth, workflow\nand audit tables)]
            FTS[(Weighted tsvector + GIN index)]
            VECTORS[(record_chunks vector(768)\n+ HNSW cosine index)]
            QUEUE[(background_jobs + outbox_events)]
            HEARTBEAT[(worker_heartbeats)]
            INFERENCE[(ai_inference_runs)]
        end
    end

    ACTORS --> BROWSER
    BROWSER -->|HTTP :3000| UI
    UI --> MW
    MW <--> COOKIE
    UI --> BFF
    BFF -->|Bearer JWT + JSON| ROUTES
    ROUTES --> ACCESS
    ACCESS --> DOMAIN
    ACCESS --> HYBRID
    ROUTES --> LOGS
    ROUTES --> SCHEMAS
    DOMAIN --> DOMAINDB
    HYBRID --> FTS
    HYBRID --> VECTORS
    HYBRID -->|POST /api/embed| OLLAMA
    READY --> DOMAINDB
    READY -->|GET /api/tags| OLLAMA
    READY --> QUEUE
    READY --> HEARTBEAT
    MIGRATE --> DOMAINDB
    WORKER --> QUEUE
    WORKER --> HEARTBEAT
    WORKER --> VECTORS
    WORKER --> INFERENCE
    WORKER -->|POST /api/embed + /api/chat| OLLAMA
```

### Component responsibilities

| Component | Responsibility |
| --- | --- |
| Next.js frontend | Pages, forms, tables, permission-aware controls and same-origin API proxying. |
| FastAPI routers | Typed HTTP contracts, authentication dependencies, orchestration and audit calls. |
| Domain services | Workflow transitions, visibility, scheduling, reporting and archive behavior. |
| Hybrid retrieval service | PostgreSQL lexical retrieval, Ollama query embedding, pgvector semantic retrieval and RRF fusion. |
| PostgreSQL | System of record, search indexes, vector chunks, inference audit, durable queue and recovery authority. |
| Worker | Claims durable jobs, creates embeddings and explanations, reports heartbeat, retries failures and surfaces dead letters. |
| Ollama | Local-only embedding and structured explanation inference; no cloud model API is used. |
| Readiness probe | Requires current schema, PostgreSQL, required Ollama models and zero dead-letter jobs before reporting ready. |

## 3. Full-system PlantUML source

A higher-fidelity UML component diagram is maintained in
[`diagrams/system-component.puml`](diagrams/system-component.puml). The inline
source below is a compact version for quick embedding.

```plantuml
@startuml NAZ_Order_Papers_System_Architecture
!theme plain
skinparam componentStyle uml2
skinparam packageStyle rectangle
skinparam shadowing false
skinparam linetype ortho

title NAZ Order Papers — Full System UML Component Architecture

actor "Parliamentary staff" as Staff

node "Developer workstation" as Host {
    component "Web browser" as Browser
    component "Ollama\n172.17.0.1:11434" as Ollama
}

node "Docker Compose network" as Compose {
    package "Next.js 15 frontend\n:3000" as WebPkg {
        component "React pages & components" as UI
        component "JWT navigation middleware" as Middleware
        component "Same-origin /api BFF routes" as BFF
        component "HTTP-only naz_token cookie" as Cookie
    }

    package "FastAPI backend\n:8000" as ApiPkg {
        component "API routers\n/auth /submissions /records\n/search /reviews /scheduling\n/reports /ai" as Routes
        component "Authentication, permissions\nand record visibility" as Access
        component "Workflow & domain services" as Domain
        component "Hybrid retrieval service\nlexical + semantic + RRF" as Retrieval
        component "Readiness & liveness checks" as Ready
        component "Structured request logs" as Logs
        component "Pydantic schemas & validation" as Schemas
    }

    component "Durable background worker\npython -m app.jobs.worker" as Worker
    component "One-shot Alembic migrator\npython -m scripts.migrate" as Migrator

    database "PostgreSQL 16 + pgvector\n:5432" as DB
}

Staff --> Browser : uses
Browser --> UI : HTTP :3000
UI --> Middleware : protects routes
Middleware <--> Cookie : reads/writes
UI --> BFF : fetch /api/*
BFF --> Routes : Bearer JWT + JSON

Routes --> Access : Depends()
Access --> Domain : authorised logic
Access --> Retrieval : authorised search
Routes --> Logs : every request
Routes --> Schemas : request/response

Domain --> DB : transactional SQL
Retrieval --> DB : weighted FTS + vector search
Retrieval --> Ollama : POST /api/embed

Worker --> DB : claim / complete / retry
Worker --> DB : upsert chunks + explanations
Worker --> Ollama : /api/embed + /api/chat

Ready --> DB : schema + queue + heartbeat
Ready --> Ollama : GET /api/tags + required models

Migrator --> DB : advisory-locked upgrade
@enduml
```

## 4. Hybrid RAG system architecture

The public search contract supports `keyword` and `hybrid` modes. Hybrid is the
default. Semantic retrieval is an internal branch of hybrid mode rather than a
third public mode. A standalone, colour-coded version of this diagram is in
[`diagrams/ai-rag-pipeline.mmd`](diagrams/ai-rag-pipeline.mmd).

```mermaid
flowchart TB
    subgraph INPUT["User request"]
        QUERY["Query text + filters\nsession_id, item_type, status,\ndate, member, ministry"]
        AUTH["Auth + visibility filters\nrestrict_draft_visibility\nrestrict_archive_visibility"]
    end

    subgraph LEXICAL["Lexical retrieval branch"]
        TSQUERY["websearch_to_tsquery('english', query)"]
        GIN["GIN index on search_vector\nsubject A | full_text B | member/ministry C"]
        LRANK["Lexical top-k\nts_rank_cd DESC"]
    end

    subgraph SEMANTIC["Semantic retrieval branch"]
        EMBED["Ollama POST /api/embed\nmodel: embeddinggemma:300m\ndimension: 768"]
        COMPAT["Compatibility filter\nembedding_model + model_digest\ndimension + preprocessing_version"]
        HNSW["pgvector HNSW cosine index\nembedding <=> query_vector"]
        BEST["Best chunk per record\nDISTINCT record_id"]
        SRANK["Semantic top-k\ncosine similarity DESC"]
    end

    subgraph FUSION["Rank fusion"]
        RRF["Reciprocal Rank Fusion\nscore = Σ 1 / (k + rank), k=60"]
        NORM["Normalise by max possible score"]
        PAGE["Apply offset + limit"]
    end

    RESULT["Hybrid search response\nresults[] with lexical_rank,\nsemantic_rank, rrf_score,\ncosine_similarity, metadata"]

    FALLBACK["Degraded lexical fallback\nretrieval_mode='lexical'\ndegraded=true + warning"]

    QUERY --> AUTH
    AUTH --> TSQUERY
    TSQUERY --> GIN --> LRANK
    AUTH --> EMBED
    EMBED --> COMPAT --> HNSW --> BEST --> SRANK
    LRANK --> RRF
    SRANK --> RRF
    RRF --> NORM --> PAGE --> RESULT

    EMBED -. circuit open / unreachable /\nmodel missing / dimension mismatch .-> FALLBACK
    LRANK --> FALLBACK

    subgraph EXPLAIN["Grounded explanation (optional)"]
        SELECT["Clerk selects 1-5 evidence records"]
        VISCHECK["Visibility check +\ncache lookup"]
        QUEUE["Queue generate_explanation job"]
        CONTEXT["Prepare bounded context\nquery + evidence JSON"]
        LLM["Ollama POST /api/chat\nmodel: qwen3.5:4b\nformat: JSON schema"]
        PARSE["Parse + validate JSON\ncheck evidence IDs subset"]
        AUDIT["Persist AIInferenceRun\nmodel, digest, latency, outcome"]
    end

    RESULT --> SELECT
    SELECT --> VISCHECK
    VISCHECK --> QUEUE --> CONTEXT --> LLM --> PARSE --> AUDIT
```

### Healthy live response shape

```json
{
  "retrieval_mode": "hybrid",
  "degraded": false,
  "warnings": [],
  "total_lexical": 1,
  "total_semantic": 6,
  "results": [
    {
      "lexical_rank": 1,
      "semantic_rank": 1,
      "metadata": {
        "subject": "Community Water Point Rehabilitation"
      }
    }
  ]
}
```

## 5. Indexing and recovery architecture

```mermaid
sequenceDiagram
    participant API as FastAPI
    participant DB as PostgreSQL
    participant W as Durable worker
    participant O as Ollama :11434

    API->>DB: Commit record + audit + outbox + embedding job
    W->>DB: Claim due job with FOR UPDATE SKIP LOCKED
    W->>DB: Read record version and content hash
    W->>W: Create deterministic overlapping chunks
    W->>O: POST /api/embed ordered batch
    O-->>W: 768-dimensional vectors
    W->>DB: Store record_chunks with model digest and chunks-v1

    alt Success
        W->>DB: completed; publish outbox event
    else Temporary failure
        W->>DB: retry at now + min(2^attempt, 3600s)
    else Attempts exhausted
        W->>DB: dead_letter + bounded error
        Note over DB: /readyz becomes not_ready and exposes dead_letter count
    end

    Note over W,DB: Manual recovery records reason, time and previous error,
    Note over W,DB: resets attempts, then requeues the same durable job.
```

Every non-draft record is eligible for chunk indexing. A compatible chunk is
identified by record, chunk index, content hash, model name, exact model digest,
dimension and preprocessing version. Stale or incompatible vectors are excluded
from retrieval.

## 6. Grounded explanation RAG flow

```mermaid
sequenceDiagram
    actor Clerk
    participant API as FastAPI AI router
    participant DB as PostgreSQL
    participant W as Durable worker
    participant LLM as Ollama qwen3.5:4b

    Clerk->>API: Select 1-5 retrieved evidence records
    API->>DB: Enforce review permission and record visibility
    API->>DB: Create/cache AI inference run + durable job
    API-->>Clerk: 202 queued or 200 cached
    W->>DB: Claim explanation job
    W->>LLM: Bounded query + evidence + JSON schema
    LLM-->>W: Structured classification and rationale
    W->>W: Validate IDs, enums and human-review requirement
    W->>DB: Persist result, model digest, latency and outcome
    Clerk->>API: Poll explanation run
    API-->>Clerk: Grounded advisory result; human review required
```

The LLM receives only the selected retrieved evidence. It cannot silently add
records, and its output cannot make or persist a parliamentary decision.

## 7. Startup and readiness sequence

```mermaid
sequenceDiagram
    participant C as Docker Compose
    participant P as PostgreSQL
    participant M as Migrator
    participant A as FastAPI
    participant O as Ollama bridge listener
    participant W as Worker
    participant F as Frontend

    C->>P: Start and wait for pg_isready
    C->>M: Run migrations once
    M->>P: Upgrade to 20260805_0011 and commit
    C->>A: Start API
    C->>W: Start worker
    A->>P: Check connection, schema and dead-letter count
    A->>O: GET /api/tags
    O-->>A: embeddinggemma:300m + qwen3.5:4b
    A-->>C: /readyz 200 ready
    C->>F: Start frontend only after backend is healthy
```

`/livez` and `/health` only prove that the API process is alive. `/readyz` is
the traffic gate and returns HTTP 503 when PostgreSQL/schema is unavailable,
Ollama or its required models are unavailable, or any job is dead-lettered.

## 8. Search and AI data model

```mermaid
erDiagram
    PARLIAMENTARY_RECORDS ||--o{ RECORD_CHUNKS : split_into
    PARLIAMENTARY_RECORDS ||--o{ REVIEW_DECISIONS : reviewed_as
    PARLIAMENTARY_RECORDS ||--o{ BACKGROUND_JOBS : indexed_by
    BACKGROUND_JOBS ||--o{ OUTBOX_EVENTS : publishes
    USERS ||--o{ AI_INFERENCE_RUNS : requests
    AI_INFERENCE_RUNS }o--o{ PARLIAMENTARY_RECORDS : grounded_in

    PARLIAMENTARY_RECORDS {
        uuid id PK
        text subject
        text full_text
        tsvector search_vector
        vector embedding
        text embedding_model
        text status
    }

    RECORD_CHUNKS {
        uuid id PK
        uuid record_id FK
        int chunk_index
        text chunk_text
        text content_hash
        vector_768 embedding
        text embedding_model
        text model_digest
        int dimension
        text preprocessing_version
    }

    BACKGROUND_JOBS {
        uuid id PK
        text job_type
        text status
        int attempt_count
        int max_attempts
        timestamptz next_attempt_at
        jsonb payload
        text last_error
    }

    AI_INFERENCE_RUNS {
        uuid id PK
        text run_type
        text query_hash
        uuid_array evidence_ids
        text model
        text model_digest
        jsonb result
        text outcome
    }
```

## 9. Network and trust boundaries

- Browser input is untrusted and validated again by FastAPI/Pydantic.
- The Next.js BFF keeps the JWT in an HTTP-only cookie and forwards it as a
  Bearer token.
- FastAPI validates persistent session state, permissions and row visibility.
- PostgreSQL queries are parameterized and enforce relational constraints.
- Ollama uses the standard port `11434` and is bound to Docker's bridge address,
  not the public LAN interface. Containers resolve it through
  `host.docker.internal`.
- The embedding model is `embeddinggemma:300m` with dimension 768. Semantic SQL
  only accepts chunks with the active exact model digest and preprocessing
  identity.
- Structured logs contain request IDs, routes, status codes and durations; they
  do not require Prometheus or OpenTelemetry for this prototype.

## 10. Source map

- AI implementation explanation: [ai-explanation.html](ai-explanation.html)
- As-built RAG architecture (HTML): [naive-rag-architecture.html](naive-rag-architecture.html)
- Full system UML component diagram (PlantUML): [diagrams/system-component.puml](diagrams/system-component.puml)
- AI RAG pipeline diagram (Mermaid): [diagrams/ai-rag-pipeline.mmd](diagrams/ai-rag-pipeline.mmd)
- System requirements: [system-specification.md](system-specification.md)
- Implementation status: [implementation-report.md](implementation-report.md)
- File guide: [file-guide.md](file-guide.md)
- Local startup and Ollama binding: [../README.md](../README.md)
