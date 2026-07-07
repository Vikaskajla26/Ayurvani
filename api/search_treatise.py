"""
API endpoint: full-text search across the Charaka Samhita (carakasamhitaonline.com)
for a keyword (e.g. a disease name like "Jvara"), returning matching chapters
with a short snippet -- so "Search Classical Treatise" actually shows results
on the Ayurvani site instead of silently opening a blind new tab.

GET /api/search_treatise?q=<term>&limit=8
Returns: {"results": [{"title": "...", "snippet": "...", "sthana": "...", "chapter": 8}, ...]}
"""
import os
import sys
import json
import re
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_verse import CSO_API_HOSTS, CHARAKA_PAGE_TITLES

# Build a reverse lookup: wiki page title -> (sthana, chapter number),
# so search results (which only give us a title) can be mapped back to a
# proper Sthana/Chapter reference for the "click to view full verse" flow.
_TITLE_TO_REF = {}
for _sthana, _chapters in CHARAKA_PAGE_TITLES.items():
    for _chnum, _title in _chapters.items():
        _TITLE_TO_REF[_title.strip().lower()] = (_sthana, _chnum)


def _strip_html(text):
    """MediaWiki search snippets come with <span class="searchmatch"> highlighting
    and HTML entities -- strip tags but keep the plain highlighted words."""
    text = re.sub(r'<span class="searchmatch">(.*?)</span>', r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&quot;', '"').replace('&amp;', '&').replace('&#039;', "'")
    return text


def search_treatise(query, limit=8):
    query = query.strip()
    if not query:
        return {"error": "Empty query.", "results": []}

    safe_q = urllib.parse.quote(query)
    last_error = None
    for host in CSO_API_HOSTS:
        url = (f"{host}?action=query&list=search&srsearch={safe_q}"
               f"&format=json&srlimit={limit}&srprop=snippet")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Ayurvani/1.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            raw_results = data.get("query", {}).get("search", [])
            results = []
            for r in raw_results:
                title = r.get("title", "")
                ref = _TITLE_TO_REF.get(title.strip().lower())
                results.append({
                    "title": title,
                    "snippet": _strip_html(r.get("snippet", "")),
                    "sthana": ref[0] if ref else None,
                    "chapter": ref[1] if ref else None,
                })
            return {"results": results}
        except Exception as e:
            last_error = e
            print(f"[search_treatise] Host '{host}' failed for '{query}': {e}")
            continue

    return {"error": f"Could not reach the source wiki ({last_error}).", "results": []}


class handler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        BaseHTTPRequestHandler.end_headers(self)

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        q = params.get("q", [""])[0].strip()
        limit = params.get("limit", ["8"])[0]
        try:
            limit = max(1, min(int(limit), 20))
        except ValueError:
            limit = 8

        if not q:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "q parameter required"}).encode("utf-8"))
            return

        try:
            result = search_treatise(q, limit)
            resp_json = json.dumps(result, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(resp_json)))
            self.end_headers()
            self.wfile.write(resp_json)
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        return
