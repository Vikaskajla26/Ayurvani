import os
import json
import re
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

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

HERE = os.path.dirname(os.path.abspath(__file__))
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
                # Save persistent cache (fail-safe for read-only environments)
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

def _from_devanagari_num(dn_str):
    """Convert Devanagari numeral digits to English digits."""
    res = ""
    for c in dn_str:
        val = ord(c) - 0x0966
        if 0 <= val <= 9:
            res += str(val)
        else:
            res += c
    return res

def _normalize_num_string(text):
    """Normalize string by converting all Devanagari digits to English digits."""
    chars = []
    for c in text:
        val = ord(c) - 0x0966
        if 0 <= val <= 9:
            chars.append(str(val))
        else:
            chars.append(c)
    return "".join(chars)

def parse_page_into_units(content):
    """Parse MediaWiki content into units corresponding to each collapsible block."""
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
    """Find the collapsible unit that contains or references this verse number."""
    vn = str(verse_num)
    dn = _to_devanagari_num(verse_num)
    
    # 1. Search for exact markers
    for u in units:
        if f"||{dn}||" in u["full_text"] or f"||{vn}||" in u["full_text"]:
            return u
        if f"[{vn}]" in u["full_text"] or f"[{dn}]" in u["full_text"]:
            return u
            
    # 2. Search for ranges like 11-15 or ११-१५
    for u in units:
        # Match any range in Devanagari
        for m in re.finditer(r'([०-९]+)\s*-\s*([०-९]+)', u["full_text"]):
            start = int(_from_devanagari_num(m.group(1)))
            end = int(_from_devanagari_num(m.group(2)))
            if start <= verse_num <= end:
                return u
                
        # Match any range in English digits
        for m in re.finditer(r'(\d+)\s*-\s*(\d+)', u["full_text"]):
            start = int(m.group(1))
            end = int(m.group(2))
            if start <= verse_num <= end:
                return u
    return None

def _extract_verse_fallback(content, verse_num):
    """Fallback extraction method using walk-backwards regex logic if units are not found."""
    dn = _to_devanagari_num(verse_num)
    vn = str(verse_num)
    marker = '||' + dn + '||'
    pos = content.find(marker)
    if pos == -1:
        return None, None
    
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
        
    after_marker = content[pos + len(marker):]
    close_pos = after_marker.find('</div></div>')
    translation = None
    if close_pos != -1:
        after_close = after_marker[close_pos + len('</div></div>'):]
        bracket_patterns = [r'\[' + vn + r'\]', r'\[\d+-' + vn + r'\]']
        best_match = None
        for pat in bracket_patterns:
            m = re.search(pat, after_close)
            if m and (best_match is None or m.start() < best_match.start()):
                best_match = m
        if best_match:
            raw_trans = after_close[:best_match.start()]
            raw_trans = _clean_wiki_text(raw_trans).strip()
            raw_trans = re.sub(r'={2,}[^=]+=+', '', raw_trans).strip()
            paragraphs = [p.strip() for p in raw_trans.split('\n\n') if p.strip()]
            if paragraphs:
                translation = paragraphs[-1]
    return sanskrit_text, translation

def _extract_verse(content, verse_num):
    """Extract Sanskrit verse text and English translation from raw wikitext by parsing collapsible units."""
    units = parse_page_into_units(content)
    unit = find_unit_for_verse(units, verse_num)
    if not unit:
        return _extract_verse_fallback(content, verse_num)
        
    # Extract Sanskrit
    coll = unit["collapsible"]
    inner_idx = coll.find('<div class="mw-collapsible-content">')
    if inner_idx != -1:
        sanskrit_raw = coll[len('<div class="mw-collapsible mw-collapsed">'):inner_idx]
    else:
        sanskrit_raw = coll
        
    sanskrit = _clean_wiki_text(sanskrit_raw).strip()
    
    # Extract Translation
    translation = _clean_wiki_text(unit["trailing"]).strip()
    
    return sanskrit, translation

def _get_section_heading(content, verse_num):
    """Get the section heading (====heading====) for a given verse."""
    units = parse_page_into_units(content)
    unit = find_unit_for_verse(units, verse_num)
    if unit:
        pos = content.find(unit["collapsible"])
        if pos != -1:
            before = content[:pos]
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
    
    tattva_match = re.search(r'==\s*Tattva Vimarsha[^=]*==', content)
    vidhi_match = re.search(r'==\s*Vidhi Vimarsha[^=]*==', content)
    
    def _verse_ref_matches(text, verse_num_str):
        """Check if text contains a verse reference that includes this verse number."""
        normalized_text = _normalize_num_string(text)
        vn = verse_num_str
        vi = int(vn)
        
        brackets = re.findall(r'\[([^\]]+)\]', normalized_text)
        for content_in_bracket in brackets:
            cleaned = re.sub(r'\bverses?\b', '', content_in_bracket, flags=re.IGNORECASE).strip().lower()
            
            # Check for range pattern: 11-15 or 11 to 15
            range_match = re.match(r'^(\d+)\s*(?:-|to)\s*(\d+)$', cleaned)
            if range_match:
                start = int(range_match.group(1))
                end = int(range_match.group(2))
                if start <= vi <= end:
                    return True
                    
            # Check for list or single match
            cleaned_nums = re.findall(r'\b\d+\b', cleaned)
            if vn in cleaned_nums:
                return True
                
        # Substring backup in brackets
        for content_in_bracket in brackets:
            if vn in content_in_bracket:
                return True
        return False
    
    def _topic_matches(text, heading):
        """Check if bullet text is about the same topic as the verse heading."""
        if not heading:
            return False
        skip = {'of', 'and', 'the', 'its', 'in', 'a', 'an', 'for', 'with', 'to', 'on'}
        keywords = [w.lower() for w in re.findall(r'[A-Za-z]+', heading) if len(w) > 2 and w.lower() not in skip]
        if not keywords:
            return False
        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw in text_lower)
        return matches >= 2
    
    def _find_relevant_bullets(section_text, heading=None):
        """Find bullet points referencing this verse in a section."""
        results = []
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


class handler(BaseHTTPRequestHandler):
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
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        return
