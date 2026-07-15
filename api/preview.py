import re
import json
from http.server import BaseHTTPRequestHandler

# ── Self-contained Indic Pre-processing Rules ──────────────────────────────────────────
# Implemented locally so Sandhi preview is always online, fast, and does not require a GPU.

VIRAMA = "्"
VISARGA = "ः"
ANUSVARA = "ं"
JIHVA = "ᳵ"
UPADH = "ᳶ"

KA_V = set("कखगघङ"); CA_V = set("चछजझञ"); TTA_V = set("टठडढण")
TA_V = set("तथदधन");  PA_V = set("पफबभम")
STOP_NASAL = {**{c:"ङ" for c in KA_V}, **{c:"ञ" for c in CA_V}, **{c:"ण" for c in TTA_V},
              **{c:"न" for c in TA_V}, **{c:"म" for c in PA_V}}
K_UNVOICED = set("कख"); P_UNVOICED = set("पफ")
VIS_SIB = {**{c:"स" for c in "सतथ"}, **{c:"श" for c in "शचछ"}, **{c:"ष" for c in "षटठ"}}
PUNCT_DROP = set("।॥|/\\—–\"'“”‘’„«»‹›*•·().,;!?‌‍")
SKIP = set(" \t\n-") | PUNCT_DROP | set("0123456789०१२३४५६७८९")

# Transliteration mappings (local mini-sanscript fallback)
# Maps SLP1, Devanagari, and Kannada scripts simply for syllable alignment
SLP1_TO_DEVA = {
    "a":"अ","A":"आ","i":"इ","I":"ई","u":"उ","U":"ऊ","f":"ऋ","F":"ॠ","x":"ऌ","X":"ॡ","e":"ए","E":"ऐ","o":"ओ","O":"औ",
    "k":"क","K":"ख","g":"ग","G":"घ","N":"ङ","c":"च","C":"छ","j":"ज","J":"झ","Y":"ञ",
    "w":"ट","W":"ठ","q":"ड","Q":"ढ","R":"ण","t":"त","T":"थ","d":"द","D":"ध","n":"न",
    "p":"प","P":"फ","b":"ब","B":"भ","m":"म",
    "y":"य","r":"र","l":"ल","v":"व","S":"श","z":"ष","s":"स","h":"ह",
    "M":"ं","H":"ः","~":"ँ","'":"ऽ"
}
DEVA_TO_SLP1 = {v: k for k, v in SLP1_TO_DEVA.items() if len(v) == 1}

# Standard Sanskrit Unicode blocks transliterated into SLP1
def to_slp1(t):
    # Minimal Brahmic to Deva, then Deva to SLP1 conversion
    out = []
    for c in t:
        o = ord(c)
        # Shift script ranges to Devanagari range (0x0900-0x097F)
        # Kannada (0x0C80-0x0CFF), Telugu (0x0C00-0x0C7F), Malayalam (0x0D00-0x0D7F)
        if 0x0C80 <= o <= 0x0CFF:
            o -= 0x0380
        elif 0x0C00 <= o <= 0x0C7F:
            o -= 0x0300
        elif 0x0D00 <= o <= 0x0D7F:
            o -= 0x0400
        elif 0x0980 <= o <= 0x09FF: # Bengali
            o -= 0x0080
        elif 0x0A80 <= o <= 0x0AFF: # Gujarati
            o -= 0x0180
            
        c_shifted = chr(o)
        if c_shifted in DEVA_TO_SLP1:
            out.append(DEVA_TO_SLP1[c_shifted])
        elif c_shifted in ["ा","ि","ी","ु","ू","ृ","ॄ","ॢ","ॣ","े","ै","ो","ौ","्"]:
            # Matras mapping to SLP1 vowels/virama
            matra_map = {"ा":"A","ि":"i","ी":"I","ु":"u","ू":"U","ृ":"f","ॄ":"F","ॢ":"x","ॣ":"X","े":"e","ै":"E","ो":"o","ौ":"O","्":""}
            out.append(matra_map[c_shifted])
        else:
            out.append(c)
    return "".join(out)

def slp1_to_kannada(slp):
    # Simple SLP1 to Kannada mapper
    k_vowels = {"a":"ಅ","A":"ಆ","i":"ಇ","I":"ಈ","u":"ಉ","U":"ಊ","f":"ಋ","F":"ಋೂ","x":"ಌ","X":"ೡ","e":"ಎ","E":"ಐ","o":"ಒ","O":"ಔ"}
    k_cons = {
        "k":"ಕ","K":"ಖ","g":"ಗ","G":"ಘ","N":"ಙ","c":"ಚ","C":"ಛ","j":"ಜ","J":"ಝ","Y":"ಞ",
        "w":"ಟ","W":"ಠ","q":"ಡ","Q":"ಢ","R":"ಣ","t":"ತ","T":"ಥ","d":"ದ","D":"ಧ","n":"ನ",
        "p":"ಪ","P":"ಫ","b":"ಬ","B":"ಭ","m":"ಮ",
        "y":"ಯ","r":"ರ","l":"ಲ","v":"ವ","S":"ಶ","z":"ಷ","s":"ಸ","h":"ಹ"
    }
    out = []
    i = 0
    L = len(slp)
    while i < L:
        c = slp[i]
        if c in k_vowels:
            out.append(k_vowels[c])
            i += 1
        elif c in k_cons:
            # Check if followed by vowel (represented by matra)
            nxt = slp[i+1] if i+1 < L else ""
            out.append(k_cons[c])
            if nxt in k_vowels:
                # Append matra
                matra_map = {"a":"","A":"ಾ","i":"ಿ","I":"ೀ","u":"ು","U":"ೂ","f":"ೃ","F":"ೃೂ","x":"ೢ","X":"ೣ","e":"ೆ","E":"ೈ","o":"ೊ","O":"ೋ"}
                out.append(matra_map[nxt])
                i += 2
            elif nxt == "M":
                out.append("ಂ")
                i += 2
            elif nxt == "H":
                out.append("ಃ")
                i += 2
            else:
                out.append("್")
                i += 1
        elif c == "M":
            out.append("ಂ"); i += 1
        elif c == "H":
            out.append("ಃ"); i += 1
        elif c == "'":
            out.append("ಽ"); i += 1
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

