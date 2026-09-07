import ollama
import json
import os
from logger_config import get_logger
from resume_structurer import extract_json_from_response
from config import LLM_MODEL

logger = get_logger(os.path.splitext(os.path.basename(__file__))[0])

PROMPT_TEMPLATE = """You are an expert technical recruiter scoring a candidate against a job rubric.

STRICT RULES:
1. Score each criterion independently on a scale of 1-10, where 1 means no relevant evidence found and 10 means strong, explicit evidence.
2. Every justification MUST reference specific evidence actually present in the structured resume data below (a specific skill, project, role, or education entry). Do not reference anything not present in the resume data.
3. If the resume shows NO relevant evidence for a criterion, you MUST give it a score of 1 and the justification must be exactly: "No evidence found for this criterion in the resume."
4. Do not calculate or include any overall/total score — only score each criterion individually. The total will be calculated separately.
5. Do not invent, assume, or infer skills, experience, or qualifications that are not explicitly present in the resume data.

Rubric (criteria to score against):
{rubric_json}

Structured Resume Data:
{resume_json}

Return ONLY valid JSON — no explanation, no markdown formatting. The JSON must be an array where each item has exactly these fields:
- "criterion": the exact criterion name from the rubric (must match exactly)
- "score": integer from 1 to 10
- "justification": one sentence, grounded in specific resume evidence, or the exact "no evidence" sentence from Rule 3
"""


def validate_scores(scores: list[dict], rubric: list[dict]) -> None:
    if not isinstance(scores, list) or len(scores) == 0:
        raise ValueError("Scores must be a non-empty list")

    rubric_criteria = {item["criterion"] for item in rubric}
    scored_criteria = {item.get("criterion") for item in scores}

    missing = rubric_criteria - scored_criteria
    if missing:
        raise ValueError(f"Missing scores for criteria: {missing}")

    for item in scores:
        required_fields = {"criterion", "score", "justification"}
        missing_fields = required_fields - item.keys()
        if missing_fields:
            raise ValueError(f"Score item missing fields: {missing_fields}")

        if not isinstance(item["score"], (int, float)):
            raise ValueError(f"Score for {item['criterion']} is not a number: {item['score']}")

NO_EVIDENCE_PHRASES = ["no evidence", "not mentioned", "no relevant experience", "not explicitly mentioned"]

def normalize_no_evidence_scores(scores: list[dict]) -> list[dict]:
    for item in scores:
        justification_lower = item["justification"].lower()
        implies_no_evidence = any(phrase in justification_lower for phrase in NO_EVIDENCE_PHRASES)

        if implies_no_evidence and item["score"] != 1:
            logger.debug(
                f"Correcting '{item['criterion']}': justification implies no evidence "
                f"but score was {item['score']}. Forcing to 1."
            )
            item["score"] = 1
            item["justification"] = "No evidence found for this criterion in the resume."

        # Clamp any out-of-range score instead of relying purely on retry
        item["score"] = max(1, min(10, item["score"]))

    return scores

def calculate_weighted_total(scores: list[dict], rubric: list[dict]) -> float:
    weight_lookup = {item["criterion"]: item["weight"] for item in rubric}

    weighted_sum = 0
    for item in scores:
        weight = weight_lookup.get(item["criterion"], 0)
        weighted_sum += item["score"] * (weight / 100)

    return round(weighted_sum, 2)


def score_resume(resume_data: dict, rubric: list[dict], max_retries: int = 3) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        rubric_json=json.dumps(rubric, indent=2),
        resume_json=json.dumps(resume_data, indent=2)
    )

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
            scores = json.loads(json_text)
            validate_scores(scores, rubric)
            scores = normalize_no_evidence_scores(scores)

            total_score = calculate_weighted_total(scores, rubric)

            result = {
                "candidate_name": resume_data.get("name", "Unknown"),
                "total_score": total_score,
                "criteria_breakdown": scores
            }
            result["summary"] = generate_summary(result, rubric)

            logger.info(f"Successfully scored {result['candidate_name']}: {total_score}/10")
            logger.debug(f"Full scoring result:\n{json.dumps(result, indent=2)}")
            return result

        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            logger.warning(f"Attempt {attempt} failed to score resume: {e}. Retrying...")

    logger.error(f"Failed to score resume after {max_retries} attempts. Last error: {last_error}")
    raise RuntimeError(f"Failed to score resume after {max_retries} attempts. Last error: {last_error}")

def generate_summary(result: dict, rubric: list[dict]) -> str:
    name = result["candidate_name"]
    total = result["total_score"]
    breakdown = result["criteria_breakdown"]

    # Sort criteria by score to find genuine standouts and gaps
    sorted_by_score = sorted(breakdown, key=lambda x: x["score"], reverse=True)
    strengths = [item for item in sorted_by_score if item["score"] >= 8][:3]
    gaps = [item for item in sorted_by_score if item["score"] <= 2][:3]

    lines = [f"{name} scored {total}/10 overall."]

    if strengths:
        strength_names = ", ".join(item["criterion"] for item in strengths)
        lines.append(f"Strongest areas: {strength_names}.")

    if gaps:
        gap_names = ", ".join(item["criterion"] for item in gaps)
        lines.append(f"Weakest areas: {gap_names}.")

    if not strengths and not gaps:
        lines.append("Scores were moderate and evenly spread across all criteria.")

    return " ".join(lines)


if __name__ == "__main__":
    from resume_parser import extract_text_from_pdf
    from resume_structurer import structure_resume
    from rubric_builder import build_rubric

    sample_jd = """
    We are seeking a versatile Full Stack Developer with a strong background in IT infrastructure to design, build, and maintain our web applications and internal tools. 
    In this role, you will be responsible for the entire software lifecycle, creating responsive frontend user interfaces, developing scalable backend APIs,
    managing relational and NoSQL databases, and ensuring seamless integration with our cloud networks and servers (AWS/Azure/Docker).
    The ideal candidate possesses deep proficiency in modern JavaScript frameworks (like React or Angular) and server-side languages (such as Node.js or Python),
    combined with a solid understanding of network security, systems administration, and DevOps pipelines to keep our production environments stable and secure.
    """

    # Generate the rubric ONCE - this represents one job posting
    rubric = build_rubric(sample_jd)
    logger.info(f"Using rubric with {len(rubric)} criteria for all candidates below")

    # Score MULTIPLE resumes against that SAME rubric
    test_resumes = ["data/sample_pdf_1.pdf", "data/sample_pdf_2.pdf", "data/sample_pdf_3.pdf", "data/sample_pdf_4.pdf"]

    for resume_path in test_resumes:
        cleaned_text = extract_text_from_pdf(resume_path)
        if cleaned_text is None:
            print(f"Could not extract text from {resume_path}, skipping.")
            continue

        resume_data = structure_resume(cleaned_text)
        result = score_resume(resume_data, rubric)
        print(f"\n{'='*50}")
        print(json.dumps(result, indent=2))