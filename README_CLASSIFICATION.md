# Classification implementation (Classification_instruction)

## New / changed files

| File | Status | Purpose |
|---|---|---|
| `config.py` | updated | Adds `PROJECT_TYPES`, `PRIMARY_DATA_EXTENSIONS`, `VALID_DATA_EXTENSIONS`, classification DB name/path, report/XLSX output paths |
| `database.py` | updated | `projects.type` documented + CHECK-constrained to PROJECT_TYPE values; new tables `project_classification`, `file_classification`, `tags` (+ indexes) |
| `taxonomy_isic.py` | **new** | UN ISIC Rev. 4 taxonomy from <https://unstats.un.org/unsd/classifications/Econ/> — two levels: sections (A–U) and divisions (01–99), each division with a keyword lexicon |
| `classifier.py` | **new** | `derive_project_type()` (file-type rules) and the keyword classifier `classify_text()` over base data + metadata; emits search tags |
| `run_classification.py` | **new** | Pipeline: derive PROJECT_TYPE → classify QDA_PROJECTs then QD_PROJECTs (project + each primary data file), by repository → copy DB to `23277555-sq26-classification.db` → print per-repository statistics |
| `export_xlsx.py` | **new** | XLSX table: `repository_id, project_type, project_title, primary_class, secondary_class, no_project_files` |
| `report_pdf.py` | **new** | PDF report per repository: vector histogram of primary classes (full class names as bin names, counts on top of bars), rank-ordered top-20 class table, comments |
| `main.py` | updated | Newly inserted projects default to `NOT_A_PROJECT`; classification + exports run automatically after harvesting |

## PROJECT_TYPE rules

Derived from the file types of a project's files, in this order:

1. `QDA_PROJECT` — at least one file with a QDA extension (`.qdpx`, `.qpdx`, `.qda`, `.atlproj`, `.nvp`, `.nvpx`)
2. `QD_PROJECT` — otherwise, at least one *primary data* file (tabular/statistical data, structured data, text corpora/transcripts, audio/video, images — see `PRIMARY_DATA_EXTENSIONS` in `config.py`)
3. `OTHER_PROJECT` — otherwise, at least one other *valid* data file (`.pdf`, archives, HTML, slides, …)
4. `NOT_A_PROJECT` — no files, or nothing derivable from the file types

The result is written to the existing `projects.type` column.

## The classifier

Rule-based keyword classifier over the ISIC Rev. 4 hierarchy, two
levels down (sections **and** divisions), as required. It uses:

- **metadata**: title, description, keywords
- **base data**: file names (de-snaked/de-camelled) and, for readable text
  formats (`.txt`, `.csv`, `.json`, `.xml`, …), up to 20 000 characters of
  file content

Multi-word taxonomy keywords score ×3 (more specific). The top-scoring
division is the primary class; the runner-up becomes the secondary class
if it reaches ≥ 40 % of the primary score. All matched keywords are stored
in the `tags` table for topic search.

## Running

```
python main.py                 # full pipeline: harvest + classify + exports
# or individually:
python run_classification.py   # types + classification + stats + deliverable DB
python export_xlsx.py          # data/database/exports/classification_table.xlsx
python report_pdf.py           # data/reports/classification_report.pdf
```

## Committing the deliverable database

`run_classification.py` copies the database to
`data/database/23277555-sq26-classification.db`. Commit and tag it:

```
git add data/database/23277555-sq26-classification.db
git commit -m "Add classification results database"
git tag classification-results
git push && git push --tags
```

## Dependencies

```
pip install requests beautifulsoup4 openpyxl matplotlib
```