def model_text_sandhi(src_text, echo_final=True):
    slp = to_slp1(src_text)
    slp = visarga_sandhi(slp)
    if echo_final:
        slp = visarga_echo_final(slp)
    slp = slp.replace("F", "rU")
    return slp_to_kannada(slp)

# Preprocessing helpers
def n_aksharas(s):
    n = 0; L = len(s)
    for i, c in enumerate(s):
        o = ord(c)
        indep = (0x0905 <= o <= 0x0914) or (0x0C85 <= o <= 0x0C94)
        cons  = (0x0915 <= o <= 0x0939) or (0x0C95 <= o <= 0x0CB9)
        if indep:
            n += 1
        elif cons:
            nxt = s[i+1] if i+1 < L else ""
            if nxt not in ("्", "್"):
                n += 1
    return n

_AN_KA=set("ಕಖಗಘಙ"); _AN_CA=set("ಚಛಜಝಞ"); _AN_TTA=set("ಟಠಡಢಣ"); _AN_TA=set("ತಥದಧನ")
def _anusvara_m(s):
    res=[]; n=len(s)
    for i,c in enumerate(s):
        if c=="ಂ":
            j=i+1
            while j<n and s[j]==" ": j+=1
            nxt=s[j] if j<n else ""
            if   not nxt:        res.append("ಂ")
            elif nxt in _AN_KA:  res.append("ಙ್")
            elif nxt in _AN_CA:  res.append("ಞ್")
            elif nxt in _AN_TTA: res.append("ಣ್")
            elif nxt in _AN_TA:  res.append("ನ್")
            else:                res.append("ಮ್")
        else: res.append(c)
    return "".join(res)

_SATVA = {"ಚ": "ಶ್", "ಛ": "ಶ್", "ಟ": "ಷ್", "ಠ": "ಷ್", "ತ": "ಸ್", "ಥ": "ಸ್"}
def _satva(s):
    out = []; n = len(s); i = 0
    while i < n:
        c = s[i]
        if c == "ಃ":
            j = i + 1
            while j < n and s[j] == " ": j += 1
            nxt = s[j] if j < n else ""
            if nxt in _SATVA:
                out.append(_SATVA[nxt]); i = j; continue
        out.append(c); i += 1
    return "".join(out)

def _hna_metathesis(s):
    return s.replace("ಹ್ಣ", "ಣ್ಹ").replace("ಹ್ನ", "ನ್ಹ")

def _vocalic_l(s):
    return s.replace("ೢ", "್ಲೃ").replace("ೣ", "್ಲೄ").replace("", "ಲೃ").replace("ೡ", "ಲೄ")

_VECHO_SHORT = {"i": "hi", "u": "hu", "e": "he"}
_VLONG = set("ಾೀೂೄೆೇೈೊೋೌ")
def _danda_fix(s):
    s = s.rstrip()
    if not s: return s
    if s.endswith("ಃ"):
        core = s[:-1]; pv = core[-1] if core else ""
        if pv in _VECHO_SHORT:      s = core + _VECHO_SHORT[pv]
        elif pv in _VLONG:          pass
        else:                        s = core + "ಹ"
    elif s.endswith("ಂ"):
        s = s[:-1] + "ಮ್"
    return s

def preview_text(text):
    try:
        padas = [p.strip() for p in re.split(r'[\n|।\u0964]+', text) if p.strip()]
        padas = [p for p in padas if not re.match(r'^[\d\u0966-\u096f\s]+$', p)]
        if not padas:
            padas = [text]
        pieces = [model_text_sandhi(p, echo_final=True) for p in padas]
        pieces = [_satva(x) for x in pieces]
        pieces = [_danda_fix(_anusvara_m(x)) for x in pieces]
        pieces = [_hna_metathesis(x) for x in pieces]
        pieces = [_vocalic_l(x) for x in pieces]
        slp_pieces = [to_slp1(p) for p in padas]
        return {
            "padas": padas,
            "kannada_routed": pieces,
            "slp1": slp_pieces,
            "n_syllables": [n_aksharas(x) for x in pieces],
        }
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
                
            # Process locally inside Vercel's Python backend - always online!
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
