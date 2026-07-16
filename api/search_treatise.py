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


INDEX_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index_data", "charaka_verse_index.json")
_INDEX = None


def _load_index():
    global _INDEX
    if _INDEX is not None:
        return _INDEX
    if not os.path.exists(INDEX_FILE):
        _INDEX = []
        return _INDEX
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            _INDEX = json.load(f)
    except Exception as e:
        print(f"[search_treatise] Error loading index: {e}")
        _INDEX = []
    return _INDEX


def local_search_treatise(query, limit=8):
    index = _load_index()
    if not index:
        return []
        
    query_lower = query.lower()
    results = []
    
    for entry in index:
        sanskrit = entry.get("sanskrit", "")
        translation = entry.get("translation", "")
        sthana = entry.get("sthana", "")
        chapter = entry.get("chapter", 1)
        chapter_title = entry.get("chapter_title", "")
        verse = entry.get("verse", 1)
        
        in_sanskrit = query in sanskrit
        in_translation = query_lower in translation.lower()
        in_title = query_lower in chapter_title.lower()
        
        if in_sanskrit or in_translation or in_title:
            snippet = ""
            if in_translation:
                idx = translation.lower().find(query_lower)
                start = max(0, idx - 40)
                end = min(len(translation), idx + len(query) + 40)
                snippet = translation[start:end]
                if start > 0: snippet = "..." + snippet
                if end < len(translation): snippet = snippet + "..."
            elif in_sanskrit:
                idx = sanskrit.find(query)
                start = max(0, idx - 30)
                end = min(len(sanskrit), idx + len(query) + 30)
                snippet = sanskrit[start:end]
                if start > 0: snippet = "..." + snippet
                if end < len(sanskrit): snippet = snippet + "..."
            else:
                snippet = (sanskrit[:60] + "...") if len(sanskrit) > 60 else sanskrit
                
            score = 0
            if query_lower == translation.lower() or query == sanskrit:
                score = 100
            elif translation.lower().startswith(query_lower) or sanskrit.startswith(query):
                score = 80
            elif in_translation:
                score = 50
            else:
                score = 30
                
            title = f"{chapter_title} - Verse {verse}"
            results.append((score, {
                "title": title,
                "snippet": snippet,
                "sthana": sthana,
                "chapter": chapter,
                "verse": verse
            }))
            
    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:limit]]


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

    # Fallback to local index search if online search fails
    print(f"[search_treatise] Online search failed. Falling back to local offline search for '{query}'...")
    try:
        local_results = local_search_treatise(query, limit)
        if local_results:
            return {"results": local_results}
    except Exception as local_e:
        print(f"[search_treatise] Local search failed: {local_e}")

    return {"error": f"Could not reach the search service ({last_error}).", "results": []}


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
