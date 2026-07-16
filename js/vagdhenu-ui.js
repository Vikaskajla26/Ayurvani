/**
 * vagdhenu-ui.js — Vāgdhenu Sanskrit TTS Frontend Module
 * Ayurvani · Sanskrit Recitation Studio
 *
 * Provides:
 *  - VagdhenuClient: fetch wrapper for /recite, /meters, /preview
 *  - SandhiPreview: Sandhi Analysis panel
 *  - RecitationStudio: full modal with controls and download
 *  - openRecitationStudio(text, meter): called from inline verse buttons
 *
 * Depends on: VAGDHENU_SERVER and getReciteUrl() defined in index.html
 */

/* ─────────────────────────────────────────────────────────
   METER CATALOGUE  (static fallback; dynamic from /meters)
───────────────────────────────────────────────────────── */
const METER_CATALOGUE = [
  { id: 'anushtubh',      label: 'Anushtubh (अनुष्टुभ्)',           syllables: 8  },
  { id: 'gayatri',        label: 'Gāyatrī (गायत्री)',               syllables: 8  },
  { id: 'trishtubh',      label: 'Trishtubh (त्रिष्टुभ्)',           syllables: 11 },
  { id: 'jagati',         label: 'Jagati (जगती)',                   syllables: 12 },
  { id: 'vasantatilaka',  label: 'Vasantatilaka (वसन्ततिलका)',     syllables: 14 },
  { id: 'malini',         label: 'Mālinī (मालिनी)',                 syllables: 15 },
  { id: 'mandakranta',    label: 'Mandākrāntā (मन्दाक्रान्ता)',    syllables: 17 },
  { id: 'sragdhara',      label: 'Sragdharā (स्रग्धरा)',            syllables: 21 },
  { id: 'shardulavikridita', label: 'Śārdūlavikrīḍita (शार्दूलविक्रीडित)', syllables: 19 },
  { id: 'shikharini',     label: 'Śikharinī (शिखरिणी)',             syllables: 17 },
  { id: 'jajati',         label: 'Yayāti/Jajati (ययाति)',           syllables: 12 },
  { id: 'upajati',        label: 'Upajāti (उपजाति)',                syllables: 11 },
  { id: 'rathoddhatah',   label: 'Rathoddhatā (रथोद्धता)',          syllables: 11 },
];

/* ─────────────────────────────────────────────────────────
   PRESET SHLOKAS
───────────────────────────────────────────────────────── */
const PRESETS = [
  {
    label: '🌞 Gāyatrī Mantra',
    meter: 'gayatri',
    text: 'ॐ भूर्भुवः स्वः तत्सवितुर्वरेण्यं भर्गो देवस्य धीमहि धियो यो नः प्रचोदयात्'
  },
  {
    label: '💫 Mahāmṛtyuñjaya',
    meter: 'anushtubh',
    text: 'ॐ त्र्यम्बकं यजामहे सुगन्धिं पुष्टिवर्धनम् ।\nउर्वारुकमिव बन्धनान् मृत्योर्मुक्षीय मामृतात् ॥'
  },
  {
    label: '🌿 Caraka Mangalacaranam',
    meter: 'anushtubh',
    text: 'यस्य त्रिस्कन्धमायुर्वेदं पुनरवतारयिषमाणस्य\nबुद्धिः प्रादुर्बभूव सात्म्यात् तमग्निवेशादिभिर्वक्ष्यामि ॥'
  },
  {
    label: '🏔️ Śāntiḥ Pātha',
    meter: 'trishtubh',
    text: 'ॐ सर्वे भवन्तु सुखिनः सर्वे सन्तु निरामयाः ।\nसर्वे भद्राणि पश्यन्तु मा कश्चिद्दुःखभाग्भवेत् ॥'
  },
  {
    label: '⚕️ Dhanvantari Śloka',
    meter: 'anushtubh',
    text: 'ॐ नमो भगवते वासुदेवाय धन्वन्तरये अमृतकलशहस्ताय ।\nसर्वामयविनाशाय त्रिलोकनाथाय श्रीमहाविष्णवे नमः ॥'
  },
];

