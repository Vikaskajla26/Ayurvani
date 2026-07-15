"""Vagdhenu Sanskrit/chant TTS demo (Hugging Face ZeroGPU Space).

Loads the released DiT voice + BigVGAN vocoder (from prathoshap/vagdhenu) and the reference bank
shipped in this repo, then synthesizes metered chant from a verse in any Indic script.

REST API for Ayurvani integration (no PC required):
    GET /recite?text=...&meter=anushtubh&seed=42  -> audio/wav
    GET /meters                                    -> JSON list of available meters
    GET /preview?text=...                          -> JSON G2P analysis
    GET /health                                    -> 200 OK

Local run (with a real GPU + the weights downloaded):
    VAGDHENU_HF=prathoshap/vagdhenu python demo/app.py
"""
import io, os, sys, json, re

import gradio as gr
import spaces
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = next((p for p in (os.path.join(os.path.dirname(HERE), "src"), os.path.join(HERE, "src"))
            if os.path.exists(os.path.join(p, "render_core.py"))), os.path.join(HERE, "src"))
sys.path.insert(0, SRC)

from huggingface_hub import hf_hub_download
import limits


def _ensure_bigvgan():
    try:
        import bigvgan; return
    except ImportError:
        pass
    import subprocess
    dst = os.path.join(HERE, "BigVGAN")
    if not os.path.isdir(os.path.join(dst, ".git")):
        subprocess.run(["git", "clone", "--depth", "1",
                        "https://github.com/NVIDIA/BigVGAN.git", dst], check=True)
    if dst not in sys.path:
        sys.path.insert(0, dst)

_ensure_bigvgan()

WEIGHTS_REPO = os.environ.get("VAGDHENU_HF", "prathoshap/vagdhenu")
VOICE_FILE   = os.environ.get("VAGDHENU_VOICE", "voice_steer_ema_2026-06-17.pt")
VOC_FILE     = os.environ.get("VAGDHENU_VOC",   "voc_bigvgan_EMA_2026-06-11.pth")
VOCAB_FILE   = os.environ.get("VAGDHENU_VOCAB", "vocab.txt")
BANK_PATH    = os.path.join(SRC, "reference_bank", "bank.json")
BUNDLED_VOCAB = os.path.join(SRC, "reference_bank", VOCAB_FILE)

AUTO = "__auto__"

_bank = json.load(open(BANK_PATH, encoding="utf-8"))
METERS = [k for k, v in _bank.items() if not k.startswith("_") and isinstance(v, dict) and "wav" in v]
_PREFERRED = [m for m in ("anustubh", "upajati", "shardulavikridita", "vasantatilaka") if m in METERS]
METERS = _PREFERRED + [m for m in METERS if m not in _PREFERRED]
_FALLBACK_DISPLAY = "vasantatilaka" if "vasantatilaka" in METERS else METERS[0] if METERS else "anushtubh"

_ALIAS = {}
for _k, _v in _bank.items():
    if _k.startswith("_") or not isinstance(_v, dict) or "wav" not in _v:
        continue
    _ALIAS[_k.lower()] = _k
    _ALIAS[_v["wav"].replace(".wav", "").lower()] = _k

METER_CHOICES = [("Auto-detect (recommended)", AUTO)] + [(m, m) for m in METERS]

from indic_transliteration import sanscript as _S

def _tx(deva, scheme):
    return deva if scheme == _S.DEVANAGARI else _S.transliterate(deva, _S.DEVANAGARI, scheme)

