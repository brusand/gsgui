"""
Paths Utility - Centralized path management for GSGUI
Provides absolute paths to project directories and files regardless of CWD
"""

from pathlib import Path
import os

# Calculate project root from this file's location
# backend/app/utils/paths.py -> backend/app/utils -> backend/app -> backend -> PROJECT_ROOT
_THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = _THIS_FILE.parent.parent.parent.parent

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
BACKEND_DATA_DIR = PROJECT_ROOT / "backend" / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
PIDS_DIR = PROJECT_ROOT / "pids"

# Configuration files (always use root data/ directory)
GSGUI_INI_PATH = DATA_DIR / "gsgui.ini"
STRATEGIES_INI_PATH = DATA_DIR / "strategies.ini"
CHALLENGES_DB_PATH = DATA_DIR / "challenges.db"

# Backend specific files
BACKEND_STRATEGIES_INI_PATH = BACKEND_DATA_DIR / "backend_strategies.ini"

# Ensure paths are strings for compatibility with ConfigObj and older code
GSGUI_INI_PATH_STR = str(GSGUI_INI_PATH)
STRATEGIES_INI_PATH_STR = str(STRATEGIES_INI_PATH)
CHALLENGES_DB_PATH_STR = str(CHALLENGES_DB_PATH)
BACKEND_STRATEGIES_INI_PATH_STR = str(BACKEND_STRATEGIES_INI_PATH)

# Log absolute paths at import time for debugging
import logging
logger = logging.getLogger(__name__)
logger.info(f"📂 GSGUI Paths initialized:")
logger.info(f"   PROJECT_ROOT: {PROJECT_ROOT}")
logger.info(f"   CWD: {Path.cwd()}")
logger.info(f"   gsgui.ini: {GSGUI_INI_PATH}")
logger.info(f"   strategies.ini: {STRATEGIES_INI_PATH}")
logger.info(f"   Files exist: gsgui.ini={GSGUI_INI_PATH.exists()}, strategies.ini={STRATEGIES_INI_PATH.exists()}")

# Ensure critical directories exist
for directory in [DATA_DIR, LOGS_DIR, PIDS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
