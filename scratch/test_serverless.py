import sys
import os
sys.path.append(os.path.abspath('api'))
try:
    import fetch_verse
    print("Import successful!")
    res = fetch_verse.fetch_charaka_verse("Sutrasthana", 1, 42)
    print("Sanskrit:", res.get("sanskrit")[:100].replace('\n', ' ') + "...")
    print("Translation:", res.get("translation")[:100] + "...")
    print("Tattva Vimarsha count:", len(res.get("tattva_vimarsha", [])))
    print("Success!")
except Exception as e:
    print("Error during test:", e)
    import traceback
    traceback.print_exc()