_SAMPLES = [
    ("Vasudeva-sutam (Devanagari)",
     "vasudEvasutaM dEvaM kaMsacANUramardanam | dEvakIparamAnandaM kRRiSNaM vandE jagadgurum ||", _S.DEVANAGARI, AUTO),
    ("Shuklambaradharam (Devanagari)",
     "shuklaambharadharam viShNuM shashivarNaM chaturbhujam | prasannavadanaM dhyAyet sarvavighNopashAntaye ||", _S.DEVANAGARI, AUTO),
]
try:
    _SAMPLES = [
        ("Krsna - Vasudevasutam", "वसुदेवसुतं देवं कंसचाणूरमर्दनम् ।\nदेवकीपरमानन्दं कृष्णं वन्दे जगद्गुरुम् ॥", _S.DEVANAGARI, AUTO),
        ("Visnu - Shuklambaradharam", "शुक्लाम्बरधरं विष्णुं शशिवर्णं चतुर्भुजम् ।\nप्रसन्नवदनं ध्यायेत् सर्वविघ्नोपशान्तये ॥", _S.DEVANAGARI, AUTO),
        ("Ganesa - Vakratunda", "वक्रतुण्ड महाकाय सूर्यकोटिसमप्रभ ।\nनिर्विघ्नं कुरु मे देव सर्वकार्येषु सर्वदा ॥", _S.DEVANAGARI, AUTO),
        ("Guru - Gururbrahma (Kannada)", "गुरुर्ब्रह्मा गुरुर्विष्णुः गुरुर्देवो महेश्वरः ।\nगुरुः साक्षात् परं ब्रह्म तस्मै श्रीगुरवे नमः ॥", _S.KANNADA, AUTO),
    ]
except Exception:
    pass

EXAMPLES = [[_tx(d, sc), m, 60] for _, d, sc, m in _SAMPLES]
EXAMPLE_LABELS = [n for n, _, _, _ in _SAMPLES]
EX_DEFAULT = EXAMPLES[0][0]

_RENDERER = None


def _ensure_assets():
    voice = hf_hub_download(WEIGHTS_REPO, VOICE_FILE)
    voc   = hf_hub_download(WEIGHTS_REPO, VOC_FILE)
    vocab = BUNDLED_VOCAB if os.path.exists(BUNDLED_VOCAB) else None
    if vocab is None:
        try: vocab = hf_hub_download(WEIGHTS_REPO, VOCAB_FILE)
        except Exception: vocab = None
    return voice, voc, vocab


def _get_renderer():
    global _RENDERER
    if _RENDERER is None:
        from render_core import Renderer
        voice, voc, vocab = _ensure_assets()
        _RENDERER = Renderer(voice, voc, BANK_PATH, device="cuda", vocab_file=vocab)
    return _RENDERER


def _resolve_display(name):
    k = _ALIAS.get((name or "").lower())
    return (k, True) if k else (_FALLBACK_DISPLAY, False)


@spaces.GPU(duration=120)
def _render(text, used, seed):
    return _get_renderer().render_one(text, used, seed=int(seed))


def synthesize(text, meter_choice, seed, request: gr.Request):
    text = (text or "").strip()
    if not text:
        raise gr.Error("Please paste a verse first")
    msg = limits.validate_one_shloka(text)
    if msg:
        raise gr.Error(msg)
    if not limits.check_and_count(limits.client_ip(request)):
        raise gr.Error(f"Daily limit of {limits.DAILY_LIMIT} chants reached. Come back tomorrow.")
    from render_core import detect_meter_key
    if meter_choice == AUTO or not meter_choice:
        used, recognized = _resolve_display(detect_meter_key(text))
        status = f"Meter: **{used}**" + ("" if recognized else " (auto-fallback)")
    else:
        used, status = meter_choice, f"Meter: **{meter_choice}**"
    try:
        sr, audio = _render(text, used, seed)
    except Exception as e:
        raise gr.Error(f"Rendering failed: {e}")
    return (sr, audio), status


