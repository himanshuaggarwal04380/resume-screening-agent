import os
import re
import pdfplumber
from logger_config import get_logger


logger = get_logger(os.path.splitext(os.path.basename(__file__))[0])

ALLOWED_PUNCTUATION = set(".,;:'\"!?()[]{}-_/\\@#$%&*+=<>|~`^•·–—")
MIN_VALID_LENGTH = 100  # a real resume should have at least this many characters


def clean_text(text: str) -> str:
    # Normalize Unicode punctuation
    text = text.replace("–", "-")   # en dash
    text = text.replace("−", "-")   # minus sign
    # Remove PDF character-ID artifacts like (cid:131)
    text = re.sub(r"\(cid:\d+\)", "", text)

    # Keep only letters/digits (any language), whitespace, and known-safe punctuation
    cleaned_chars = [
        ch for ch in text
        if ch.isalnum() or ch.isspace() or ch in ALLOWED_PUNCTUATION
    ]
    text = "".join(cleaned_chars)

    # Tidy up spacing
    text = re.sub(r"[ \t]+", " ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)  # collapse 3+ blank lines to 2

    # Strip a leading symbol only when it's followed by a space
    # (e.g. "+ Greater Noida" -> "Greater Noida", but "+91 123..." is untouched
    # because there's no space directly after the +)
    text = re.sub(r"^[^\w\s]+(?=\s)", "", text, flags=re.MULTILINE)
    text = "\n".join(line.strip() for line in text.split("\n"))

    return text


def extract_text_from_pdf(pdf_path: str) -> str | None:
    try:
        text_parts = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        raw_text = "\n".join(text_parts)

        if len(raw_text.strip()) < MIN_VALID_LENGTH:
            logger.warning(
                f"Extracted text too short ({len(raw_text.strip())} chars) from {pdf_path} "
                f"- likely a scanned/image-only PDF or empty document"
            )
            return None

        cleaned = clean_text(raw_text)
        logger.debug(f"Successfully extracted {len(raw_text)} raw characters from {pdf_path}")
        logger.debug(f"Full extracted text from {pdf_path}:\n{cleaned}")
        return cleaned

    except Exception as e:
        logger.error(f"Could not parse PDF {pdf_path} - {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    data_folder = "data"
    pdf_files = [f for f in os.listdir(data_folder) if f.lower().endswith(".pdf")]

    logger.info(f"Found {len(pdf_files)} PDF file(s) in {data_folder}/")

    success_count = 0
    skipped_count = 0

    for filename in pdf_files:
        file_path = os.path.join(data_folder, filename)
        print(f"\n{'='*50}")
        print(f"FILE: {filename}")
        print('='*50)

        raw_text = extract_text_from_pdf(file_path)

        if raw_text is None:
            print(f"  SKIPPED: {filename} could not be processed")
            skipped_count += 1
            continue

        print(raw_text)
        print(f"\n--- Extracted {len(raw_text)} characters ---")
        success_count += 1

    logger.info(f"Done. Processed: {success_count}, Skipped: {skipped_count}")