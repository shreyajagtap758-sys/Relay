# Relay

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141.1-009688.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)](https://www.sqlalchemy.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A durable, crash-resilient distributed background job execution engine built on top of **PostgreSQL transactional primitives**. 

> **Zero Redis. Zero RabbitMQ. Zero Celery.**
> One relational table, atomic state transitions, and strict durability guarantees.

---

## 🎯 The Core Contract

Relay is designed around five non-negotiable distributed execution invariants:

* **Durability First:** An accepted job is never lost across API crashes, DB restarts, or worker failures.
* **At-Least-Once Execution:** Jobs surviving node/process crashes are guaranteed to be recovered and executed.
* **Bounded Retries & DLQ:** Transient failures retry with backoff; exhausted attempts route to Dead Letter Queue.
* **Deterministic Traceability:** Exact state and lifecycle stage is queryable in real-time.
* **Clean Transaction Boundaries:** Non-database execution I/O is decoupled from row locks to prevent connection starvation.

---

## 📐 Architecture & Flow

```mermaid
flowchart TD
    Client([HTTP Client]) -->|POST /jobs| API[FastAPI Ingress]
    API -->|1. INSERT ... RETURNING\n2. COMMIT| DB[(PostgreSQL\njobs table)]
    API -->|202 Accepted| Client

    Worker[Worker Process] -->|1. SELECT ... FOR UPDATE\n2. UPDATE status='running'\n3. COMMIT| DB
    Worker -->|Execute Handler\nZero DB Locks Held| Handler[Async Task Execution]
    Handler -->|1. UPDATE status='succeeded'/'failed'\n2. COMMIT| DB

    Reaper[Reaper Loop\nWeek 2] -.->|Heartbeat / Lease Timeout\nReset running to pending| DB
```

---

## 🔄 State Machine

Every state transition is enforced via **atomic Compare-and-Set (CAS)**:

```mermaid
stateDiagram-v2
    [*] --> pending : POST /jobs (Committed)
    pending --> running : Worker Claim (CAS Guarded)
    running --> succeeded : Execution Success
    running --> failed : Handler Exception
    failed --> pending : Retry (Exponential Backoff)
    failed --> dead_letter : Max Attempts Exhausted
```

#### Guarded Atomic Transition Primitive
```sql
UPDATE jobs 
SET status = 'running' 
WHERE id = $1 AND status = 'pending';
```
> If `rowcount == 0`, a concurrent writer or lease reaper modified the state first. The worker yields immediately without clobbering external state.

---

## ⚡ Quickstart

### 1. Start Infrastructure & App
```bash
# Start PostgreSQL container
docker compose up -d

# Run database migrations
alembic upgrade head

# Terminal 1: Start API Server
uvicorn src.main:app --reload

# Terminal 2: Start Worker Process
python -m src.worker
```

### 2. Enqueue & Inspect Jobs
```powershell
# Enqueue a background job
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/jobs `
  -ContentType application/json `
  -Body '{"type":"sleep","payload":{}}'

# Query job execution status
Invoke-RestMethod http://127.0.0.1:8000/jobs/1
```

---

## 🛠️ Key Architectural Decisions

Comprehensive rationale and trade-offs documented in [`docs/DECISIONS.md`](docs/DECISIONS.md).

| Component | Design Choice | Systems Rationale |
|---|---|---|
| **Storage Engine** | PostgreSQL (`jobs` table) | Native ACID durability; `COMMIT` guarantees zero-loss ingress without an external broker. |
| **Identity Model** | DB-generated `bigint` | Primary Key and future Idempotency Keys are decoupled into separate concerns. |
| **Status Domain** | `TEXT` + `CHECK` constraint | Avoids Postgres enum `DROP VALUE` lock hazards and migration incompatibilities. |
| **Ingress Bounds** | HTTP Middleware byte bound | Drops oversized requests before reading/parsing body into application memory. |
| **Lock Discipline** | Claim commit before handler | Decouples execution latency from Postgres row locks, eliminating `idle in transaction` hazards. |
| **Signal Handling** | Custom `SIGINT`/`SIGTERM` hooks | Enforces *finish-current* graceful shutdown (exit code 0) without leaving abandoned in-flight rows. |

---

## 🗺️ Project Roadmap

- [x] **Week 1: Core Engine**
  - Durable `jobs` schema & migrations
  - `POST /jobs` (202 Accepted) and `GET /jobs/{id}` endpoints
  - Single-transaction claim query (`SELECT FOR UPDATE` + CAS guard)
  - Decoupled worker loop & dynamic Handler Registry
  - Finish-current graceful shutdown lifecycle
- [ ] **Week 2: Crash Resilience & Recovery**
  - Worker leases, heartbeats & background Reaper process
  - Bounded exponential retries & Dead Letter Queue (`dead_letter`)
- [ ] **Week 3: Exactly-Once Processing**
  - Idempotency keys, request deduplication, side-effect isolation
- [ ] **Week 4: Production Hardening & Benchmarking**
  - `EXPLAIN ANALYZE` index tuning, stream rate-limiting, load testing

---

## 📁 Repository Layout

```text
src/
├── main.py        # FastAPI endpoints (POST /jobs, GET /jobs/{id})
├── worker.py      # Worker polling, claim-execute-mark loop, signal handling
├── models.py      # SQLAlchemy declarative models & schema constraints
├── schemas.py     # Pydantic v2 validation contracts
├── database.py    # Asyncpg connection pooling & engine configuration
└── middleware.py  # Ingress payload size-limiting middleware
alembic/           # Schema migration revisions
docs/              # Architecture Decision Records (ADRs) & empirical logs
```

---

## 📄 License
MIT