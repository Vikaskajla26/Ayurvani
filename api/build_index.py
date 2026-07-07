"""
Builds a searchable index of every verse in the Charaka Samhita, sourced from
carakasamhitaonline.com, so that a pasted shloka can be matched against the
whole text without hitting the live wiki on every search request.

WHY THIS IS A SEPARATE OFFLINE SCRIPT (not something the live API does per-request):
Fetching and parsing all ~120 chapters on every visitor search would be slow,
unreliable (depends on the source wiki being up), and hammers a third-party
site with every user's query. Instead, this script is run ONCE (and re-run
whenever you want to refresh the data), producing a static JSON file that
match_shloka.py loads and searches locally at request time.

USAGE:
    python3 api/build_index.py
    (writes api/index_data/charaka_verse_index.json)

This must be run from an environment with real network access to
carakasamhitaonline.com -- e.g. your own machine, or a CI job. It reuses the
already-fixed fetch/parsing machinery in fetch_verse.py (HTTPS + multi-host
fallback), so any future fix there automatically benefits this script too.
"""
"""
Builds a searchable index of every verse in the Charaka Samhita, sourced from
carakasamhitaonline.com, so that a pasted shloka can be matched against the
whole text without hitting the live wiki on every search request.

WHY THIS IS A SEPARATE OFFLINE SCRIPT (not something the live API does per-request):
Fetching and parsing all ~120 chapters on every visitor search would be slow,
unreliable (depends on the source wiki being up), and hammers a third-party
site with every user's query. Instead, this script is run ONCE (and re-run
whenever you want to refresh the data), producing a static JSON file that
match_shloka.py loads and searches locally at request time.

USAGE:
    python3 api/build_index.py
    (writes api/index_data/charaka_verse_index.json)

RESUMABLE: if index_data/charaka_verse_index.json already exists, this script
loads it first and SKIPS any (sthana, chapter) already covered -- so re-running
after a partial run (e.g. some chapters timed out) only retries what's missing,
instead of re-fetching all 120 chapters from scratch. To force a full rebuild
from zero, delete the existing JSON file first or pass --force.

This must be run from an environment with real network access to
carakasamhitaonline.com -- e.g. your own machine, or a CI job. It reuses the
already-fixed fetch/parsing machinery in fetch_verse.py (HTTPS + multi-host
fallback), so any future fix there automatically benefits this script too.
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetch_verse import (
    CHARAKA_PAGE_TITLES,
    _resolve_page_title,
    _fetch_wiki_page,
    _extract_verse,
    _normalize_verse_separators,
    _from_devanagari_num,
)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index_data")
OUT_FILE = os.path.join(OUT_DIR, "charaka_verse_index.json")

MAX_RETRIES = 3           # per chapter, for transient network failures
RETRY_DELAY_SECONDS = 5   # wait between retries


def _discover_verse_numbers(content):
    """Scan a chapter's raw wikitext for every distinct verse number referenced
    by a '||N||' (or Devanagari-digit) marker, so we know which verse numbers
    to actually try extracting -- rather than guessing an upper bound."""
    normalized = _normalize_verse_separators(content)
    found = set()
    for m in re.finditer(r'\|\|\s*([0-9०-९]+)\s*\|\|', normalized):
        raw = m.group(1)
        raw_ascii = _from_devanagari_num(raw)
        if raw_ascii.isdigit():
            n = int(raw_ascii)
            if 0 < n <= 300:  # sanity bound -- no CS chapter has anywhere near this many verses
                found.add(n)
    return sorted(found)


def _fetch_with_retries(page_title, chapter_label):
    """Wraps _fetch_wiki_page with retries -- longer/heavier chapters (mostly in
    Chikitsasthana) are more prone to transient timeouts on a single attempt."""
    last_content = None
    for attempt in range(1, MAX_RETRIES + 1):
        content = _fetch_wiki_page(page_title)
        if content:
            return content
        if attempt < MAX_RETRIES:
            print(f"    retry {attempt}/{MAX_RETRIES} for {chapter_label} in {RETRY_DELAY_SECONDS}s...")
            time.sleep(RETRY_DELAY_SECONDS)
    return last_content


def build_index(force=False):
    existing_entries = []
    covered = set()

    if not force and os.path.exists(OUT_FILE):
        try:
            with open(OUT_FILE, "r", encoding="utf-8") as f:
                existing_entries = json.load(f)
            covered = set((e["sthana"], e["chapter"]) for e in existing_entries)
            print(f"Resuming: found existing index with {len(existing_entries)} verses "
                  f"across {len(covered)} chapters already covered. Skipping those.\n")
        except Exception as e:
            print(f"Could not read existing index ({e}); starting fresh.\n")
            existing_entries = []
            covered = set()

    new_entries = []
    total_chapters = sum(len(v) for v in CHARAKA_PAGE_TITLES.values())
    done = 0
    newly_covered = 0

    for sthana, chapters in CHARAKA_PAGE_TITLES.items():
        for chapter_num, guessed_title in chapters.items():
            done += 1
            if (sthana, chapter_num) in covered:
                print(f"[{done}/{total_chapters}] SKIP {sthana} ch.{chapter_num} -- already indexed")
                continue

            label = f"{sthana} ch.{chapter_num}"
            page_title = _resolve_page_title(sthana, chapter_num, guessed_title)
            if not page_title:
                print(f"[{done}/{total_chapters}] MISS {label} -- could not resolve page title")
                continue

            content = _fetch_with_retries(page_title, label)
            if not content:
                print(f"[{done}/{total_chapters}] MISS {label} ({page_title}) -- fetch failed after {MAX_RETRIES} attempts")
                continue

            verse_nums = _discover_verse_numbers(content)
            chapter_verse_count = 0
            for vn in verse_nums:
                sanskrit, translation = _extract_verse(content, vn)
                if not sanskrit:
                    continue
                new_entries.append({
                    "sthana": sthana,
                    "chapter": chapter_num,
                    "chapter_title": page_title,
                    "verse": vn,
                    "sanskrit": sanskrit,
                    "translation": (translation or "")[:200],  # short snippet only; full text is fetched live on match
                })
                chapter_verse_count += 1

            print(f"[{done}/{total_chapters}] OK {label} ({page_title}) -- {chapter_verse_count} verses")
            newly_covered += 1
            time.sleep(0.3)  # be polite to the source wiki

    all_entries = existing_entries + new_entries
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False)

    total_covered_chapters = len(covered) + newly_covered
    print(f"\nDone. {newly_covered} new chapters fetched this run.")
    print(f"Total: {len(all_entries)} verses across {total_covered_chapters}/{total_chapters} chapters.")
    print(f"Written to: {OUT_FILE}")
    if total_covered_chapters < total_chapters:
        print(f"{total_chapters - total_covered_chapters} chapters still missing -- just run this script again to retry them.")
    print("Commit this file to your repo so match_shloka.py can use it in production.")


if __name__ == "__main__":
    force_rebuild = "--force" in sys.argv
    build_index(force=force_rebuild)
