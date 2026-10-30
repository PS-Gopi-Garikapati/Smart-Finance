import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

# Directory where log files are stored
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.getenv("LOG_DIR", os.path.join(BASE_DIR, "logs"))
LOG_FILE_PATH = os.getenv("LOG_FILE", os.path.join(LOG_DIR, "smart_finance.log"))

# Default configuration settings
DEFAULT_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Maximum size per log file (5 MB) and maximum backup history files (5 files)
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 5

_initialized = False


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    enable_console: bool = True
) -> None:
    """
    Initialize global application logging with dual outputs:
    1. Console (stdout) for real-time terminal monitoring.
    2. Rotating File (logs/smart_finance.log) for persistent audit history.
    """
    global _initialized
    if _initialized:
        return

    level_name = (log_level or DEFAULT_LOG_LEVEL).upper()
    level = getattr(logging, level_name, logging.INFO)

    target_file = log_file or LOG_FILE_PATH
    os.makedirs(os.path.dirname(os.path.abspath(target_file)), exist_ok=True)

    formatter = logging.Formatter(fmt=DEFAULT_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 1. Console Handler (stdout)
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # 2. Rotating File Handler
    try:
        file_handler = RotatingFileHandler(
            filename=target_file,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"[Logger Setup Warning] Could not initialize file handler at {target_file}: {e}")

    _initialized = True


def get_logger(name: str = "SmartFinance") -> logging.Logger:
    """
    Retrieve a named logger instance configured with application formatting.
    Ensures setup_logging() is initialized automatically on first call.
    """
    if not _initialized:
        setup_logging()
    return logging.getLogger(name)


if __name__ == "__main__":
    # Self-test when executed directly
    log = get_logger("LoggerTest")
    log.info("Logger initialized successfully!")
    log.warning("This is a sample warning message.")
    log.error("This is a sample error message.")
    print(f"Log file written to: {LOG_FILE_PATH}")
