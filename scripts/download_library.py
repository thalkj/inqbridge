"""Download English Inquisit 7 scripts from the Millisecond Test Library.

Scrapes https://www.millisecond.com/library for all task pages,
finds English Inquisit 7 download links (.iqzip), and saves them
into scripts/library/.
"""
import re
import time
import urllib.request
import urllib.error
from html.parser import HTMLParser
from pathlib import Path

LIBRARY_URL = "https://www.millisecond.com/library"
OUTPUT_DIR = Path(__file__).parent / "library"
DELAY = 0.5  # seconds between requests, be polite


class LinkParser(HTMLParser):
    """Extract <a href=...> links from HTML."""
    def __init__(self):
        super().__init__()
        self.links = []
        self._in_a = False
        self._href = ""
        self._text = ""

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._in_a = True
            self._text = ""
            for name, val in attrs:
                if name == "href":
                    self._href = val or ""

    def handle_data(self, data):
        if self._in_a:
            self._text += data

    def handle_endtag(self, tag):
        if tag == "a" and self._in_a:
            self.links.append((self._href, self._text.strip()))
            self._in_a = False
            self._href = ""
            self._text = ""


def fetch(url: str) -> str:
    """Fetch URL and return text content."""
    req = urllib.request.Request(url, headers={"User-Agent": "InqBridge/0.1 (research)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def download_file(url: str, dest: Path) -> bool:
    """Download a binary file. Returns True on success."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "InqBridge/0.1 (research)"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.read())
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        print(f"  FAILED: {e}")
        return False


def get_task_urls() -> list[tuple[str, str]]:
    """Get all task page URLs from the main library page."""
    html = fetch(LIBRARY_URL)
    parser = LinkParser()
    parser.feed(html)

    tasks = []
    seen = set()
    for href, text in parser.links:
        if not href or not text:
            continue
        # Task links look like /library/something or full URL
        if "/library/" in href and href != "/library/" and href != "/library":
            full = href if href.startswith("http") else f"https://www.millisecond.com{href}"
            # Skip category/language pages
            if "/categories" in full or "/languages" in full:
                continue
            if full not in seen:
                seen.add(full)
                tasks.append((full, text))
    return tasks


def get_english_iq7_download(task_url: str) -> str | None:
    """Visit a task page and find the English Inquisit 7 .iqzip download URL."""
    try:
        html = fetch(task_url)
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"  Could not fetch {task_url}: {e}")
        return None

    parser = LinkParser()
    parser.feed(html)

    # Find all .iqzip links (Inquisit 7 format)
    iq7_links = [(href, text) for href, text in parser.links
                 if href and href.endswith(".iqzip")]

    if not iq7_links:
        return None

    # Prefer English: exclude links with language suffixes
    # Language-specific ones typically have _german, _french, _bulgarian etc. in the filename
    lang_suffixes = [
        "_bulgarian", "_german", "_italian", "_french", "_spanish",
        "_portuguese", "_dutch", "_polish", "_czech", "_turkish",
        "_chinese", "_japanese", "_korean", "_arabic", "_hebrew",
        "_russian", "_swedish", "_norwegian", "_danish", "_finnish",
        "_hungarian", "_romanian", "_greek", "_serbian", "_croatian",
        "_slovenian", "_slovak", "_hindi", "_urdu", "_persian",
        "_thai", "_vietnamese", "_indonesian", "_malay",
    ]

    for href, text in iq7_links:
        filename_lower = href.lower().rsplit("/", 1)[-1]
        if not any(s in filename_lower for s in lang_suffixes):
            full = href if href.startswith("http") else f"https://www.millisecond.com{href}"
            return full

    # Fallback: return first one
    href = iq7_links[0][0]
    return href if href.startswith("http") else f"https://www.millisecond.com{href}"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching task list from library...")
    tasks = get_task_urls()
    print(f"Found {len(tasks)} tasks.\n")

    downloaded = 0
    skipped = 0
    failed = 0
    no_iq7 = 0

    for i, (url, name) in enumerate(tasks, 1):
        print(f"[{i}/{len(tasks)}] {name}")

        # Find download link
        dl_url = get_english_iq7_download(url)
        if not dl_url:
            print("  No Inquisit 7 English download found, skipping.")
            no_iq7 += 1
            time.sleep(DELAY)
            continue

        # Determine filename
        filename = dl_url.rsplit("/", 1)[-1]
        dest = OUTPUT_DIR / filename

        if dest.exists():
            print(f"  Already exists: {filename}")
            skipped += 1
            time.sleep(DELAY)
            continue

        print(f"  Downloading: {filename}")
        if download_file(dl_url, dest):
            downloaded += 1
        else:
            failed += 1

        time.sleep(DELAY)

    print(f"\nDone! Downloaded: {downloaded}, Skipped: {skipped}, Failed: {failed}, No IQ7: {no_iq7}")


if __name__ == "__main__":
    main()
