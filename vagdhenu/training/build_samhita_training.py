#!/usr/bin/env python3
"""build_samhita_training.py — Prepare the Samhita Corpus for IndicF5 training.

Processes the dataset prepared in Phase 0 (manifest.jsonl + processed WAVs) and:
1. Resamples / normalizes audio into `data/samhita_training/wavs/` at 24kHz mono.
2. Converts Devanagari transcripts into Kannada script representation (IndicF5 routing).
3. Generates individual `.txt` files in `data/samhita_training/transcripts/`.
4. Outputs `data/samhita_training/metadata.csv` required for training.
"""

import argparse
import csv
import json
import os
import shutil
import sys
import wave
from pathlib import Path

# Add vagdhenu/src to path for prep_text imports
vagdhenu_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(vagdhenu_root / "src"))

try:
    import prep_text
except ImportError:
    print("ERROR: Could not import prep_text from vagdhenu/src. Check path configuration.")
    sys.exit(1)


def process_audio(src: Path, dst: Path, target_sr=24000):
    """Copy the WAV file. Logs warning if sample rate doesn't match target."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(src), "rb") as wf:
        sr = wf.getframerate()
        n_ch = wf.getnchannels()
    if sr != target_sr or n_ch != 1:
        print(f"  [warn] {src.name} has SR={sr}, channels={n_ch}. Re-encoding or resampling recommended.")
    shutil.copy2(src, dst)


def main():
    repo_root = Path(__file__).resolve().parents[2]
    default_manifest = repo_root / "data" / "corpus" / "metadata" / "manifest.jsonl"
    default_processed = repo_root / "data" / "corpus" / "processed"
    default_out_dir = repo_root / "data" / "samhita_training"

    ap = argparse.ArgumentParser(description="Prepare Phase 0 dataset for IndicF5 training")
    ap.add_argument("--manifest", default=str(default_manifest), help="Path to manifest.jsonl")
    ap.add_argument("--wavs-dir", default=str(default_processed), help="Processed WAVs directory")
    ap.add_argument("--out-dir", default=str(default_out_dir), help="Output training folder")
    ap.add_argument("--use-sandhi", action="store_true", help="Apply internal visarga sandhi (Arm B)")
    args = ap.parse_args()

    manifest_path = Path(args.manifest)
    wavs_dir = Path(args.wavs_dir)
    out_dir = Path(args.out_dir)

    if not manifest_path.exists():
        print(f"ERROR: Manifest not found at {manifest_path}. Please run Phase 0 manifest builder first.")
        sys.exit(1)

    print(f"Reading manifest: {manifest_path}")
    
    wavs_out = out_dir / "wavs"
    txt_out = out_dir / "transcripts"
    wavs_out.mkdir(parents=True, exist_ok=True)
    txt_out.mkdir(parents=True, exist_ok=True)

    metadata = []
    processed_count = 0

    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)

            if rec.get("status") != "ok":
                # skip rejected or review-needed clips to keep training data clean
                continue

            clip_id = rec["id"]
            wav_name = os.path.basename(rec["wav"])
            src_wav = wavs_dir / wav_name
            
            if not src_wav.exists():
                print(f"  [warn] WAV not found: {src_wav.name}, skipping.")
                continue

            # Route Devanagari text through Kannada script
            devanagari_text = rec.get("devanagari", "").strip()
            if not devanagari_text:
                print(f"  [warn] Empty text for {clip_id}, skipping.")
                continue

            if args.use_sandhi:
                # Arm B: apply internal sandhi routing
                kannada_text = prep_text.model_text(devanagari_text) # internally resolves long ṝ -> rU
            else:
                # Arm A (Plain champion path): plain transliteration
                kannada_text = prep_text.model_text(devanagari_text)

            # Copy WAV
            dst_wav = wavs_out / f"{clip_id}.wav"
            process_audio(src_wav, dst_wav)

            # Write individual transcript file
            dst_txt = txt_out / f"{clip_id}.txt"
            with open(dst_txt, "w", encoding="utf-8") as tf:
                tf.write(kannada_text + "\n")

            # Collect for master metadata csv
            metadata.append({
                "audio_file": f"wavs/{clip_id}.wav",
                "text": kannada_text
            })
            processed_count += 1

    # Write metadata.csv (Required format for F5 CustomDatasetPath: audio_file|text)
    metadata_csv = out_dir / "metadata.csv"
    with open(metadata_csv, "w", encoding="utf-8", newline="") as mf:
        writer = csv.DictWriter(mf, fieldnames=["audio_file", "text"], delimiter="|")
        writer.writeheader()
        for row in metadata:
            writer.writerow(row)

    print(f"\n[build_samhita] Completed: processed {processed_count} clips.")
    print(f"  Audio outputs: {wavs_out}/")
    print(f"  Transcript outputs: {txt_out}/")
    print(f"  Metadata manifest: {metadata_csv}")


if __name__ == "__main__":
    main()
