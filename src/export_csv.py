import csv
import sqlite3
from config import DB_PATH, EXPORT_DIR


TABLES = ["projects", "files", "keywords", "person_role", "licenses"]


def export_table_to_csv(cursor: sqlite3.Cursor, table: str):
    output_file = EXPORT_DIR / f"{table}.csv"

    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    column_names = [d[0] for d in cursor.description]

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(column_names)
        writer.writerows(rows)

    print(f"Exported {len(rows):>6} rows  →  {output_file}")


def export_all():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"Exporting {len(TABLES)} tables to {EXPORT_DIR}\n")
    for table in TABLES:
        export_table_to_csv(cursor, table)

    conn.close()
    print("\nExport complete.")


if __name__ == "__main__":
    export_all()