   # AI Resume Screening Agent with Bias Audit

   ## Problem Statement
   Recruiters screen hundreds of resumes per job posting with too little time
   per candidate, which leads to missed qualified candidates and unconscious
   bias (based on names, colleges, employment gaps, etc.) creeping into
   decisions. Most AI resume screeners automate scoring but never verify
   fairness. This project screens resumes against a transparent, editable
   rubric AND actively audits its own scoring for demographic bias using
   paired test resumes.

   ## Tech Stack
   - Backend: FastAPI (Python)
   - Frontend: Streamlit
   - Database: SQLite (dev) → PostgreSQL (deployment)
   - ORM: SQLAlchemy
   - PDF parsing: pdfplumber
   - Bias statistics: pandas + scipy

   ## Status
   🚧 In development — Phase 2 complete.

   ## Project Structure
```
   backend/   → FastAPI app, database models, core logic
   frontend/  → Streamlit UI
   tests/     → test scripts
   data/      → sample resumes and test fixtures
```