/* ─────────────────────────────────────────────────────────
   URL HELPERS  (mirror logic from index.html)
───────────────────────────────────────────────────────── */
function _getBase() {
  const isLocal = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  return { isLocal, server: (typeof VAGDHENU_SERVER !== 'undefined' ? VAGDHENU_SERVER : 'http://localhost:5001') };
}

function _getApiUrl(endpoint, queryObj = {}) {
  const { isLocal, server } = _getBase();
  const q = new URLSearchParams(queryObj);
  if (!isLocal) q.set('server_url', server);
  const base = isLocal ? server : '';
  const api  = isLocal ? `/${endpoint}` : `/api/${endpoint}`;
  const qs   = q.toString();
  return base + api + (qs ? '?' + qs : '');
}

/* ─────────────────────────────────────────────────────────
   VAGDHENU CLIENT
───────────────────────────────────────────────────────── */
const VagdhenuClient = {
  async fetchMeters() {
    try {
      const res = await fetch(_getApiUrl('meters'), { headers: { 'Bypass-Tunnel-Reminder': 'true' } });
      if (!res.ok) return null;
      const data = await res.json();
      return data.meters || null;
    } catch { return null; }
  },

  async fetchPreview(text) {
    const res = await fetch(_getApiUrl('preview', { text }), { headers: { 'Bypass-Tunnel-Reminder': 'true' } });
    if (!res.ok) throw new Error('Preview failed: ' + res.status);
    return res.json();
  },

  async recite(text, meter = 'anushtubh', seed = 42, speed = 0.90, onProgress) {
    const { isLocal, server } = _getBase();

    // If running locally with a real server, use the local server
    if (isLocal) {
      onProgress?.('Sending to local Vāgdhenu server...');
      const url = _getApiUrl('recite', { text, meter, seed, speed });
      const res = await fetch(url, { headers: { 'Bypass-Tunnel-Reminder': 'true' }, signal: AbortSignal.timeout(90_000) });
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.error || 'Server error ' + res.status); }
      onProgress?.('Receiving audio...');
      const blob = await res.blob();
      if (blob.size < 1000) throw new Error('Empty audio received. Please try again.');
      return blob;
    }

    // Web Speech API — works in all browsers, instant, no server needed
    onProgress?.('Using browser speech synthesis...');
    return this._reciteWebSpeech(text, speed, onProgress);
  },

  _reciteWebSpeech(text, speed = 0.90, onProgress) {
    return new Promise((resolve, reject) => {
      if (!window.speechSynthesis) {
        reject(new Error('Browser speech synthesis not supported. Please use Chrome/Edge/Safari.'));
        return;
      }

      // Cancel any ongoing speech
      window.speechSynthesis.cancel();

      // Record audio using MediaRecorder
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const dest = new AudioCtx().createMediaStreamDestination();
      const recorder = new MediaRecorder(dest.stream);
      const chunks = [];

      // We use Web Audio API to capture but Web Speech doesn't pipe through it.
      // Instead: synthesize speech, capture via MediaRecorder from audio output.
      // Simpler: collect audio from speechSynthesis via the audio element trick.

      // Best approach for blob: use MediaRecorder on a silent stream + play in parallel,
      // then return the blob. But Web Speech output can't be captured to a blob in most browsers.
      // So: speak it live AND simultaneously record the system audio if possible,
      // otherwise just speak it and return a special sentinel blob.

      const utt = new SpeechSynthesisUtterance(text);
      utt.rate = parseFloat(speed) * 0.85;  // Sanskrit is slower
      utt.pitch = 0.9;
      utt.volume = 1.0;
      utt.lang = 'hi-IN';  // Devanagari / Hindi voice closest to Sanskrit

      // Pick best available voice for Sanskrit/Hindi
      const voices = window.speechSynthesis.getVoices();
      const preferred = voices.find(v => v.lang === 'hi-IN' && v.localService) ||
                        voices.find(v => v.lang === 'hi-IN') ||
                        voices.find(v => v.lang.startsWith('hi')) ||
                        voices.find(v => v.lang.startsWith('sa')) ||  // Sanskrit voice if available
                        null;
      if (preferred) utt.voice = preferred;

      onProgress?.('Speaking Sanskrit...');

      utt.onend = () => {
        // Return a tiny WAV blob as sentinel so caller knows speech completed
        const wav = _makeSilentWav(500);
        resolve(new Blob([wav], { type: 'audio/wav' }));
      };
      utt.onerror = (e) => {
        if (e.error === 'interrupted' || e.error === 'canceled') return;
        reject(new Error('Speech synthesis error: ' + e.error));
      };

      window.speechSynthesis.speak(utt);
    });
  },

  openHFSpace() {
    window.open('https://prathoshap-vagdhenu-demo.hf.space', '_blank');
  }

};

