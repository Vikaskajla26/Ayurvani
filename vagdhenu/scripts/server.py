# Import datasets first to resolve pyarrow/torch DLL loading conflict on Windows
import datasets

import os
import sys
import json
import re
import urllib.parse
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
import numpy as np
import soundfile as sf
import torch


# Paths
HERE = os.path.dirname(os.path.abspath(__file__))  # vagdhenu/scripts/
REPO = os.path.dirname(HERE)                       # vagdhenu/
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.join(REPO, "BigVGAN"))

import prep_text as PT
import bigvgan


from f5_tts.infer.utils_infer import load_model, load_vocoder, infer_process, preprocess_ref_audio_text
from f5_tts.model import DiT
import torchaudio as _ta

CHAMP = os.environ.get("CHAMP_ROOT", os.path.join(REPO, "models"))
SR = 24000
FALLBACK_METER = "vasantatilaka"

# Load vocabulary
_vocab_cands = [
    os.path.join(CHAMP, "vocab.txt"),
    os.path.join(REPO, "src", "reference_bank", "vocab.txt")
]
vocab = next((v for v in _vocab_cands if v and os.path.exists(v)), None)
if vocab is None:
    print("Warning: vocab.txt not found in default paths, waiting for download...")
    vocab = os.path.join(CHAMP, "vocab.txt")

# Helper functions for rendering
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

def _aksharas(s):
    out=[]; cur=""
    for i,c in enumerate(s):
        o=ord(c); base=(0x0C85<=o<=0x0C94) or (0x0905<=o<=0x0914) or (0x0C95<=o<=0x0CB9) or (0x0915<=o<=0x0939)
        prev=s[i-1] if i>0 else ""
        if base and prev not in ("್","्"):
            if cur: out.append(cur)
            cur=c
        else: cur+=c
    if cur: out.append(cur)
    return out

def _rep_depths(aks):
    n=len(aks); mono=1; i=0
    while i<n:
        j=i+1
        while j<n and aks[j]==aks[i]: j+=1
        mono=max(mono,j-i); i=j if j>i+1 else i+1
    di=1; i=0
    while i+1<n:
        if aks[i]!=aks[i+1]:
            cnt=1; j=i+2
            while j+1<n and aks[j]==aks[i] and aks[j+1]==aks[i+1]: cnt+=1; j+=2
            di=max(di,cnt); i=j if cnt>1 else i+1
        else: i+=1
    return mono, di

_VMATRA = set("ಾಿೀುೂೃೄೆೇೈೊೋೌ")
_VECHO_SHORT = {"i": "hi", "u": "hu", "e": "he"}
_VLONG = set("ಾೀೂೄೆೇೈೊೋೌ")

def gate(au, voice=0.08, sil=0.012, fin=0.015, fout=0.040, lead=0.03, keep=0.06, fade=True, fric=False, halant=False):
    win = int(0.02*SR); r = [float(np.sqrt((au[i:i+win]**2).mean())) for i in range(0, len(au)-win, win)]; n = len(r)
    if n == 0: return au
    if fric:
        FR = 0.006
        s = next((i for i in range(n-1) if r[i] > FR and r[i+1] > FR), int(np.argmax(r)))
        while s > 0 and r[s-1] > FR: s -= 1
        _vdef = s
    else:
        vs = next((i for i in range(n-1) if r[i] > voice and r[i+1] > sil), int(np.argmax(r))); s = vs
        while s > 0 and r[s-1] > sil: s -= 1
        _vdef = vs
    ve_thr = 0.012 if halant else 0.035
    ve = max((i for i in range(n) if r[i] > ve_thr), default=_vdef)
    keep_s = 0.12 if halant else keep
    start = max(0, s*win - int(lead*SR))
    end = min(len(au), ve*win + int(keep_s*SR)); out = au[start:end].copy()
    if fade:
        fi = (0 if fric else int(fin*SR)); fo = int((0.018 if halant else fout)*SR)
        if fi and len(out) > fi: out[:fi] *= np.linspace(0, 1, fi)
        if fo and len(out) > fo: out[-fo:] *= (np.cos(np.linspace(0, np.pi, fo))*0.5 + 0.5)
    return out

