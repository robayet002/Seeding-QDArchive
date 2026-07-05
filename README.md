# Seeding QDArchive

**ID:** 23277555
**Semester:** Winter 25/26 + Summer 26

A research tool that discovers, downloads, and catalogues **Qualitative Data Analysis (QDA) project files** from target repositories. It scrapes metadata and files from SADA (DataFirst UCT) and Dataverse Norway, stores everything in a structured SQLite database across five normalised tables, and then classifies each project against the UN ISIC taxonomy — producing an XLSX table and a per-repository PDF report.

---

## Overview

QDArchive Seeder automates the collection and classification of QDA research datasets from open repositories. For each discovered project it:

1. Searches configured repositories using keyword queries.
2. Visits each record's detail page to extract full metadata — title, description, authors, keywords, licenses, DOI, language, and year.
3. Discovers downloadable file links, including those behind intermediate "Access Data" pages.
4. Downloads files into an organised local folder structure.
5. Records everything in a normalised SQLite database across five related tables.
6. Derives a project type from the downloaded files, classifies each project against the ISIC taxonomy, and exports the results.

The primary goal is to build an archive of QDA project files (`.qdpx`, `.atlproj`, `.nvpx`, etc.) for research purposes. Raw data is stored exactly as received — data-quality cleaning is handled in a separate downstream step.

---

## Target Repositories

| ID | Name | Base URL | Method |
|----|------|----------|--------|
| 1 | SADA (DataFirst UCT) | https://www.datafirst.uct.ac.za | Scraping |
| 2 | Dataverse Norway | https://dataverse.no | Scraping |

---

## Downloaded Data

The harvested dataset is available here:
https://faubox.rrze.uni-erlangen.de/getlink/fiCPL5c8azroVFNbSVo7mR/QDArchive

---

## Installation

**Requirements:** Python 3.11 or later.

```bash
# 1. Clone the repository
git clone https://github.com/robayet002/Seeding-QDArchive.git
cd Seeding-QDArchive

# 2. Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install requests beautifulsoup4 openpyxl matplotlib
```

| Dependency | Used for |
|------------|----------|
| `requests` | HTTP requests to repositories |
| `beautifulsoup4` | HTML parsing / scraping |
| `openpyxl` | XLSX export of the classification table |
| `matplotlib` | Vector histograms in the PDF report |

---

## Configuration

To change which search terms each scraper uses, edit the `SEARCH_QUERIES` list at the top of each scraper file:

```python
# scraper_sada.py
SEARCH_QUERIES = ["science", "qualitative"]

# scraper_dataverse.py
SEARCH_QUERIES = ["student", "interview"]
```

---

## Project Structure

| File | Status | Purpose |
|------|--------|---------|
| `config.py` | updated | Adds `PROJECT_TYPES`, `PRIMARY_DATA_EXTENSIONS`, `VALID_DATA_EXTENSIONS`, classification DB name/path, report/XLSX output paths |
| `database.py` | updated | `projects.type` documented + CHECK-constrained to `PROJECT_TYPE` values; new tables `project_classification`, `file_classification`, `tags` (+ indexes) |
| `taxonomy_isic.py` | **new** | UN ISIC taxonomy from <https://unstats.un.org/unsd/classifications/Econ/> — two levels: sections (A–U) and divisions (01–99), each division with a keyword lexicon |
| `classifier.py` | **new** | `derive_project_type()` (file-type rules) and the keyword classifier `classify_text()` over base data + metadata; emits search tags |
| `run_classification.py` | **new** | Pipeline: derive `PROJECT_TYPE` → classify `QDA_PROJECT`s then `QD_PROJECT`s (project + each primary data file), by repository → copy DB to the deliverable DB → print per-repository statistics |
| `export_xlsx.py` | **new** | XLSX table: `repository_id, project_type, project_title, primary_class, secondary_class, no_project_files` |
| `report_pdf.py` | **new** | PDF report per repository: vector histogram of primary classes (full class names as bin labels, counts atop bars), rank-ordered top-20 class table, comments |
| `export_csv.py` | — | Exports all five core tables to CSV |
| `main.py` | updated | Newly inserted projects default to `NOT_A_PROJECT`; classification + exports run automatically after harvesting |

---

## Database Schema

The database is normalised across five related tables.

