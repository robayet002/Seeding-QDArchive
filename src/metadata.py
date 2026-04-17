from datetime import datetime, UTC
from database import get_connection


# ---------------------------------------------------------------------------
# PROJECTS
# ---------------------------------------------------------------------------

def insert_project(data: dict) -> int | None:
    """
    Insert one row into the projects table.
    Returns the new row's id, or None if ignored (duplicate).
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO projects (
            query_string, repository_id, repository_url, project_url,
            version, type, title, description, language, doi,
            upload_date, download_date, download_repository_folder,
            download_project_folder, download_version_folder, download_method
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("query_string"),
        data["repository_id"],
        data["repository_url"],
        data["project_url"],
        data.get("version"),
        data["type"],
        data["title"],
        data["description"],
        data.get("language"),
        data.get("doi"),
        data.get("upload_date"),
        data.get("download_date", datetime.now(UTC).isoformat()),
        data["download_repository_folder"],
        data["download_project_folder"],
        data.get("download_version_folder"),
        data["download_method"],
    ))

    conn.commit()
    project_id = cursor.lastrowid if cursor.rowcount > 0 else None
    conn.close()
    return project_id


def get_or_create_project(data: dict) -> int:
    """Return id of existing project row, inserting first if needed."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM projects
        WHERE repository_id = ?
          AND project_url   = ?
          AND COALESCE(version, '') = COALESCE(?, '')
    """, (data["repository_id"], data["project_url"], data.get("version")))

    row = cursor.fetchone()
    conn.close()

    if row:
        return row[0]

    project_id = insert_project(data)
    if project_id is None:
        raise RuntimeError(f"Could not insert or find project: {data.get('project_url')}")
    return project_id


# ---------------------------------------------------------------------------
# FILES
# ---------------------------------------------------------------------------

def insert_file(project_id: int, file_name: str, file_type: str, status: str):
    """
    Insert one row into the files table.

    Valid DOWNLOAD_RESULT values (exact strings, checker is strict):
        'SUCCEEDED'                  — download succeeded
        'FAILED'                     — generic failure
        'FAILED_SERVER_UNRESPONSIVE' — server did not respond
        'FAILED_LOGIN_REQUIRED'      — resource requires login
        'FAILED_TOO_LARGE'           — file too large
        'DOWNLODED'                  — alternate success value in spec (typo)
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO files (project_id, file_name, file_type, status)
        VALUES (?, ?, ?, ?)
    """, (project_id, file_name, file_type, status))

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# KEYWORDS
# ---------------------------------------------------------------------------

def insert_keyword(project_id: int, keyword: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO keywords (project_id, keyword) VALUES (?, ?)",
                   (project_id, keyword))
    conn.commit()
    conn.close()


def insert_keywords(project_id: int, keywords: list[str]):
    for kw in keywords:
        kw = kw.strip()
        if kw:
            insert_keyword(project_id, kw)


# ---------------------------------------------------------------------------
# PERSON_ROLE
# ---------------------------------------------------------------------------

def insert_person_role(project_id: int, name: str, role: str = "UNKNOWN"):
    """
    Valid PERSON_ROLE values:
        AUTHOR | UPLOADER | OWNER | OTHER | UNKNOWN
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO person_role (project_id, name, role) VALUES (?, ?, ?)",
                   (project_id, name, role))
    conn.commit()
    conn.close()


def insert_persons(project_id: int, persons: list[dict]):
    """Each dict needs 'name' and optionally 'role'."""
    valid_roles = {"AUTHOR", "UPLOADER", "OWNER", "OTHER", "UNKNOWN"}
    for p in persons:
        name = (p.get("name") or "").strip()
        role = (p.get("role") or "UNKNOWN").strip().upper()
        if role not in valid_roles:
            role = "UNKNOWN"
        if name:
            insert_person_role(project_id, name, role)


# ---------------------------------------------------------------------------
# LICENSES
# ---------------------------------------------------------------------------

def insert_license(project_id: int, license_text: str):
    """
    Store the raw original license string exactly as scraped.
    Do NOT convert to SPDX format.

    Checker recognises (with optional version suffix e.g. '4.0'):
        CC BY | CC BY-SA | CC BY-NC | CC BY-ND | CC BY-NC-ND | CC0
        ODbL  | ODC-By   | PDDL     | ODbL-1.0 | ODC-By-1.0
    Any other original string is also accepted per the schema spec.
    """
    if not license_text or not license_text.strip():
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO licenses (project_id, license) VALUES (?, ?)",
                   (project_id, license_text.strip()))
    conn.commit()
    conn.close()


def insert_licenses(project_id: int, license_list: list[str]):
    """Bulk-insert license strings. Deduplicates within the list."""
    seen: set[str] = set()
    for lic in license_list:
        lic = (lic or "").strip()
        if lic and lic not in seen:
            seen.add(lic)
            insert_license(project_id, lic)