_VIRAMA = "्್"
def _ends_halant(txt):
    t = txt.rstrip(" ।॥|.,;:!?‌‍")
    return len(t) > 0 and t[-1] in _VIRAMA

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
    return s.replace("ೢ", "್ಲೃ").replace("ೣ", "್ಲೄ").replace("ಌ", "ಲೃ").replace("ೡ", "ಲೄ")

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

# Global models and state placeholders
cfm = None
real_voc = None
big_vgan = None
bank = {}
lut = {}
ref_cache = {}
primes = {}

def init_models():
    global cfm, real_voc, big_vgan, bank, lut, primes
    print("[server] Loading models into GPU memory...")
    
    CFG = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)
    
    # Paths to checkpoints
    voice_path = os.path.join(CHAMP, "voice_steer_ema_2026-06-17.pt")
    voc_path = os.path.join(CHAMP, "voc_bigvgan_EMA_2026-06-11.pth")
    bank_path = os.path.join(REPO, "src", "reference_bank", "bank.json")
    
    cfm = load_model(DiT, CFG, mel_spec_type="vocos", vocab_file=vocab, device="cuda")
    ck = torch.load(voice_path, map_location="cpu", weights_only=True)
    ema = {k.replace("ema_model.", ""): v for k, v in ck["ema_model_state_dict"].items() if k not in ("initted", "step")}
    cfm.load_state_dict(ema, strict=False)
    cfm.eval()
    
    real_voc = load_vocoder("vocos")
    
    # Vocos decoder wrapper
    class Cap:
        def __init__(self, r): self.r = r; self.last = None
        def decode(self, m): self.last = m.detach().cpu().numpy(); return self.r.decode(m)
    
    global cap
    cap = Cap(real_voc)
    
    # BigVGAN Vocoder
    big_vgan = bigvgan.BigVGAN.from_pretrained("nvidia/bigvgan_v2_24khz_100band_256x", use_cuda_kernel=False)
    bsd = torch.load(voc_path, map_location="cpu")
    bsd = bsd.get("model", bsd)
    big_vgan.load_state_dict(bsd)
    big_vgan.remove_weight_norm()
    big_vgan = big_vgan.cuda().eval()
    
    for p in big_vgan.parameters():
        p.requires_grad = False
        
    # Reference Bank
    bank = json.load(open(bank_path, encoding="utf-8"))
    bdir = os.path.dirname(bank_path)
    for k, v in bank.items():
        if k.startswith("_") or not isinstance(v, dict) or "wav" not in v: continue
        lut[k.lower()] = v
        lut[v["wav"].replace(".wav", "").lower()] = v
    primes = bank.get("repeat_primes", {})
    print("[server] Models successfully loaded!")

def get_ref(meter):
    key = meter.lower().replace(".wav", "")
    if key in ref_cache: return ref_cache[key]
    if key not in lut:
        key = FALLBACK_METER
    e = lut[key]
    ref_wav = os.path.join(REPO, "src", "reference_bank", e["wav"])
    ref_text = e["ref_text"]
    sps = float(e.get("sec_per_syll", 0.26))
    ref_audio, ref_t = preprocess_ref_audio_text(ref_wav, ref_text, clip_short=True)
    ra, sr = _ta.load(ref_audio); ref_len = ra.shape[-1] / sr
    val = (ref_audio, ref_t, sps, ref_len)
    ref_cache[key] = val
    return val

def _stitch(segs, GAPS, fric=False, halant=False):
    if len(segs) == 1: return gate(segs[0], fric=fric, halant=halant)
    b = []; last = len(segs) - 1
    for i, s in enumerate(segs): 
        b += [gate(s, fric=(fric and i == 0), halant=(halant and i == last)), GAPS[i] if i < len(GAPS) else GAPS[-1]]
    return np.concatenate(b[:-1])

