import re
import json
import urllib
import urllib.parse
import urllib.request
import os
import sys
from http.server import BaseHTTPRequestHandler

# Add vagdhenu/src to path for local meter/scansion
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
vagdhenu_src = os.path.join(base_dir, "vagdhenu", "src")
if vagdhenu_src not in sys.path:
    sys.path.insert(0, vagdhenu_src)

# Try importing vagdhenu libraries, fail gracefully if unavailable
try:
    import chandas_labeler
    import tts_syllabify
    import tts_weight
    import tts_meter
    from prep_text import detect_script
    HAS_LOCAL_SCANSION = True
except ImportError:
    HAS_LOCAL_SCANSION = False
    def detect_script(t):
        return "devanagari"

try:
    from indic_transliteration import sanscript
    HAS_SANSCRIPT = True
except ImportError:
    HAS_SANSCRIPT = False

# ── Self-contained Indic Pre-processing Rules (fallback) ────────────────────────────────
VIRAMA = "्"
VISARGA = "ः"
ANUSVARA = "ं"

KA_V = set("कखगघङ"); CA_V = set("चछजझञ"); TTA_V = set("टठडढण")
TA_V = set("तथदधन");  PA_V = set("पफबभम")
STOP_NASAL = {**{c:"ङ" for c in KA_V}, **{c:"ञ" for c in CA_V}, **{c:"ण" for c in TTA_V},
              **{c:"न" for c in TA_V}, **{c:"म" for c in PA_V}}
K_UNVOICED = set("कख"); P_UNVOICED = set("पफ")
VIS_SIB = {**{c:"स" for c in "सतथ"}, **{c:"श" for c in "शचछ"}, **{c:"ष" for c in "षटठ"}}
PUNCT_DROP = set("।॥|/\\—–\"'“”‘’„«»‹›*•·().,;!?‌‍")
SKIP = set(" \t\n-") | PUNCT_DROP | set("0123456789०१२३४५६७८९")

SLP1_TO_DEVA = {
    "a":"अ","A":"आ","i":"इ","I":"ई","u":"उ","U":"ऊ","f":"ऋ","F":"ॠ","x":"ऌ","X":"ॡ","e":"ए","E":"ऐ","o":"ओ","O":"औ",
    "k":"क","K":"ख","g":"ग","G":"घ","N":"ङ","c":"च","C":"छ","j":"ज","J":"झ","Y":"ञ",
    "w":"ट","W":"ठ","q":"ड","Q":"ढ","R":"ण","t":"त","T":"थ","d":"द","D":"ध","n":"न",
    "p":"प","P":"फ","b":"ब","B":"भ","m":"म",
    "y":"य","r":"र","l":"ल","v":"व","S":"श","z":"ष","s":"स","h":"ह",
    "M":"ं","H":"ः","~":"ँ","'":"ऽ"
}
DEVA_TO_SLP1 = {v: k for k, v in SLP1_TO_DEVA.items() if len(v) == 1}

def to_slp1(t):
    if HAS_SANSCRIPT:
        src = detect_script(t)
        # Map back to sanscript scheme name
        scheme = sanscript.DEVANAGARI
        if src == "kannada": scheme = sanscript.KANNADA
        elif src == "telugu": scheme = sanscript.TELUGU
        elif src == "malayalam": scheme = sanscript.MALAYALAM
        elif src == "grantha": scheme = sanscript.GRANTHA
        elif src == "bengali": scheme = sanscript.BENGALI
        elif src == "gujarati": scheme = sanscript.GUJARATI
        return sanscript.transliterate(t, scheme, sanscript.SLP1)

    out = []
    for c in t:
        o = ord(c)
        if 0x0C80 <= o <= 0x0CFF: o -= 0x0380
        elif 0x0C00 <= o <= 0x0C7F: o -= 0x0300
        elif 0x0D00 <= o <= 0x0D7F: o -= 0x0400
        elif 0x0980 <= o <= 0x09FF: o -= 0x0080
        elif 0x0A80 <= o <= 0x0AFF: o -= 0x0180
            
        c_shifted = chr(o)
        if c_shifted in DEVA_TO_SLP1:
            out.append(DEVA_TO_SLP1[c_shifted])
        elif c_shifted in ["ा","ि","ी","ु","ू","ृ","ॄ","ॢ","ॣ","े","ै","ो","ौ","्"]:
            matra_map = {"ा":"A","ि":"i","ी":"I","ु":"u","ू":"U","ृ":"f","ॄ":"F","ॢ":"x","ॣ":"X","े":"e","ै":"E","ो":"o","ौ":"O","्":""}
            out.append(matra_map[c_shifted])
        else:
            out.append(c)
    return "".join(out)