// Helper: create a minimal silent WAV blob
function _makeSilentWav(durationMs = 500) {
  const sr = 22050, channels = 1, bps = 16;
  const samples = Math.floor(sr * durationMs / 1000);
  const buf = new ArrayBuffer(44 + samples * 2);
  const v = new DataView(buf);
  const str = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  str(0, 'RIFF'); v.setUint32(4, 36 + samples * 2, true); str(8, 'WAVE');
  str(12, 'fmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true);
  v.setUint16(22, channels, true); v.setUint32(24, sr, true);
  v.setUint32(28, sr * channels * bps / 8, true); v.setUint16(32, channels * bps / 8, true);
  v.setUint16(34, bps, true); str(36, 'data'); v.setUint32(40, samples * 2, true);
  return buf;
}



/* ─────────────────────────────────────────────────────────
   SANDHI PREVIEW PANEL
───────────────────────────────────────────────────────── */
const SandhiPreview = {
  _el: null,

  mount(container) {
    this._el = container;
  },

  async refresh(text) {
    if (!this._el) return;
    this._el.innerHTML = `<div style="text-align:center;padding:12px;color:var(--ink-soft);font-size:0.8rem;">⏳ Analysing sandhi...</div>`;
    try {
      const data = await VagdhenuClient.fetchPreview(text);
      if (data.error) throw new Error(data.error);
      this._render(data);
    } catch (e) {
      this._el.innerHTML = `<div style="color:var(--copper);font-size:0.8rem;padding:8px;">Sandhi preview unavailable (server offline?)</div>`;
    }
  },

  _render(data) {
    const rows = (data.padas || []).map((pada, i) => `
      <div style="margin-bottom:12px;padding:10px 14px;background:rgba(255,255,255,0.03);border-radius:8px;border-left:3px solid var(--gold);">
        <div style="font-family:'Tiro Devanagari Hindi',serif;font-size:1.05rem;color:var(--gold-light);margin-bottom:4px;">${pada}</div>
        <div style="font-size:0.72rem;color:var(--ink-soft);letter-spacing:0.04em;text-transform:uppercase;margin-bottom:3px;">
          Sandhi-Processed (Devanagari):
        </div>
        <div style="font-family:'Tiro Devanagari Hindi',serif;font-size:1rem;color:var(--sage);word-break:break-all;margin-bottom:4px;">${data.devanagari_routed?.[i] || ''}</div>
        <div style="margin-top:4px;font-size:0.72rem;color:var(--ink-soft);">
          SLP1: <span style="font-family:monospace;color:var(--copper);">${data.slp1?.[i] || ''}</span>
          &nbsp;·&nbsp; Syllables: <strong style="color:var(--gold);">${data.n_syllables?.[i] || '?'}</strong>
        </div>
      </div>`).join('');
    this._el.innerHTML = rows || '<div style="color:var(--ink-soft);font-size:0.8rem;">No padas found.</div>';
  }
};

/* ─────────────────────────────────────────────────────────
   RECITATION STUDIO MODAL
───────────────────────────────────────────────────────── */
let _studioOpen = false;
let _studioAudio = null;
let _studioBlob  = null;

function _buildStudioHTML() {
  const meterOptions = METER_CATALOGUE.map(m =>
    `<option value="${m.id}">${m.label}</option>`).join('');
  const presetBtns = PRESETS.map(p =>
    `<button class="vag-preset-btn" onclick="window._vagPreset(${JSON.stringify(p.label)},${JSON.stringify(p.text)},${JSON.stringify(p.meter)})">${p.label}</button>`
  ).join('');

  return `
<div id="vagStudio" style="
  position:fixed; inset:0; z-index:4000;
  display:flex; align-items:center; justify-content:center;
  background:rgba(8,14,10,0.82); backdrop-filter:blur(14px);
  animation: vagFadeIn 0.3s ease;
">
<div style="
  background:linear-gradient(160deg, #1a3028 0%, #0e1f16 100%);
  border:1.5px solid rgba(228,201,124,0.22);
  border-radius:24px; width:min(740px,96vw); max-height:92vh;
  overflow-y:auto; padding:0; position:relative;
  box-shadow: 0 32px 80px rgba(0,0,0,0.7), 0 0 0 1px rgba(228,201,124,0.06);
">

  <!-- Header -->
  <div style="
    background:linear-gradient(90deg, rgba(228,201,124,0.12), rgba(193,99,59,0.08));
    border-bottom:1px solid rgba(228,201,124,0.15);
    padding:22px 28px 18px; display:flex; align-items:center; justify-content:space-between;
    border-radius:24px 24px 0 0;
  ">
    <div>
      <div style="display:flex;align-items:center;gap:10px;">
        <span style="font-size:1.6rem;">🕉</span>
        <div>
          <div style="font-family:'Cormorant Garamond',serif;font-size:1.45rem;color:#f3eedf;font-weight:600;letter-spacing:0.02em;">
            Sanskrit Recitation Studio
          </div>
          <div style="font-size:0.72rem;color:var(--sage);letter-spacing:0.12em;text-transform:uppercase;margin-top:1px;">
            Powered by Vāgdhenu AI · MOS 4.6
          </div>
        </div>
      </div>
    </div>
    <button onclick="window.closeRecitationStudio()" style="
      background:rgba(255,255,255,0.07); border:1px solid rgba(255,255,255,0.1);
      color:var(--sage); width:36px; height:36px; border-radius:50%;
      font-size:1.2rem; cursor:pointer; display:flex; align-items:center; justify-content:center;
      transition:background 0.2s;
    " onmouseover="this.style.background='rgba(255,255,255,0.15)'"
       onmouseout="this.style.background='rgba(255,255,255,0.07)'" title="Close">×</button>
  </div>

  <div style="padding:24px 28px 28px; display:flex; flex-direction:column; gap:20px;">

    <!-- Preset quick-fill row -->
    <div>
      <div style="font-size:0.72rem;color:var(--ink-soft);letter-spacing:0.1em;text-transform:uppercase;margin-bottom:8px;">Quick Presets</div>
      <div id="vagPresetRow" style="display:flex;flex-wrap:wrap;gap:7px;">${presetBtns}</div>
    </div>

    <!-- Sanskrit text input -->
    <div>
      <label for="vagText" style="font-size:0.8rem;color:var(--ink-soft);letter-spacing:0.06em;text-transform:uppercase;display:block;margin-bottom:7px;">
        Sanskrit Text (Devanagari or any Indic script)
      </label>
      <textarea id="vagText" rows="4" placeholder="ॐ भूर्भुवः स्वः तत्सवितुर्वरेण्यम्..." style="
        width:100%; padding:14px 16px; border-radius:12px;
        border:1.5px solid rgba(228,201,124,0.2); outline:none;
        background:rgba(255,255,255,0.04); color:#f3eedf;
        font-family:'Tiro Devanagari Hindi',serif; font-size:1.15rem;
        line-height:1.65; resize:vertical; transition:border-color 0.25s;
        box-sizing:border-box;
      " oninput="window._vagTextChanged()"
         onfocus="this.style.borderColor='rgba(228,201,124,0.5)'"
         onblur="this.style.borderColor='rgba(228,201,124,0.2)'"></textarea>
    </div>

    <!-- Controls row -->
    <div style="display:grid;grid-template-columns:1fr 1fr auto;gap:14px;align-items:end;flex-wrap:wrap;">

      <!-- Meter -->
      <div>
        <label for="vagMeter" style="font-size:0.78rem;color:var(--ink-soft);letter-spacing:0.06em;text-transform:uppercase;display:block;margin-bottom:6px;">
          Chandas (Meter)
        </label>
        <select id="vagMeter" style="
          width:100%; padding:10px 14px; border-radius:10px;
          border:1.5px solid rgba(228,201,124,0.2); outline:none;
          background:#162a20; color:#f3eedf; font-size:0.9rem;
          transition:border-color 0.25s;
        " onfocus="this.style.borderColor='rgba(228,201,124,0.5)'"
           onblur="this.style.borderColor='rgba(228,201,124,0.2)'">${meterOptions}</select>
      </div>

      <!-- Speed -->
      <div>
        <label for="vagSpeed" style="font-size:0.78rem;color:var(--ink-soft);letter-spacing:0.06em;text-transform:uppercase;display:block;margin-bottom:6px;">
          Gati (Speed): <span id="vagSpeedLabel" style="color:var(--gold);">0.90×</span>
        </label>
        <input type="range" id="vagSpeed" min="0.70" max="1.10" step="0.05" value="0.90"
          oninput="document.getElementById('vagSpeedLabel').textContent = parseFloat(this.value).toFixed(2) + '×'"
          style="width:100%; accent-color:var(--gold);">
      </div>

      <!-- Seed -->
      <div>
        <label for="vagSeed" style="font-size:0.78rem;color:var(--ink-soft);letter-spacing:0.06em;text-transform:uppercase;display:block;margin-bottom:6px;">
          Seed
        </label>
        <input type="number" id="vagSeed" value="42" min="0" max="9999" style="
          width:80px; padding:9px 12px; border-radius:10px;
          border:1.5px solid rgba(228,201,124,0.2); outline:none;
          background:#162a20; color:#f3eedf; font-size:0.9rem;
          transition:border-color 0.25s;
        " onfocus="this.style.borderColor='rgba(228,201,124,0.5)'"
           onblur="this.style.borderColor='rgba(228,201,124,0.2)'">
      </div>
    </div>

    <!-- Recite button -->
    <button id="vagReciteBtn" onclick="window.vagRecite()" style="
      background:linear-gradient(135deg, #c1633b 0%, #a84e2a 100%);
      color:#fff; border:none; padding:15px 28px;
      border-radius:14px; font-size:1rem; font-weight:700; cursor:pointer;
      display:flex; align-items:center; justify-content:center; gap:10px;
      transition:transform 0.2s, box-shadow 0.2s;
      box-shadow: 0 6px 20px rgba(193,99,59,0.4);
      letter-spacing:0.03em;
    "
    onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 10px 28px rgba(193,99,59,0.55)'"
    onmouseout="this.style.transform='';this.style.boxShadow='0 6px 20px rgba(193,99,59,0.4)'">
      <span id="vagReciteIcon">🔊</span>
      <span id="vagReciteLabel">AI Recite</span>
    </button>

    <!-- Progress / Status -->
    <div id="vagProgress" style="display:none; text-align:center;">
      <div style="display:inline-flex;align-items:center;gap:10px;background:rgba(228,201,124,0.06);
           border:1px solid rgba(228,201,124,0.15);border-radius:10px;padding:10px 18px;">
        <div id="vagSpinner" style="
          width:18px;height:18px;border:2.5px solid rgba(228,201,124,0.25);
          border-top-color:var(--gold);border-radius:50%;
          animation:spin 0.8s linear infinite;
        "></div>
        <span id="vagStatusText" style="font-size:0.85rem;color:var(--sage);">Generating...</span>
      </div>
    </div>

    <!-- Audio Player -->
    <div id="vagPlayerWrap" style="display:none;">
      <div style="
        background:rgba(255,255,255,0.03); border:1px solid rgba(228,201,124,0.18);
        border-radius:16px; padding:18px 20px;
      ">
        <!-- Waveform bars -->
        <div id="vagWave" style="
          display:flex; align-items:center; gap:3px; height:36px;
          justify-content:center; margin-bottom:14px;
        ">
          ${Array.from({length: 18}, (_,i) => {
            const h = [8,14,20,28,22,16,32,18,24,36,20,28,14,30,22,10,26,16][i] || 16;
            return `<div class="vag-bar" style="width:3px;height:${h}px;background:rgba(228,201,124,0.5);border-radius:2px;transition:height 0.1s;"></div>`;
          }).join('')}
        </div>

        <audio id="vagAudio" controls style="width:100%;border-radius:8px;"></audio>

        <div style="display:flex;gap:10px;margin-top:12px;flex-wrap:wrap;">
          <button id="vagDownloadBtn" onclick="window.vagDownload()" style="
            flex:1; min-width:140px; padding:10px 16px; border-radius:10px;
            background:rgba(228,201,124,0.1); border:1.5px solid rgba(228,201,124,0.3);
            color:var(--gold-light); font-size:0.85rem; font-weight:600; cursor:pointer;
            transition:background 0.2s;
          "
          onmouseover="this.style.background='rgba(228,201,124,0.2)'"
          onmouseout="this.style.background='rgba(228,201,124,0.1)'">
            📥 Download WAV
          </button>
          <button onclick="window.vagRecite()" style="
            flex:1; min-width:140px; padding:10px 16px; border-radius:10px;
            background:rgba(193,99,59,0.12); border:1.5px solid rgba(193,99,59,0.3);
            color:var(--copper); font-size:0.85rem; font-weight:600; cursor:pointer;
            transition:background 0.2s;
          "
          onmouseover="this.style.background='rgba(193,99,59,0.25)'"
          onmouseout="this.style.background='rgba(193,99,59,0.12)'">
            🔄 Re-generate
          </button>
        </div>
      </div>
    </div>

    <!-- Sandhi Analysis Panel -->
    <details id="vagSandhiDetails" style="border:1px solid rgba(228,201,124,0.15);border-radius:12px;overflow:hidden;">
      <summary style="
        padding:12px 16px; cursor:pointer; font-size:0.82rem; font-weight:600;
        color:var(--gold); background:rgba(228,201,124,0.05);
        letter-spacing:0.04em; list-style:none; display:flex; align-items:center; gap:8px;
        user-select:none;
      ">
        🔬 Sandhi Vicheda Analysis
        <span style="font-size:0.7rem;color:var(--ink-soft);font-weight:400;margin-left:auto;">G2P · Visarga · Anusvāra</span>
      </summary>
      <div id="vagSandhiContent" style="padding:14px 16px;font-size:0.82rem;color:var(--sage);">
        Type text above to see sandhi analysis.
      </div>
    </details>

    <!-- Server settings shortcut -->
    <div style="text-align:center;padding-top:4px;border-top:1px solid rgba(255,255,255,0.06);">
      <button onclick="if(typeof openServerSettingsModal==='function')openServerSettingsModal();window.closeRecitationStudio()" style="
        background:none;border:none;color:var(--ink-soft);font-size:0.75rem;
        cursor:pointer;text-decoration:underline;text-underline-offset:3px;
      ">⚙️ Configure Vāgdhenu Server URL</button>
    </div>

  </div><!-- /inner -->
</div><!-- /modal -->
</div>`;
}

function _injectStyles() {
  if (document.getElementById('vagStyles')) return;
  const s = document.createElement('style');
  s.id = 'vagStyles';
  s.textContent = `
    @keyframes vagFadeIn { from { opacity:0; } to { opacity:1; } }
    .vag-preset-btn {
      padding: 5px 13px; border-radius: 20px; font-size: 0.77rem;
      background: rgba(228,201,124,0.08); border: 1px solid rgba(228,201,124,0.22);
      color: var(--gold-light); cursor: pointer; transition: background 0.2s, transform 0.15s;
      white-space: nowrap;
    }
    .vag-preset-btn:hover {
      background: rgba(228,201,124,0.2); transform: translateY(-1px);
    }
    #vagWave.playing .vag-bar {
      animation: vagBeat 0.8s ease-in-out infinite alternate;
    }
    #vagWave.playing .vag-bar:nth-child(2n)   { animation-delay: 0.1s; }
    #vagWave.playing .vag-bar:nth-child(3n)   { animation-delay: 0.2s; }
    #vagWave.playing .vag-bar:nth-child(5n)   { animation-delay: 0.35s; }
    @keyframes vagBeat {
      from { opacity: 0.4; transform: scaleY(0.4); }
      to   { opacity: 1;   transform: scaleY(1.5); }
    }
    #vagText:focus, #vagMeter:focus, #vagSeed:focus { box-shadow: 0 0 0 3px rgba(228,201,124,0.12); }
    #vagStudio details > summary::-webkit-details-marker { display:none; }
    #vagStudio details[open] > summary { background: rgba(228,201,124,0.08); }
  `;
  document.head.appendChild(s);
}

/* Public: open studio, pre-fill text & meter */
window.openRecitationStudio = function(text = '', meter = 'anushtubh') {
  if (_studioOpen) { window.closeRecitationStudio(); }
  _injectStyles();
  const div = document.createElement('div');
  div.id = 'vagStudioWrap';
  div.innerHTML = _buildStudioHTML();
  document.body.appendChild(div);
  _studioOpen = true;

  SandhiPreview.mount(document.getElementById('vagSandhiContent'));

  if (text) {
    document.getElementById('vagText').value = text;
    _vagTextChanged();
  }
  if (meter) {
    const sel = document.getElementById('vagMeter');
    if ([...sel.options].some(o => o.value === meter)) sel.value = meter;
  }

  // Try to load dynamic meter list
  VagdhenuClient.fetchMeters().then(meters => {
    if (!meters) return;
    const sel = document.getElementById('vagMeter');
    if (!sel) return;
    const cur = sel.value;
    const seen = new Set(METER_CATALOGUE.map(m => m.id));
    const extra = meters.filter(m => !seen.has(m.id));
    if (extra.length) {
      extra.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.id;
        opt.textContent = m.id.charAt(0).toUpperCase() + m.id.slice(1).replace(/_/g,' ');
        sel.appendChild(opt);
      });
    }
    if (cur) sel.value = cur;
  });
};

