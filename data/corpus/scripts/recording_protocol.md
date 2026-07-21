# Ayurvani Samhita Corpus — Recording Protocol
# For use with AIIA Goa professors / pandits / senior students

---

## Purpose

This protocol governs the recording sessions for the **Ayurvani Samhita Pronunciation Corpus** —
a dataset of classical Ayurvedic shloka recitations used to build a BAMS study tool.
It ensures consistent, ML-trainable audio across all sessions.

---

## Room & Equipment Setup

| Parameter | Target | Notes |
|---|---|---|
| Room | Small, carpeted, no echo | AC off during recording to eliminate hum |
| Microphone | Condenser mic (e.g. Blue Yeti, AKG P120) | Position 20–30 cm from reciter, slightly off-axis |
| Interface / Recorder | USB audio interface or Zoom H5/H6 | Record directly to WAV, do not use phone voice memo |
| Sample rate | **48 kHz, 24-bit stereo** | Will be downsampled to 24 kHz mono during preprocessing |
| Monitoring | Headphones for recordist only | Reciter should not monitor through headphones (affects prosody) |
| Pre-session | Run 30-second room tone capture | Used for noise floor estimation |

---

## Session Structure

### 1. Warm-Up (10 minutes)
- Reciter performs 2–3 familiar shlokas NOT in the target corpus
- Recordist checks levels: peak no higher than –6 dBFS, floor below –50 dBFS
- Adjust mic placement if needed

### 2. Recording Blocks (45 minutes on, 15 minutes off)
- Each block covers one adhyaya (chapter)
- Begin each shloka with a 1-second silence
- Reciter states the verse reference aloud before reciting:
  > "Charaka, Sutrasthana, adhyaya eka, shloka eka."
  *(This verbal tag aids segmentation and QC)*
- Reciter then recites the full shloka at normal pandit pace (not slow/instructional)
- One pause between each pada (hemistich) is acceptable
- **Error correction:** if the reciter makes a mistake, they pause 2 seconds, say "punaḥ",
  then repeat the entire shloka from the beginning. Do NOT edit mid-shloka.

### 3. Error / Ambiguity Log
- Recordist keeps a session log noting timestamps of errors, unusual pronunciations,
  or verses where the reciter was uncertain about pāṭha (textual variant)
- Flag uncertain verses — they require expert review before being used in training

---

## Chapter Priority Order

Record in this order across sessions. P0 (highest priority) must be complete before P1 begins.

### P0 — Charaka Sutrasthana Ch. 1–10 (~300 verses)
- Session 1: Ch. 1–3
- Session 2: Ch. 4–6
- Session 3: Ch. 7–10

### P0 — Charaka Nidanasthana Ch. 1–3 (~120 verses)
- Session 4: Full Nidanasthana P0 set

### P1 — Sushruta Sutrasthana Ch. 1–15 (~600 verses)
- Sessions 5–9 (one chapter range per session)

### P2 — Ashtanga Hridaya Sutrasthana Ch. 1–12 (~500 verses)
- Sessions 10–14

---

## Prosody Guidance for Reciters

- Recite in the **traditional pandit/āmnāya style** — not academic/slow-dictation style
- Preserve natural **mātrā** (syllable weight) durations: guru ≈ 2× laghu
- For **anushtubh** (most common): no melodic contour needed, flat recitation is correct
- For **trishtubh / jagati**: follow the traditional raga/swara if familiar, else flat
- Do **not** insert schwa vowels (अ) where the text has saṃhitā-form elision
- Maintain the same pace throughout a shloka — no slowing at the end

---

## File Naming Convention

Files are named by the recordist immediately after each session:

```
{treatise}_{sthana}_{chapter:02d}_{verse:03d}_{reciter_id}_{take}.wav
```

Examples:
```
charaka_su_01_001_prof_abc_t1.wav
charaka_ni_02_015_prof_abc_t1.wav
sushruta_su_05_003_pandit_xyz_t1.wav
```

`take` is `t1` for the first clean take (after any error retry).

---

## Quality Check (Post-Session)

Run `data/corpus/scripts/build_manifest.py` after each session to auto-validate:
- All expected verse files are present
- Duration is within 2–60 seconds per clip
- No clipping (peak > −0.5 dBFS flags the clip)
- SNR estimate (room tone vs. clip RMS) > 20 dB

Clips that fail QC are marked `status: review_needed` in the manifest — they are not
automatically excluded but must be manually reviewed before inclusion in training.
