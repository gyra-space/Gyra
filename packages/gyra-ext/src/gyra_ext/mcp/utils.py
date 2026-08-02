import logging


def setup_logger(level: str | int = logging.INFO):
    """Setup logger - delegates to gyra's unified logging system.

    This function no longer calls logging.basicConfig to prevent duplicate log output.
    The actual logging setup is handled by gyra.util.logger.setup_logging.
    """
    logger = logging.getLogger("mcp")
    logger.setLevel(level)
    return logger
