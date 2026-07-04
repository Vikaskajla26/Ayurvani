import os
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler

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
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            
            text = params.get("text", [""])[0].strip()
            meter = params.get("meter", ["anushtubh"])[0].strip()
            speed = params.get("speed", ["0.90"])[0].strip()
            seed = params.get("seed", ["42"])[0].strip()
            
            server_url = params.get("server_url", [""])[0].strip()
            if not server_url:
                server_url = os.environ.get("VAGDHENU_SERVER_URL", "https://major-jobs-design.loca.lt")
                
            if not text:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "text parameter is required"}).encode("utf-8"))
                return
                
            server_url = server_url.rstrip('/')
            target_url = f"{server_url}/recite?text={urllib.parse.quote(text)}&meter={meter}&seed={seed}&speed={speed}"
            
            req = urllib.request.Request(
                target_url,
                headers={"User-Agent": "Ayurvani/1.0"}
            )
            
            try:
                with urllib.request.urlopen(req, timeout=25) as resp:
                    audio_bytes = resp.read()
                    content_type = resp.headers.get("Content-Type", "audio/wav")
                    
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(audio_bytes)))
                    self.end_headers()
                    self.wfile.write(audio_bytes)
            except Exception as e:
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": f"Vagdhenu server connection failed at {server_url}. Make sure your local server is running: python vagdhenu/scripts/server.py"
                }).encode("utf-8"))
                
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        return
