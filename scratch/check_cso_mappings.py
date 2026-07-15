import sys
import os
import json
import urllib.request
import urllib.parse

sys.path.append(os.path.abspath('api'))
from fetch_verse import CHARAKA_PAGE_TITLES, CSO_API

print("Checking fetch_verse.py mappings against MediaWiki API...")
broken_chapters = []

for sthana, chapters in CHARAKA_PAGE_TITLES.items():
    print(f"Checking {sthana}...")
    for ch_num, page_title in chapters.items():
        safe_title = urllib.parse.quote(page_title.replace(" ", "_"))
        url = f"{CSO_API}?action=query&titles={safe_title}&format=json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Ayurvani/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for page_id in pages.keys():
                if page_id == "-1":
                    print(f"  [BROKEN] {sthana} Chapter {ch_num}: '{page_title}'")
                    broken_chapters.append((sthana, ch_num, page_title))
        except Exception as e:
            print(f"  [ERROR] {sthana} Chapter {ch_num} ({page_title}): {e}")
            broken_chapters.append((sthana, ch_num, page_title))

print("\n--- Summary of Broken Mappings ---")
print(f"Total Broken: {len(broken_chapters)}")
for sthana, ch_num, title in broken_chapters:
    print(f"  {sthana} Ch {ch_num}: '{title}'")