def render_verse(text, meter="anushtubh", seed=42, speed=0.90):
    ref_audio, ref_t, sps, ref_len = get_ref(meter)
    
    def _basetext(p):
        return PT.model_text_sandhi(p, echo_final=False)
        
    # Split text by line/danda to segment it into shorter, faster pieces
    padas = [p.strip() for p in re.split(r'[\n|।]+', text) if p.strip()]
    # Filter out verse numbers (e.g. ४२, 42)
    padas = [p for p in padas if not re.match(r'^[\d\u0966-\u096f\s]+$', p)]
    if not padas:
        padas = [text]
        
    PIECES = [_basetext(p) for p in padas]
    PIECES = [_satva(x) for x in PIECES]
    PIECES = [_danda_fix(_anusvara_m(x)) for x in PIECES]
    PIECES = [_hna_metathesis(x) for x in PIECES]
    PIECES = [_vocalic_l(x) for x in PIECES]
    
    _ra, _rt = ref_audio, ref_t
    _mono = max((_rep_depths(_aksharas(x))[0] for x in PIECES), default=1)
    _di   = max((_rep_depths(_aksharas(x))[1] for x in PIECES), default=1)
    _pick = None
    
    if _di >= 3:
        _pick = next((k for k in ["prime_jaya","prime_chata"] if k in primes and primes[k].get("di_max",0)>=_di), None) \
                or next((k for k,v in primes.items() if isinstance(v,dict) and v.get("di_max",0)>=_di), None)
    if _pick is None and _mono >= 2 and "prime_mono" in primes and primes["prime_mono"].get("mono_max",0) >= _mono:
        _pick = "prime_mono"
        
    if _pick:
        bdir = os.path.dirname(os.path.join(REPO, "src", "reference_bank", "bank.json"))
        _pv = primes[_pick]
        _ra, _rt = preprocess_ref_audio_text(os.path.join(bdir, _pv["wav"]), _pv["ref_text"], clip_short=True)
        _prb, _psr = _ta.load(_ra)
        ref_len = _prb.shape[-1] / _psr
        
    NSYLL = [n_aksharas(x) for x in PIECES]
    GAPS = [np.zeros(int(0.55 * SR) + (int(0.20 * SR) if _ends_halant(_p) else 0), dtype=np.float32) for _p in PIECES]
    
    bseg = []
    for i, p in enumerate(PIECES):
        au = None
        for att in range(2):
            torch.manual_seed(seed + att)
            _fixd = (ref_len + NSYLL[i] * sps) if (sps > 0 and NSYLL) else None
            w, sr, _ = infer_process(_ra, _rt, p, cfm, cap, mel_spec_type="vocos", speed=speed, nfe_step=32, cfg_strength=3.0, device="cuda", fix_duration=_fixd)
            w = np.array(w, dtype=np.float32)
            if np.abs(w).max() > 1.5: w = w / 32768.0
            if float(np.sqrt((w**2).mean())) > 0.04: au = w; break
        if au is None: au = w
        
        # BigVGAN Vocoder call
        m = torch.from_numpy(cap.last).cuda()
        with torch.no_grad():
            if m.dim() == 3 and m.shape[1] != 100 and m.shape[2] == 100: 
                m = m.transpose(1, 2)
            y = big_vgan(m).squeeze().cpu().numpy().astype(np.float32)
            
        mx = np.abs(y).max()
        y = y / mx * 0.97 if mx > 1 else y
        bseg.append(y)
        
    _slp = PT.align_slp1(padas[0])
    fric = bool(_slp) and _slp[0] in ("S", "z", "s", "h")
    halant = _ends_halant(PIECES[-1])
    final = _stitch(bseg, GAPS, fric=fric, halant=halant)
    return final

# HTTP Request Handler

# ---- Charaka Samhita Online verse fetcher via MediaWiki API ----
CSO_API = "http://www.carakasamhitaonline.com/api.php"

