import json
from database import init_db, get_session
from crud import create_job, create_resume, create_score, get_rankings_for_job
from rubric_builder import build_rubric
from resume_parser import extract_text_from_pdf
from resume_structurer import structure_resume
from scoring_agent import score_resume

# Make sure tables exist
init_db()

sample_jd = """
We are seeking a versatile Full Stack Developer with a strong background in IT infrastructure to design, build, and maintain our web applications and internal tools. 
In this role, you will be responsible for the entire software lifecycle, creating responsive frontend user interfaces, developing scalable backend APIs,
managing relational and NoSQL databases, and ensuring seamless integration with our cloud networks and servers (AWS/Azure/Docker).
The ideal candidate possesses deep proficiency in modern JavaScript frameworks (like React or Angular) and server-side languages (such as Node.js or Python),
combined with a solid understanding of network security, systems administration, and DevOps pipelines to keep our production environments stable and secure.
"""

db = get_session()

try:
    # Step 1: Create the job (generates + saves the rubric)
    rubric = build_rubric(sample_jd)
    job = create_job(db, title="Backend Developer", raw_description=sample_jd, rubric=rubric)

    # Step 2: Process multiple resumes against this ONE saved job
    resume_paths = ["data/sample_pdf_1.pdf", "data/sample_pdf_2.pdf", "data/sample_pdf_3.pdf", "data/sample_pdf_4.pdf"]

    for path in resume_paths:
        cleaned_text = extract_text_from_pdf(path)
        if cleaned_text is None:
            print(f"Skipping {path} - could not extract text")
            continue

        resume_data = structure_resume(cleaned_text)
        resume_record = create_resume(
            db,
            job_id=job.id,
            filename=path,
            raw_text=cleaned_text,
            parsed_data=resume_data
        )

        scoring_result = score_resume(resume_data, rubric)
        create_score(db, resume_id=resume_record.id, job_id=job.id, scoring_result=scoring_result)

    # Step 3: Read back the full ranking for this job
    rankings = get_rankings_for_job(db, job.id)

    print(f"\n{'='*60}")
    print(f"RANKINGS FOR JOB: {job.title} (job_id={job.id})")
    print('='*60)
    for i, entry in enumerate(rankings, start=1):
        print(f"\n#{i}. {entry['filename']} - {entry['total_score']}/10")
        print(f"    {entry['summary']}")

finally:
    db.close()