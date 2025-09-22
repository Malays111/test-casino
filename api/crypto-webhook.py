import json
import os
import sys
import asyncio
from flask import Flask, request, jsonify

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импорты из проекта
from config import CRYPTO_BOT_TOKEN, CRYPTO_BOT_API, DATABASE_PATH

app = Flask(__name__)
app.config['DEBUG'] = False

# Асинхронная функция для обработки платежа через основную систему бота
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

@app.route('/api/crypto-webhook', methods=['POST'])
def webhook_handler():
    """Обработчик вебхука для Railway"""
    try:
        # Получаем данные из запроса
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Обрабатываем вебхук асинхронно
        result = asyncio.run(process_payment_webhook(data))

        if result.get('ok'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        print(f"Ошибка в webhook handler: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/crypto-webhook', methods=['GET'])
def health_check():
    """Проверка доступности endpoint"""
    return jsonify({"status": "ok", "message": "CryptoBot webhook endpoint is running"}), 200
