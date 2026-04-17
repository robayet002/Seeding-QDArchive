import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, quote

BASE_URL = "https://dataverse.no"
SEARCH_URL = "https://dataverse.no/dataverse/root/"

SEARCH_QUERIES = [
    "student",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_persistent_id(url: str) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    pid = qs.get("persistentId", [""])[0].strip()
    if pid:
        return pid

    m = re.search(r"[?&]id=([^&]+)", url)
    return m.group(1).strip() if m else ""


def _build_datafile_download_url(file_pid: str) -> str:
    return (
        f"{BASE_URL}/api/access/datafile/:persistentId"
        f"?persistentId={quote(file_pid, safe='')}"
    )


def _clean(text: str) -> str:
    return " ".join((text or "").split()).strip()


def _extract_year(text: str) -> str:
    m = re.search(r"\b(19|20)\d{2}\b", text or "")
    return m.group(0) if m else ""


# ---------------------------------------------------------------------------
# Detail-page metadata extraction
# ---------------------------------------------------------------------------

def _fetch_dataset_metadata(session: requests.Session, dataset_url: str) -> dict:
    """
    Fetch the Dataverse dataset page and extract:
      title, description, year, doi, language,
      authors (list of dicts), keywords (list), licenses (list)
    """
    meta = {
        "title":       "",
        "description": "",
        "year":        "",
        "doi":         "",
        "language":    "",
        "authors":     [],
        "keywords":    [],
        "licenses":    [],
    }

    try:
        r = session.get(dataset_url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"    DV detail fetch failed {dataset_url}: {e}")
        return meta

    soup = BeautifulSoup(r.text, "html.parser")

    # ------------------------------------------------------------------ title
    for sel in ["h1", "title"]:
        el = soup.select_one(sel)
        if el:
            meta["title"] = _clean(el.get_text(" ", strip=True))
            break

    # --------------------------------------------------------------- description
    for sel in [
        'meta[name="description"]',
        'meta[property="og:description"]',
        ".dataset-description",
        "#datasetDescription",
        ".dsDescription",
        '[class*="description"]',
    ]:
        el = soup.select_one(sel)
        if not el:
            continue
        text = (el.get("content") or "").strip() if el.name == "meta" \
               else _clean(el.get_text(" ", strip=True))
        if text:
            meta["description"] = text
            break

    # -------------------------------------------------------------------- year
    meta["year"] = _extract_year(soup.get_text(" ", strip=True))

    # --------------------------------------------------------------------- doi
    for a in soup.select("a[href*='doi.org']"):
        meta["doi"] = (a.get("href") or "").strip()
        break

    # ---------------------------------------------------------------- language
    # Dataverse often puts language in a metadata block labelled "Language"
    for row in soup.select(".metadata-label, .datasetFieldType"):
        label = _clean(row.get_text(" ", strip=True)).lower()
        if "language" in label:
            nxt = row.find_next_sibling()
            if nxt:
                meta["language"] = _clean(nxt.get_text(" ", strip=True))
            break

    # ----------------------------------------------------------------- authors
    authors: list[dict] = []
    seen_names: set[str] = set()

    # Dataverse wraps authors in elements with class "author" or inside
    # a metadata section labelled "Author"
    for sel in [
        ".authorName",
        ".author",
        '[class*="author"]',
        ".datasetFieldValue",   # generic value block — filtered below
    ]:
        for el in soup.select(sel):
            # For generic value blocks, check the preceding label sibling
            if "datasetFieldValue" in (el.get("class") or []):
                prev = el.find_previous_sibling()
                if not prev:
                    continue
                if "author" not in _clean(prev.get_text()).lower():
                    continue

            name = _clean(el.get_text(" ", strip=True))
            if name and name not in seen_names:
                seen_names.add(name)
                authors.append({"name": name, "role": "AUTHOR"})

        if authors:
            break

    # Fallback: scan metadata table rows
    if not authors:
        author_re = re.compile(r"\bauthor\b|\bcreator\b", re.I)
        for row in soup.select("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            if author_re.search(_clean(cells[0].get_text())):
                name = _clean(cells[1].get_text(" ", strip=True))
                if name and name not in seen_names:
                    seen_names.add(name)
                    authors.append({"name": name, "role": "AUTHOR"})

    meta["authors"] = authors

    # ---------------------------------------------------------------- keywords
    keywords: list[str] = []
    seen_kw: set[str] = set()

    kw_re = re.compile(r"keyword|subject|topic", re.I)

    # Strategy 1: elements with keyword-like class names
    for sel in [".keywordValue", ".keyword", '[class*="keyword"]',
                ".subjectValue", '[class*="subject"]']:
        for el in soup.select(sel):
            for kw in re.split(r"[,;|]+", el.get_text(" ", strip=True)):
                kw = kw.strip()
                if kw and kw not in seen_kw:
                    seen_kw.add(kw)
                    keywords.append(kw)
        if keywords:
            break

    # Strategy 2: generic metadata value blocks preceded by keyword label
    if not keywords:
        for el in soup.select(".datasetFieldValue"):
            prev = el.find_previous_sibling()
            if prev and kw_re.search(_clean(prev.get_text())):
                for kw in re.split(r"[,;|]+", el.get_text(" ", strip=True)):
                    kw = kw.strip()
                    if kw and kw not in seen_kw:
                        seen_kw.add(kw)
                        keywords.append(kw)

    # Strategy 3: metadata table rows
    if not keywords:
        for row in soup.select("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            if kw_re.search(_clean(cells[0].get_text())):
                for kw in re.split(r"[,;|]+", cells[1].get_text(" ", strip=True)):
                    kw = kw.strip()
                    if kw and kw not in seen_kw:
                        seen_kw.add(kw)
                        keywords.append(kw)

    meta["keywords"] = keywords

    # ---------------------------------------------------------------- licenses
    licenses: list[str] = []
    seen_lic: set[str] = set()

    lic_re = re.compile(r"licen[sc]e|terms of use|access", re.I)

    for sel in [".licenseName", ".license", '[class*="license"]',
                '[href*="creativecommons"]', '[href*="opensource"]']:
        for el in soup.select(sel):
            lic = _clean(el.get_text(" ", strip=True)) or (el.get("href") or "").strip()
            if lic and lic not in seen_lic:
                seen_lic.add(lic)
                licenses.append(lic)
        if licenses:
            break

    # Fallback: metadata table rows
    if not licenses:
        for row in soup.select("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            if lic_re.search(_clean(cells[0].get_text())):
                lic = _clean(cells[1].get_text(" ", strip=True))
                if lic and lic not in seen_lic:
                    seen_lic.add(lic)
                    licenses.append(lic)

    meta["licenses"] = licenses

    return meta


# ---------------------------------------------------------------------------
# File-level record extraction
# ---------------------------------------------------------------------------

def _extract_file_records_from_dataset(
    session: requests.Session,
    dataset_url: str,
    dataset_meta: dict,
) -> list[dict]:
    """Return one record per file found on the dataset page, each carrying
    the full dataset metadata so main.py can populate all tables."""
    records = []
    seen_file_ids: set[str] = set()

    try:
        r = session.get(dataset_url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"    DV file-list fetch failed {dataset_url}: {e}")
        return records

    soup = BeautifulSoup(r.text, "html.parser")

    for link in soup.select('a[href*="/file.xhtml"]'):
        href = (link.get("href") or "").strip()
        if not href:
            continue

        file_page_url = urljoin(BASE_URL, href)
        file_pid = _extract_persistent_id(file_page_url)

        if not file_pid or file_pid in seen_file_ids:
            continue
        seen_file_ids.add(file_pid)

        link_text = _clean(link.get_text(" ", strip=True))
        title = link_text or dataset_meta.get("title") or file_pid

        records.append({
            "id":          file_pid,
            "title":       title,
            "url":         file_page_url,
            "download_url": _build_datafile_download_url(file_pid),
            "year":        dataset_meta.get("year", ""),
            "description": dataset_meta.get("description", ""),
            "doi":         dataset_meta.get("doi", ""),
            "language":    dataset_meta.get("language", ""),
            "license":     dataset_meta["licenses"][0] if dataset_meta.get("licenses") else "",
            # structured fields for metadata.py helpers
            "persons":     dataset_meta.get("authors", []),
            "keywords":    dataset_meta.get("keywords", []),
            "licenses":    dataset_meta.get("licenses", []),
        })

    return records


# ---------------------------------------------------------------------------
# Public search function
# ---------------------------------------------------------------------------

def search_dv(rows=None, per_page=10, max_pages=100):
    headers = {"User-Agent": "Mozilla/5.0"}

    results: list[dict] = []
    seen_dataset_ids: set[str] = set()
    seen_file_ids_global: set[str] = set()

    session = requests.Session()
    session.headers.update(headers)

    for query in SEARCH_QUERIES:
        print(f"DataverseNO query: {query!r}")

        for page in range(1, max_pages + 1):
            params = {
                "q":     query,
                "page":  page,
                "sort":  "score",
                "order": "desc",
                "types": "dataverses:datasets:files",
            }

            r = session.get(SEARCH_URL, params=params, timeout=30)
            r.raise_for_status()

            soup = BeautifulSoup(r.text, "html.parser")

            dataset_links: list[dict] = []
            seen_on_page: set[str] = set()

            for link in soup.select('a[href*="/dataset.xhtml"]'):
                href = (link.get("href") or "").strip()
                title = _clean(link.get_text(" ", strip=True))
                if not href:
                    continue

                full_url = urljoin(BASE_URL, href)
                if "/dataset.xhtml" not in full_url or full_url in seen_on_page:
                    continue
                seen_on_page.add(full_url)

                pid = _extract_persistent_id(full_url)
                if not pid:
                    continue

                dataset_links.append({"id": pid, "title": title, "url": full_url})

            if not dataset_links:
                print(f"  page {page}: 0 dataset records — stopping")
                break

            new_datasets = 0
            new_files = 0

            for dataset in dataset_links:
                dataset_id = dataset["id"]
                if dataset_id in seen_dataset_ids:
                    continue
                seen_dataset_ids.add(dataset_id)
                new_datasets += 1

                # Fetch full metadata (title, description, authors, keywords, licenses…)
                meta = _fetch_dataset_metadata(session, dataset["url"])
                if not meta["title"]:
                    meta["title"] = dataset["title"] or dataset_id

                file_records = _extract_file_records_from_dataset(
                    session, dataset["url"], meta
                )

                for rec in file_records:
                    if rec["id"] in seen_file_ids_global:
                        continue
                    seen_file_ids_global.add(rec["id"])
                    results.append(rec)
                    new_files += 1

                    if rows is not None and len(results) >= rows:
                        return results

            print(f"  page {page}: {new_datasets} new datasets, {new_files} file records")

            if new_datasets == 0:
                break

    return results