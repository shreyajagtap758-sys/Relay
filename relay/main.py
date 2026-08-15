from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from relay.db import get_db
from relay.models import Job
from relay.schema import JobCreateRequest, JobCreateResponse, JobStatusResponse

app = FastAPI(title="Relay API")


@app.post(
    "/jobs",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED # success response default : 202(accepted) not 200 (ok)
)
async def enqueue_job(
        request_data: JobCreateRequest,
        db: AsyncSession = Depends(get_db)
):
    new_job = Job(
        type=request_data.type,
        payload=request_data.payload
    )

    db.add(new_job)

    try:
        # Jab commit call hoga, Postgres RETURNING statement se auto-incremented ID fetch
        # karke new_job object me map kar dega.
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue job securely."
        )

    # new_job.id ab populated hai humare response ke liye
    return JobCreateResponse(
        job_id=new_job.id,
        status=new_job.status
    )
# result shows : job_id    status
#                  1      pending -> while terminal : 202 accepted


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


