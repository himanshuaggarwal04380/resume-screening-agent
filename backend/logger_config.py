import logging
import os
from datetime import datetime


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # already configured, avoid duplicate handlers

    logger.setLevel(logging.DEBUG)

    # Create logs folder if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Create a NEW log file for every program execution
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join("logs", f"app_{timestamp}.log")

    # Console handler - shows INFO and above in terminal
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # File handler - saves EVERYTHING including DEBUG
    file_handler = logging.FileHandler(
        log_file,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)

    # Common formatter
    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logger.info(f"Log file created: {log_file}")

    return logger

