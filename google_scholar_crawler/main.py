"""
Google Scholar citation crawler
Fetches profile and per-publication citation data from Google Scholar.
Falls back to cached data if the request is blocked.
"""
import json
import os
import re
import sys
from datetime import datetime

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: Missing dependencies. Run: pip install requests beautifulsoup4")
    sys.exit(1)

# ── Config ──────────────────────────────────────────────────────────────
USER_ID = "g5xlNmkAAAAJ"
RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

# Map of author_pub_id -> paper title (for display/verification)
PAPERS = {
    "Uf9GqRsAAAAJ:bEWYMUwI8FkC": "Meta-Transfer Learning for Few-Shot learning",
    "Uf9GqRsAAAAJ:k_IJM867U9cC": "Mnemonics Training: Multi-Class Incremental Learning without Forgetting",
    "Uf9GqRsAAAAJ:u_35RYKgDlwC": "AANets: Adaptive Aggregation Networks for Few-Shot Learning",
    "Uf9GqRsAAAAJ:vV6vV6tmYwMC": "E3BM: Episodic-Evolving Error-Bounded Memory for Class-Incremental Learning",
    "Uf9GqRsAAAAJ:TFP_iSt0sucC": "Long Short-Term Transformer for Online Action Detection",
}

# Google Scholar might block if the author_pub_id prefix differs from USER_ID.
# We'll try to match papers by title for per-paper citations in case IDs change.
PAPERS_BY_TITLE = {v.lower(): k for k, v in PAPERS.items()}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://scholar.google.com/",
    "DNT": "1",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

TIMEOUT = 30
MAX_RETRIES = 3


# ── Helpers ─────────────────────────────────────────────────────────────
def _build_session() -> requests.Session:
    session = requests.Session()
    # Don't pick up system proxy settings automatically; we'll handle proxies explicitly
    session.trust_env = False
    adapter = requests.adapters.HTTPAdapter(max_retries=MAX_RETRIES)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _extract_author_pub_id(row_tag) -> str | None:
    """Extract author_pub_id from a publication table row."""
    link = row_tag.find("a", class_="gsc_a_at")
    if link and link.get("href"):
        m = re.search(r"citation_for_view=([\w:-]+)", link["href"])
        if m:
            return m.group(1)
    return None


def _extract_title(row_tag) -> str | None:
    link = row_tag.find("a", class_="gsc_a_at")
    if link:
        return link.text.strip()
    return None


def _extract_citation_count(row_tag) -> int:
    citedby = row_tag.find("td", class_="gsc_a_c")
    if citedby:
        link = citedby.find("a", class_="gsc_a_ac")
        if link:
            txt = link.text.strip()
            if txt and txt != "—":
                try:
                    return int(txt)
                except ValueError:
                    pass
    return 0


def _extract_year(row_tag) -> str | None:
    year_td = row_tag.find("td", class_="gsc_a_y")
    if year_td:
        span = year_td.find("span")
        if span:
            return span.text.strip()
    return None


# ── Main logic ──────────────────────────────────────────────────────────
def fetch_google_scholar_data() -> dict | None:
    """Fetch author profile data from Google Scholar. Returns None on failure."""
    url = f"https://scholar.google.com/citations?user={USER_ID}&hl=en&pagesize=100"
    session = _build_session()

    # Respect system proxy if set (e.g. http://127.0.0.1:7890 for users in CN)
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    proxies = {}
    if http_proxy:
        proxies["http"] = http_proxy
    if https_proxy:
        proxies["https"] = https_proxy

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(
                url, headers=HEADERS, proxies=proxies if proxies else None,
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[Attempt {attempt}/{MAX_RETRIES}] Request failed: {e}")
            if attempt < MAX_RETRIES:
                import time
                time.sleep(3)
            continue

        html = resp.text

        # Check for CAPTCHA / blocking
        if "sorry" in html[:3000].lower():
            print(f"[Attempt {attempt}/{MAX_RETRIES}] Google Scholar CAPTCHA/block page detected.")
            if attempt < MAX_RETRIES:
                import time
                time.sleep(5)
            continue

        soup = BeautifulSoup(html, "html.parser")

        # ── Author basics ──
        name_el = soup.find("div", id="gsc_prf_in")
        name = name_el.text.strip() if name_el else "Unknown"

        # ── Stats indices ──
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
            pub_year = _extract_year(row)

            if not pub_id and not title:
                continue

            pub_data = {
                "author_pub_id": pub_id or "",
                "num_citations": num_citations,
                "title": title or "",
                "year": pub_year or "",
            }
            key = pub_id or title or str(len(publications))
            publications[key] = pub_data

        author_data = {
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
        return author_data

    return None


def generate_shieldio(author: dict, pub_key: str | None = None) -> dict:
    """Generate a shields.io-compatible JSON object."""
    if pub_key is None:
        count = author.get("citedby", 0)
    else:
        count = 0
        pub = author.get("publications", {}).get(pub_key)
        if pub:
            count = pub.get("num_citations", 0)
        else:
            # Try matching by title
            title_lower = PAPERS.get(pub_key, "").lower()
            for p in author.get("publications", {}).values():
                if p.get("title", "").lower() == title_lower:
                    count = p.get("num_citations", 0)
                    break
    return {
        "schemaVersion": 1,
        "label": "citations",
        "message": str(count),
    }


def write_json(path: str, data) -> None:
    full_path = os.path.join(RESULTS_DIR, path)
    with open(full_path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {full_path}")


# ── Entry point ─────────────────────────────────────────────────────────
def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Fetching Google Scholar data for user {USER_ID}...")
    author = fetch_google_scholar_data()

    if author is None:
        print("ERROR: Failed to fetch data from Google Scholar after all retries.")
        print("       The workflow will keep the previous data on the google-scholar-stats branch.")
        sys.exit(1)

    print(f"  Name: {author['name']}")
    print(f"  Total citations: {author['citedby']}")
    print(f"  h-index: {author['hindex']}")
    print(f"  Publications found: {len(author['publications'])}")

    # ── Write full data ──
    write_json("gs_data.json", author)

    # ── Write shields.io JSON files ──
    write_json("gs_data_shieldsio.json", generate_shieldio(author))

    for pub_key in PAPERS:
        shield = generate_shieldio(author, pub_key)
        label = pub_key.split(":")[-1] if ":" in pub_key else pub_key
        filename = f"gs_data_shieldsio_{label}.json"
        # Also try to match paper-specific filenames used by existing code
        paper_title_lower = PAPERS[pub_key].lower()
        short_names = {
            "meta-transfer learning for few-shot learning": "mtl",
            "mnemonics training: multi-class incremental learning without forgetting": "mnemonics",
            "aanets: adaptive aggregation networks for few-shot learning": "aanets",
            "e3bm: episodic-evolving error-bounded memory for class-incremental learning": "e3bm",
            "long short-term transformer for online action detection": "lst",
        }
        short_name = short_names.get(paper_title_lower, label)
        write_json(f"gs_data_shieldsio_{short_name}.json", shield)

    print(f"\n✓ Done. All files saved to {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
