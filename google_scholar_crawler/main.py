"""
Google Scholar citation crawler
Fetches profile and per-publication citation data from Google Scholar.
"""
import json
import os
import re
import sys
import time
from datetime import datetime
from typing import Optional

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: Missing dependencies. Run: pip install requests beautifulsoup4")
    sys.exit(1)

# ── Config ──────────────────────────────────────────────────────────────
USER_ID = "g5xlNmkAAAAJ"
RESULTS_DIR = "results"
SCHOLAR_HOSTS = (
    "scholar.google.com",
    "scholar.google.com.hk",
    "scholar.google.co.uk",
)

# Papers to track individually by title (matched case-insensitively).
#  Key = short label for output filename, Value = paper title to match.
TRACKED_PAPERS = {
    # Top-cited papers on the current profile.
    # Edit these to track specific papers on your Google Scholar profile.
    # Key = short filename label, Value = exact paper title (case-insensitive match).
    "dl_rs_fusion": "Deep learning in remote sensing image fusion: Methods, protocols, data, and future perspectives",
    "ctdf": "A coupled tensor double-factor method for hyperspectral and multispectral image fusion",
    "vp": "Variational pansharpening based on coefficient estimation with nonlocal regression",
    "hs_diffusion": "Hyperspectral pansharpening via diffusion models with iteratively zero-shot guidance",
    "ucl": "Unsupervised coefficient learning framework for variational pansharpening",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://scholar.google.com/",
}

TIMEOUT = 20


# ── HTTP session ────────────────────────────────────────────────────────
def _build_session() -> requests.Session:
    session = requests.Session()
    # Use standard environment or operating-system proxy settings when present.
    # The GitHub workflow explicitly clears HTTP(S)_PROXY for its direct access.
    session.trust_env = True
    return session


# ── HTML parsers ────────────────────────────────────────────────────────
def _extract_author_pub_id(row_tag) -> Optional[str]:
    link = row_tag.find("a", class_="gsc_a_at")
    if link and link.get("href"):
        m = re.search(r"citation_for_view=([\w:-]+)", link["href"])
        return m.group(1) if m else None
    return None


def _extract_title(row_tag) -> Optional[str]:
    link = row_tag.find("a", class_="gsc_a_at")
    return link.text.strip() if link else None


def _extract_citation_count(row_tag) -> int:
    link = row_tag.find("a", class_="gsc_a_ac")
    if link:
        txt = link.text.strip()
        if txt and txt != "\u2014":
            try:
                return int(txt)
            except ValueError:
                pass
    return 0


def _parse_count(value: str) -> Optional[int]:
    """Parse a Scholar count while tolerating thousands separators."""
    digits = re.sub(r"[^0-9]", "", value or "")
    return int(digits) if digits else None


def _extract_profile_summary(soup) -> tuple[Optional[str], Optional[int]]:
    """Extract the profile name and total citations from a real profile page."""
    name_el = soup.find("div", id="gsc_prf_in")
    name = name_el.get_text(strip=True) if name_el else None

    if not name:
        title_meta = soup.find("meta", property="og:title")
        if title_meta:
            name = title_meta.get("content", "").strip() or None

    stats_tds = soup.find_all("td", class_="gsc_rsb_std")
    citedby = _parse_count(stats_tds[0].get_text()) if stats_tds else None

    # Scholar also publishes the total in the profile description. This is a
    # useful fallback when the visible statistics table is rendered differently.
    if citedby is None:
        description = soup.find("meta", attrs={"name": "description"})
        description_text = description.get("content", "") if description else ""
        match = re.search(r"Cited by\s+([0-9,]+)", description_text, re.IGNORECASE)
        citedby = _parse_count(match.group(1)) if match else None

    return name, citedby


