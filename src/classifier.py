"""
Classifier for the QDArchive data.

Implements the Classification_instruction requirements:

1. PROJECT_TYPE derivation from file types:
       QDA_PROJECT    - at least one file with a QDA file extension
       QD_PROJECT     - not QDA, but contains primary data files
       OTHER_PROJECT  - not QD, but contains other valid data files
       NOT_A_PROJECT  - nothing can be derived about file types

2. A hierarchical topic classifier based on the UN ISIC Rev.4 taxonomy
   (see taxonomy_isic.py), going two levels down:
       Level 1: sections  (A..U)
       Level 2: divisions (01..99)
   The classifier uses BOTH the base data (file names and, where
   readable, file content) AND the metadata (title, description,
   keywords) of a project.

3. Search tags: the matched taxonomy keywords are emitted as tags so
   projects/files become searchable by topic.
"""

from __future__ import annotations

import re
from pathlib import Path

from config import (
    QDA_EXTENSIONS,
    PRIMARY_DATA_EXTENSIONS,
    VALID_DATA_EXTENSIONS,
)
from taxonomy_isic import DIVISIONS

# ---------------------------------------------------------------------------
# PROJECT_TYPE derivation
# ---------------------------------------------------------------------------


def _norm_ext(file_type: str, file_name: str = "") -> str:
    """Normalise a stored file_type ('csv' / '.csv' / '') to '.csv'.
    Falls back to the file name's suffix."""
    ft = (file_type or "").strip().lower()
    if ft and not ft.startswith("."):
        ft = "." + ft
    if not ft and file_name:
        ft = Path(file_name).suffix.lower()
    return ft


def is_qda_file(file_type: str, file_name: str = "") -> bool:
    return _norm_ext(file_type, file_name) in QDA_EXTENSIONS


def is_primary_data_file(file_type: str, file_name: str = "") -> bool:
    return _norm_ext(file_type, file_name) in PRIMARY_DATA_EXTENSIONS


def is_valid_data_file(file_type: str, file_name: str = "") -> bool:
    return _norm_ext(file_type, file_name) in VALID_DATA_EXTENSIONS


def derive_project_type(files: list[dict]) -> str:
    """
    Derive the PROJECT_TYPE from the file types of a project's files.

    `files` is a list of dicts with at least 'file_type' and 'file_name'.
    """
    if not files:
        return "NOT_A_PROJECT"

    has_qda = False
    has_primary = False
    has_valid = False
    has_any_ext = False

    for f in files:
        ext = _norm_ext(f.get("file_type", ""), f.get("file_name", ""))
        if not ext:
            continue
        has_any_ext = True
        if ext in QDA_EXTENSIONS:
            has_qda = True
        if ext in PRIMARY_DATA_EXTENSIONS:
            has_primary = True
        if ext in VALID_DATA_EXTENSIONS:
            has_valid = True

    if has_qda:
        return "QDA_PROJECT"
    if has_primary:
        return "QD_PROJECT"
    if has_valid:
        return "OTHER_PROJECT"
    if not has_any_ext:
        return "NOT_A_PROJECT"
    # Files exist but none with a recognised/valid extension
    return "NOT_A_PROJECT"


# ---------------------------------------------------------------------------
# ISIC keyword classifier
# ---------------------------------------------------------------------------

# Pre-compile one regex per division keyword for word-boundary matching.
_COMPILED: dict[str, list[tuple[re.Pattern, str, int]]] = {}


def _compile_lexicon():
    if _COMPILED:
        return
    for code, div in DIVISIONS.items():
        patterns = []
        for kw in div["keywords"]:
            # Multi-word keywords score higher (they are more specific).
            weight = 3 if " " in kw else 1
            pattern = re.compile(r"\b" + re.escape(kw.lower()) + r"\b")
            patterns.append((pattern, kw, weight))
        _COMPILED[code] = patterns