with gr.Blocks(title="Vagdhenu - Sanskrit chant") as demo:
    gr.Markdown("# Vagdhenu - Sanskrit Chant TTS\nPaste a Sanskrit verse, press **Chant it**.")
    with gr.Row():
        with gr.Column(scale=3):
            txt = gr.Textbox(label="Sanskrit verse", placeholder="Paste a verse in any Indian script...",
                             value=EX_DEFAULT, lines=4)
            with gr.Accordion("Advanced", open=False):
                meter = gr.Dropdown(METER_CHOICES, value=AUTO, label="Meter (chandas)")
                seed  = gr.Slider(0, 1000, value=60, step=1, label="Seed")
            btn = gr.Button("Chant it", variant="primary", size="lg")
        with gr.Column(scale=2):
            out    = gr.Audio(label="Chant", type="numpy", autoplay=False)
            status = gr.Markdown("")
    btn.click(synthesize, inputs=[txt, meter, seed], outputs=[out, status])
    gr.Examples(examples=EXAMPLES, example_labels=EXAMPLE_LABELS, inputs=[txt, meter, seed])
    gr.Markdown("*Developed by Prof. Prathosh, IISc Bengaluru. [prathoshap/vagdhenu](https://huggingface.co/prathoshap/vagdhenu)*")


# ─── REST API ────────────────────────────────────────────────────────────────────────────
# Mounted alongside the Gradio UI on the same port.
# Ayurvani calls: GET https://<space>.hf.space/recite?text=...&meter=anushtubh&seed=42

import soundfile as sf
from fastapi import FastAPI, Query
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

api = FastAPI(title="Vagdhenu REST API")
api.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "OPTIONS"], allow_headers=["*"])


@api.get("/health")
def health():
    return {"status": "ok", "engine": "vagdhenu"}


@api.get("/meters")
def get_meters():
    meter_list = [{"id": k, "sec_per_syll": v.get("sec_per_syll", 0.26)}
                  for k, v in _bank.items()
                  if not k.startswith("_") and isinstance(v, dict) and "wav" in v]
    return JSONResponse({"meters": meter_list})


@api.get("/preview")
def get_preview(text: str = Query(...)):
    import prep_text as PT
    try:
        padas = [p.strip() for p in re.split(r"[\n|\u0964]+", text) if p.strip()]
        padas = [p for p in padas if not re.match(r"^[\d\u0966-\u096f\s]+$", p)] or [text]
        pieces = [PT.model_text_sandhi(p, echo_final=True) for p in padas]
        slp_pieces = [PT.align_slp1(p) for p in padas]
        def _n(s):
            n=0; L=len(s)
            for i,c in enumerate(s):
                o=ord(c)
                if (0x0905<=o<=0x0914)or(0x0C85<=o<=0x0C94): n+=1
                elif (0x0915<=o<=0x0939)or(0x0C95<=o<=0x0CB9):
                    if(s[i+1]if i+1<L else"")not in("्","್"): n+=1
            return n
        return JSONResponse({"padas":padas,"kannada_routed":pieces,"slp1":slp_pieces,"n_syllables":[_n(x) for x in pieces]})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@spaces.GPU(duration=120)
def _render_wav(text: str, meter: str, seed: int) -> bytes:
    from render_core import detect_meter_key
    r = _get_renderer()
    bank_meter = _ALIAS.get(meter.lower(), meter) if meter and meter != AUTO else None
    if not bank_meter:
        bank_meter = _ALIAS.get(detect_meter_key(text).lower(), _FALLBACK_DISPLAY)
    sr, audio = r.render_one(text, bank_meter, seed=seed)
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV")
    return buf.getvalue()


@api.get("/recite")
def recite(text: str = Query(...), meter: str = Query("anushtubh"), seed: int = Query(42), speed: float = Query(0.90)):
    text = text.strip()
    if not text:
        return JSONResponse({"error": "text parameter is required"}, status_code=400)
    msg = limits.validate_one_shloka(text)
    if msg:
        return JSONResponse({"error": msg}, status_code=400)
    try:
        wav_bytes = _render_wav(text, meter, seed)
        return Response(content=wav_bytes, media_type="audio/wav",
                        headers={"Content-Disposition": "inline; filename=recitation.wav"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Mount Gradio app on the FastAPI root
app = gr.mount_gradio_app(api, demo, path="/gradio")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
