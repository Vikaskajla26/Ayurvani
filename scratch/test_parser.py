import sys
import os
import json
import re

# Add api to path
sys.path.append(os.path.abspath('api'))
from fetch_verse import _to_devanagari_num, _clean_wiki_text

def _from_devanagari_num(dn_str):
    res = ""
    for c in dn_str:
        val = ord(c) - 0x0966
        if 0 <= val <= 9:
            res += str(val)
        else:
            res += c
    try:
        return int(res)
    except:
        return 0

def parse_page_into_units(content):
    units = []
    start_tag = '<div class="mw-collapsible mw-collapsed">'
    end_tag = '</div></div>'
    
    positions = []
    idx = content.find(start_tag)
    while idx != -1:
        positions.append(idx)
        idx = content.find(start_tag, idx + 1)
        
    for i, pos in enumerate(positions):
        end_idx = content.find(end_tag, pos)
        if end_idx == -1:
            continue
            
        collapsible_content = content[pos:end_idx + len(end_tag)]
        
        next_pos = positions[i+1] if i + 1 < len(positions) else len(content)
        trailing_content = content[end_idx + len(end_tag):next_pos]
        
        heading_match = re.search(r'==+\s*[^=]+==+', trailing_content)
        if heading_match:
            trailing_content = trailing_content[:heading_match.start()]
            
        units.append({
            "collapsible": collapsible_content,
            "trailing": trailing_content,
            "full_text": collapsible_content + "\n" + trailing_content
        })
    return units

def find_unit_for_verse(units, verse_num):
    vn = str(verse_num)
    dn = _to_devanagari_num(verse_num)
    
    # 1. Search for exact markers
    for u in units:
        if f"||{dn}||" in u["full_text"] or f"||{vn}||" in u["full_text"]:
            return u
        if f"[{vn}]" in u["full_text"] or f"[{dn}]" in u["full_text"]:
            return u
            
    # 2. Search for ranges
    for u in units:
        # Match any range in Devanagari
        for m in re.finditer(r'([०-९]+)\s*-\s*([०-९]+)', u["full_text"]):
            start = _from_devanagari_num(m.group(1))
            end = _from_devanagari_num(m.group(2))
            if start <= verse_num <= end:
                return u
                
        # Match any range in English digits
        for m in re.finditer(r'(\d+)\s*-\s*(\d+)', u["full_text"]):
            start = int(m.group(1))
            end = int(m.group(2))
            if start <= verse_num <= end:
                return u
    return None

# Load cached page for Sutrasthana Chapter 1
cache_file = "api/cso_page_cache.json"
if os.path.exists(cache_file):
    with open(cache_file, "r", encoding="utf-8") as f:
        cache = json.load(f)
    content = cache.get("Deerghanjiviteeya Adhyaya")
    if content:
        units = parse_page_into_units(content)
        print(f"Parsed {len(units)} units successfully.")
        
        # Test for a few verses
        for v in [1, 2, 3, 4, 11, 42]:
            u = find_unit_for_verse(units, v)
            if u:
                print(f"Verse {v} FOUND!")
                # Print clean translation
                trans = _clean_wiki_text(u["trailing"]).strip()
                print(f"  Translation: {trans[:100]}...")
            else:
                print(f"Verse {v} NOT found!")