# Map chapter wiki page titles for all 120 chapters of Charaka Samhita
CHARAKA_PAGE_TITLES = {
    "Sutrasthana": {
        1: "Deerghanjiviteeya Adhyaya",
        2: "Apamarga Tanduliya",
        3: "Aragvadhiya Adhyaya",
        4: "Shadvirechanashatashritiya Adhyaya",
        5: "Matrashiteeya Adhyaya",
        6: "Tasyashiteeya Adhyaya",
        7: "Naveganadharaniya Adhyaya",
        8: "Indriyopakramaniya Adhyaya",
        9: "Khuddakachatushpada",
        10: "Mahachatushpada",
        11: "Tistraishaniya Adhyaya",
        12: "Vatakalakaliya Adhyaya",
        13: "Snehadhyaya",
        14: "Swedadhyaya",
        15: "Upakalpaniya Adhyaya",
        16: "Chikitsaprabhritiya Adhyaya",
        17: "Kiyanta Shiraseeya Adhyaya",
        18: "Trishothiya Adhyaya",
        19: "Ashtodariya Adhyaya",
        20: "Maharoga Adhyaya",
        21: "Ashtauninditiya Adhyaya",
        22: "Langhanabrimhaniya Adhyaya",
        23: "Santarpaniya Adhyaya",
        24: "Vidhishonitiya Adhyaya",
        25: "Yajjah Purushiya Adhyaya",
        26: "Atreyabhadrakapyiya Adhyaya",
        27: "Annapanavidhi Adhyaya",
        28: "Vividhashitapitiya Adhyaya",
        29: "Dashapranayataneeya Adhyaya",
        30: "Arthedashmahamooliya Adhyaya",
    },
    "Nidanasthana": {
        1: "Jwara Nidana",
        2: "Raktapitta Nidana",
        3: "Gulma Nidana",
        4: "Prameha Nidana",
        5: "Kushtha Nidana",
        6: "Shosha Nidana",
        7: "Unmada Nidana",
        8: "Apasmara Nidana",
    },
    "Vimanasthana": {
        1: "Rasa Vimana Adhyaya",
        2: "Trividhakukshiya Vimana Adhyaya",
        3: "Janapadodhvansaniya Vimana Adhyaya",
        4: "Trividha Roga Vishesha Vijnaniya Vimana Adhyaya",
        5: "Sroto Vimana Adhyaya",
        6: "Roganika Vimana Adhyaya",
        7: "Vyadhita Rupiya Vimana Adhyaya",
        8: "Rogabhishagjitiya Vimana Adhyaya",
    },
    "Sharirasthana": {
        1: "Katidhapurusha Sharira Adhyaya",
        2: "Atulyagotriya Sharira Adhyaya",
        3: "Khuddika Garbhavakranti Sharira Adhyaya",
        4: "Mahatigarbhavakranti Sharira Adhyaya",
        5: "Purusha Vichaya Sharira Adhyaya",
        6: "Sharira Vichaya Sharira Adhyaya",
        7: "Sharira Sankhya Sharira Adhyaya",
        8: "Jatisutriya Sharira Adhyaya",
    },
    "Indriyasthana": {
        1: "Varnasvariyam Indriyam Adhyaya",
        2: "Pushpitakam Indriyam Adhyaya",
        3: "Parimarshaneeyam Indriyam Adhyaya",
        4: "Indriyaneekam Indriyam Adhyaya",
        5: "Purvarupeeyam Indriyam Adhyaya",
        6: "Katamanisharireeyam Indriyam Adhyaya",
        7: "Pannarupiyam Indriyam Adhyaya",
        8: "Avakshiraseeyam Indriyam Adhyaya",
        9: "Yasyashyavanimittiyam Indriyam Adhyaya",
        10: "Sadyomaraneeyam Indriyam Adhyaya",
        11: "Anujyotiyam Indriyam Adhyaya",
        12: "Gomayachurniyam Indriyam Adhyaya",
    },
    "Chikitsasthana": {
        1: "Rasayana Adhyaya",
        2: "Vajikarana Adhyaya",
        3: "Jwara Chikitsa Adhyaya",
        4: "Raktapitta Chikitsa Adhyaya",
        5: "Gulma Chikitsa Adhyaya",
        6: "Prameha Chikitsa Adhyaya",
        7: "Kushtha Chikitsa Adhyaya",
        8: "Rajayakshma Chikitsa Adhyaya",
        9: "Unmada Chikitsa Adhyaya",
        10: "Apasmara Chikitsa Adhyaya",
        11: "Kshatakshina Chikitsa Adhyaya",
        12: "Shvayathu Chikitsa Adhyaya",
        13: "Udara Chikitsa Adhyaya",
        14: "Arsha Chikitsa",
        15: "Grahani Chikitsa",
        16: "Pandu Chikitsa Adhyaya",
        17: "Hikka Shwasa Chikitsa Adhyaya",
        18: "Kasa Chikitsa",
        19: "Atisara Chikitsa",
        20: "Chhardi Chikitsa",
        21: "Visarpa Chikitsa",
        22: "Trishna Chikitsa",
        23: "Visha Chikitsa",
        24: "Madatyaya Chikitsa",
        25: "Dwivraniya Chikitsa",
        26: "Trimarmiya Chikitsa",
        27: "Urustambha Chikitsa Adhyaya",
        28: "Vatarakta Chikitsa",
        29: "Vatavyadhi Chikitsa",
        30: "Yonivyapat Chikitsa Adhyaya",
    },
    "Kalpasthana": {
        1: "Madana Kalpa Adhyaya",
        2: "Jimutaka Kalpa Adhyaya",
        3: "Ikshvaku Kalpa Adhyaya",
        4: "Dhamargava Kalpa Adhyaya",
        5: "Vatsaka Kalpa Adhyaya",
        6: "Kritavedhana Kalpa Adhyaya",
        7: "Shyamatrivrita Kalpa Adhyaya",
        8: "Chaturangula Kalpa Adhyaya",
        9: "Tilvaka Kalpa Adhyaya",
        10: "Sudha Kalpa Adhyaya",
        11: "Saptalashankhini Kalpa Adhyaya",
        12: "Dantidravanti Kalpa Adhyaya",
    },
    "Siddhisthana": {
        1: "Kalpana Siddhi Adhyaya",
        2: "Panchakarmiya Siddhi Adhyaya",
        3: "Bastisutriyam Siddhi Adhyaya",
        4: "Snehavyapat Siddhi Adhyaya",
        5: "Netrabastivyapat Siddhi Adhyaya",
        6: "Vamana Virechana Vyapat Siddhi Adhyaya",
        7: "Uttar Basti Siddhi Adhyaya",
        8: "Prasrita Yogiyam Siddhi Adhyaya",
        9: "Trimarmiya Siddhi Adhyaya",
        10: "Basti Siddhi Adhyaya",
        11: "Phalamatra Siddhi Adhyaya",
        12: "Bastivyapat Siddhi Adhyaya",
    },
}

