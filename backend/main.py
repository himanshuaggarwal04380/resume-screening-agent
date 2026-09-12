from fastapi import FastAPI, Depends , HTTPException
from sqlalchemy.orm import Session

from database import init_db, get_session
from crud import create_job , update_job_rubric
from rubric_builder import build_rubric
from schemas import JobCreateRequest, JobResponse , RubricUpdateRequest
import json



app = FastAPI(title="Resume Screening Agent API")


@app.on_event("startup")
def on_startup():
    init_db()


def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()


@app.post("/jobs", response_model=JobResponse)
def create_job_endpoint(request: JobCreateRequest, db: Session = Depends(get_db)):
    rubric = build_rubric(request.raw_description)
    job = create_job(
        db,
        title=request.title,
        raw_description=request.raw_description,
        rubric=rubric
    )

    return JobResponse(
        id=job.id,
        title=job.title,
        raw_description=job.raw_description,
        rubric=json.loads(job.rubric_json)
    )
    
@app.put("/jobs/{job_id}/rubric", response_model=JobResponse)
def update_rubric_endpoint(job_id: int, request: RubricUpdateRequest, db: Session = Depends(get_db)):
    job = update_job_rubric(db, job_id, request.rubric)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job with id {job_id} not found")

    return JobResponse(
        id=job.id,
        title=job.title,
        raw_description=job.raw_description,
        rubric=json.loads(job.rubric_json)
    )
    
from crud import create_job, update_job_rubric, get_rankings_for_job, get_job
from schemas import JobCreateRequest, JobResponse, RubricUpdateRequest, RankingsResponse


@app.get("/jobs/{job_id}/rankings", response_model=RankingsResponse)
def get_rankings_endpoint(job_id: int, db: Session = Depends(get_db)):
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job with id {job_id} not found")

    rankings = get_rankings_for_job(db, job_id)

    return RankingsResponse(
        job_id=job.id,
        job_title=job.title,
        rankings=rankings
    )