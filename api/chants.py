import os
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler
from _auth import verify_token

# Default chants to load on initial state
DEFAULT_CHANTS = [
  {"id":"c1", "cat":"Deity · Healing", "sanskrit":"ॐ धन्वन्तरये नमः", "translit":"Om Dhanvantaraye Namah", "meaning":"Bhagwan Dhanvantari (Ayurveda ke devta) ko naman — rog-nivaran aur swasthya ke liye.", "audioUrl":""},
  {"id":"c2", "cat":"Healing", "sanskrit":"ॐ त्र्यम्बकं यजामहे सुगन्धिं पुष्टिवर्धनम् । उर्वारुकमिव बन्धनान् मृत्योर्मुक्षीय मामृतात् ॥", "translit":"Om Tryambakam Yajamahe...", "meaning":"Mahamrityunjaya mantra — dirghayu, swasthya aur bhay se mukti ki prarthana.", "audioUrl":""},
  {"id":"c3", "cat":"Wisdom", "sanskrit":"ॐ भूर्भुवः स्वः तत्सवितुर्वरेण्यं भर्गो देवस्य धीमहि धियो यो नः प्रचोदयात्", "translit":"Om Bhur Bhuvah Swah...", "meaning":"Gayatri mantra — buddhi aur prakash ke liye prarthana, healing aur clarity dono mein sahayak.", "audioUrl":""},
  {"id":"c4", "cat":"Herb · Tulsi", "sanskrit":"महाप्रसाद जननी सर्व सौभाग्यवर्धिनी । आधि व्याधि हरा नित्यं तुलसी त्वं नमोऽस्तु ते ॥", "translit":"Mahaprasada Janani...", "meaning":"Tulsi (holy basil) ki stuti — rog aur mansik peeda ko dur karne wali maani jaati hai.", "audioUrl":""},
  {"id":"c5", "cat":"Shanti", "sanskrit":"ॐ सर्वे भवन्तु सुखिनः सर्वे सन्तु निरामयाः । सर्वे भद्राणि पश्यन्तु मा कश्चिद्duःखभाग्भवेत् ॥", "translit":"Om Sarve Bhavantu Sukhinah...", "meaning":"Sabke sukh, swasthya aur mangal ki saamuhik prarthana — Ayurveda ki bhawna ka saar.", "audioUrl":""},
  {"id":"c6", "cat":"Wisdom · Subhashita", "sanskrit":"आरोग्यं भास्करादिच्छेत् द्रविणं हुतवाहनात् ।", "translit":"Arogyam Bhaskaradicchhet...", "meaning":"Swasthya Surya se, dhan Agni se maango — ek prachin subhashita jo Ayurveda ke prakriti-sambandh ko darshata hai.", "audioUrl":""}
]

LOCAL_FILE = "chants.json"

class handler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        BaseHTTPRequestHandler.end_headers(self)

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        try:
            chants = self.load_chants()
            resp_json = json.dumps(chants, ensure_ascii=False).encode("utf-8")
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

    def do_POST(self):
        try:
            # Check admin token
            auth_token = self.headers.get('x-admin-token', '')
            if not verify_token(auth_token):
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Unauthorized"}).encode("utf-8"))
                return

            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            chants = json.loads(post_data.decode('utf-8'))

            self.save_chants(chants)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def load_chants(self):
        kv_url = os.environ.get("KV_REST_API_URL")
        kv_token = os.environ.get("KV_REST_API_TOKEN")
        if kv_url and kv_token:
            try:
                req = urllib.request.Request(
                    f"{kv_url}/get/ayurved_chants",
                    headers={"Authorization": f"Bearer {kv_token}"}
                )
                with urllib.request.urlopen(req) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    val = res.get("result")
                    if val:
                        return json.loads(val)
            except Exception as e:
                print("KV load failed:", e)

        if os.path.exists(LOCAL_FILE):
            try:
                with open(LOCAL_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print("Local file load failed:", e)

        return DEFAULT_CHANTS

    def save_chants(self, chants):
        kv_url = os.environ.get("KV_REST_API_URL")
        kv_token = os.environ.get("KV_REST_API_TOKEN")
        if kv_url and kv_token:
            try:
                # KV upstash SET REST command
                payload = json.dumps(["SET", "ayurved_chants", json.dumps(chants)])
                req = urllib.request.Request(
                    kv_url,
                    data=payload.encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {kv_token}",
                        "Content-Type": "application/json"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    if "error" in res:
                        raise Exception(res["error"])
                return
            except Exception as e:
                print("KV save failed:", e)

        try:
            with open(LOCAL_FILE, "w", encoding="utf-8") as f:
                json.dump(chants, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Local file save failed:", e)
