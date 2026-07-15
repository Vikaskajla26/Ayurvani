import os
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler

# ── Permanent cloud endpoint (HuggingFace Space with ZeroGPU) ────────────────────────────
# This URL points to the Vagdhenu TTS Space on HuggingFace — always online, free GPU.
# Format: https://<hf-username>-vagdhenu.hf.space
# Set the VAGDHENU_HF_SPACE env variable in Vercel dashboard to override.
HF_SPACE_URL = os.environ.get(
    "VAGDHENU_HF_SPACE",
    os.environ.get("VAGDHENU_SERVER_URL", "")  # fallback: old env var
)

class handler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        BaseHTTPRequestHandler.end_headers(self)

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)

            text  = params.get("text",  [""])[0].strip()
            meter = params.get("meter", ["anushtubh"])[0].strip()
            speed = params.get("speed", ["0.90"])[0].strip()
            seed  = params.get("seed",  ["42"])[0].strip()

            # Priority: 1. explicit server_url param  2. HF Space env  3. fallback error
            server_url = params.get("server_url", [""])[0].strip() or HF_SPACE_URL

            if not text:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "text parameter is required"}).encode("utf-8"))
                return

            if not server_url:
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "Vagdhenu server not configured. Set VAGDHENU_HF_SPACE env variable in Vercel dashboard."
                }).encode("utf-8"))
                return

            server_url = server_url.rstrip("/")
            target_url = (
                f"{server_url}/recite"
                f"?text={urllib.parse.quote(text)}"
                f"&meter={urllib.parse.quote(meter)}"
                f"&seed={seed}&speed={speed}"
            )

            req = urllib.request.Request(
                target_url,
                headers={
                    "User-Agent": "Ayurvani/1.0",
                    "Bypass-Tunnel-Reminder": "true",
                }
            )

            try:
                # HF Space cold start can take 60s; allow 90s timeout
                with urllib.request.urlopen(req, timeout=90) as resp:
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
                    "error": (
                        f"Vagdhenu server unreachable at {server_url}. "
                        "The HuggingFace Space may be waking up — try again in 60 seconds."
                    )
                }).encode("utf-8"))

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        return
