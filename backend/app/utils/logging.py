import sys

from loguru import logger

from app.config import settings


def setup_logging() -> None:
    """Configure loguru to write to stdout and a rotating log file."""
    logger.remove()  # Remove default handler

    # Human-readable colored output to stdout
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # Rotating file log for debugging (rotates at 10MB, kept for 7 days)
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
    )