# Persistent cache file path
_cache_file = os.path.join(HERE, "cso_page_cache.json")

# Load persistent cache
_page_cache = {}
if os.path.exists(_cache_file):
    try:
        with open(_cache_file, "r", encoding="utf-8") as f:
            _page_cache = json.load(f)
        print(f"[server] Loaded {len(_page_cache)} cached pages from {_cache_file}")
    except Exception as e:
        print(f"[server] Error loading cache: {e}")

def _to_devanagari_num(n):
    """Convert integer to Devanagari numeral string."""
    return ''.join(chr(ord(c) + 0x0966 - 48) for c in str(n))

def _fetch_wiki_page(title):
    """Fetch raw wikitext for a page from carakasamhitaonline.com MediaWiki API."""
    if title in _page_cache:
        return _page_cache[title]
    
    safe_title = urllib.parse.quote(title.replace(" ", "_"))
    url = f"{CSO_API}?action=query&prop=revisions&titles={safe_title}&rvslots=*&rvprop=content&format=json"
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Ayurvani/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        pages = data.get("query", {}).get("pages", {})
        for page_id, page_data in pages.items():
            if page_id == "-1":
                return None
            revisions = page_data.get("revisions", [])
            if revisions:
                content = revisions[0].get("slots", {}).get("main", {}).get("*", "")
                _page_cache[title] = content
                # Save persistent cache
                try:
                    with open(_cache_file, "w", encoding="utf-8") as f:
                        json.dump(_page_cache, f, ensure_ascii=False, indent=2)
                except Exception as ex:
                    print(f"[fetch_verse] Error writing cache: {ex}")
                return content
    except Exception as e:
        print(f"[fetch_verse] Error fetching wiki page '{title}': {e}")
    return None

