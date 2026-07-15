import os
import json
from http.server import BaseHTTPRequestHandler

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
            # Locate local bank.json relative to repository root
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            bank_path = os.path.join(base_dir, "vagdhenu", "src", "reference_bank", "bank.json")
            
            with open(bank_path, "r", encoding="utf-8") as f:
                bank_data = json.load(f)
                
            meter_list = []
            for k, v in bank_data.items():
                if not k.startswith("_") and isinstance(v, dict) and "wav" in v:
                    meter_list.append({
                        "id": k,
                        "sec_per_syll": v.get("sec_per_syll", 0.26)
                    })
                    
            resp_json = json.dumps({"meters": meter_list}, ensure_ascii=False).encode("utf-8")
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
