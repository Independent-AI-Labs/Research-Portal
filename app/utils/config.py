import os
from pathlib import Path

# Configuration for the Smart Reports directory
REPORTS_DIR_CONFIG_KEY = "SMART_REPORTS_DIR_PATH"
DEFAULT_REPORTS_DIR = Path(__file__).parent.parent.parent.parent / "Smart Reports"

# Determine the actual reports directory path
REPORTS_BASE_DIR = Path(os.getenv(REPORTS_DIR_CONFIG_KEY, DEFAULT_REPORTS_DIR)).resolve()

# Path to the static CSS file
CSS_PATH = Path(__file__).parent.parent.parent / "static" / "gallery.css"
