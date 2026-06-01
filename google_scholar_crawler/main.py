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

# Papers to track individually by title (matched case-insensitively).
#  Key = short label for output filename, Value = paper title to match.
TRACKED_PAPERS = {
    # Top-cited papers on the current profile.
    # Edit these to track specific papers on your Google Scholar profile.
    # Key = short filename label, Value = exact paper title (case-insensitive match).
    "dl_rs_fusion": "Deep learning in remote sensing image fusion: Methods, protocols, data, and future prospects",
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
    session.trust_env = False
    # Respect system proxy if set (common in CN)
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if http_proxy or https_proxy:
        proxies = {}
        if http_proxy:
            proxies["http"] = http_proxy
        if https_proxy:
            proxies["https"] = https_proxy
        session.proxies.update(proxies)
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


# ── Fetch & parse ───────────────────────────────────────────────────────
def fetch_google_scholar_data() -> Optional[dict]:
    """Fetch author profile from Google Scholar."""
    url = f"https://scholar.google.com/citations?user={USER_ID}&hl=en&pagesize=100"
    session = _build_session()

    for attempt in range(1, 4):
        try:
            resp = session.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  [Attempt {attempt}/3] {e}")
            if attempt < 3:
                time.sleep(3)
            continue

        if "sorry" in resp.text[:3000].lower():
            print(f"  [Attempt {attempt}/3] Google Scholar block page detected.")
            if attempt < 3:
                time.sleep(5)
            continue

        break
    else:
        return None  # All attempts failed

    soup = BeautifulSoup(resp.text, "html.parser")

    # ── Name ──
    name_el = soup.find("div", id="gsc_prf_in")
    name = name_el.text.strip() if name_el else "Unknown"

    # ── Stats ──
    stats_tds = soup.find_all("td", class_="gsc_rsb_std")
    citedby = int(stats_tds[0].text) if len(stats_tds) > 0 else 0
    citedby5y = int(stats_tds[1].text) if len(stats_tds) > 1 else 0
    hindex = int(stats_tds[2].text) if len(stats_tds) > 2 else 0
    hindex5y = int(stats_tds[3].text) if len(stats_tds) > 3 else 0
    i10index = int(stats_tds[4].text) if len(stats_tds) > 4 else 0
    i10index5y = int(stats_tds[5].text) if len(stats_tds) > 5 else 0

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
