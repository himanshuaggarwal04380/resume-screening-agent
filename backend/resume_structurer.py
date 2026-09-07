import ollama
import json
import re
import os
from logger_config import get_logger
from config import LLM_MODEL

logger = get_logger(os.path.splitext(os.path.basename(__file__))[0])

PROMPT_TEMPLATE = """You are an expert resume analyst. Extract structured information from the resume text below.

STRICT RULES:
1. A "role" is ONLY a position at a real employer/organization the candidate worked for (a job, internship, or formal position). The company name must be an actual organization name — never a project name, product name, or app name the candidate built themselves.
2. A common mistake to avoid: resumes often list self-built systems/products under headings that sound like experience, such as "Real-World Software Experience", "Professional Experience (Projects)", or similar. If the "company" you would write is actually just the name of a system/app/product the candidate personally built — not a distinct organization that employed them — this belongs under "projects", NOT "roles", regardless of what the section heading says.
3. Never invent a job title. Only use a title if the resume explicitly states one. If no explicit title is given for a genuine role, use "Not specified" rather than guessing.
4. For ANY field where the true value is not explicitly present in the text, use null. NEVER substitute nearby unrelated text (e.g. a location, a CGPA, or an unrelated line) just to fill the field. It is always better to return null than to guess.
5. Only extract information explicitly present in the text. Do not infer or fabricate details.

EXAMPLE OF RULE 2:
If the resume text contains:
"Clinic Management System | Dec 2025 - Present
React, Node.js, Express.js, SQLite
Independently designed and developed a full-stack healthcare management system..."

This is a PROJECT, not a role. It should be extracted as:
{{"name": "Clinic Management System", "summary": "Independently designed and developed a full-stack healthcare management system...", "tech_used": ["React", "Node.js", "Express.js", "SQLite"]}}
It must NOT appear under "roles".

EXAMPLE OF RULE 4:
If the resume text contains:
"B.Tech in Computer Science, Bennett University
CGPA: 7.59/10.00, Greater Noida, Uttar Pradesh"

There is no year range stated here. Extract it as:
{{"degree": "B.Tech in Computer Science", "institution": "Bennett University", "years": null}}
Do NOT write "years": "Greater Noida, Uttar Pradesh" — that is a location, not a year, and must not be used to fill the field.

SKILL CATEGORIZATION:
Split all skills into exactly two groups:
- "technical_skills": programming languages, frameworks, tools, libraries, databases, and technical/domain concepts (e.g. Python, React, SQL, Machine Learning, REST APIs)
- "soft_skills": communication, leadership, teamwork, and other interpersonal/non-technical skills (e.g. Communication, Leadership, Adaptability, Time Management)

Return ONLY valid JSON — no explanation, no markdown formatting, just the raw JSON object. The object must have exactly these fields:
- "name": candidate's full name (string)
- "email": candidate's email if present, else null
- "phone": candidate's phone number if present, else null
- "skills": an object with two fields, "technical_skills" and "soft_skills" (each an array of strings), per the categorization rules above
- "years_of_experience": estimated total years of professional experience as a number (use 0 if the candidate appears to be a student/fresher with no real employer-based work experience — never count personal projects toward this)
- "education": a list of objects, each with "degree", "institution", and "years" (use null for "years" if not explicitly stated — see Rule 4)
- "roles": a list of objects, each with "title", "company", and "duration" — per the strict rules above
- "projects": a list of objects, each with "name", "summary", and "tech_used" (array of strings listing the technologies/tools used in that specific project)

Resume Text:
{resume_text}
"""

def extract_json_from_response(raw_text: str) -> str:
    # Look for a fenced code block anywhere in the text (not just at the start)
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", raw_text, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    # No fence found - figure out whether the JSON is an object {..} or array [..],
    # by checking whichever opening character appears first in the text
    brace_start = raw_text.find("{")
    bracket_start = raw_text.find("[")

    if brace_start == -1 and bracket_start == -1:
        return raw_text.strip()  # no JSON structure found at all

    if bracket_start != -1 and (brace_start == -1 or bracket_start < brace_start):
        start, end = bracket_start, raw_text.rfind("]")
    else:
        start, end = brace_start, raw_text.rfind("}")

    if start != -1 and end != -1 and end > start:
        return raw_text[start:end + 1].strip()

    return raw_text.strip()

def clean_email(email: str | None) -> str | None:
    if not email:
        return email
    return re.sub(r"^[^\w]+", "", email)


def validate_structured_resume(data: dict) -> None:
    required_fields = {"name", "email", "phone", "skills", "years_of_experience", "education", "roles", "projects"}
    missing = required_fields - data.keys()
    if missing:
        raise ValueError(f"Structured resume missing fields: {missing}")

    if not isinstance(data["skills"], dict):
        raise ValueError("'skills' must be an object with 'technical_skills' and 'soft_skills'")
    if "technical_skills" not in data["skills"] or "soft_skills" not in data["skills"]:
        raise ValueError("'skills' must contain both 'technical_skills' and 'soft_skills'")
    if not isinstance(data["skills"]["technical_skills"], list) or not isinstance(data["skills"]["soft_skills"], list):
        raise ValueError("'technical_skills' and 'soft_skills' must both be lists")

    if not isinstance(data["education"], list):
        raise ValueError("'education' must be a list")
    if not isinstance(data["roles"], list):
        raise ValueError("'roles' must be a list")
    if not isinstance(data["projects"], list):
        raise ValueError("'projects' must be a list")


def structure_resume(resume_text: str, max_retries: int = 3) -> dict:
    prompt = PROMPT_TEMPLATE.format(resume_text=resume_text)

    last_error = None

    for attempt in range(1, max_retries + 1):
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )

        raw_text = response["message"]["content"].strip()
        logger.debug(f"Attempt {attempt} raw LLM response:\n{raw_text!r}")

        json_text = extract_json_from_response(raw_text)

        try:
            data = json.loads(json_text)
            validate_structured_resume(data)
            data["email"] = clean_email(data.get("email"))
            logger.info(f"Successfully structured resume for: {data.get('name', 'unknown')}")
            logger.debug(f"Final structured resume:\n{json.dumps(data, indent=2)}")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            logger.warning(f"Attempt {attempt} failed to structure resume: {e}. Retrying...")

    logger.error(f"Failed to structure resume after {max_retries} attempts. Last error: {last_error}")
    raise RuntimeError(f"Failed to structure resume after {max_retries} attempts. Last error: {last_error}")



if __name__ == "__main__":
    from resume_parser import extract_text_from_pdf

    sample_path = "data/sample_pdf_2.pdf"
    cleaned_text = extract_text_from_pdf(sample_path)

    if cleaned_text is None:
        print("Could not extract text from sample PDF.")
    else:
        result = structure_resume(cleaned_text)
        logger.debug(f"Final structured resume:\n{json.dumps(result, indent=2)}")
        print(json.dumps(result, indent=2))