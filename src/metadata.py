from datetime import datetime, UTC
from database import get_connection


# ---------------------------------------------------------------------------
# PROJECTS
# ---------------------------------------------------------------------------

def insert_project(data: dict) -> int | None:
    """
    Insert one row into the projects table.
    Returns the new row's id, or None if the row was ignored (duplicate).

    Required keys in `data`:
        repository_id, repository_url, project_url, type,
        title, description, download_date,
        download_repository_folder, download_project_folder,
        download_method  ('SCRAPING' | 'API-CALL')

    Optional keys:
        query_string, version, language, doi, upload_date,
        download_version_folder
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO projects (
            query_string,
            repository_id,
            repository_url,
            project_url,
            version,
            type,
            title,
            description,
            language,
            doi,
            upload_date,
            download_date,
            download_repository_folder,
            download_project_folder,
            download_version_folder,
            download_method
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
    """
    Return the id of an existing project row (matched on the UNIQUE key:
    repository_id + project_url + version), inserting it first if needed.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM projects
        WHERE repository_id = ?
          AND project_url   = ?
          AND COALESCE(version, '') = COALESCE(?, '')
    """, (
        data["repository_id"],
        data["project_url"],
        data.get("version"),
    ))

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

    status should be a DOWNLOAD_RESULT value, e.g. 'success' or 'failed'.
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

    cursor.execute("""
        INSERT INTO keywords (project_id, keyword)
        VALUES (?, ?)
    """, (project_id, keyword))

    conn.commit()
    conn.close()


def insert_keywords(project_id: int, keywords: list[str]):
    """Bulk-insert a list of keyword strings for one project."""
    for kw in keywords:
        kw = kw.strip()
        if kw:
            insert_keyword(project_id, kw)


# ---------------------------------------------------------------------------
# PERSON_ROLE
# ---------------------------------------------------------------------------

def insert_person_role(project_id: int, name: str, role: str = "UNKNOWN"):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO person_role (project_id, name, role)
        VALUES (?, ?, ?)
    """, (project_id, name, role))

    conn.commit()
    conn.close()


def insert_persons(project_id: int, persons: list[dict]):
    """
    Bulk-insert person/role pairs.
    Each dict should have 'name' and optionally 'role'.
    Example: [{'name': 'Li, Huaqiang', 'role': 'AUTHOR'}]
    """
    for p in persons:
        name = (p.get("name") or "").strip()
        role = (p.get("role") or "UNKNOWN").strip()
        if name:
            insert_person_role(project_id, name, role)


# ---------------------------------------------------------------------------
# LICENSES
# ---------------------------------------------------------------------------

def insert_license(project_id: int, license_text: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO licenses (project_id, license)
        VALUES (?, ?)
    """, (project_id, license_text))

    conn.commit()
    conn.close()


def insert_licenses(project_id: int, license_list: list[str]):
    """Bulk-insert a list of license strings for one project."""
    for lic in license_list:
        lic = lic.strip()
        if lic:
            insert_license(project_id, lic)