def _clean_wiki_text(text):
    """Remove wiki markup from text."""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Convert [[link|display]] to display
    text = re.sub(r'\[\[[^\]|]*\|([^\]]*)\]\]', r'\1', text)
    # Convert [[link]] to link
    text = re.sub(r'\[\[([^\]]*)\]\]', r'\1', text)
    # Remove external links [url text] -> text
    text = re.sub(r'\[https?://\S+\s+([^\]]*)\]', r'\1', text)
    # Remove bare external URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove wiki bold/italic markup
    text = re.sub(r"'{2,3}", '', text)
    return text.strip()

def _extract_verse(content, verse_num):
    """Extract Sanskrit verse text and English translation from raw wikitext."""
    dn = _to_devanagari_num(verse_num)
    vn = str(verse_num)
    
    # Find the Devanagari verse marker ||dn||
    marker = '||' + dn + '||'
    pos = content.find(marker)
    if pos == -1:
        return None, None
    
    # Extract Sanskrit: walk backward from marker to collect Devanagari lines
    before = content[:pos]
    lines_before = before.split('\n')
    
    sanskrit_lines = []
    blank_count = 0
    for line in reversed(lines_before):
        stripped = line.strip()
        if not stripped:
            blank_count += 1
            if blank_count > 2 and sanskrit_lines:
                break
            continue
        # Stop at HTML, wiki headings, or non-Devanagari content
        if stripped.startswith('<') or stripped.startswith('=') or stripped.startswith('{'):
            break
        has_devanagari = any(0x0900 <= ord(c) <= 0x097F for c in stripped)
        if has_devanagari:
            sanskrit_lines.insert(0, stripped)
            blank_count = 0
        else:
            if sanskrit_lines:
                break
    
    sanskrit_text = '\n'.join(sanskrit_lines)
    if sanskrit_text:
        sanskrit_text += marker
    
    # Extract English translation after the transliteration block
    after_marker = content[pos + len(marker):]
    close_pos = after_marker.find('</div></div>')
    translation = None
    
    if close_pos != -1:
        after_close = after_marker[close_pos + len('</div></div>'):]
        # Look for [vn] or [vn-something] or similar patterns
        # Handle single verse [42] or range ending [40-42]
        bracket_patterns = [
            r'\[' + vn + r'\]',                           # [42]
            r'\[\d+-' + vn + r'\]',                       # [40-42]
        ]
        
        best_match = None
        for pat in bracket_patterns:
            m = re.search(pat, after_close)
            if m and (best_match is None or m.start() < best_match.start()):
                best_match = m
        
        if best_match:
            raw_trans = after_close[:best_match.start()]
            # Find the start of actual translation (skip wiki markup sections)
            # The translation usually starts after </div></div> possibly with <div> wrapper
            raw_trans = _clean_wiki_text(raw_trans).strip()
            # Remove any sub-headings that leaked in
            raw_trans = re.sub(r'={2,}[^=]+=+', '', raw_trans).strip()
            # Take only the last paragraph (closest to the [vn] marker) if multiple paragraphs
            paragraphs = [p.strip() for p in raw_trans.split('\n\n') if p.strip()]
            if paragraphs:
                translation = paragraphs[-1]
    
    return sanskrit_text, translation

