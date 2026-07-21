"""Ayurvani — /api/gloss

Standalone word-by-word gloss endpoint for Sanskrit shlokas.
Accepts a `text` query param (Devanagari / IAST / HK / colloquial Roman) and an
optional `treatise` hint ('charaka' | 'sushruta' | 'ashtanga_hridaya' | 'auto').

Returns JSON:
{
  "words": [
    {
      "devanagari": "आयुः",
      "iast":        "āyuḥ",
      "root":        "i (to go/live)",
      "grammar":     "n. nom. sg.",
      "gloss_en":    "life, lifespan",
      "commentary_note": "Chakrapani: āyuḥ = combination of sharira, indriya, sattva, ātma"
    }, …
  ],
  "treatise_hint": "charaka",
  "model": "gemini-2.5-flash"
}
"""

import os
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler

GEMINI_MODEL = "gemini-2.0-flash"

TREATISE_CONTEXT = {
    "charaka": (
        "The text is from Charaka Samhita. "
        "Use Chakrapani Datta's commentary (Ayurveda Dipika) for word-level interpretations."
    ),
    "sushruta": (
        "The text is from Sushruta Samhita. "
        "Use Dalhana's commentary (Nibandhasangraha) for word-level interpretations."
    ),
    "ashtanga_hridaya": (
        "The text is from Ashtanga Hridayam. "
        "Use Arunadatta's (Sarvangasundara) and Hemadri's (Ayurvedarasayana) commentaries."
    ),
    "auto": (
        "The text is from one of the classical Ayurvedic samhitas (Charaka, Sushruta, or Ashtanga Hridaya). "
        "Apply whichever commentary tradition is most relevant."
    ),
}


def call_gemini_gloss(text: str, treatise: str = "auto") -> list:
    """Call Gemini and return the word_meanings list, or [] on failure."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return []

    treatise_ctx = TREATISE_CONTEXT.get(treatise.lower(), TREATISE_CONTEXT["auto"])

    prompt = (
        "You are an expert traditional Sanskrit scholar specializing in Ayurvedic literature "
        "and classical Vyakarana (Paninian) grammar.\n"
        f"{treatise_ctx}\n\n"
        "For the Sanskrit text below, provide a word-by-word gloss. "
        "First mentally apply sandhi-viccheda to separate the compounds, then gloss each individual word. "
        "For every word provide:\n"
        "  - devanagari: the word in Devanagari script\n"
        "  - iast: IAST transliteration\n"
        "  - root: the dhatu or pratipadika with a brief meaning "
        "(e.g. 'āyu (to live)', 'rāj (to shine)', 'dravya (substance)')\n"
        "  - grammar: grammatical analysis in concise notation "
        "(e.g. 'n. nom. sg.', 'v. 3sg. pres. act.', 'ppp. nom. sg. m.')\n"
        "  - gloss_en: concise English meaning in this specific context\n"
        "  - commentary_note: if this word has a specific technical interpretation "
        "in the relevant commentary tradition, state it in one sentence. Otherwise return empty string.\n\n"
        f"Sanskrit text:\n{text}"
    )

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "words": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "devanagari":      {"type": "STRING"},
                                "iast":            {"type": "STRING"},
                                "root":            {"type": "STRING"},
                                "grammar":         {"type": "STRING"},
                                "gloss_en":        {"type": "STRING"},
                                "commentary_note": {"type": "STRING"},
                            },
                            "required": ["devanagari", "iast", "gloss_en"],
                        },
                    }
                },
                "required": ["words"],
            },
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            raw = res["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(raw).get("words", [])
    except Exception as e:
        print(f"[gloss] Gemini call failed: {e}")
        return []


class handler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        BaseHTTPRequestHandler.end_headers(self)

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)

            text     = params.get("text",     [""])[0].strip()
            treatise = params.get("treatise", ["auto"])[0].strip().lower()

            if not text:
                self._error(400, "text parameter is required")
                return

            words = call_gemini_gloss(text, treatise)

            body = json.dumps(
                {
                    "words":         words,
                    "treatise_hint": treatise,
                    "model":         GEMINI_MODEL,
                },
                ensure_ascii=False,
            ).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        except Exception as e:
            self._error(500, str(e))

    def _error(self, code: int, msg: str):
        body = json.dumps({"error": msg}).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
