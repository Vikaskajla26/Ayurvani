"""build_manifest.py — Ayurvani Samhita Corpus Manifest Builder

Scans data/corpus/processed/ for .wav files, validates each clip,
and writes / updates data/corpus/metadata/manifest.jsonl.

Usage:
    python data/corpus/scripts/build_manifest.py [--processed-dir PATH] [--out PATH]

Expected filename format:
    {treatise}_{sthana}_{chapter:02d}_{verse:03d}_{reciter_id}_{take}.wav
    e.g. charaka_su_01_001_prof_abc_t1.wav

For each clip the script emits a JSON record:
{
  "id":           "charaka_su_01_001",
  "treatise":     "charaka",
  "sthana":       "sutrasthana",
  "chapter":      1,
  "verse":        1,
  "reciter":      "prof_abc",
  "take":         "t1",
  "wav":          "processed/charaka_su_01_001_prof_abc_t1.wav",
  "duration_s":   12.4,
  "sample_rate":  24000,
  "peak_dbfs":    -6.2,
  "snr_db":       35.1,
  "status":       "ok",          // "ok" | "review_needed" | "rejected"
  "flags":        [],            // list of QC warning strings
  "devanagari":   "",            // filled manually or via lookup
  "iast":         "",
  "meter":        "",
  "session_date": ""             // YYYY-MM-DD, filled manually
}
"""

import argparse
import json
import os
import struct
import sys
import wave
from pathlib import Path

# ── QC thresholds ────────────────────────────────────────────────────────────
MIN_DURATION_S   = 2.0     # shorter clips are almost certainly errors
MAX_DURATION_S   = 60.0    # longer clips are probably unsegmented sessions
CLIP_PEAK_DBFS   = -0.5    # above this = clipping
MIN_SNR_DB       = 20.0    # below this = too noisy (requires room-tone reference)
TARGET_SR        = 24_000  # expected sample rate after preprocessing

STHANA_EXPAND = {
    "su": "sutrasthana",
    "ni": "nidanasthana",
    "vi": "vimanasthana",
    "sh": "sharirasthana",
    "in": "indriyasthana",
    "ch": "chikitsasthana",
    "ka": "kalpasthana",
    "si": "siddhisthana",
}

# ── WAV helpers ──────────────────────────────────────────────────────────────
def _read_wav_info(path: Path):
    """Return (n_frames, sample_rate, n_channels, sampwidth) without scipy."""
    with wave.open(str(path), "rb") as wf:
        return (
            wf.getnframes(),
            wf.getframerate(),
            wf.getnchannels(),
            wf.getsampwidth(),
        )


def _peak_dbfs(path: Path, n_frames: int, sampwidth: int, n_channels: int) -> float:
    """Compute peak dBFS from raw PCM without numpy."""
    import math
    with wave.open(str(path), "rb") as wf:
        raw = wf.readframes(n_frames)

    fmt = {1: "b", 2: "h", 4: "i"}.get(sampwidth, "h")
    n_samples = len(raw) // sampwidth
    samples = struct.unpack(f"<{n_samples}{fmt}", raw)
    max_val = max(abs(s) for s in samples) if samples else 1
    max_possible = (2 ** (sampwidth * 8 - 1))
    return 20 * math.log10(max(max_val / max_possible, 1e-9))


def _rms_dbfs(path: Path, n_frames: int, sampwidth: int) -> float:
    """Compute RMS dBFS."""
    import math
    with wave.open(str(path), "rb") as wf:
        raw = wf.readframes(n_frames)
    fmt = {1: "b", 2: "h", 4: "i"}.get(sampwidth, "h")
    n_samples = len(raw) // sampwidth
    if n_samples == 0:
        return -96.0
    samples = struct.unpack(f"<{n_samples}{fmt}", raw)
    rms = (sum(s * s for s in samples) / n_samples) ** 0.5
    max_possible = (2 ** (sampwidth * 8 - 1))
    return 20 * math.log10(max(rms / max_possible, 1e-9))


# ── Filename parser ──────────────────────────────────────────────────────────
def parse_filename(stem: str):
    """
    Parse stem like 'charaka_su_01_001_prof_abc_t1'.
    Returns a dict or None on parse failure.
    """
    parts = stem.split("_")
    if len(parts) < 5:
        return None
    treatise  = parts[0]
    sthana_code = parts[1]
    try:
        chapter = int(parts[2])
        verse   = int(parts[3])
    except ValueError:
        return None
    # reciter id may contain underscores; take ends with 't\d+'
    remaining = parts[4:]
    take = ""
    reciter_parts = []
    for p in remaining:
        if p.startswith("t") and p[1:].isdigit():
            take = p
        else:
            reciter_parts.append(p)
    reciter = "_".join(reciter_parts) if reciter_parts else "unknown"
    sthana  = STHANA_EXPAND.get(sthana_code.lower(), sthana_code)
    clip_id = f"{treatise}_{sthana_code}_{chapter:02d}_{verse:03d}"
    return {
        "id":       clip_id,
        "treatise": treatise,
        "sthana":   sthana,
        "chapter":  chapter,
        "verse":    verse,
        "reciter":  reciter,
        "take":     take or "t1",
    }


