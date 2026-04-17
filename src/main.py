from datetime import datetime, UTC
from pathlib import Path
from urllib.parse import urljoin, urlparse
import mimetypes
import requests
from bs4 import BeautifulSoup

from config import DOWNLOAD_DIR, QDA_EXTENSIONS
from database import init_db
from downloader import download_file, sanitize_filename
from metadata import (
    get_or_create_project,
    insert_file,
    insert_keywords,
    insert_persons,
    insert_licenses,
)
from scraper_sada import search_sada
from scraper_dataverse import search_dv


# ---------------------------------------------------------------------------
# Repository registry
# Maps a source_name string -> (repository_id, repository_url, folder_name)
# Add more repos here as the project grows.
# ---------------------------------------------------------------------------
REPOSITORY_REGISTRY: dict[str, tuple[int, str, str]] = {
    "SADA":      (1, "https://www.datafirst.uct.ac.za", "sada"),
    "Dataverse": (2, "https://dataverse.no",             "dataverse"),
    "Zenodo":    (3, "https://zenodo.org",               "zenodo"),
}


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def extension_from_content_type(content_type: str) -> str:
    content_type = (content_type or "").split(";")[0].strip().lower()

    mapping = {
        "application/pdf": ".pdf",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.ms-excel": ".xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "text/csv": ".csv",
        "application/zip": ".zip",
        "application/x-zip-compressed": ".zip",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        "application/vnd.ms-powerpoint": ".ppt",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "video/mp4": ".mp4",
        "video/x-msvideo": ".avi",
        "text/plain": ".txt",
        "application/json": ".json",
        "application/xml": ".xml",
        "text/xml": ".xml",
    }

    if content_type in mapping:
        return mapping[content_type]

    return mimetypes.guess_extension(content_type) or ""


def get_url_head_info(url: str) -> tuple[str, str]:
    try:
        r = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
            allow_redirects=True,
            stream=True,
        )
        r.raise_for_status()
        content_type = (r.headers.get("Content-Type") or "").lower()
        final_url = r.url
        r.close()
        return content_type, final_url
    except Exception:
        return "", url


