from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text


from relay.db import get_db
from relay.models import Job
from relay.middleware import limit_payload_size
from relay.schema import JobCreateRequest, JobCreateResponse, JobStatusResponse


app = FastAPI(title="Relay API")

#register ingress middleware
app.middleware("http")(limit_payload_size)
#check size before doing anything

import hashlib
import json
from sqlalchemy.exc import IntegrityError


def request_fingerprint(job_type: str, payload: dict) -> str:
    # Canonical JSON: sort_keys=True ensure karta hai ki key order se hash na badle
    canonical_payload = json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    )
    raw = f"{job_type.strip()}:{canonical_payload}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_exc_metadata(exc: Exception):
    objects = [
        exc,
        getattr(exc, "orig", None),
        getattr(getattr(exc, "orig", None), "__cause__", None),
    ]
    state = next(
        (
            getattr(o, name)
            for o in objects
            if o
            for name in ("sqlstate", "pgcode")
            if getattr(o, name, None)
        ),
        None,
    )
    constraint = next(
        (
            getattr(o, "constraint_name")
            for o in objects
            if o and getattr(o, "constraint_name", None)
        ),
        None,
    )
    return state, constraint


@app.post(
    "/jobs",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def create_job(
        request_data: JobCreateRequest,
        db: AsyncSession = Depends(get_db)
):
    fp = (
        request_fingerprint(request_data.type, request_data.payload)
        if request_data.idempotency_key
        else None
    )

    new_job = Job(
        type=request_data.type,
        payload=request_data.payload,
        idempotency_key=request_data.idempotency_key,
        request_fingerprint=fp,
    )

    db.add(new_job)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        state, constraint = get_exc_metadata(exc)
        if state == "23505" and constraint == "uq_jobs_idempotency_key":
            result = await db.execute(
                select(Job).where(Job.idempotency_key == request_data.idempotency_key)
            )
            existing = result.scalar_one()
            if existing.request_fingerprint != fp:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "idempotency_key_mismatch",
                        "job_id": existing.id,
                    },
                )
            return JobCreateResponse(
                job_id=existing.id,
                status=existing.status,
            )
        # Unrelated integrity errors (e.g. jobs_status_check) must not be treated as replay
        print(f"[API] Integrity error: state={state}, constraint={constraint}", flush=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Integrity violation: {constraint or state}",
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue job securely."
        )

    return JobCreateResponse(
        job_id=new_job.id,
        status=new_job.status
    )


@app.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse
)
async def get_job_status(
        job_id: int,
        db: AsyncSession = Depends(get_db)
):
    query = select(Job).where(Job.id == job_id)
    result = await db.execute(query)
    db_job = result.scalar_one_or_none()

    if db_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found."
        )

    return db_job

# result : {"id":1,"type":"send_email","payload":{"to":"vikas@example.com"},"status":"pending","attempts":0,"created_at":"2026-08-15T19:30:03.022215Z","updated_at":"2026-08-15T19:30:03.022215Z"}
# status : 200 ok

#entered random job id : {"detail":"Job not found."} status : 404 not found
#empty 'type' inputted : {
  #"detail": [
   # {
     # "type": "string_too_short",
    #  "loc": ["body", "type"],
    #  "msg": "String should have at least 1 character",
    #  "input": ""
    #}
  #]
#} status : 422 unprocessable entity

# make new job, job_id : 2, close the serve(API KILL), architecture : fastapi -> db commit job first -> server restart -> same job id query again (get job/2)(job not lost) -> it returned valid 200 ok -> durability pass.


