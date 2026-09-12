import json
from sqlalchemy.orm import Session
from models import Job, Resume, Score
from logger_config import get_logger
import os

logger = get_logger(os.path.splitext(os.path.basename(__file__))[0])


def create_job(db: Session, title: str, raw_description: str, rubric: list[dict]) -> Job:
    job = Job(
        title=title,
        raw_description=raw_description,
        rubric_json=json.dumps(rubric)
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info(f"Created job '{title}' with id {job.id}")
    return job


def get_job(db: Session, job_id: int) -> Job | None:
    return db.query(Job).filter(Job.id == job_id).first()

def update_job_rubric(db: Session, job_id: int, rubric: list[dict]) -> Job | None:
    job = get_job(db, job_id)
    if job is None:
        return None

    job.rubric_json = json.dumps(rubric)
    db.commit()
    db.refresh(job)
    logger.info(f"Updated rubric for job_id {job_id}")
    return job


def get_job_rubric(db: Session, job_id: int) -> list[dict] | None:
    job = get_job(db, job_id)
    if job is None:
        return None
    return json.loads(job.rubric_json)


def create_resume(db: Session, job_id: int, filename: str, raw_text: str, parsed_data: dict) -> Resume:
    resume = Resume(
        job_id=job_id,
        filename=filename,
        raw_text=raw_text,
        parsed_json=json.dumps(parsed_data)
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    logger.info(f"Saved resume '{filename}' for job_id {job_id} with id {resume.id}")
    return resume


def get_resumes_for_job(db: Session, job_id: int) -> list[Resume]:
    return db.query(Resume).filter(Resume.job_id == job_id).all()


def create_score(db: Session, resume_id: int, job_id: int, scoring_result: dict) -> Score:
    score = Score(
        resume_id=resume_id,
        job_id=job_id,
        total_score=scoring_result["total_score"],
        criteria_breakdown_json=json.dumps(scoring_result["criteria_breakdown"]),
        justification_text=scoring_result.get("summary", "")
    )
    db.add(score)
    db.commit()
    db.refresh(score)
    logger.info(f"Saved score for resume_id {resume_id}: {score.total_score}/10")
    return score


def get_rankings_for_job(db: Session, job_id: int) -> list[dict]:
    scores = db.query(Score).filter(Score.job_id == job_id).order_by(Score.total_score.desc()).all()

    rankings = []
    for score in scores:
        resume = db.query(Resume).filter(Resume.id == score.resume_id).first()
        rankings.append({
            "resume_id": score.resume_id,
            "filename": resume.filename if resume else "Unknown",
            "total_score": score.total_score,
            "criteria_breakdown": json.loads(score.criteria_breakdown_json),
            "summary": score.justification_text
        })
        


    return rankings