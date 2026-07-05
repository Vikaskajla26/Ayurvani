"""
API endpoint: given a pasted shloka (full or partial, Devanagari or IAST/ASCII
transliteration), finds the best-matching verse(s) in the Charaka Samhita by
comparing against the prebuilt index (see build_index.py).

GET /api/match_shloka?text=<pasted shloka>&limit=5

Returns:
{
  "matches": [
    {"sthana": "...", "chapter": 8, "chapter_title": "...", "verse": 5,
     "score": 0.93, "sanskrit": "..."},
    ...
  ]
}
or {"error": "..."} if the index hasn't been built yet.
"""
import os
import json
import re
import difflib
import urllib.parse
from http.server import BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(HERE, "index_data", "charaka_verse_index.json")

_INDEX = None  # lazy-loaded, cached per warm container


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
        print(f"[match_shloka] Error loading index: {e}")
        _INDEX = []
    return _INDEX


# Devanagari combining marks / punctuation that don't carry matching signal
_DEVANAGARI_STRIP = re.compile(r'[\u0964\u0965।॥,;.\-\|\[\]०-९0-9\s]+')
_LATIN_STRIP = re.compile(r"[^a-zA-Z']+")


def _has_devanagari(text):
    return bool(re.search(r'[\u0900-\u097F]', text))


def normalize_for_match(text):
    """Canonicalize text for fuzzy comparison: strips verse-number markers,
    punctuation and whitespace, and lowercases Latin script. Devanagari and
    Latin (IAST/ASCII-phonetic) inputs are normalized separately since they
    aren't directly comparable character-for-character -- the index stores
    Devanagari as the canonical form, so Latin-script input is only usefully
    matched if the index also carries a transliteration (future improvement;
    for now Latin-script queries fall back to a looser token-based score)."""
    text = text.strip()
    if _has_devanagari(text):
        return _DEVANAGARI_STRIP.sub('', text)
    else:
        return _LATIN_STRIP.sub('', text).lower()


def _score(query_norm, candidate_norm):
    if not query_norm or not candidate_norm:
        return 0.0
    return difflib.SequenceMatcher(None, query_norm, candidate_norm).ratio()


def match_shloka(pasted_text, limit=5):
    index = _load_index()
    if not index:
        return {
            "error": "Verse index not built yet. Run `python3 api/build_index.py` "
                     "(with real network access to carakasamhitaonline.com) and "
                     "commit the resulting index_data/charaka_verse_index.json file.",
            "matches": []
        }

    query_norm = normalize_for_match(pasted_text)
    if not query_norm:
        return {"error": "Empty query after normalization.", "matches": []}

    query_is_devanagari = _has_devanagari(pasted_text)

    scored = []
    for entry in index:
        candidate = entry["sanskrit"]
        candidate_norm = normalize_for_match(candidate) if query_is_devanagari else _LATIN_STRIP.sub('', candidate).lower()
        s = _score(query_norm, candidate_norm)
        if s > 0.15:  # cheap prefilter before sorting
            scored.append((s, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:limit]

    return {
        "matches": [
            {
                "sthana": e["sthana"],
                "chapter": e["chapter"],
                "chapter_title": e["chapter_title"],
                "verse": e["verse"],
                "score": round(s, 3),
                "sanskrit": e["sanskrit"],
            }
            for s, e in top
        ]
    }


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
        text = params.get("text", [""])[0].strip()
        limit = params.get("limit", ["5"])[0]
        try:
            limit = max(1, min(int(limit), 20))
        except ValueError:
            limit = 5

        if not text:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "text parameter required"}).encode("utf-8"))
            return

        try:
            result = match_shloka(text, limit)
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