def _get_section_heading(content, verse_num):
    """Get the section heading (====heading====) for a given verse."""
    dn = _to_devanagari_num(verse_num)
    marker = '||' + dn + '||'
    pos = content.find(marker)
    if pos == -1:
        return None
    
    before = content[:pos]
    # Find the last ==== heading ==== before this verse
    headings = list(re.finditer(r'={2,4}\s*([^=]+?)\s*={2,4}', before))
    if headings:
        heading = headings[-1].group(1).strip()
        return _clean_wiki_text(heading)
    return None

def _extract_vimarsha(content, verse_num, section_heading=None):
    """Extract Tattva Vimarsha and Vidhi Vimarsha commentary for a specific verse."""
    vn = str(verse_num)
    tattva = []
    vidhi = []
    
    # Find Tattva Vimarsha section
    tattva_match = re.search(r'==\s*Tattva Vimarsha[^=]*==', content)
    vidhi_match = re.search(r'==\s*Vidhi Vimarsha[^=]*==', content)
    
    def _verse_ref_matches(text, verse_num_str):
        """Check if text contains a verse reference that includes this verse number."""
        vn = verse_num_str
        vi = int(vn)
        # Direct match: [verse 42] or [Verse 42]
        if re.search(r'\[(?:verse|Verse)\s+' + vn + r'\]', text, re.IGNORECASE):
            return True
        # Range match: [verse 40-42] or [verse 42-45]
        for m in re.finditer(r'\[(?:verse|Verse)\s+(\d+)-(\d+)\]', text, re.IGNORECASE):
            if int(m.group(1)) <= vi <= int(m.group(2)):
                return True
        # Comma-separated: [Verse 17,28,42]
        for m in re.finditer(r'\[(?:verse|Verse)\s+([\d,\s]+)\]', text, re.IGNORECASE):
            nums = [n.strip() for n in m.group(1).split(',')]
            if vn in nums:
                return True
        return False
    
    def _topic_matches(text, heading):
        """Check if bullet text is about the same topic as the verse heading."""
        if not heading:
            return False
        # Extract key words from heading (remove common words)
        skip = {'of', 'and', 'the', 'its', 'in', 'a', 'an', 'for', 'with', 'to', 'on'}
        keywords = [w.lower() for w in re.findall(r'[A-Za-z]+', heading) if len(w) > 2 and w.lower() not in skip]
        if not keywords:
            return False
        text_lower = text.lower()
        # At least 2 keyword matches for topic relevance
        matches = sum(1 for kw in keywords if kw in text_lower)
        return matches >= 2
    
    def _find_relevant_bullets(section_text, heading=None):
        """Find bullet points referencing this verse in a section."""
        results = []
        # Split into bullet points (lines starting with *)
        bullets = re.split(r'\n\s*\*\s+', section_text)
        for bullet in bullets:
            bullet = bullet.strip()
            if not bullet:
                continue
            matched = _verse_ref_matches(bullet, vn)
            if not matched and heading:
                matched = _topic_matches(bullet, heading)
            if matched:
                cleaned = _clean_wiki_text(bullet)
                # Remove verse reference markers
                cleaned = re.sub(r'\[(?:verse|Verse)\s+[\d,\s-]+\]', '', cleaned, flags=re.IGNORECASE).strip()
                if cleaned and len(cleaned) > 20:
                    results.append(cleaned)
        return results
    
    if tattva_match:
        start = tattva_match.end()
        end = vidhi_match.start() if vidhi_match else len(content)
        tattva_section = content[start:end]
        tattva = _find_relevant_bullets(tattva_section, section_heading)
    
    if vidhi_match:
        vidhi_section = content[vidhi_match.end():]
        vidhi = _find_relevant_bullets(vidhi_section, section_heading)
        
        # Also search for paragraph-level content referencing this verse
        paragraphs = vidhi_section.split('\n\n')
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if _verse_ref_matches(para, vn):
                cleaned = _clean_wiki_text(para)
                cleaned = re.sub(r'\[(?:verse|Verse)\s+[\d,\s-]+\]', '', cleaned, flags=re.IGNORECASE).strip()
                cleaned = re.sub(r'={2,}[^=]+=+', '', cleaned).strip()
                if cleaned and len(cleaned) > 30 and cleaned not in vidhi:
                    vidhi.append(cleaned)
    
    return tattva, vidhi

