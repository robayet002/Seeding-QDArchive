import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://www.datafirst.uct.ac.za"
SEARCH_URL = "https://www.datafirst.uct.ac.za/dataportal/index.php/catalog/"

SEARCH_QUERIES = [
    "science",
]


def _clean(text: str) -> str:
    return " ".join((text or "").split()).strip()


def _fetch_record_detail(session: requests.Session, url: str) -> dict:
    """
    Visit a SADA catalog detail page and extract:
      - title, description, year, doi, language
      - authors  → list of {"name": ..., "role": "AUTHOR"}
      - keywords → list of strings
      - licenses → list of strings
    """
    detail = {
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
        r = session.get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"    SADA detail fetch failed {url}: {e}")
        return detail

    soup = BeautifulSoup(r.text, "html.parser")

    # ------------------------------------------------------------------ title
    h1 = soup.select_one("h1.title") or soup.select_one("h1")
    if h1:
        detail["title"] = _clean(h1.get_text(" ", strip=True))

    # --------------------------------------------------------------- description
    for sel in [".abstract", "#abstract", '[id*="abstract"]', ".description"]:
        el = soup.select_one(sel)
        if el:
            detail["description"] = _clean(el.get_text(" ", strip=True))
            break

    # -------------------------------------------------------------------- year
    m = re.search(r"\b(19|20)\d{2}\b", soup.get_text(" ", strip=True))
    if m:
        detail["year"] = m.group(0)

    # --------------------------------------------------------------------- doi
    for a in soup.select("a[href*='doi.org']"):
        detail["doi"] = (a.get("href") or "").strip()
        break

    # ---------------------------------------------------------------- language
    for sel in [".language", '[id*="language"]']:
        el = soup.select_one(sel)
        if el:
            detail["language"] = _clean(el.get_text(" ", strip=True))
            break

    # ----------------------------------------------------------------- authors
    # The SADA portal renders authors in a metadata table; rows typically have
    # a label cell containing "Author" / "Principal Investigator" and a value cell.
    authors = []
    seen_names: set[str] = set()

    author_labels = re.compile(
        r"(author|principal investigator|creator|researcher|contributor)",
        re.I,
    )

    # Strategy 1: look for <tr> where the first <td>/<th> matches an author label
    for row in soup.select("table tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        label = _clean(cells[0].get_text(" ", strip=True)).lower()
        if author_labels.search(label):
            name = _clean(cells[1].get_text(" ", strip=True))
            if name and name not in seen_names:
                seen_names.add(name)
                authors.append({"name": name, "role": "AUTHOR"})

    # Strategy 2: dedicated author/creator elements
    if not authors:
        for sel in [".authors", ".author", ".creator",
                    '[id*="author"]', '[class*="author"]']:
            for el in soup.select(sel):
                name = _clean(el.get_text(" ", strip=True))
                if name and name not in seen_names:
                    seen_names.add(name)
                    authors.append({"name": name, "role": "AUTHOR"})

    detail["authors"] = authors

    # ---------------------------------------------------------------- keywords
    keywords: list[str] = []
    seen_kw: set[str] = set()

    keyword_labels = re.compile(r"keyword|subject|topic|tag", re.I)

    # Strategy 1: metadata table rows whose label matches keyword-like text
    for row in soup.select("table tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        label = _clean(cells[0].get_text(" ", strip=True)).lower()
        if keyword_labels.search(label):
            # Value cell may contain multiple comma/semicolon separated terms
            raw = _clean(cells[1].get_text(" | ", strip=True))
            for kw in re.split(r"[,;|]+", raw):
                kw = kw.strip()
                if kw and kw not in seen_kw:
                    seen_kw.add(kw)
                    keywords.append(kw)

    # Strategy 2: dedicated keyword/tag elements
    if not keywords:
        for sel in [".keywords", ".keyword", ".tags", ".tag",
                    '[id*="keyword"]', '[class*="keyword"]']:
            for el in soup.select(sel):
                for kw in re.split(r"[,;|]+", el.get_text(" ", strip=True)):
                    kw = kw.strip()
                    if kw and kw not in seen_kw:
                        seen_kw.add(kw)
                        keywords.append(kw)

    detail["keywords"] = keywords

    # ---------------------------------------------------------------- licenses
    licenses: list[str] = []
    seen_lic: set[str] = set()

    license_labels = re.compile(r"licen[sc]e|terms of use|access condition", re.I)

    for row in soup.select("table tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        label = _clean(cells[0].get_text(" ", strip=True)).lower()
        if license_labels.search(label):
            lic = _clean(cells[1].get_text(" ", strip=True))
            if lic and lic not in seen_lic:
                seen_lic.add(lic)
                licenses.append(lic)

    if not licenses:
        for sel in [".license", ".licence", '[id*="license"]',
                    '[class*="license"]', '[href*="creativecommons"]']:
            for el in soup.select(sel):
                lic = _clean(el.get_text(" ", strip=True)) or (el.get("href") or "").strip()
                if lic and lic not in seen_lic:
                    seen_lic.add(lic)
                    licenses.append(lic)

    detail["licenses"] = licenses

    return detail


def search_sada(rows=None, per_page=15, max_pages=100):
    headers = {"User-Agent": "Mozilla/5.0"}
    datasets = []
    seen_ids: set[str] = set()

    session = requests.Session()
    session.headers.update(headers)

    for query in SEARCH_QUERIES:
        print(f"SADA query: {query!r}")

        for page in range(1, max_pages + 1):
            params = {"page": page, "sk": query, "ps": per_page}

            r = session.get(SEARCH_URL, params=params, timeout=30)
            r.raise_for_status()

            soup = BeautifulSoup(r.text, "html.parser")
            page_count = 0

            for link in soup.select("a[href]"):
                href = (link.get("href") or "").strip()
                title = _clean(link.get_text(" ", strip=True))

                if not href or not title:
                    continue

                full_url = urljoin(BASE_URL, href)

                if "/catalog/" not in full_url:
                    continue

                match = re.search(r"/catalog/(\d+)", full_url)
                if not match:
                    continue

                record_id = match.group(1)

                if record_id in seen_ids:
                    continue
                seen_ids.add(record_id)
                page_count += 1

                # Fetch the detail page to get enriched metadata
                detail = _fetch_record_detail(session, full_url)

                datasets.append({
                    "id":          record_id,
                    "title":       detail["title"] or title,
                    "url":         full_url,
                    "year":        detail["year"],
                    "description": detail["description"],
                    "doi":         detail["doi"],
                    "language":    detail["language"],
                    "license":     detail["licenses"][0] if detail["licenses"] else "",
                    # structured fields consumed by metadata.py helpers
                    "persons":     detail["authors"],
                    "keywords":    detail["keywords"],
                    "licenses":    detail["licenses"],
                })

                if rows is not None and len(datasets) >= rows:
                    return datasets

            print(f"  page {page}: {page_count} new records")

            if page_count == 0:
                break

    return datasets