### `projects`
The central table — one row per discovered research project or dataset.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | ✓ | Primary key |
| `query_string` | TEXT | | Search query that surfaced this project |
| `repository_id` | INTEGER | ✓ | ID from the repository registry |
| `repository_url` | TEXT | ✓ | Top-level URL of the source repository |
| `project_url` | TEXT | ✓ | Full URL to this specific project/record |
| `version` | TEXT | | Version string, if any |
| `type` | TEXT | ✓ | Project type, e.g. `QDA_PROJECT` (CHECK-constrained) |
| `title` | TEXT | ✓ | Project title |
| `description` | TEXT | ✓ | Description from the source site |
| `language` | TEXT | | BCP 47 language tag, e.g. `en-US` |
| `doi` | TEXT | | DOI URL, e.g. `https://doi.org/10.5281/zenodo.16082705` |
| `upload_date` | TEXT | | Original upload date (`YYYY` or `YYYY-MM-DD`) |
| `download_date` | TEXT | ✓ | Timestamp when the download concluded |
| `download_repository_folder` | TEXT | ✓ | Folder name for the repository, e.g. `zenodo` |
| `download_project_folder` | TEXT | ✓ | Folder name for this project (record ID) |
| `download_version_folder` | TEXT | | Version subfolder, if any |
| `download_method` | TEXT | ✓ | `SCRAPING` or `API-CALL` |

### `files`
One row per file downloaded for a project.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | ✓ | Primary key |
| `project_id` | INTEGER | ✓ | Foreign key → `projects.id` |
| `file_name` | TEXT | ✓ | Filename on disk, e.g. `Country_Article_counts.xlsx` |
| `file_type` | TEXT | ✓ | File extension, e.g. `xlsx`, `qdpx` |
| `status` | TEXT | ✓ | Download result: `success` or `failed` |

### `keywords`
One row per keyword associated with a project.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | ✓ | Primary key |
| `project_id` | INTEGER | ✓ | Foreign key → `projects.id` |
| `keyword` | TEXT | ✓ | Keyword string, e.g. `EFL learners` |

### `person_role`
One row per person (author, uploader, contributor) linked to a project.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | ✓ | Primary key |
| `project_id` | INTEGER | ✓ | Foreign key → `projects.id` |
| `name` | TEXT | ✓ | Full name string, e.g. `Li, Huaqiang` |
| `role` | TEXT | ✓ | `AUTHOR`, `UPLOADER`, `CONTRIBUTOR`, or `UNKNOWN` |

### `licenses`
One row per license associated with a project.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | ✓ | Primary key |
| `project_id` | INTEGER | ✓ | Foreign key → `projects.id` |
| `license` | TEXT | ✓ | License string, e.g. `CC-BY-4.0` |

---

## QDA File Formats

The following extensions are recognised as QDA project files and flagged in the `files` table:

| Extension | Software |
|-----------|----------|
| `.qdpx` | REFI-QDA exchange format (multi-tool) |
| `.qpdx` | REFI-QDA variant |
| `.qda` | Generic QDA |
| `.atlproj` | ATLAS.ti |
| `.nvp` | NVivo (older) |
| `.nvpx` | NVivo |

---

## Classification

### PROJECT_TYPE rules

The project type is derived from the file types of a project's files, in this order:

1. `QDA_PROJECT` — at least one file with a QDA extension (`.qdpx`, `.qpdx`, `.qda`, `.atlproj`, `.nvp`, `.nvpx`).
2. `QD_PROJECT` — otherwise, at least one *primary data* file (tabular/statistical data, structured data, text corpora/transcripts, audio/video, images — see `PRIMARY_DATA_EXTENSIONS` in `config.py`).
3. `OTHER_PROJECT` — otherwise, at least one other *valid* data file (`.pdf`, archives, HTML, slides, …).
4. `NOT_A_PROJECT` — no files, or nothing derivable from the file types.

The result is written to the existing `projects.type` column.

### The classifier

A rule-based keyword classifier over the UN **ISIC Rev. 5** hierarchy, two levels down (sections **and** divisions), as required. It uses:

- **metadata:** title, description, keywords.
- **base data:** file names (de-snaked / de-camelled) and, for readable text formats (`.txt`, `.csv`, `.json`, `.xml`, …), up to 20 000 characters of file content.

Multi-word taxonomy keywords score ×3 (more specific). The top-scoring division is the primary class; the runner-up becomes the secondary class if it reaches ≥ 40 % of the primary score. All matched keywords are stored in the `tags` table for topic search.

---

## Usage

### Run the full pipeline

```bash
cd src
python main.py                 # harvest + classify + exports
```

### Run individual stages

```bash
python run_classification.py   # types + classification + stats + deliverable DB
python export_xlsx.py          # -> data/database/exports/classification_table.xlsx
python report_pdf.py           # -> data/reports/classification_report.pdf
```

### Export all tables to CSV

```bash
python export_csv.py
```

Output files are written to `data/database/exports/`:

```
exports/
├── projects.csv
├── files.csv
├── keywords.csv
├── person_role.csv
└── licenses.csv
```

---

## Outputs

| Output | Path | Produced by |
|--------|------|-------------|
| Working database | `data/database/qdarchive_part1.db` | harvesting pipeline |
| Deliverable database | `23277555-sq26-classification.db` | `run_classification.py` |
| CSV exports | `data/database/exports/*.csv` | `export_csv.py` |
| Classification table (XLSX) | `data/database/exports/classification_table.xlsx` | `export_xlsx.py` |
| Classification report (PDF) | `data/reports/classification_report.pdf` | `report_pdf.py` |