def fetch_charaka_verse(sthana, chapter_num, verse_num):
    """Main function to fetch a verse from Charaka Samhita with deep research."""
    sthana_pages = CHARAKA_PAGE_TITLES.get(sthana)
    if not sthana_pages:
        return {"error": f"Unknown sthana: {sthana}"}
    
    page_title = sthana_pages.get(chapter_num)
    if not page_title:
        return {"error": f"Chapter {chapter_num} not found in {sthana}"}
    
    content = _fetch_wiki_page(page_title)
    if not content:
        return {"error": f"Could not fetch wiki page: {page_title}"}
    
    sanskrit, translation = _extract_verse(content, verse_num)
    heading = _get_section_heading(content, verse_num)
    tattva, vidhi = _extract_vimarsha(content, verse_num, section_heading=heading)
    
    if not sanskrit:
        return {"error": f"Verse {verse_num} not found in {page_title}"}
    
    result = {
        "sthana": sthana,
        "chapter": chapter_num,
        "chapter_title": page_title,
        "verse": verse_num,
        "sanskrit": sanskrit,
        "translation": translation or "Translation not available for this verse.",
        "section_heading": heading or "",
        "tattva_vimarsha": tattva,
        "vidhi_vimarsha": vidhi,
        "source": "carakasamhitaonline.com"
    }
    return result


class RecitationHandler(BaseHTTPRequestHandler):
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
        if parsed.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
            return
        elif parsed.path == "/fetch_verse":
            params = urllib.parse.parse_qs(parsed.query)
            sthana = params.get("sthana", [""])[0].strip()
            chapter = params.get("chapter", [""])[0].strip()
            verse = params.get("verse", [""])[0].strip()
            
            if not sthana or not chapter or not verse:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "sthana, chapter, and verse parameters required"}).encode("utf-8"))
                return
            
            try:
                result = fetch_charaka_verse(sthana, int(chapter), int(verse))
                resp_json = json.dumps(result, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(resp_json)))
                self.end_headers()
                self.wfile.write(resp_json)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return
        elif parsed.path == "/recite":
            params = urllib.parse.parse_qs(parsed.query)
            text = params.get("text", [""])[0].strip()
            meter = params.get("meter", ["anushtubh"])[0].strip()
            seed = int(params.get("seed", [42])[0])
            speed = float(params.get("speed", [0.90])[0])
            
            if not text:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Error: text parameter is required")
                return
                
            try:
                # Render the verse to raw floating point numpy array
                audio_data = render_verse(text, meter=meter, seed=seed, speed=speed)
                
                # Write to in-memory bytes as a WAV
                import io
                wav_io = io.BytesIO()
                sf.write(wav_io, audio_data, SR, format="WAV")
                wav_bytes = wav_io.getvalue()
                
                self.send_response(200)
                self.send_header("Content-Type", "audio/wav")
                self.send_header("Content-Length", str(len(wav_bytes)))
                self.end_headers()
                self.wfile.write(wav_bytes)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error rendering: {str(e)}".encode())
        else:
            self.send_response(404)
            self.end_headers()

def run(port=5001):
    init_models()
    server_address = ('', port)
    httpd = HTTPServer(server_address, RecitationHandler)
    print(f"[server] Running Sanskrit Chanting API Server on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    print("[server] Shutting down...")

if __name__ == "__main__":
    run()
