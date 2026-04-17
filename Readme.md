# QDArchive Seeder (Part I)
---
**ID:** 23277555

**Semester:** Winter 25/26 + Summer 26

A research tool that discovers, downloads, and catalogues **Qualitative Data Analysis (QDA) project files** from target repositories. It scrapes metadata and files from SADA (DataFirst UCT) and Dataverse Norway, storing everything in a structured SQLite database across five normalised tables.

---


## Overview

QDArchive Seeder automates the collection of QDA research datasets from open repositories. For each discovered project it:

1. Searches configured repositories using keyword queries
2. Visits each record's detail page to extract full metadata — title, description, authors, keywords, licenses, DOI, language, and year
3. Discovers downloadable file links, including those behind intermediate "Access Data" pages
4. Downloads files into an organised local folder structure
5. Records everything in a normalised SQLite database across five related tables

The primary goal is to build an archive of QDA project files (`.qdpx`, `.atlproj`, `.nvpx`, etc.) for research purposes. Raw data is stored exactly as received — data quality cleaning is handled in a separate downstream step.

---

---

## Target Repositories

| ID | Name | Base URL | Method |
|---|---|---|---|
| 1 | SADA (DataFirst UCT) | https://www.datafirst.uct.ac.za | Scraping |
| 2 | Dataverse Norway | https://dataverse.no | Scraping |

---

## Project Structure

```
project-root/
│
├── src/
│   ├── config.py              # Paths, constants, QDA extensions, license keywords
│   ├── database.py            # SQLite schema creation (init_db)
│   ├── metadata.py            # Insert helpers for all 5 database tables
│   ├── main.py                # Orchestrator: search → download → store
│   ├── downloader.py          # HTTP file downloader + filename sanitiser
│   ├── export_csv.py          # Export all tables to CSV files
│   ├── scraper_sada.py        # Scraper for SADA / DataFirst UCT
│   ├── scraper_dataverse.py   # Scraper for Dataverse Norway
│   └── scraper_zenodo.py      # API client for Zenodo
│
└──  Database and CSV/
        ├── qdarchive_part1.db # SQLite database
        └── exports/           # CSV exports (one file per table)
```

---

## Downloaded Data Link:
https://faubox.rrze.uni-erlangen.de/getlink/fiCPL5c8azroVFNbSVo7mR/QDArchive

---


### `projects`
The central table — one row per discovered research project or dataset.

| Column | Type | Required | Description |
|---|---|---|---|
| `id` | INTEGER | ✓ | Primary key |
| `query_string` | TEXT | | Search query that surfaced this project |
| `repository_id` | INTEGER | ✓ | ID from the repository registry |
| `repository_url` | TEXT | ✓ | Top-level URL of the source repository |
| `project_url` | TEXT | ✓ | Full URL to this specific project/record |
| `version` | TEXT | | Version string, if any |
| `type` | TEXT | ✓ | Project type e.g. `QDA_PROJECT` |
| `title` | TEXT | ✓ | Project title |
| `description` | TEXT | ✓ | Description from the source site |
| `language` | TEXT | | BCP 47 language tag e.g. `en-US` |
| `doi` | TEXT | | DOI URL e.g. `https://doi.org/10.5281/zenodo.16082705` |
| `upload_date` | TEXT | | Original upload date (`YYYY` or `YYYY-MM-DD`) |
| `download_date` | TEXT | ✓ | Timestamp when the download concluded |
| `download_repository_folder` | TEXT | ✓ | Folder name for the repository e.g. `zenodo` |
| `download_project_folder` | TEXT | ✓ | Folder name for this project (record ID) |
| `download_version_folder` | TEXT | | Version subfolder, if any |
| `download_method` | TEXT | ✓ | `SCRAPING` or `API-CALL` |

### `files`
One row per file downloaded for a project.

| Column | Type | Required | Description |
|---|---|---|---|
| `id` | INTEGER | ✓ | Primary key |
| `project_id` | INTEGER | ✓ | Foreign key → `projects.id` |
| `file_name` | TEXT | ✓ | Filename on disk e.g. `Country_Article_counts.xlsx` |
| `file_type` | TEXT | ✓ | File extension e.g. `xlsx`, `qdpx` |
| `status` | TEXT | ✓ | Download result: `success` or `failed` |

### `keywords`
One row per keyword associated with a project.

| Column | Type | Required | Description |
|---|---|---|---|
| `id` | INTEGER | ✓ | Primary key |
| `project_id` | INTEGER | ✓ | Foreign key → `projects.id` |
| `keyword` | TEXT | ✓ | Keyword string e.g. `EFL learners` |

### `person_role`
One row per person (author, uploader, contributor) linked to a project.

| Column | Type | Required | Description |
|---|---|---|---|
| `id` | INTEGER | ✓ | Primary key |
| `project_id` | INTEGER | ✓ | Foreign key → `projects.id` |
| `name` | TEXT | ✓ | Full name string e.g. `Li, Huaqiang` |
| `role` | TEXT | ✓ | `AUTHOR`, `UPLOADER`, `CONTRIBUTOR`, or `UNKNOWN` |

### `licenses`
One row per license associated with a project.

| Column | Type | Required | Description |
|---|---|---|---|
| `id` | INTEGER | ✓ | Primary key |
| `project_id` | INTEGER | ✓ | Foreign key → `projects.id` |
| `license` | TEXT | ✓ | License string e.g. `CC-BY-4.0` |

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
pip install requests beautifulsoup4
```

---

## Configuration

All paths and constants live in `src/config.py`. The `data/` directory tree is created automatically on first run — no manual setup needed.

| Constant | Default | Description |
|---|---|---|
| `DOWNLOAD_DIR` | `data/downloads/` | Root folder for downloaded files |
| `DATABASE_DIR` | `data/database/` | Folder containing the SQLite database |
| `EXPORT_DIR` | `data/database/exports/` | Folder for CSV exports |
| `DB_PATH` | `data/database/qdarchive_part1.db` | SQLite database file path |
| `QDA_EXTENSIONS` | `.qdpx` `.qpdx` `.qda` `.atlproj` `.nvp` `.nvpx` | Extensions treated as QDA project files |
| `OPEN_LICENSE_KEYWORDS` | `cc-by`, `cc0`, `creative commons`, … | Keywords used to identify open licenses |

To change which search terms each scraper uses, edit the `SEARCH_QUERIES` list at the top of each scraper file:

```python
# scraper_sada.py
SEARCH_QUERIES = ["science", "qualitative"]

# scraper_dataverse.py
SEARCH_QUERIES = ["student", "interview"]

---

### Export all tables to CSV

```bash
cd src
python export_csv.py
```


## Exporting Data

After running the pipeline, export all tables to CSV:

```bash
cd src
python export_csv.py
```

Output files written to `data/database/exports/`:

```
exports/
├── projects.csv
├── files.csv
├── keywords.csv
├── person_role.csv
└── licenses.csv
```

---

## QDA File Formats

The following extensions are recognised as QDA project files and flagged in the `files` table:

| Extension | Software |
|---|---|
| `.qdpx` | REFI-QDA exchange format (multi-tool) |
| `.qpdx` | REFI-QDA variant |
| `.qda` | Generic QDA |
| `.atlproj` | ATLAS.ti |
| `.nvp` | NVivo (older) |
| `.nvpx` | NVivo |

---