# ── Fetch & parse ───────────────────────────────────────────────────────
def fetch_google_scholar_data() -> Optional[dict]:
    """Fetch author profile from Google Scholar."""
    session = _build_session()

    soup = None
    name = None
    citedby = None

    for attempt, host in enumerate(SCHOLAR_HOSTS, start=1):
        url = (
            f"https://{host}/citations?view_op=list_works"
            f"&user={USER_ID}&hl=en&pagesize=100"
        )
        try:
            resp = session.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  [Attempt {attempt}/{len(SCHOLAR_HOSTS)}] {host}: {e}")
            if attempt < len(SCHOLAR_HOSTS):
                time.sleep(2)
            continue

        candidate_soup = BeautifulSoup(resp.text, "html.parser")
        candidate_name, candidate_citedby = _extract_profile_summary(candidate_soup)

        # A challenge/consent page can return HTTP 200. Do not silently convert
        # a missing profile into "Unknown" with zero citations.
        if not candidate_name or candidate_citedby is None or candidate_citedby <= 0:
            page_title = candidate_soup.title.get_text(" ", strip=True) if candidate_soup.title else "no title"
            print(
                f"  [Attempt {attempt}/{len(SCHOLAR_HOSTS)}] {host}: "
                f"invalid profile response ({page_title!r}, {len(resp.text)} bytes)."
            )
            if attempt < len(SCHOLAR_HOSTS):
                time.sleep(2)
            continue

        soup = candidate_soup
        name = candidate_name
        citedby = candidate_citedby
        break
    else:
        return None

    # ── Stats ──
    stats_tds = soup.find_all("td", class_="gsc_rsb_std")
    stat_values = [_parse_count(td.get_text()) or 0 for td in stats_tds]
    citedby5y = stat_values[1] if len(stat_values) > 1 else 0
    hindex = stat_values[2] if len(stat_values) > 2 else 0
    hindex5y = stat_values[3] if len(stat_values) > 3 else 0
    i10index = stat_values[4] if len(stat_values) > 4 else 0
    i10index5y = stat_values[5] if len(stat_values) > 5 else 0

    # ── Citations per year ──
    years = [int(y.text) for y in soup.find_all("span", class_="gsc_g_t")]
    cites = [int(c.text) for c in soup.find_all("span", class_="gsc_g_al")]
    cites_per_year = dict(zip(years, cites))

    # ── Publications ──
    publications = {}
    for row in soup.find_all("tr", class_="gsc_a_tr"):
        pub_id = _extract_author_pub_id(row)
        title = _extract_title(row)
        num_citations = _extract_citation_count(row)

        if not pub_id and not title:
            continue

        key = pub_id or title or str(len(publications))
        publications[key] = {
            "author_pub_id": pub_id or "",
            "num_citations": num_citations,
            "title": title or "",
        }

    return {
        "scholar_id": USER_ID,
        "name": name,
        "citedby": citedby,
        "citedby5y": citedby5y,
        "hindex": hindex,
        "hindex5y": hindex5y,
        "i10index": i10index,
        "i10index5y": i10index5y,
        "cites_per_year": cites_per_year,
        "publications": publications,
        "updated": str(datetime.now()),
    }


# ── Output ──────────────────────────────────────────────────────────────
def find_paper_citations(author: dict, title: str) -> int:
    target = title.lower().strip()
    for pub in author.get("publications", {}).values():
        if pub.get("title", "").lower().strip() == target:
            return pub.get("num_citations", 0)
    return 0


def write_json(path: str, data) -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    full_path = os.path.join(RESULTS_DIR, path)
    with open(full_path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  {full_path}")


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
          f"Fetching Google Scholar data for user {USER_ID} ...")

    author = fetch_google_scholar_data()

    if author is None:
        print("\nERROR: Failed to fetch data from Google Scholar after all retries.")
        print("       The workflow will keep the previous data on the google-scholar-stats branch.")
        sys.exit(1)

    # Clean old result files
    import glob
    for f in glob.glob(os.path.join(RESULTS_DIR, "gs_data*.json")):
        os.remove(f)

    print(f"\n  Name:              {author['name']}")
    print(f"  Total citations:   {author['citedby']}")
    print(f"  h-index:           {author['hindex']}")
    print(f"  Publications:      {len(author['publications'])}")

    # ── Full data ──
    write_json("gs_data.json", author)

    # ── Total citation badge ──
    write_json("gs_data_shieldsio.json", {
        "schemaVersion": 1,
        "label": "citations",
        "message": str(author["citedby"]),
    })

    # ── Per-paper badges ──
    for label, title in TRACKED_PAPERS.items():
        count = find_paper_citations(author, title)
        write_json(f"gs_data_shieldsio_{label}.json", {
            "schemaVersion": 1,
            "label": "citations",
            "message": str(count),
        })
        status = f"{count} citations" if count > 0 else "not found"
        print(f"    {label}: {title[:45]}... → {status}")

    print(f"\n✅ Done. All files saved to {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