def slp_to_deva(slp):
    if HAS_SANSCRIPT:
        return sanscript.transliterate(slp, sanscript.SLP1, sanscript.DEVANAGARI)

    v_matras = {"a":"","A":"ा","i":"ि","I":"ी","u":"ु","U":"ू","f":"ೃ","F":"ॄ","x":"ॢ","X":"ॣ","e":"े","E":"ै","o":"ो","O":"ौ"}
    v_indep = {"a":"अ","A":"आ","i":"इ","I":"ई","u":"उ","U":"ऊ","f":"ऋ","F":"ॠ","x":"ऌ","X":"ॡ","e":"ए","E":"ऐ","o":"ओ","O":"औ"}
    cons = {
        "k":"क","K":"ख","g":"ग","G":"घ","N":"ङ","c":"च","C":"छ","j":"ज","J":"झ","Y":"ञ",
        "w":"ट","W":"ठ","q":"ड","Q":"ढ","R":"ण","t":"त","T":"थ","d":"द","D":"ध","n":"न",
        "p":"प","P":"फ","b":"ब","B":"भ","m":"म",
        "y":"य","r":"र","l":"ल","v":"व","S":"श","z":"ष","s":"स","h":"ह"
    }
    out = []
    i = 0
    L = len(slp)
    while i < L:
        c = slp[i]
        if c in v_indep:
            out.append(v_indep[c])
            i += 1
        elif c in cons:
            nxt = slp[i+1] if i+1 < L else ""
            out.append(cons[c])
            if nxt in v_indep:
                out.append(v_matras[nxt])
                i += 2
            elif nxt == "M":
                out.append("ं")
                i += 2
            elif nxt == "H":
                out.append("ः")
                i += 2
            else:
                out.append("्")
                i += 1
        elif c == "M":
            out.append("ं"); i += 1
        elif c == "H":
            out.append("ः"); i += 1
        elif c == "'":
            out.append("ऽ"); i += 1
        else:
            out.append(c); i += 1
    return "".join(out)

# Visarga Sandhi utva/rutva/lopa
_VS_VOICED = set("gGjJqQdDbBNYRnmyrlvh"); _VS_OTHERV = set("iIuUfFxXeEoO")
_VS_ALLV = set("aAiIuUfFxXeEoO"); _VS_LEN = {"a":"A","i":"I","u":"U","f":"F","A":"A","I":"I","U":"U"}

def visarga_sandhi(slp):
    ws = slp.split(" "); i = 0; out = []
    while i < len(ws):
        w = ws[i]
        if w.endswith("H") and i < len(ws) - 1 and len(w) >= 2:
            V = w[-2]; base = w[:-1]; nxt = ws[i + 1]; F = nxt[0] if nxt else ""
            if F == "r":                                       out.append(base[:-1] + _VS_LEN.get(V, V)); i += 1; continue
            if w in ("saH", "ezaH") and F != "a":              out.append(base); i += 1; continue
            if F not in _VS_ALLV and F not in _VS_VOICED:      out.append(w); i += 1; continue
            if V == "a":
                if F == "a":                                   out.append(base[:-1] + "o"); ws[i + 1] = "'" + nxt[1:]; i += 1; continue
                if F in _VS_VOICED:                             out.append(base[:-1] + "o"); i += 1; continue
                out.append(base); i += 1; continue
            if V == "A":                                       out.append(base); i += 1; continue
            if V in _VS_OTHERV:                                 out.append(base + "r"); i += 1; continue
            out.append(w); i += 1
        else:
            out.append(w); i += 1
    return " ".join(out)

def visarga_echo_final(slp):
    ws = slp.split(" ")
    if ws and ws[-1].endswith("H") and len(ws[-1]) >= 2 and ws[-1][-2] in _VS_ALLV:
        ws[-1] = ws[-1][:-1] + "h" + ws[-1][-2]
    return " ".join(ws)

def n_aksharas(s):
    n = 0; L = len(s)
    for i, c in enumerate(s):
        o = ord(c)
        indep = (0x0905 <= o <= 0x0914)
        cons  = (0x0915 <= o <= 0x0939)
        if indep:
            n += 1
        elif cons:
            nxt = s[i+1] if i+1 < L else ""
            if nxt != "्":
                n += 1
    return n

