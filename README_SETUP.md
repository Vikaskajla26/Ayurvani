# Paste-a-Shloka Search — Setup Instructions

## Files here
- `api/fetch_verse.py` — your existing file, with the HTTPS + /tmp cache fixes from before (replace your copy)
- `api/match_shloka.py` — NEW. The fuzzy-matching endpoint.
- `api/build_index.py` — NEW. Run this once (and whenever you want to refresh) to build the searchable verse index.
- `api/index_data/charaka_verse_index.json` — a SMALL DEMO index (16 verses from 2 chapters only — Sharira Sthana ch.1 and Vimana Sthana ch.8) so you can test the feature immediately.
- `index.html` — your existing file, with the new "Paste Your Shloka" search box wired in.

## To go live with the FULL Charaka Samhita (all 120 chapters)
The demo index only proves the pipeline works — it does NOT cover the whole text.
I couldn't build the full index myself because my sandbox can't reach
carakasamhitaonline.com (network allowlist). You need to run this from an
environment with normal internet access (your own machine, or a GitHub Action):

```bash
cd api
python3 build_index.py
```

This fetches all ~120 chapters (politely, with a small delay between requests)
and writes the real `index_data/charaka_verse_index.json` (a few thousand verses).
Commit that file to your repo and redeploy — no code changes needed, `match_shloka.py`
just loads whatever JSON is there.

## How it works
1. Visitor pastes a shloka (full or partial) into the new box.
2. Frontend calls `/api/match_shloka?text=...`
3. That endpoint fuzzy-matches (difflib ratio on normalized Devanagari) against
   the prebuilt index and returns the top candidates with sthana/chapter/verse + score.
4. The frontend auto-loads the best match's full verse + translation + tika using
   your existing `findCarakaReference()` pipeline (reused, not duplicated).

## Known limitations (by design, for this first version)
- Devanagari input only matches well right now (Latin/IAST-pasted input uses a
  much looser fallback comparison — worth improving later if people paste transliterated text).
- Only Charaka Samhita is covered — Sushruta Samhita and Ashtanga Hridaya don't have
  an equivalent clean structured source (see earlier discussion); that's a separate,
  bigger effort.
- Matching is substring/character-similarity based, not semantic — a paraphrase won't
  match, but OCR errors, missing diacritics, or a partial quote will.
