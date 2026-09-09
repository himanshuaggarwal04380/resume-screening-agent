from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from database import init_db, get_session
from crud import create_job
from rubric_builder import build_rubric
from schemas import JobCreateRequest, JobResponse
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