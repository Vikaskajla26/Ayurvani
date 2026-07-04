import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler
from _auth import verify_token

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
            filename = self.headers.get('x-filename', 'file.bin')
            content_type = self.headers.get('content-type', 'application/octet-stream')

            # Authenticate admin before uploading files
            auth_token = self.headers.get('x-admin-token', '')
            if not verify_token(auth_token):
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Unauthorized"}).encode("utf-8"))
                return

            if content_length == 0:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Empty file payload"}).encode("utf-8"))
                return

            file_bytes = self.rfile.read(content_length)

            # Check if Vercel Blob is connected
            token = os.environ.get("BLOB_READ_WRITE_TOKEN")
            if not token:
                # Local fallback mock url for dev environment
                print("BLOB_READ_WRITE_TOKEN not set. Using local mock fallback.")
                # We can save temporarily or mock a url
                mock_url = f"https://ayurvani.vercel.app/bg/ezgif-frame-001.jpg" # dummy fallback
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "url": mock_url,
                    "downloadUrl": mock_url,
                    "pathname": filename,
                    "contentType": content_type
                }).encode("utf-8"))
                return

            # Make a PUT request to Vercel Blob REST API
            import urllib.error
            blob_url = f"https://blob.vercel-storage.com/{urllib.parse.quote(filename)}"
            
            req = urllib.request.Request(
                blob_url,
                data=file_bytes,
                headers={
                    "Authorization": f"Bearer {token}",
                    "x-api-version": "1",
                    "x-add-random-suffix": "1"
                },
                method="PUT"
            )

            try:
                with urllib.request.urlopen(req) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(res).encode("utf-8"))
            except urllib.error.HTTPError as he:
                err_content = he.read().decode("utf-8")
                self.send_response(he.code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Vercel Blob failed: {err_content}"}).encode("utf-8"))

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        return
