import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(__file__))

# Асинхронная функция для обработки платежа
async def process_payment_webhook(data):
    """Обработка вебхука от CryptoBot через основную систему бота"""
    try:
        print(f"Получен webhook: {data}")

        # Извлекаем данные из webhook
        update_type = data.get('update_type')

        if update_type == 'invoice_paid':
            # Новый формат webhook для invoice
            invoice_data = data.get('payload', {})
            invoice_id = invoice_data.get('invoice_id')
            status = invoice_data.get('status')
            amount = invoice_data.get('amount')

            if status == 'paid' and invoice_id:
                print(f"Обработка платежа: invoice_id={invoice_id}, amount={amount}")

                # Импортируем функцию process_webhook_payment из bot.py
                from bot import process_webhook_payment

                # Обрабатываем платеж через основную систему
                result = await process_webhook_payment(invoice_id, status, amount)

                if result.get('success'):
                    print(f"Платеж успешно обработан: {result}")
                    return {"ok": True, "message": result.get('message')}
                else:
                    print(f"Ошибка обработки платежа: {result}")
                    return {"ok": False, "error": result.get('error')}

        elif update_type == 'check':
            # Старый формат webhook для чеков (оставляем для совместимости)
            invoice_data = data.get('check', {})
            invoice_id = invoice_data.get('id')
            check_status = invoice_data.get('status')

            if check_status == 'activated' and invoice_id:
                print(f"Обработка чека: invoice_id={invoice_id}")

                # Импортируем функцию process_webhook_payment из bot.py
                from bot import process_webhook_payment

                # Обрабатываем чек через основную систему
                result = await process_webhook_payment(invoice_id, 'paid')

                if result.get('success'):
                    print(f"Чек успешно обработан: {result}")
                    return {"ok": True, "message": result.get('message')}
                else:
                    print(f"Ошибка обработки чека: {result}")
                    return {"ok": False, "error": result.get('error')}

        return {"ok": True, "message": "Webhook processed"}

    except Exception as e:
        print(f"Ошибка обработки webhook: {e}")
        return {"ok": False, "error": str(e)}

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

                # Обрабатываем вебхук асинхронно
                import asyncio
                result = asyncio.run(process_payment_webhook(data))

                if result.get('ok'):
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(result).encode())
                else:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(result).encode())

            except Exception as e:
                print(f"Ошибка в POST handler: {e}")
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