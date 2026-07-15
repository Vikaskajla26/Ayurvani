import os, json, urllib.request, urllib.parse
from http.server import BaseHTTPRequestHandler

HF_SPACE_URL = os.environ.get("VAGDHENU_HF_SPACE", os.environ.get("VAGDHENU_SERVER_URL", ""))

class handler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        BaseHTTPRequestHandler.end_headers(self)
    def do_OPTIONS(self):
        self.send_response(200); self.end_headers()
    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            server_url = (params.get("server_url", [""])[0].strip() or HF_SPACE_URL).rstrip("/")
            if not server_url:
                self.send_response(503); self.send_header("Content-Type","application/json"); self.end_headers()
                self.wfile.write(json.dumps({"error":"VAGDHENU_HF_SPACE not configured"}).encode()); return
            req = urllib.request.Request(f"{server_url}/meters", headers={"User-Agent":"Ayurvani/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read()
                    self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
            except Exception as e:
                self.send_response(502); self.send_header("Content-Type","application/json"); self.end_headers()
                self.wfile.write(json.dumps({"error":str(e)}).encode())
        except Exception as e:
            self.send_response(500); self.send_header("Content-Type","application/json"); self.end_headers()
            self.wfile.write(json.dumps({"error":str(e)}).encode())
        return