window.closeRecitationStudio = function() {
  const w = document.getElementById('vagStudioWrap');
  if (w) w.remove();
  if (_studioAudio) { _studioAudio.pause(); _studioAudio = null; }
  _studioBlob = null;
  _studioOpen = false;
};

/* Close on backdrop click */
document.addEventListener('click', e => {
  const studio = document.getElementById('vagStudio');
  if (studio && e.target === studio) window.closeRecitationStudio();
});

/* Preset button handler */
window._vagPreset = function(label, text, meter) {
  const ta = document.getElementById('vagText');
  const sel = document.getElementById('vagMeter');
  if (ta) ta.value = text;
  if (sel && meter) {
    if ([...sel.options].some(o => o.value === meter)) sel.value = meter;
  }
  _vagTextChanged();
};

/* Text changed — debounced sandhi preview */
let _sandhiDebounce = null;
window._vagTextChanged = function() {
  const text = (document.getElementById('vagText')?.value || '').trim();
  clearTimeout(_sandhiDebounce);
  if (!text) {
    const c = document.getElementById('vagSandhiContent');
    if (c) c.innerHTML = 'Type text above to see sandhi analysis.';
    return;
  }
  _sandhiDebounce = setTimeout(() => {
    SandhiPreview.refresh(text);
  }, 600);
};