def extract_year(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text[:4] if len(text) >= 4 else text


def is_probable_file_url(url: str) -> bool:
    if not url:
        return False
    path = urlparse(url).path.lower()
    file_exts = {
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".zip", ".rar", ".7z",
        ".txt", ".rtf", ".xml", ".json", ".jpg", ".jpeg", ".png", ".mp3", ".mp4",
        ".wav", ".avi", ".mov", ".qda", ".qdpx", ".qdp", ".nvp", ".nvpx",
    }
    return any(path.endswith(ext) for ext in file_exts)


# ---------------------------------------------------------------------------
# Normalise a raw scraper record into a common shape
# ---------------------------------------------------------------------------

def normalize_record(record: dict, source_name: str) -> dict:
    record_id = str(record.get("id") or record.get("record_id") or "").strip()
    title = str(record.get("title") or "").strip()
    source_url = str(record.get("url") or "").strip()
    description = str(record.get("description") or "").strip()
    year = extract_year(record.get("year") or record.get("date") or "")
    license_text = str(record.get("license") or "").strip()

    # Author / creators
    author = ""
    if record.get("author"):
        author = str(record["author"]).strip()
    elif record.get("authors"):
        authors = record["authors"]
        if isinstance(authors, list):
            author = "; ".join(str(a).strip() for a in authors if str(a).strip())
        else:
            author = str(authors).strip()
    elif record.get("creators"):
        creators = record["creators"]
        if isinstance(creators, list):
            author = "; ".join(
                (c.get("name", "") if isinstance(c, dict) else str(c)).strip()
                for c in creators
            ).strip("; ")
        else:
            author = str(creators).strip()

    file_url = str(
        record.get("file_url") or record.get("download_url") or source_url
    ).strip()

    return {
        "source_name": source_name,
        "record_id": record_id,
        "title": title,
        "author": author,
        "year": year,
        "description": description,
        "license": license_text,
        "source_url": source_url,
        "file_url": file_url,
        # pass through anything extra the scraper returned
        "keywords": record.get("keywords", []),
        "persons":  record.get("persons", []),
        "licenses": record.get("licenses", []),
    }


# ---------------------------------------------------------------------------
# Page-scraping helpers (unchanged logic, extracted for clarity)
# ---------------------------------------------------------------------------

def extract_file_links_from_page(page_url: str) -> list[dict]:
    headers = {"User-Agent": "Mozilla/5.0"}
    results: list[dict] = []
    seen: set[tuple] = set()

    def add_result(filename: str, url: str):
        key = (filename, url)
        if key not in seen:
            seen.add(key)
            results.append({"filename": filename, "url": url})

    def looks_downloadable(url: str, text: str = "") -> bool:
        url_lower = url.lower()
        text_lower = (text or "").lower()
        if is_probable_file_url(url):
            return True
        strong_words = [
            "download", "pdf", "csv", "zip", "xls", "xlsx",
            "doc", "docx", "audio", "video", "mp3", "mp4", "wav", "xml",
        ]
        if any(w in text_lower for w in strong_words):
            return True
        tokens = ["/download/", "format=raw", "attachment", "bitstream",
                  "/metadata/export/", "downloadfile", "download="]
        return any(t in url_lower for t in tokens)

    def fetch(url: str):
        try:
            r = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
            r.raise_for_status()
            return r
        except Exception as e:
            print(f"  Could not fetch {url}: {e}")
            return None

    def links_from_soup(html_url: str, soup: BeautifulSoup) -> list[dict]:
        items = []
        for a in soup.select("a[href]"):
            href = (a.get("href") or "").strip()
            if not href:
                continue
            full = urljoin(html_url, href)
            text = " ".join(a.get_text(" ", strip=True).split())
            fname = Path(urlparse(full).path).name.strip()
            if looks_downloadable(full, text):
                if not fname:
                    fname = sanitize_filename(text) if text else "downloaded_file"
                items.append({"filename": fname, "url": full, "text": text})
        return items

    r = fetch(page_url)
    if not r:
        return results

    ct = (r.headers.get("Content-Type") or "").lower()
    if "text/html" not in ct and is_probable_file_url(page_url):
        fname = Path(urlparse(r.url).path).name or "downloaded_file"
        return [{"filename": fname, "url": r.url}]

    soup = BeautifulSoup(r.text, "html.parser")

    # 1) SADA explicit download buttons
    for a in soup.select("a.download"):
        href = (a.get("href") or "").strip()
        fname = (a.get("data-filename") or "").strip()
        ext = (a.get("data-extension") or "").strip().lower()
        if not href:
            continue
        full = urljoin(page_url, href)
        if not fname:
            fname = Path(urlparse(full).path).name or "downloaded_file"
        if ext and not fname.lower().endswith("." + ext):
            fname = f"{fname}.{ext}"
        add_result(fname, full)

    if results:
        return results

    # 2) Generic direct download links
    for item in links_from_soup(page_url, soup):
        add_result(item["filename"], item["url"])

    if results:
        return results

    # 3) Follow intermediate "Access / Download" pages
    access_words = ["access dataset", "access file", "access data",
                    "download", "get data", "view files", "files"]
    visited: set[str] = set()
    for a in soup.select("a[href], button[onclick]"):
        href = ""
        if a.name == "a":
            href = (a.get("href") or "").strip()
        elif a.name == "button":
            onclick = (a.get("onclick") or "").strip()
            if "location.href=" in onclick:
                href = onclick.split("location.href=")[-1].strip(" '\";")
        text = " ".join(a.get_text(" ", strip=True).split()).lower()
        if not href or not any(w in text for w in access_words):
            continue
        full = urljoin(page_url, href)
        if full in visited:
            continue
        visited.add(full)
        r2 = fetch(full)
        if not r2:
            continue
        ct2 = (r2.headers.get("Content-Type") or "").lower()
        if "text/html" not in ct2:
            fname = Path(urlparse(r2.url).path).name or "downloaded_file"
            add_result(fname, r2.url)
            continue
        for item in links_from_soup(r2.url, BeautifulSoup(r2.text, "html.parser")):
            add_result(item["filename"], item["url"])

    return results


# ---------------------------------------------------------------------------
# Core: process one scraped record end-to-end
# ---------------------------------------------------------------------------

def process_record(record: dict, source_name: str):
    norm = normalize_record(record, source_name)

    title = norm["title"]
    source_url = norm["source_url"]
    direct_file_url = norm["file_url"]

    if not title and not source_url:
        print(f"Skipping {source_name} record: missing title and URL")
        return

    record_id = norm["record_id"]

    # Resolve repository info from registry
    repo_info = REPOSITORY_REGISTRY.get(source_name)
    if repo_info is None:
        print(f"Unknown source '{source_name}' — add it to REPOSITORY_REGISTRY")
        return
    repository_id, repository_url, repo_folder = repo_info

    # Build download folder
    safe_record_id = sanitize_filename(record_id)[:60] if record_id else ""
    safe_title = sanitize_filename(title)[:60] if title else "untitled"
    folder_name = (safe_record_id or safe_title or "unknown_record")[:80].rstrip(". ")
    record_folder = DOWNLOAD_DIR / repo_folder / folder_name
    record_folder.mkdir(parents=True, exist_ok=True)

    # Determine project_folder relative to the repo folder
    project_folder = folder_name

    # Collect downloadable file links
    if direct_file_url and direct_file_url != source_url:
        guessed_fname = sanitize_filename(title or record_id or "downloaded_file")
        file_links = [{"filename": guessed_fname, "url": direct_file_url}]
    else:
        file_links = extract_file_links_from_page(source_url)

    if not file_links:
        print(f"No downloadable files found on [{source_name}] {source_url}")
        return

    print(f"Found {len(file_links)} file(s) for [{source_name}] {title}")

    download_date = datetime.now(UTC).isoformat()

    # ------------------------------------------------------------------
    # Upsert the PROJECTS row (once per record, shared by all its files)
    # ------------------------------------------------------------------
    project_data = {
        "query_string":                 None,          # populated by scrapers if available
        "repository_id":                repository_id,
        "repository_url":               repository_url,
        "project_url":                  source_url,
        "version":                      record.get("version"),
        "type":                         "QDA_PROJECT", # default; scrapers can override
        "title":                        title or record_id or "Untitled",
        "description":                  norm["description"] or "",
        "language":                     record.get("language"),
        "doi":                          record.get("doi"),
        "upload_date":                  norm["year"] or None,
        "download_date":                download_date,
        "download_repository_folder":   repo_folder,
        "download_project_folder":      project_folder,
        "download_version_folder":      record.get("version"),
        "download_method":              "SCRAPING",
    }

    try:
        project_id = get_or_create_project(project_data)
    except Exception as e:
        print(f"Could not insert project [{source_name}] {source_url}: {e}")
        return

    # ------------------------------------------------------------------
    # KEYWORDS, PERSONS, LICENSES (once per project insert)
    # ------------------------------------------------------------------
    if norm["keywords"]:
        insert_keywords(project_id, norm["keywords"])

    # Build persons list from the author string if no structured list given
    persons = norm["persons"]
    if not persons and norm["author"]:
        for name in norm["author"].split(";"):
            name = name.strip()
            if name:
                persons.append({"name": name, "role": "UNKNOWN"})
    if persons:
        insert_persons(project_id, persons)

    licenses = norm["licenses"]
    if not licenses and norm["license"]:
        licenses = [norm["license"]]
    if licenses:
        insert_licenses(project_id, licenses)

    # ------------------------------------------------------------------
    # Download each file and insert a FILES row
    # ------------------------------------------------------------------
    for file_info in file_links:
        original_filename = file_info["filename"]
        file_url = file_info["url"]

        content_type, final_url = get_url_head_info(file_url)

        if "text/html" in content_type:
            print(f"  Skipping HTML page: {file_url}")
            continue

        safe_filename = sanitize_filename(original_filename)[:100]
        suffix = Path(safe_filename).suffix.lower()

        if not suffix:
            ext = extension_from_content_type(content_type) or \
                  Path(urlparse(final_url).path).suffix.lower()
            if ext:
                safe_filename += ext
                suffix = ext

        destination = record_folder / safe_filename
        success = download_file(file_url, destination)
        status = "SUCCEEDED" if success else "FAILED_LOGIN_REQUIRED"

        insert_file(
            project_id=project_id,
            file_name=safe_filename,
            file_type=suffix.lstrip(".") if suffix else "",
            status=status,
        )

        if success:
            print(f"  Downloaded: {destination}")
        else:
            print(f"  Failed:     {file_url}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("Initializing database...")
    init_db()

    print("\nSearching SADA...")
    try:
        sada_records = search_sada(rows=None, per_page=15, max_pages=50)
        print(f"Found {len(sada_records)} SADA records")
    except Exception as e:
        print(f"Error searching SADA: {e}")
        sada_records = []

    print("\nSearching Dataverse...")
    try:
        dv_records = search_dv()
        print(f"Found {len(dv_records)} Dataverse records")
    except Exception as e:
        print(f"Error searching Dataverse: {e}")
        dv_records = []

    for record in sada_records:
        process_record(record, "SADA")

    for record in dv_records:
        process_record(record, "Dataverse")

    print("\nDone.")


if __name__ == "__main__":
    main()