import os
import json
import time
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler

# Permanent cloud fallback Space (Official high-performance ZeroGPU space)
OFFICIAL_SPACE = "prathoshap/vagdhenu-demo"

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

            if not text:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "text parameter is required"}).encode("utf-8"))
                return

            # Read configured custom server URL or HF Space (e.g. personal space)
            server_url = params.get("server_url", [""])[0].strip() or os.environ.get("VAGDHENU_HF_SPACE", os.environ.get("VAGDHENU_SERVER_URL", ""))

            # 1. Try to query the direct REST server URL if it is a local server or custom URL
            is_local = server_url and any(x in server_url for x in ["localhost", "127.0.0.1", "loca.lt", "ngrok"])
            
            audio_bytes = None
            content_type = "audio/wav"

            if is_local:
                # Direct HTTP query to the local server
                try:
                    server_url = server_url.rstrip("/")
                    target_url = (
                        f"{server_url}/recite"
                        f"?text={urllib.parse.quote(text)}"
                        f"&meter={urllib.parse.quote(meter)}"
                        f"&seed={seed}&speed={speed}"
                    )
                    req = urllib.request.Request(
                        target_url,
                        headers={"User-Agent": "Ayurvani/1.0", "Bypass-Tunnel-Reminder": "true"}
                    )
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        audio_bytes = resp.read()
                        content_type = resp.headers.get("Content-Type", "audio/wav")
                except Exception as e:
                    print(f"Local server failed: {e}")

            # 2. Fall back to querying the Hugging Face Space (Gradio 5 Queue REST API)
            if not audio_bytes:
                # Decide which space to target
                target_space = OFFICIAL_SPACE
                if server_url and "hf.space" in server_url:
                    # extract space owner/name from personal hf.space URL if present
                    try:
                        domain = urllib.parse.urlparse(server_url).netloc or server_url.replace("https://", "").replace("http://", "")
                        parts = domain.split("-")
                        if len(parts) >= 2:
                            owner = parts[0]
                            name = "-".join(parts[1:]).split(".")[0].replace("vagdhenu", "vagdhenu")
                            target_space = f"{owner}/{name}"
                    except Exception:
                        pass

                # If targeting personal space but it's failed, fallback to official space
                try:
                    audio_bytes = self.query_hf_space(target_space, text, meter, seed, speed)
                except Exception as e:
                    if target_space != OFFICIAL_SPACE:
                        print(f"Personal space failed: {e}. Falling back to official space...")
                        try:
                            audio_bytes = self.query_hf_space(OFFICIAL_SPACE, text, meter, seed, speed)
                        except Exception as inner_e:
                            raise Exception(f"Official space query failed: {inner_e}")
                    else:
                        raise e

            if audio_bytes:
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(audio_bytes)))
                self.end_headers()
                self.wfile.write(audio_bytes)
            else:
                raise Exception("Could not generate or download audio.")

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        return

    def query_hf_space(self, target_space, text, meter, seed, speed):
        """Query HuggingFace Space via Gradio 5 queue REST protocol."""
        space_url = f"https://{target_space.replace('/', '-')}.hf.space"
        call_url = f"{space_url}/gradio_api/call/synthesize"
        
        # Format input data array corresponding to components: [text, meter, seed]
        # Dropdown uses original diacritics/pretty name or __auto__
        payload = {
            "data": [
                text,
                "__auto__" if meter == "anushtubh" or not meter else meter,
                int(seed)
            ]
        }
        
        req_headers = {
            "Content-Type": "application/json",
            "User-Agent": "Ayurvani/1.0"
        }
        
        # Pass token if provided to authenticate/increase ZeroGPU limits
        hf_token = os.environ.get("HF_TOKEN")
        if hf_token:
            req_headers["Authorization"] = f"Bearer {hf_token}"

        # 1. Post request to create event
        req_call = urllib.request.Request(
            call_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=req_headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req_call, timeout=15) as resp:
            event_id = json.loads(resp.read().decode("utf-8")).get("event_id")
            
        if not event_id:
            raise Exception("Failed to queue request on HuggingFace Space.")

        # 2. Poll for results (SSE event stream)
        status_url = f"{space_url}/gradio_api/call/synthesize/{event_id}"
        audio_url = None
        
        start_time = time.time()
        # Max poll duration 60 seconds
        while time.time() - start_time < 60:
            time.sleep(2)
            req_poll = urllib.request.Request(status_url, headers=req_headers, method="GET")
            try:
                with urllib.request.urlopen(req_poll, timeout=12) as resp_poll:
                    content = resp_poll.read().decode("utf-8")
                    done = False
                    for line in content.split("\n"):
                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                            if not data_str or data_str == "null":
                                continue
                            event_payload = json.loads(data_str)
                            msg = event_payload.get("msg")
                            if msg == "process_completed":
                                if event_payload.get("success"):
                                    output_data = event_payload.get("output", {}).get("data", [])
                                    if output_data:
                                        audio_info = output_data[0]
                                        if isinstance(audio_info, dict) and "url" in audio_info:
                                            audio_url = audio_info.get("url")
                                            # format relative URL to absolute
                                            if audio_url.startswith("/"):
                                                audio_url = f"{space_url}{audio_url}"
                                            elif not audio_url.startswith("http"):
                                                audio_url = f"{space_url}/gradio_api/file={audio_url}"
                                            done = True
                                            break
                                else:
                                    error_detail = event_payload.get("output", {}).get("error", "Generation failed")
                                    raise Exception(error_detail)
                    if done:
                        break
            except Exception as pe:
                if "ZeroGPU quota" in str(pe):
                    raise pe
                continue

        if not audio_url:
            raise Exception("Generation timed out on HuggingFace Space.")

        # 3. Download final audio bytes
        req_audio = urllib.request.Request(audio_url, headers=req_headers)
        with urllib.request.urlopen(req_audio, timeout=15) as resp_audio:
            return resp_audio.read()
