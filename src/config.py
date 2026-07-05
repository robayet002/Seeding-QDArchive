import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Console encoding fix (Windows cp1252 consoles can't print many Unicode
# characters found in scraped titles). Force UTF-8 with safe replacement
# so print() never raises UnicodeEncodeError.
# ---------------------------------------------------------------------------
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data folders
DATA_DIR = BASE_DIR / "data"
DOWNLOAD_DIR = DATA_DIR / "downloads"
DATABASE_DIR = DATA_DIR / "database"
EXPORT_DIR = DATABASE_DIR / "exports"

# Database file
DB_PATH = DATABASE_DIR / "qdarchive_part1.db"

# Create directories if they don't exist
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# QDA project file extensions
QDA_EXTENSIONS = {
    ".qdpx",
    ".qpdx",
    ".qda",
    ".atlproj",
    ".nvp",
    ".nvpx"
}

# Open license keywords
OPEN_LICENSE_KEYWORDS = {
    "cc-by",
    "cc-by-4.0",
    "cc-by-sa",
    "cc-by-sa-4.0",
    "cc0",
    "cc0-1.0",
    "creative commons",
    "open"
}
# ---------------------------------------------------------------------------
# Classification settings (Classification_instruction)
# ---------------------------------------------------------------------------

# Classification result database (committed to the repository)
CLASSIFICATION_DB_NAME = "23277555-sq26-classification.db"
CLASSIFICATION_DB_PATH = DATABASE_DIR / CLASSIFICATION_DB_NAME

# Report output (PDF, vector graphics)
REPORT_DIR = DATA_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PDF_PATH = REPORT_DIR / "classification_report.pdf"
REPORT_XLSX_PATH = EXPORT_DIR / "classification_table.xlsx"

# PROJECT_TYPE values
PROJECT_TYPES = {
    "QDA_PROJECT",      # contains at least one file with a QDA extension
    "QD_PROJECT",       # no QDA file, but contains primary data files
    "OTHER_PROJECT",    # no primary data, but contains other valid data files
    "NOT_A_PROJECT",    # nothing can be derived about file types
}

# Primary (raw/base) data file extensions: the actual research data
PRIMARY_DATA_EXTENSIONS = {
    # tabular / statistical data
    ".csv", ".tsv", ".xls", ".xlsx", ".sav", ".dta", ".por", ".rda",
    ".rdata", ".sas7bdat", ".parquet",
    # structured data
    ".json", ".xml",
    # text corpora / transcripts
    ".txt", ".rtf", ".doc", ".docx",
    # audio / video recordings (e.g. interviews)
    ".mp3", ".wav", ".m4a", ".ogg", ".mp4", ".avi", ".mov", ".mkv",
    # images used as data
    ".jpg", ".jpeg", ".png", ".tif", ".tiff",
}

# Other valid (recognised) data file extensions: documentation, packaging etc.
VALID_DATA_EXTENSIONS = PRIMARY_DATA_EXTENSIONS | QDA_EXTENSIONS | {
    ".pdf", ".zip", ".rar", ".7z", ".tar", ".gz",
    ".html", ".htm", ".md", ".ppt", ".pptx", ".odt", ".ods",
}