def score_text(text: str) -> tuple[dict[str, float], dict[str, set[str]]]:
    """
    Score a text blob against every ISIC division.

    Returns:
        scores:  division code -> score
        matched: division code -> set of matched keywords (used as tags)
    """
    _compile_lexicon()
    text_lower = (text or "").lower()

    scores: dict[str, float] = {}
    matched: dict[str, set[str]] = {}

    if not text_lower.strip():
        return scores, matched

    for code, patterns in _COMPILED.items():
        score = 0.0
        hits: set[str] = set()
        for pattern, kw, weight in patterns:
            n = len(pattern.findall(text_lower))
            if n:
                score += weight * n
                hits.add(kw)
        if score > 0:
            scores[code] = score
            matched[code] = hits

    return scores, matched


def classify_text(text: str) -> dict:
    """
    Classify a text blob into the ISIC hierarchy (two levels).

    Returns a dict:
        {
          "primary_division":   "85" or None,
          "secondary_division": "86" or None,
          "primary_section":    "P"  or None,
          "secondary_section":  "Q"  or None,
          "primary_score":      float,
          "secondary_score":    float,
          "tags":               sorted list of matched keywords,
        }
    """
    scores, matched = score_text(text)

    result = {
        "primary_division": None,
        "secondary_division": None,
        "primary_section": None,
        "secondary_section": None,
        "primary_score": 0.0,
        "secondary_score": 0.0,
        "tags": [],
    }

    if not scores:
        return result

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))

    primary_code, primary_score = ranked[0]
    result["primary_division"] = primary_code
    result["primary_section"] = DIVISIONS[primary_code]["section"]
    result["primary_score"] = primary_score

    if len(ranked) > 1:
        secondary_code, secondary_score = ranked[1]
        # Only report a secondary class if it is reasonably strong
        # relative to the primary class (at least 40 %).
        if secondary_score >= 0.4 * primary_score:
            result["secondary_division"] = secondary_code
            result["secondary_section"] = DIVISIONS[secondary_code]["section"]
            result["secondary_score"] = secondary_score

    tags: set[str] = set()
    for code in (result["primary_division"], result["secondary_division"]):
        if code and code in matched:
            tags |= matched[code]
    result["tags"] = sorted(tags)

    return result


# ---------------------------------------------------------------------------
# Reading base data (file content) for classification
# ---------------------------------------------------------------------------

_READABLE_TEXT_EXTENSIONS = {".txt", ".csv", ".tsv", ".json", ".xml",
                             ".md", ".rtf", ".html", ".htm"}

_MAX_CONTENT_CHARS = 20_000  # read at most this much per file


def read_file_snippet(path: Path) -> str:
    """Read a bounded text snippet from a base-data file, if readable."""
    try:
        if not path.is_file():
            return ""
        if path.suffix.lower() not in _READABLE_TEXT_EXTENSIONS:
            return ""
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read(_MAX_CONTENT_CHARS)
    except Exception:
        return ""


def build_file_text(file_name: str, local_path: Path | None = None) -> str:
    """Text used to classify a single file: its name plus readable content."""
    # De-camel / de-snake the file name so keywords match.
    stem = Path(file_name or "").stem
    name_text = re.sub(r"[_\-.]+", " ", stem)
    name_text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name_text)

    parts = [name_text]
    if local_path is not None:
        content = read_file_snippet(local_path)
        if content:
            parts.append(content)
    return "\n".join(parts)


def build_project_text(project: dict, files: list[dict],
                       download_dir: Path | None = None) -> str:
    """
    Text used to classify a project "as the sum of its files":
    metadata (title, description, keywords) + all file names + readable
    file content snippets.
    """
    parts = [
        project.get("title") or "",
        project.get("description") or "",
        " ".join(project.get("keywords") or []),
    ]

    for f in files:
        local = None
        if download_dir is not None:
            candidate = (download_dir
                         / (project.get("download_repository_folder") or "")
                         / (project.get("download_project_folder") or "")
                         / (f.get("file_name") or ""))
            local = candidate
        parts.append(build_file_text(f.get("file_name") or "", local))

    return "\n".join(p for p in parts if p)