# ── Verse source lookup ─────────────────────────────────────────────────────
_VERSE_INDEX_CACHE = None

def _load_verse_index():
    global _VERSE_INDEX_CACHE
    if _VERSE_INDEX_CACHE is not None:
        return _VERSE_INDEX_CACHE
    try:
        idx_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "charaka_verse_index.json")
        with open(idx_path, "r", encoding="utf-8") as f:
            _VERSE_INDEX_CACHE = json.load(f)
    except Exception:
        _VERSE_INDEX_CACHE = []
    return _VERSE_INDEX_CACHE

def _strip_punct(s):
    """Remove dandas, spaces, and digits for fuzzy verse matching."""
    import unicodedata
    out = []
    for c in s:
        cat = unicodedata.category(c)
        if cat.startswith("P") or cat.startswith("N") or c in " \t\n|।॥":
            continue
        out.append(c)
    return "".join(out)

def lookup_verse_source(text):
    """Try to match `text` against charaka_verse_index. Returns a dict or None."""
    idx = _load_verse_index()
    if not idx:
        return None
    needle = _strip_punct(text)
    if len(needle) < 8:
        return None
    # Short-circuit: look for the longest common prefix match (≥ 60% of chars)
    best_ratio = 0.0
    best_entry = None
    for entry in idx:
        haystack = _strip_punct(entry.get("sanskrit", ""))
        if not haystack:
            continue
        # Cheap overlap: count chars of needle that appear in order in haystack
        hi = 0
        matched = 0
        for ch in needle:
            while hi < len(haystack) and haystack[hi] != ch:
                hi += 1
            if hi < len(haystack):
                matched += 1
                hi += 1
        ratio = matched / max(len(needle), 1)
        if ratio > best_ratio:
            best_ratio = ratio
            best_entry = entry
    if best_ratio >= 0.75 and best_entry:
        return {
            "treatise": "Charaka Samhita",
            "sthana": best_entry.get("sthana", ""),
            "chapter": best_entry.get("chapter"),
            "chapter_title": best_entry.get("chapter_title", ""),
            "verse": best_entry.get("verse"),
            "match_confidence": round(best_ratio, 2)
        }
    return None


