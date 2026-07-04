import os
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler

# Default books to load on initial state
DEFAULT_BOOKS = [
  {"id":"b1", "titleHi":"चरक संहिता", "titleEn":"Charak Samhita", "author":"Acharya Charak · ~400 BCE", "cat":"Foundational text", "proff":"2nd Proff", "subject":"Charak Samhita", "pdfUrl":"", "desc":"Ayurveda ka sabse pramukh grantha, jisme internal medicine (Kaya Chikitsa), rog-nidaan aur chikitsa siddhant vistar se varnit hain."},
  {"id":"b2", "titleHi":"सुश्रुत संहिता", "titleEn":"Sushruta Samhita", "author":"Acharya Sushruta · ~600 BCE", "cat":"Surgery text", "proff":"3rd Proff", "subject":"", "pdfUrl":"", "desc":"Shalya chikitsa (surgery) par kendrit granth — plastic surgery jaisi ancient techniques ka varnan bhi ismein milta hai."},
  {"id":"b3", "titleHi":"अष्टांग हृदयम्", "titleEn":"Ashtanga Hridayam", "author":"Vagbhata · ~7th century CE", "cat":"Compilation", "proff":"1st Proff", "subject":"", "pdfUrl":"", "desc":"Charak aur Sushruta dono ke gyaan ko sankshep mein prastut karta hai — Ayurveda ke aath angon ka sarvangeen vivaran."},
  {"id":"b4", "titleHi":"भावप्रकाश", "titleEn":"Bhavaprakasha", "author":"Bhavamishra · 16th century CE", "cat":"Materia medica", "proff":"2nd Proff", "subject":"Dravyaguna", "pdfUrl":"", "desc":"Aushadhiyon (herbs, minerals) ka vistrit varnan — dravyaguna shastra ka mahatvapurn granth."},
  {"id":"b5", "titleHi":"माधव निदानम्", "titleEn":"Madhava Nidanam", "author":"Madhavakara · ~7th century CE", "cat":"Diagnosis text", "proff":"2nd Proff", "subject":"Roga Nidan", "pdfUrl":"", "desc":"Rog-nidaan (diagnosis) par kendrit — lakshan aur karan ke aadhar par rogon ka vargikaran."},
  {"id":"b6", "titleHi":"शारंगधर संहिता", "titleEn":"Sharangdhara Samhita", "author":"Sharangdhara · 13th century CE", "cat":"Pharmacology", "proff":"2nd Proff", "subject":"Rasashastra & Bhaishajya", "pdfUrl":"", "desc":"Aushadhi nirman vidhi (pharmaceutical processes) aur nadi-pariksha (pulse diagnosis) ka vivaran."},
  {"id":"b7", "titleHi":"भैषज्य रत्नावली", "titleEn":"Bhaishajya Ratnavali", "author":"Govinda Das Sen · 18th century CE", "cat":"Ayurvedic Pharmaceutics", "proff":"2nd Proff", "subject":"Rasashastra & Bhaishajya", "pdfUrl":"", "desc":"Bhaishajya Kalpana ka vistrit granth, jismein vibhinn rogon ke liye aushadhi nirmaan aur yogon ka varnan hai."}
]

LOCAL_FILE = "books.json"

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
            books = self.load_books()
            resp_json = json.dumps(books, ensure_ascii=False).encode("utf-8")
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
            if auth_token != "ayurvani_admin_secure_token_session_2026":
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Unauthorized"}).encode("utf-8"))
                return

            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            books = json.loads(post_data.decode('utf-8'))

            self.save_books(books)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def load_books(self):
        kv_url = os.environ.get("KV_REST_API_URL")
        kv_token = os.environ.get("KV_REST_API_TOKEN")
        if kv_url and kv_token:
            try:
                req = urllib.request.Request(
                    f"{kv_url}/get/ayurved_books",
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

        return DEFAULT_BOOKS

    def save_books(self, books):
        kv_url = os.environ.get("KV_REST_API_URL")
        kv_token = os.environ.get("KV_REST_API_TOKEN")
        if kv_url and kv_token:
            try:
                # KV upstash SET REST command
                payload = json.dumps(["SET", "ayurved_books", json.dumps(books)])
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
                json.dump(books, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Local file save failed:", e)
