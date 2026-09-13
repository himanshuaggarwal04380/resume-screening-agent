from fastapi import FastAPI, Depends , HTTPException , UploadFile, File
from sqlalchemy.orm import Session

from database import init_db, get_session
from rubric_builder import build_rubric
import json
from crud import create_job, update_job_rubric, get_rankings_for_job, get_job, create_resume, create_score, get_resume_by_id, get_score_for_resume
from schemas import JobCreateRequest, JobResponse, RubricUpdateRequest, RankingsResponse, ResumeUploadResult, BulkUploadResponse, ResumeDetailResponse
import os
import shutil
from typing import List
from resume_parser import extract_text_from_pdf
from resume_structurer import structure_resume
from scoring_agent import score_resume



app = FastAPI(title="Resume Screening Agent API")
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


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
    try:
        job = update_job_rubric(db, job_id, request.rubric)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid rubric: {e}")

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job with id {job_id} not found")

    return JobResponse(
        id=job.id,
        title=job.title,
        raw_description=job.raw_description,
        rubric=json.loads(job.rubric_json)
    )

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

@app.get("/resumes/{resume_id}", response_model=ResumeDetailResponse)
def get_resume_endpoint(resume_id: int, db: Session = Depends(get_db)):
    resume = get_resume_by_id(db, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail=f"Resume with id {resume_id} not found")

    score = get_score_for_resume(db, resume_id)

    return ResumeDetailResponse(
        id=resume.id,
        job_id=resume.job_id,
        filename=resume.filename,
        parsed_data=json.loads(resume.parsed_json),
        total_score=score.total_score if score else None,
        criteria_breakdown=json.loads(score.criteria_breakdown_json) if score else None,
        summary=score.justification_text if score else None
    )
    

@app.post("/jobs/{job_id}/resumes", response_model=BulkUploadResponse)
def upload_resumes_endpoint(job_id: int, files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job with id {job_id} not found")

    rubric = json.loads(job.rubric_json)
    results = []

    for upload in files:
        file_path = os.path.join(UPLOAD_DIR, upload.filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(upload.file, f)

        cleaned_text = extract_text_from_pdf(file_path)
        if cleaned_text is None:
            results.append(ResumeUploadResult(
                filename=upload.filename, status="failed", error="Could not extract text from PDF"
            ))
            continue

        try:
            resume_data = structure_resume(cleaned_text)
        except RuntimeError as e:
            results.append(ResumeUploadResult(
                filename=upload.filename, status="failed", error=f"Structuring failed: {e}"
            ))
            continue

        resume_record = create_resume(
            db, job_id=job_id, filename=upload.filename, raw_text=cleaned_text, parsed_data=resume_data
        )

        try:
            scoring_result = score_resume(resume_data, rubric)
        except RuntimeError as e:
            results.append(ResumeUploadResult(
                filename=upload.filename, status="failed", resume_id=resume_record.id, error=f"Scoring failed: {e}"
            ))
            continue

        create_score(db, resume_id=resume_record.id, job_id=job_id, scoring_result=scoring_result)

        results.append(ResumeUploadResult(
            filename=upload.filename,
            status="success",
            resume_id=resume_record.id,
            total_score=scoring_result["total_score"]
        ))
        
        
    return BulkUploadResponse(job_id=job_id, results=results)