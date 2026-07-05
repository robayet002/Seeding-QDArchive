"""
Generate the classification report as a PDF (Classification_instruction).

Structure, per repository:
    - Histogram of primary classes identified
        * full class name as bin name
        * count printed on top of each bar
        * vector graphics (matplotlib PDF backend, zoomable)
    - Rank-ordered table of classes (most common first, top 20, with counts)
    - Comments on the findings

Run:  python report_pdf.py
"""

from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from config import REPORT_PDF_PATH
from database import get_connection

TOP_N = 20


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------

def load_report_data():
    """Return {repository_id: {"types": Counter, "classes": Counter,
                               "url": str, "n_projects": int}}"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.repository_id, p.repository_url, p.type,
               pc.primary_class_name
        FROM projects p
        LEFT JOIN project_classification pc ON pc.project_id = p.id
    """)

    data: dict[int, dict] = {}
    for repo_id, repo_url, ptype, primary_class in cursor.fetchall():
        entry = data.setdefault(repo_id, {
            "url": repo_url,
            "types": Counter(),
            "classes": Counter(),
            "n_projects": 0,
        })
        entry["n_projects"] += 1
        entry["types"][ptype or "NOT_A_PROJECT"] += 1
        if primary_class:
            entry["classes"][primary_class] += 1

    conn.close()
    return data


# ---------------------------------------------------------------------------
# Report pages
# ---------------------------------------------------------------------------

def _wrap(label: str, width: int = 45) -> str:
    """Wrap long class names for readable bin labels."""
    words, lines, current = label.split(), [], ""
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return "\n".join(lines)


def _histogram_page(pdf: PdfPages, repo_id: int, entry: dict):
    classes = entry["classes"].most_common(TOP_N)

    fig, ax = plt.subplots(figsize=(11.7, 8.3))  # A4 landscape

    if not classes:
        ax.axis("off")
        ax.text(0.5, 0.55, f"Repository {repo_id}",
                ha="center", fontsize=18, weight="bold")
        ax.text(0.5, 0.45, "No projects could be classified.",
                ha="center", fontsize=12)
        pdf.savefig(fig)
        plt.close(fig)
        return

    labels = [_wrap(name) for name, _ in classes]
    counts = [count for _, count in classes]

    y = range(len(classes))
    bars = ax.barh(y, counts, color="#4472C4", edgecolor="#2F528F")
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=7)
    ax.invert_yaxis()  # most common on top
    ax.set_xlabel("Number of projects")
    ax.set_title(
        f"Repository {repo_id} ({entry['url']})\n"
        f"Histogram of primary classes (ISIC Rev. 4 divisions)",
        fontsize=13, weight="bold",
    )

    # Count as a number on top of (i.e. at the end of) each bar
    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + max(counts) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                str(count), va="center", fontsize=8, weight="bold")

    ax.set_xlim(0, max(counts) * 1.12)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    pdf.savefig(fig)  # PDF backend -> vector graphics, zoomable
    plt.close(fig)


