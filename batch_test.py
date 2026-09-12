import os
import sys
import time

sys.path.append("backend")

from database import init_db, get_session
from crud import create_job, create_resume, create_score
from rubric_builder import build_rubric
from resume_parser import extract_text_from_pdf
from resume_structurer import structure_resume
from scoring_agent import score_resume

# ---- EDIT THESE ----
RESUME_FOLDER = "C:/Users/himan/Downloads/resumes/resumes"  # path to your folder of 180+ PDFs
JOB_TITLE = "AI Professional"
JOB_DESCRIPTION = """
We are looking for an AI professional who can design, develop, and implement AI/ML solutions using modern technologies such as LLMs, RAG, NLP, and machine learning. The role involves building intelligent applications, integrating AI APIs, working with data, optimizing models, and collaborating with the team to deliver scalable and innovative AI solutions.

"""
# ---------------------

init_db()
db = get_session()

stats = {"total": 0, "extraction_failed": 0, "structuring_failed": 0, "scoring_failed": 0, "succeeded": 0}
start_time = time.time()

try:
    rubric = build_rubric(JOB_DESCRIPTION)
    job = create_job(db, title=JOB_TITLE, raw_description=JOB_DESCRIPTION, rubric=rubric)
    print(f"Created job_id={job.id} with {len(rubric)} criteria\n")

    pdf_files = [f for f in os.listdir(RESUME_FOLDER) if f.lower().endswith(".pdf")]
    stats["total"] = len(pdf_files)
    print(f"Found {stats['total']} resumes to process\n")

    for i, filename in enumerate(pdf_files, start=1):
        file_path = os.path.join(RESUME_FOLDER, filename)
        elapsed_min = (time.time() - start_time) / 60
        print(f"[{i}/{stats['total']}] ({elapsed_min:.1f} min elapsed) Processing {filename}...")

        cleaned_text = extract_text_from_pdf(file_path)
        if cleaned_text is None:
            print(f"  SKIPPED - extraction failed")
            stats["extraction_failed"] += 1
            continue

        try:
            resume_data = structure_resume(cleaned_text)
        except RuntimeError as e:
            print(f"  SKIPPED - structuring failed: {e}")
            stats["structuring_failed"] += 1
            continue

        resume_record = create_resume(
            db, job_id=job.id, filename=filename, raw_text=cleaned_text, parsed_data=resume_data
        )

        try:
            scoring_result = score_resume(resume_data, rubric)
        except RuntimeError as e:
            print(f"  Resume saved, but scoring failed: {e}")
            stats["scoring_failed"] += 1
            continue

        create_score(db, resume_id=resume_record.id, job_id=job.id, scoring_result=scoring_result)
        print(f"  Done - scored {scoring_result['total_score']}/10")
        stats["succeeded"] += 1

finally:
    db.close()
    total_min = (time.time() - start_time) / 60
    print(f"\n{'='*50}")
    print(f"BATCH COMPLETE in {total_min:.1f} minutes")
    print(f"Total: {stats['total']}")
    print(f"Succeeded: {stats['succeeded']}")
    print(f"Extraction failed: {stats['extraction_failed']}")
    print(f"Structuring failed: {stats['structuring_failed']}")
    print(f"Scoring failed: {stats['scoring_failed']}")
    print('='*50)