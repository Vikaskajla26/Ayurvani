import os
import json
from http.server import BaseHTTPRequestHandler
import sys
sys.path.insert(0, os.path.dirname(__file__))
from _auth import create_token


class handler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        BaseHTTPRequestHandler.end_headers(self)

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def _json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._json(400, {"error": "Empty request body"})
                return

            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            username = data.get("username", "").strip()
            password = data.get("password", "")

            correct_username = os.environ.get("ADMIN_USERNAME", "admin")
            correct_password = os.environ.get("ADMIN_PASSWORD")

            # Fail closed: if no password is configured on the server, refuse login
            # rather than falling back to a hardcoded default.
            if not correct_password:
                self._json(500, {"error": "Admin login is not configured on the server yet"})
                return

            if username == correct_username and password == correct_password:
                try:
                    token = create_token(role="ADMIN")
                except RuntimeError:
                    self._json(500, {"error": "Admin login is not configured on the server yet"})
                    return
                self._json(200, {"success": True, "token": token, "role": "ADMIN"})
            else:
                self._json(401, {"success": False, "error": "Invalid username or password"})

        except Exception as e:
            self._json(500, {"error": str(e)})
        return
