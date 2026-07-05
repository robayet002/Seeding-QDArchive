"""
Classification pipeline (Classification_instruction).

Steps performed:

1. Derive the PROJECT_TYPE for every project from its file types and
   write it into the projects.type column
       (QDA_PROJECT | QD_PROJECT | OTHER_PROJECT | NOT_A_PROJECT).

2. Run the ISIC classifier by project type:
     - once for QDA_PROJECT projects
     - once for QD_PROJECT projects
   For each such project:
     - classify the project itself (as the sum of its files + metadata)
     - classify each primary data file individually
   Results go into project_classification / file_classification,
   matched taxonomy keywords go into tags.

3. Copy the resulting database to
       data/database/23277555-sq26-classification.db
   which is the file to commit to the repository and tag with the
   label "classification-results".

4. Print per-repository statistics (project types found + counts,
   dominant ISIC class).

Run:  python run_classification.py
"""

from __future__ import annotations

import shutil
from collections import Counter
from datetime import datetime, UTC
from pathlib import Path

from config import DB_PATH, DOWNLOAD_DIR, CLASSIFICATION_DB_PATH
from database import get_connection, init_db
from classifier import (
    derive_project_type,
    classify_text,
    build_project_text,
    build_file_text,
    is_primary_data_file,
)
from taxonomy_isic import full_class_name


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def fetch_projects(conn) -> list[dict]:
    cur = conn.cursor()
    cur.execute("""
        SELECT id, repository_id, repository_url, project_url, title,
               description, type,
               download_repository_folder, download_project_folder
        FROM projects
    """)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def fetch_files(conn, project_id: int) -> list[dict]:
    cur = conn.cursor()
    cur.execute("""
        SELECT id, file_name, file_type, status
        FROM files
        WHERE project_id = ?
    """, (project_id,))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def fetch_keywords(conn, project_id: int) -> list[str]:
    cur = conn.cursor()
    cur.execute("SELECT keyword FROM keywords WHERE project_id = ?", (project_id,))
    return [row[0] for row in cur.fetchall()]


def update_project_type(conn, project_id: int, project_type: str):
    conn.execute("UPDATE projects SET type = ? WHERE id = ?",
                 (project_type, project_id))


def upsert_project_classification(conn, project_id: int, result: dict):
    now = datetime.now(UTC).isoformat()
    conn.execute("""
        INSERT INTO project_classification (
            project_id, primary_section, primary_division, primary_class_name,
            secondary_section, secondary_division, secondary_class_name,
            primary_score, secondary_score, classified_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_id) DO UPDATE SET
            primary_section      = excluded.primary_section,
            primary_division     = excluded.primary_division,
            primary_class_name   = excluded.primary_class_name,
            secondary_section    = excluded.secondary_section,
            secondary_division   = excluded.secondary_division,
            secondary_class_name = excluded.secondary_class_name,
            primary_score        = excluded.primary_score,
            secondary_score      = excluded.secondary_score,
            classified_at        = excluded.classified_at
    """, (
        project_id,
        result["primary_section"],
        result["primary_division"],
        full_class_name(result["primary_division"]) if result["primary_division"] else None,
        result["secondary_section"],
        result["secondary_division"],
        full_class_name(result["secondary_division"]) if result["secondary_division"] else None,
        result["primary_score"],
        result["secondary_score"],
        now,
    ))


def upsert_file_classification(conn, file_id: int, result: dict):
    now = datetime.now(UTC).isoformat()
    conn.execute("""
        INSERT INTO file_classification (
            file_id, primary_section, primary_division, primary_class_name,
            secondary_section, secondary_division, secondary_class_name,
            primary_score, secondary_score, classified_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(file_id) DO UPDATE SET
            primary_section      = excluded.primary_section,
            primary_division     = excluded.primary_division,
            primary_class_name   = excluded.primary_class_name,
            secondary_section    = excluded.secondary_section,
            secondary_division   = excluded.secondary_division,
            secondary_class_name = excluded.secondary_class_name,
            primary_score        = excluded.primary_score,
            secondary_score      = excluded.secondary_score,
            classified_at        = excluded.classified_at
    """, (
        file_id,
        result["primary_section"],
        result["primary_division"],
        full_class_name(result["primary_division"]) if result["primary_division"] else None,
        result["secondary_section"],
        result["secondary_division"],
        full_class_name(result["secondary_division"]) if result["secondary_division"] else None,
        result["primary_score"],
        result["secondary_score"],
        now,
    ))