# ── Main ─────────────────────────────────────────────────────────────────────
def build_manifest(processed_dir: Path, out_path: Path, room_tone_rms: float = -50.0):
    wavs = sorted(processed_dir.glob("*.wav"))
    if not wavs:
        print(f"[manifest] No .wav files found in {processed_dir}")
        sys.exit(1)

    # Load existing manifest to preserve manually-filled fields
    existing: dict[str, dict] = {}
    if out_path.exists():
        with open(out_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    existing[rec["wav"]] = rec

    records = []
    ok = review = rejected = 0

    for wav_path in wavs:
        stem = wav_path.stem
        rel  = f"processed/{wav_path.name}"

        parsed = parse_filename(stem)
        if parsed is None:
            print(f"[SKIP] Cannot parse filename: {wav_path.name}")
            continue

        try:
            n_frames, sr, n_ch, sw = _read_wav_info(wav_path)
        except Exception as e:
            print(f"[ERROR] Cannot read {wav_path.name}: {e}")
            continue

        duration_s = n_frames / sr
        peak_dbfs  = _peak_dbfs(wav_path, n_frames, sw, n_ch)
        rms_dbfs   = _rms_dbfs(wav_path, n_frames, sw)
        snr_db     = rms_dbfs - room_tone_rms

        flags  = []
        status = "ok"

        if sr != TARGET_SR:
            flags.append(f"sample_rate_{sr}_expected_{TARGET_SR}")
            status = "review_needed"
        if duration_s < MIN_DURATION_S:
            flags.append(f"too_short_{duration_s:.1f}s")
            status = "rejected"
        if duration_s > MAX_DURATION_S:
            flags.append(f"too_long_{duration_s:.1f}s")
            status = "review_needed"
        if peak_dbfs > CLIP_PEAK_DBFS:
            flags.append(f"clipping_peak_{peak_dbfs:.1f}dBFS")
            status = "review_needed"
        if snr_db < MIN_SNR_DB:
            flags.append(f"low_snr_{snr_db:.1f}dB")
            status = "review_needed"

        if status == "ok":   ok += 1
        elif status == "review_needed": review += 1
        else: rejected += 1

        # Merge with existing record to preserve manually-filled fields
        base = existing.get(rel, {})
        record = {
            "id":           parsed["id"],
            "treatise":     parsed["treatise"],
            "sthana":       parsed["sthana"],
            "chapter":      parsed["chapter"],
            "verse":        parsed["verse"],
            "reciter":      parsed["reciter"],
            "take":         parsed["take"],
            "wav":          rel,
            "duration_s":   round(duration_s, 3),
            "sample_rate":  sr,
            "peak_dbfs":    round(peak_dbfs, 1),
            "snr_db":       round(snr_db, 1),
            "status":       status,
            "flags":        flags,
            # Manually-filled fields — preserve existing values
            "devanagari":   base.get("devanagari", ""),
            "iast":         base.get("iast", ""),
            "meter":        base.get("meter", ""),
            "session_date": base.get("session_date", ""),
        }
        records.append(record)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    total = len(records)
    total_h = sum(r["duration_s"] for r in records) / 3600
    print(
        f"\n[manifest] Written {total} records → {out_path}\n"
        f"  ✓ ok={ok}  ⚠ review={review}  ✗ rejected={rejected}\n"
        f"  Total audio: {total_h:.2f} h"
    )


def main():
    repo_root = Path(__file__).resolve().parents[3]
    default_processed = repo_root / "data" / "corpus" / "processed"
    default_out       = repo_root / "data" / "corpus" / "metadata" / "manifest.jsonl"

    ap = argparse.ArgumentParser(description="Build Ayurvani corpus manifest")
    ap.add_argument("--processed-dir", default=str(default_processed),
                    help="Directory containing processed 24kHz mono WAV clips")
    ap.add_argument("--out", default=str(default_out),
                    help="Output JSONL manifest path")
    ap.add_argument("--room-tone-rms", type=float, default=-50.0,
                    help="Room-tone RMS dBFS (from pre-session capture). Default -50.0")
    args = ap.parse_args()

    build_manifest(
        processed_dir=Path(args.processed_dir),
        out_path=Path(args.out),
        room_tone_rms=args.room_tone_rms,
    )


if __name__ == "__main__":
    main()
