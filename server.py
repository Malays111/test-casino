#!/usr/bin/env python3
import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(__file__))

class WebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/crypto-webhook':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"status": "ok", "message": "CryptoBot webhook endpoint is running"}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"error": "Not found"}
            self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        if self.path == '/api/crypto-webhook':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(post_data)

                # Простая обработка webhook
                update_type = data.get('update_type')
                if update_type == 'invoice_paid':
                    invoice_data = data.get('payload', {})
                    status = invoice_data.get('status')
                    if status == 'paid':
                        # Здесь будет обработка платежа
                        result = {"ok": True, "message": "Payment processed"}
                    else:
                        result = {"ok": False, "error": "Payment not paid"}
                else:
                    result = {"ok": True, "message": "Webhook received"}

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = {"error": str(e)}
                self.wfile.write(json.dumps(error_response).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"error": "Not found"}
            self.wfile.write(json.dumps(response).encode())

def run_server():
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(('0.0.0.0', port), WebhookHandler)
    print(f"Starting server on port {port}...")
    server.serve_forever()

if __name__ == '__main__':
    run_server()