/* Main recite action */
window.vagRecite = async function() {
  const text  = (document.getElementById('vagText')?.value || '').trim();
  const meter = document.getElementById('vagMeter')?.value || 'anushtubh';
  const speed = parseFloat(document.getElementById('vagSpeed')?.value || 0.90);
  const seed  = parseInt(document.getElementById('vagSeed')?.value || 42, 10);

  if (!text) {
    if (typeof showToast === 'function') showToast('⚠️ Please enter Sanskrit text.');
    return;
  }

  const btn    = document.getElementById('vagReciteBtn');
  const prog   = document.getElementById('vagProgress');
  const status = document.getElementById('vagStatusText');
  const wrap   = document.getElementById('vagPlayerWrap');
  const wave   = document.getElementById('vagWave');

  btn.disabled = true;
  document.getElementById('vagReciteLabel').textContent = 'Speaking...';
  prog.style.display = 'flex';
  if (wrap) wrap.style.display = 'none';
  if (_studioAudio) { _studioAudio.pause(); _studioAudio = null; }
  // Cancel any ongoing Web Speech
  if (window.speechSynthesis) window.speechSynthesis.cancel();

  try {
    const blob = await VagdhenuClient.recite(text, meter, seed, speed, msg => {
      if (status) status.textContent = msg;
    });

    _studioBlob = blob;

    // Check if this is a Web Speech result (silent sentinel blob < 5KB)
    // or a real server audio blob
    const isWebSpeech = blob.size < 5000;

    prog.style.display = 'none';

    if (isWebSpeech) {
      // Web Speech played live — show the wave animation briefly and a helpful note
      wave?.classList.add('playing');
      if (typeof showToast === 'function') showToast('🔊 Sanskrit recitation spoken! For AI neural audio, visit the Vāgdhenu Space.');
      // Show player wrap with note about premium AI audio
      const el = document.getElementById('vagAudio');
      if (el) el.removeAttribute('src');
      if (wrap) {
        wrap.style.display = 'block';
        // Replace download button text to indicate Web Speech mode
        const dlBtn = document.getElementById('vagDownloadBtn');
        if (dlBtn) { dlBtn.textContent = '🕉 Open Vāgdhenu AI for WAV'; dlBtn.onclick = () => VagdhenuClient.openHFSpace(); }
      }
      // Stop wave after speech ends (approximate)
      setTimeout(() => wave?.classList.remove('playing'), text.length * 80);
    } else {
      // Real server audio blob
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      _studioAudio = audio;
      const el = document.getElementById('vagAudio');
      if (el) {
        el.src = url;
        el.onplay  = () => wave?.classList.add('playing');
        el.onpause = () => wave?.classList.remove('playing');
        el.onended = () => wave?.classList.remove('playing');
      }
      if (wrap) wrap.style.display = 'block';
      if (typeof showToast === 'function') showToast('🎵 Vāgdhenu recitation ready!');
      el?.play().catch(() => {});
    }

  } catch (err) {
    prog.style.display = 'none';
    if (typeof showToast === 'function') showToast('❌ Recitation failed: ' + err.message);
    console.error('[VagdhenuStudio] recite error:', err);
  } finally {
    btn.disabled = false;
    document.getElementById('vagReciteLabel').textContent = 'AI Recite';
  }
};

/* Download */
window.vagDownload = function() {
  if (!_studioBlob) return;
  const a = document.createElement('a');
  a.href = URL.createObjectURL(_studioBlob);
  a.download = `ayurvani-recitation-${Date.now()}.wav`;
  a.click();
  if (typeof showToast === 'function') showToast('📥 WAV file downloaded!');
};

/* Expose for Charaka verse inline buttons */
window.openRecitationStudioForVerse = function(text, meter) {
  window.openRecitationStudio(text, meter || 'anushtubh');
};

console.log('[vagdhenu-ui] Vāgdhenu Recitation Studio loaded.');
