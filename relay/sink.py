import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import insert, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from relay.db import async_session, engine
from relay.models import SinkDelivery

DEDUP_OFF = os.getenv("DEDUP_OFF", "0") == "1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure constraint matches dedup switch mode
    async with engine.begin() as conn:
        if DEDUP_OFF:
            await conn.execute(
                text(
                    "ALTER TABLE sink_deliveries DROP CONSTRAINT IF EXISTS uq_sink_deliveries_idempotency_key;"
                )
            )
        else:
            await conn.execute(
                text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'uq_sink_deliveries_idempotency_key'
                    ) THEN
                        DELETE FROM sink_deliveries a USING sink_deliveries b
                        WHERE a.id > b.id AND a.idempotency_key = b.idempotency_key;
                        ALTER TABLE sink_deliveries ADD CONSTRAINT uq_sink_deliveries_idempotency_key UNIQUE (idempotency_key);
                    END IF;
                END $$;
                """)
            )
    yield


app = FastAPI(title="Relay Sink Receiver", lifespan=lifespan)


class DeliveryRequest(BaseModel):
    idempotency_key: str
    job_id: int = 0
    body: dict = {}


@app.post("/deliver")
async def deliver(req: DeliveryRequest):
    key = req.idempotency_key
    async with async_session() as session:
        async with session.begin():
            if DEDUP_OFF:
                stmt = insert(SinkDelivery).values(
                    idempotency_key=key,
                    body=req.body,
                )
                await session.execute(stmt)
                result = "applied"
            else:
                stmt = (
                    pg_insert(SinkDelivery)
                    .values(
                        idempotency_key=key,
                        body=req.body,
                    )
                    .on_conflict_do_nothing(
                        constraint="uq_sink_deliveries_idempotency_key"
                    )
                )
                res = await session.execute(stmt)
                if res.rowcount == 1:
                    result = "applied"
                else:
                    result = "duplicate"

    print(f"[deliver] idempotency_key={key} result={result}", flush=True)
    return {"result": result, "idempotency_key": key}
