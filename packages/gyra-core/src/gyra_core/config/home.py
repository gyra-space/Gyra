"""Gyra home directory utilities for cross-platform compatibility."""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_gyra_home() -> Path:
    """Get the gyra home directory path.

    Priority:
    1. GYRA_HOME environment variable
    2. ~/.gyra (Path.home() / ".gyra")
    3. ./.gyra (current working directory fallback)
    """
    env_home = os.environ.get("GYRA_HOME")
    if env_home:
        return Path(env_home)

    try:
        return Path.home() / ".gyra"
    except (RuntimeError, KeyError):
        logger.warning(
            "Cannot determine user home directory. "
            "Set GYRA_HOME environment variable or HOME. "
            "Falling back to ./.gyra in current directory."
        )
        return Path.cwd() / ".gyra"
