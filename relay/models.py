from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Integer,
    Text,
    func,
    text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    ) # job/40

    type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    ) # email, sleep, boom etc

    payload: Mapped[dict] = mapped_column(
        JSONB, # keys stay sorted + space efficient and query can be run in JSON
        nullable=False,
        server_default=text("'{}'::jsonb"),
    ) # {"to": "user@example.com"}

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'pending'"),
    ) # pending, running, succeeded, dead_letter, failed

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    ) # how many times a job was claimed (max attempt = 3)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ) # when job was created

    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    ) # job claimed TIME, heartbeat extends this timer to avoid reaper reclaim

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ) # when was a job record was updated last

    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    ) # when job fails, immediate retry is avoided, so this says when a job can be claimed/attempted.
    # jobs are picked where next attempt at IS NULL OR <= now()

    idempotency_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    ) # enqueue dedup : Client sends this id within their request to avoid same request make two rows.

    request_fingerprint: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    ) # Client's request type and payload's SHA-256 hash
    # client sends same idempotency key(same req) and changed payload to get accepted
    # fingerprint hash changes and sees this does not contain same data.

    claim_generation: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default="0"
    ) # each worker gets a generation number for each job,
    # job 12 => worker A has gen = 3, worker B has gen = 4, A checks if job 12 has 3 != 4
    # so A is stale worker, and it cant overwrite B's execution. = fencing token

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    ) # job completed time(created_at, claimed_at, completed_at) = to process latency

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    ) # a job's latest failure error message, eg : last_error = "timeout"



    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed', 'dead_letter')",
            name="jobs_status_check",
        ),
        UniqueConstraint(
            "idempotency_key",
            name="uq_jobs_idempotency_key"
        ),
    )

# how many workers has attempts/dispatches on a job
class JobExecution(Base):
    __tablename__ = "job_executions"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    job_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    worker_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ) # what exact milisec did the worker started a job, used in calculating overlap b/w two workers.

    claim_generation: Mapped[int] = mapped_column(
        BigInteger,
        nullable=True
    )



# in real how much effect/work was committed
class SideEffect(Base):
    __tablename__ = "side_effects"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    job_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )

    worker_id: Mapped[str] = mapped_column(Text, nullable=False)

    action: Mapped[str] = mapped_column(
        Text,
        nullable=False, default="email"
    ) # lets say action email bhejna tha ( 2 bar same email bhejna test)

    effect_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )  # eg : 'job:42:email', duplication exist, side eff stays exactly 1 still.
    # due to unique constraint, db doesn't allow duplicate writes

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("effect_key", name="uq_side_effects_effect_key"),
    ) # protected ledger

# external HTTP API service call krne wale kaam idhr aagye, dispatcher isme se uthake sink(external) ko dega
class Outbox(Base):
    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    job_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    effect_key: Mapped[str] = mapped_column(Text, nullable=False)
    # AT LEAST ONCE DELIVERY, retries me ye key whi rhegi. eg : job:65:email

    payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    ) # {"to": "alice@example.com", "subject": "Hi"}

    dispatched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    ) # if NULL = not dispatched yet, if has time_stamp = dispatched success.

    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    ) # dispatching attempts

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # external API server down(500, timeout), short error log recorded

# EXTERNAL API SERVICE(RECEIVER SIDE)
class SinkDelivery(Base):
    __tablename__ = "sink_deliveries"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    idempotency_key: Mapped[str] = mapped_column(
        Text, nullable=False
    ) # EXACTLY ONCE DELIVERY : same request, reject one.

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    ) # first request received at time

    body: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    ) # data deliver hua uska payload.

    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_sink_deliveries_idempotency_key"),
    )