def insert_tags(conn, project_id: int, tags: list[str]):
    for tag in tags:
        conn.execute(
            "INSERT OR IGNORE INTO tags (project_id, tag) VALUES (?, ?)",
            (project_id, tag),
        )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def classify_all():
    init_db()  # ensures classification tables exist on older databases
    conn = get_connection()

    projects = fetch_projects(conn)
    print(f"Loaded {len(projects)} projects from {DB_PATH}")

    # ------------------------------------------------------------------
    # Step 1: derive PROJECT_TYPE for every project
    # ------------------------------------------------------------------
    type_counter_by_repo: dict[int, Counter] = {}

    for project in projects:
        files = fetch_files(conn, project["id"])
        project_type = derive_project_type(files)
        update_project_type(conn, project["id"], project_type)
        project["type"] = project_type
        project["_files"] = files

        repo = project["repository_id"]
        type_counter_by_repo.setdefault(repo, Counter())[project_type] += 1

    conn.commit()
    print("PROJECT_TYPE derived for all projects.")

    # ------------------------------------------------------------------
    # Step 2: run the classifier, once per project type
    # (QDA_PROJECT first, then QD_PROJECT), and by repository
    # ------------------------------------------------------------------
    class_counter_by_repo: dict[int, Counter] = {}

    for target_type in ("QDA_PROJECT", "QD_PROJECT"):
        batch = [p for p in projects if p["type"] == target_type]
        # process repository by repository
        batch.sort(key=lambda p: p["repository_id"])
        print(f"\nClassifying {len(batch)} {target_type} project(s)...")

        for project in batch:
            files = project["_files"]
            project["keywords"] = fetch_keywords(conn, project["id"])

            # --- classify the project as the sum of its files ----------
            text = build_project_text(project, files, download_dir=DOWNLOAD_DIR)
            result = classify_text(text)
            upsert_project_classification(conn, project["id"], result)
            if result["tags"]:
                insert_tags(conn, project["id"], result["tags"])

            repo = project["repository_id"]
            if result["primary_division"]:
                class_counter_by_repo.setdefault(repo, Counter())[
                    result["primary_division"]] += 1

            # --- classify each primary data file individually ----------
            for f in files:
                if not is_primary_data_file(f.get("file_type", ""),
                                            f.get("file_name", "")):
                    continue
                local = (DOWNLOAD_DIR
                         / (project.get("download_repository_folder") or "")
                         / (project.get("download_project_folder") or "")
                         / (f.get("file_name") or ""))
                file_text = build_file_text(f.get("file_name") or "", local)
                # fall back to project metadata context if the file alone
                # yields nothing
                file_result = classify_text(file_text)
                if not file_result["primary_division"]:
                    file_result = classify_text(
                        file_text + "\n" + (project.get("title") or ""))
                upsert_file_classification(conn, f["id"], file_result)

        conn.commit()

    # ------------------------------------------------------------------
    # Step 3: copy database to the deliverable name
    # ------------------------------------------------------------------
    conn.close()
    shutil.copy2(DB_PATH, CLASSIFICATION_DB_PATH)
    print(f"\nClassification database written to: {CLASSIFICATION_DB_PATH}")
    print('Commit it to your repository and tag it with label '
          '"classification-results", e.g.:')
    print(f"    git add {CLASSIFICATION_DB_PATH.name}")
    print('    git commit -m "Add classification results database"')
    print("    git tag classification-results")
    print("    git push && git push --tags")

    # ------------------------------------------------------------------
    # Step 4: statistics by repository
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("STATISTICS BY REPOSITORY")
    print("=" * 70)

    for repo_id in sorted(type_counter_by_repo):
        print(f"\nRepository {repo_id}")
        print("-" * 40)
        print("Project types found:")
        for ptype, count in type_counter_by_repo[repo_id].most_common():
            print(f"    {ptype:<15} {count}")

        classes = class_counter_by_repo.get(repo_id)
        if classes:
            dominant, dom_count = classes.most_common(1)[0]
            print(f"Dominant class: {full_class_name(dominant)} "
                  f"({dom_count} project(s))")
        else:
            print("Dominant class: (no projects could be classified)")

    return type_counter_by_repo, class_counter_by_repo


if __name__ == "__main__":
    classify_all()
