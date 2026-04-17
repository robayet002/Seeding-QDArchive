import sqlite3
from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # ------------------------------------------------------------------
    # PROJECTS table
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id                          INTEGER PRIMARY KEY AUTOINCREMENT,
            query_string                TEXT,
            repository_id               INTEGER NOT NULL,
            repository_url              TEXT    NOT NULL,
            project_url                 TEXT    NOT NULL,
            version                     TEXT,
            type                        TEXT    NOT NULL,
            title                       TEXT    NOT NULL,
            description                 TEXT    NOT NULL,
            language                    TEXT,
            doi                         TEXT,
            upload_date                 TEXT,
            download_date               TEXT    NOT NULL,
            download_repository_folder  TEXT    NOT NULL,
            download_project_folder     TEXT    NOT NULL,
            download_version_folder     TEXT,
            download_method             TEXT    NOT NULL
                CHECK (download_method IN ('SCRAPING', 'API-CALL')),
            UNIQUE(repository_id, project_url, version)
        )
    """)

    # ------------------------------------------------------------------
    # FILES table
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL,
            file_name   TEXT    NOT NULL,
            file_type   TEXT    NOT NULL,
            status      TEXT    NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)

    # ------------------------------------------------------------------
    # KEYWORDS table
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keywords (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL,
            keyword     TEXT    NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)

    # ------------------------------------------------------------------
    # PERSON_ROLE table
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS person_role (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL,
            name        TEXT    NOT NULL,
            role        TEXT    NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)

    # ------------------------------------------------------------------
    # LICENSES table
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL,
            license     TEXT    NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_repository_id ON projects(repository_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_project_id       ON files(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_project_id    ON keywords(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_person_role_project_id ON person_role(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_licenses_project_id    ON licenses(project_id)")

    conn.commit()
    conn.close()

    print("Database initialized successfully.")


if __name__ == "__main__":
    init_db()