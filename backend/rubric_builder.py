import ollama
import json
import os
from logger_config import get_logger
from config import LLM_MODEL

logger = get_logger(os.path.splitext(os.path.basename(__file__))[0])

PROMPT_TEMPLATE = """You are an expert technical recruiter. Given the job description below, create a structured scoring rubric for evaluating candidate resumes.

STRICT RULES:
1. Only create criteria for skills, requirements, or qualifications that are EXPLICITLY stated in the job description. Do not infer or add criteria for things not mentioned.
2. Keep each distinct requirement as its OWN separate criterion — do not merge multiple distinct requirements (e.g. a programming language and a framework) into a single criterion, even if they're related.
3. Use the job description's own wording where possible for criterion names.

Return ONLY valid JSON — no explanation, no markdown formatting, just the raw JSON array. Each item in the array must have exactly these fields:
- "criterion": short name of what's being evaluated
- "description": one sentence explaining what this criterion means
- "weight": an integer percentage (all weights across all criteria must add up to 100)
- "how_to_detect": one sentence on what to look for in a resume to score this

Create one criterion per distinct requirement mentioned in the job description.

Job Description:
{job_description}
"""
def normalize_weights(rubric: list[dict]) -> list[dict]:
    total = sum(item["weight"] for item in rubric)

    if total == 0:
        # edge case: everything came back as 0, split evenly
        share = 100 // len(rubric)
        for item in rubric:
            item["weight"] = share
    else:
        for item in rubric:
            item["weight"] = round(item["weight"] / total * 100)

    # rounding can leave us 1-2 off; dump any leftover onto the largest item
    diff = 100 - sum(item["weight"] for item in rubric)
    if diff != 0:
        largest = max(rubric, key=lambda x: x["weight"])
        largest["weight"] += diff

    return rubric

def build_rubric(job_description: str, max_retries: int = 3) -> list[dict]:
    prompt = PROMPT_TEMPLATE.format(job_description=job_description)

    last_error = None

    for attempt in range(1, max_retries + 1):
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )

        raw_text = response["message"]["content"].strip()
        logger.debug(f"Attempt {attempt} raw LLM response:\n{raw_text!r}")

        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        try:
            rubric = json.loads(raw_text)
            validate_rubric(rubric)
            rubric = normalize_weights(rubric)
            logger.info(f"Successfully built rubric with {len(rubric)} criteria")
            logger.debug(f"Final rubric:\n{json.dumps(rubric, indent=2)}")
            return rubric
        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            logger.warning(f"Attempt {attempt} failed: {e}. Retrying...")

    logger.error(f"Failed to get valid rubric after {max_retries} attempts. Last error: {last_error}")
    raise RuntimeError(f"Failed to get valid rubric after {max_retries} attempts. Last error: {last_error}")



def validate_rubric(rubric: list[dict]) -> None:
    if not isinstance(rubric, list) or len(rubric) == 0:
        raise ValueError("Rubric must be a non-empty list")

    required_fields = {"criterion", "description", "weight", "how_to_detect"}

    for item in rubric:
        missing = required_fields - item.keys()
        if missing:
            raise ValueError(f"Rubric item missing fields: {missing}")
        if not isinstance(item["weight"], (int, float)) or item["weight"] < 0:
            raise ValueError(f"Invalid weight value: {item['weight']}")



def rebalance_weights(rubric: list[dict], fixed_index: int) -> list[dict]:
    total = sum(item["weight"] for item in rubric)

    if 95 <= total <= 105:
        return rubric  # close enough, leave it alone

    fixed_weight = rubric[fixed_index]["weight"]
    remaining_budget = 100 - fixed_weight

    other_items = [item for i, item in enumerate(rubric) if i != fixed_index]
    other_total = sum(item["weight"] for item in other_items)

    if other_total == 0:
        # edge case: everything else is already 0, split budget evenly
        share = remaining_budget // len(other_items) if other_items else 0
        for item in other_items:
            item["weight"] = share
    else:
        for item in other_items:
            proportion = item["weight"] / other_total
            item["weight"] = round(proportion * remaining_budget)

    # rounding can leave us 1-2 off; dump any leftover onto the largest other item
    diff = 100 - sum(item["weight"] for item in rubric)
    if diff != 0 and other_items:
        largest = max(other_items, key=lambda x: x["weight"])
        largest["weight"] += diff

    return rubric


def review_rubric(rubric: list[dict], just_rebalanced: bool = False) -> list[dict]:
    header = "--- Adjusted Rubric (weights rebalanced to total 100) ---" if just_rebalanced else "--- Generated Rubric ---"
    print(f"\n{header}")
    for i, item in enumerate(rubric):
        print(f"\n[{i}] {item['criterion']} (weight: {item['weight']})")
        print(f"    {item['description']}")
        print(f"    Detect via: {item['how_to_detect']}")

    total = sum(item['weight'] for item in rubric)
    print(f"\nTotal weight: {total}")

    print("\n--- Review ---")
    print("Type a criterion number to edit its weight, 'r' to remove one, or press Enter to accept as-is.")
    choice = input("> ").strip()

    if choice == "":
        return rubric

    if choice.lower() == "r":
        idx = int(input("Which index to remove? "))
        rubric.pop(idx)
        print(f"Removed item {idx}.")
        return review_rubric(rubric)  # show updated list again

    try:
        idx = int(choice)
        new_weight = int(input(f"New weight for '{rubric[idx]['criterion']}': "))
        rubric[idx]["weight"] = new_weight

        rubric = rebalance_weights(rubric, fixed_index=idx)

        return review_rubric(rubric, just_rebalanced=True)
    except (ValueError, IndexError):
        print("Invalid input, showing rubric again.")
        return review_rubric(rubric)



if __name__ == "__main__":
    sample_jd = """
    We are hiring a Backend Developer with 3+ years of experience in Python.
    Must know FastAPI or Django, SQL databases, and REST API design.
    Experience with cloud platforms (AWS/GCP) is a plus. Bachelor's degree
    in Computer Science or related field preferred.
    """

    result = build_rubric(sample_jd)
    final_rubric = review_rubric(result)

    print("\n--- Final Rubric ---")
    print(json.dumps(final_rubric, indent=2))