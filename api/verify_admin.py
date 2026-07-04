import os
import json
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        BaseHTTPRequestHandler.end_headers(self)

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Empty request body"}).encode("utf-8"))
                return

            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            username = data.get("username", "").strip()
            password = data.get("password", "")
            
            # Secure admin credentials checking (Password stored in Vercel environment variables)
            correct_password = os.environ.get("ADMIN_PASSWORD", "AyurvaniSecure108#")
            
            if username == "admin" and password == correct_password:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                # Return success response with a mock secure token
                self.wfile.write(json.dumps({
                    "success": True,
                    "token": "ayurvani_admin_secure_token_session_2026",
                    "role": "ADMIN"
                }).encode("utf-8"))
            else:
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": "Invalid username or password"
                }).encode("utf-8"))
                
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        return
