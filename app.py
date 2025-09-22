import json
import os
import sys
from wsgiref.simple_server import make_server

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(__file__))

from api.crypto_webhook import app

def simple_app(environ, start_response):
    """Простой WSGI application"""
    if environ['REQUEST_METHOD'] == 'POST' and environ['PATH_INFO'] == '/api/crypto-webhook':
        try:
            # Получаем данные из POST запроса
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
            data = json.loads(post_data)

            # Обрабатываем вебхук
            result = asyncio.run(process_payment_webhook(data))

            status = '200 OK' if result.get('ok') else '400 Bad Request'
            response_headers = [('Content-type', 'application/json')]
            start_response(status, response_headers)
            return [json.dumps(result).encode('utf-8')]

        except Exception as e:
            status = '500 Internal Server Error'
            response_headers = [('Content-type', 'application/json')]
            start_response(status, response_headers)
            return [json.dumps({"error": str(e)}).encode('utf-8')]

    elif environ['REQUEST_METHOD'] == 'GET' and environ['PATH_INFO'] == '/api/crypto-webhook':
        status = '200 OK'
        response_headers = [('Content-type', 'application/json')]
        start_response(status, response_headers)
        return [json.dumps({"status": "ok", "message": "CryptoBot webhook endpoint is running"}).encode('utf-8')]

    else:
        status = '404 Not Found'
        response_headers = [('Content-type', 'application/json')]
        start_response(status, response_headers)
        return [json.dumps({"error": "Not found"}).encode('utf-8')]

# Импортируем асинхронную функцию
import asyncio
from api.crypto_webhook import process_payment_webhook

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    with make_server('', port, simple_app) as httpd:
        print(f"Serving on port {port}...")
        httpd.serve_forever()