def call_gemini_analysis(text):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    prompt = (
        "You are an expert traditional Sanskrit scholar specializing in Ayurvedic literature "
        "(Charaka Samhita, Sushruta Samhita, Ashtanga Hridayam) and classical Vyakarana grammar.\n"
        "Analyze the following Sanskrit text (which may be in Devanagari, IAST, Harvard-Kyoto, "
        "or colloquial Romanized Sanskrit) and return a structured analysis with FOUR parts:\n\n"
        "1. Lipi Normalization: Convert to clean, grammatically correct Devanagari with correct "
        "anusvara, visarga, and matras. Do not silently rewrite words — only fix obvious "
        "corruption or spelling errors. If severely corrupted or ambiguous, set is_ambiguous=true "
        "and describe the issue in warning_message.\n\n"
        "2. IAST Transliteration: Generate a clean IAST transliteration of the normalized Devanagari.\n\n"
        "3. Sandhi-Vicched: Decompose each sandhi junction in the verse. For each:\n"
        "   - joined: the compound as it appears in the text\n"
        "   - split: the constituent padas (separated by ' + ')\n"
        "   - type: 'swar', 'vyanjan', 'visarga', 'none', or 'compound_splitting'\n"
        "   - explanation: short grammatical note (e.g. 'Adguṇaḥ', 'visarga utva', 'Tatpurusha samasa')\n\n"
        "4. Word Meanings: For each INDIVIDUAL WORD after sandhi-vicched, provide:\n"
        "   - devanagari: word in Devanagari\n"
        "   - iast: IAST form\n"
        "   - root: dhatu or pratipadika (e.g. 'āyu (to live)', 'rāj (to shine)')\n"
        "   - grammar: grammatical analysis (e.g. 'n. nom. sg.', 'v. 3sg. pres. act.')\n"
        "   - gloss_en: concise English meaning in context\n"
        "   - commentary_note: if this word has a notable interpretation in Chakrapani (Charaka), "
        "Dalhana (Sushruta), or Arunadatta/Hemadri (Ashtanga Hridaya) commentaries, mention it briefly. "
        "Otherwise leave empty.\n\n"
        f"Sanskrit Text to analyze:\n{text}"
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "normalized_deva": {"type": "STRING"},
                    "iast": {"type": "STRING"},
                    "sandhi_vicched": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "joined":      {"type": "STRING"},
                                "split":       {"type": "STRING"},
                                "type":        {"type": "STRING"},
                                "explanation": {"type": "STRING"}
                            },
                            "required": ["joined", "split", "type"]
                        }
                    },
                    "word_meanings": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "devanagari":      {"type": "STRING"},
                                "iast":            {"type": "STRING"},
                                "root":            {"type": "STRING"},
                                "grammar":         {"type": "STRING"},
                                "gloss_en":        {"type": "STRING"},
                                "commentary_note": {"type": "STRING"}
                            },
                            "required": ["devanagari", "iast", "gloss_en"]
                        }
                    },
                    "is_ambiguous":   {"type": "BOOLEAN"},
                    "warning_message":{"type": "STRING"}
                },
                "required": ["normalized_deva", "iast", "sandhi_vicched", "word_meanings", "is_ambiguous"]
            }
        }
    }

    req_headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=req_headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            text_out = res["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text_out)
    except Exception as e:
        print(f"[preview] Gemini API call failed: {e}")
        return None

def local_fallback_preview(text):
    # Original rule-based parser logic as fallback
    padas = [p.strip() for p in re.split(r'[\n|।\u0964]+', text) if p.strip()]
    padas = [p for p in padas if not re.match(r'^[\d\u0966-\u096f\s]+$', p)]
    if not padas:
        padas = [text]

    pieces_devanagari = []
    for p in padas:
        slp = to_slp1(p)
        slp = visarga_sandhi(slp)
        slp = visarga_echo_final(slp)
        slp = slp.replace("F", "rU")
        pieces_devanagari.append(slp_to_deva(slp))

    normalized_deva = " ".join(pieces_devanagari)
    return {
        "normalized_deva": normalized_deva,
        "iast": normalized_deva,
        "sandhi_vicched": [{"joined": p, "split": p, "type": "none", "explanation": "local fallback"} for p in padas],
        "word_meanings": [],
        "is_ambiguous": False,
        "warning_message": ""
    }

def preview_text(text):
    try:
        # 1. Try Gemini Analysis first (includes sandhi-vicched + word gloss)
        result = call_gemini_analysis(text)

        # 2. Fall back to local rule-based parser if Gemini is unavailable
        if not result:
            result = local_fallback_preview(text)

        # 3. Verse source lookup (Charaka index — fast, local, no API)
        verse_ref = lookup_verse_source(result.get("normalized_deva", text))
        if not verse_ref:
            # Try matching against the raw input in case normalization changed it
            verse_ref = lookup_verse_source(text)
        result["verse_source"] = verse_ref  # dict or None

        # 4. Chandas (Meter) & Laghu-Guru Scansion — local, via vagdhenu libraries
        if HAS_LOCAL_SCANSION:
            slp_clean = chandas_labeler.to_slp1(result["normalized_deva"], src="devanagari")
            syls = tts_syllabify.syllabify(slp_clean)
            tts_weight.tag_weights(syls)
            meter = tts_meter.analyze(syls)

            syl_list = []
            for s in syls:
                syl_list.append({
                    "text": slp_to_deva(s["text"]),
                    "slp1": s["text"],
                    "weight": s["weight"],
                    "weight_cause": s.get("weight_cause", ""),
                    "pada_index": s.get("pada_index", 0),
                    "pos_in_pada": s.get("pos_in_pada", 0),
                    "is_pada_final": s.get("is_pada_final", False)
                })

            result["meter_name"] = meter.get("name", "unknown")
            result["pada_length"] = meter.get("pada_length")
            result["syllables"] = syl_list
        else:
            result["meter_name"] = "unknown"
            result["pada_length"] = None
            result["syllables"] = []

        return result
    except Exception as e:
        return {"error": str(e)}

class handler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        BaseHTTPRequestHandler.end_headers(self)
        
    def do_OPTIONS(self):
        self.send_response(200); self.end_headers()
        
    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            text = params.get("text", [""])[0].strip()
            if not text:
                self.send_response(400); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"error": "text parameter is required"}).encode()); return
                
            result = preview_text(text)
            resp_json = json.dumps(result, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(resp_json)))
            self.end_headers()
            self.wfile.write(resp_json)
        except Exception as e:
            self.send_response(500); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
        return