def _table_page(pdf: PdfPages, repo_id: int, entry: dict):
    classes = entry["classes"].most_common(TOP_N)
    if not classes:
        return

    fig, ax = plt.subplots(figsize=(11.7, 8.3))
    ax.axis("off")
    ax.set_title(
        f"Repository {repo_id} \u2013 rank-ordered primary classes "
        f"(top {min(TOP_N, len(classes))})",
        fontsize=13, weight="bold", pad=20,
    )

    cell_text = [[str(rank), name, str(count)]
                 for rank, (name, count) in enumerate(classes, start=1)]

    table = ax.table(
        cellText=cell_text,
        colLabels=["Rank", "Class (ISIC Rev. 4 division, full name)", "Count"],
        colWidths=[0.07, 0.80, 0.10],
        cellLoc="left",
        loc="upper center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.35)

    for (row, _col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#4472C4")
            cell.set_text_props(color="white", weight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#EDF1F8")

    pdf.savefig(fig)
    plt.close(fig)


def _comments_page(pdf: PdfPages, repo_id: int, entry: dict):
    fig, ax = plt.subplots(figsize=(11.7, 8.3))
    ax.axis("off")
    ax.set_title(f"Repository {repo_id} \u2013 comments on the findings",
                 fontsize=13, weight="bold", pad=20)

    lines = []

    n = entry["n_projects"]
    lines.append(f"\u2022 Total projects harvested from this repository: {n}")

    lines.append("\u2022 Project types found:")
    for ptype, count in entry["types"].most_common():
        pct = 100.0 * count / n if n else 0.0
        lines.append(f"      {ptype}: {count} ({pct:.1f} %)")

    classified = sum(entry["classes"].values())
    lines.append(f"\u2022 Projects with an ISIC primary class: {classified}")

    if entry["classes"]:
        dominant, dom_count = entry["classes"].most_common(1)[0]
        lines.append(f"\u2022 Dominant class: {dominant} ({dom_count} project(s))")
        n_distinct = len(entry["classes"])
        lines.append(f"\u2022 Number of distinct primary classes: {n_distinct}")
        top3 = entry["classes"].most_common(3)
        top3_share = 100.0 * sum(c for _, c in top3) / classified
        lines.append(f"\u2022 The top three classes cover {top3_share:.1f} % of all "
                     "classified projects, i.e. the topical distribution is "
                     f"{'strongly concentrated' if top3_share > 60 else 'fairly spread out'}.")
        lines.append("\u2022 The classifier is keyword-based over metadata (title, "
                     "description, keywords) and base data (file names and readable "
                     "file content); multi-word taxonomy keywords are weighted higher "
                     "as they are more specific.")
        lines.append("\u2022 Projects without any keyword match remain unclassified; "
                     "their metadata was too sparse or too generic to derive an ISIC "
                     "division reliably.")
    else:
        lines.append("\u2022 No project of this repository matched the ISIC keyword "
                     "lexicon; metadata may be too sparse.")

    ax.text(0.02, 0.92, "\n".join(lines), fontsize=10, va="top",
            family="sans-serif", linespacing=1.7)

    pdf.savefig(fig)
    plt.close(fig)


def _summary_page(pdf: PdfPages, data: dict):
    fig, ax = plt.subplots(figsize=(11.7, 8.3))
    ax.axis("off")
    ax.text(0.5, 0.75, "QDArchive \u2013 Classification Report",
            ha="center", fontsize=22, weight="bold")
    ax.text(0.5, 0.66,
            "Project types and ISIC Rev. 4 topic classification, by repository",
            ha="center", fontsize=12)

    total_projects = sum(e["n_projects"] for e in data.values())
    total_classified = sum(sum(e["classes"].values()) for e in data.values())
    all_types = Counter()
    for e in data.values():
        all_types.update(e["types"])

    lines = [
        f"Repositories covered: {len(data)}",
        f"Total projects: {total_projects}",
        f"Projects with ISIC primary class: {total_classified}",
        "",
        "Project types (all repositories):",
    ]
    lines += [f"    {t}: {c}" for t, c in all_types.most_common()]

    ax.text(0.5, 0.52, "\n".join(lines), ha="center", va="top", fontsize=11,
            linespacing=1.8)
    pdf.savefig(fig)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def generate_report(output_path=REPORT_PDF_PATH):
    data = load_report_data()

    if not data:
        print("No data in database - nothing to report.")
        return None

    with PdfPages(output_path) as pdf:
        _summary_page(pdf, data)
        for repo_id in sorted(data):
            entry = data[repo_id]
            _histogram_page(pdf, repo_id, entry)
            _table_page(pdf, repo_id, entry)
            _comments_page(pdf, repo_id, entry)

    print(f"PDF report written to: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_report()
