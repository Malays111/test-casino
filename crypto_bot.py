import requests
from config import CRYPTO_BOT_TOKEN, CRYPTO_BOT_API

class CryptoBotAPI:
    def __init__(self):
        self.token = CRYPTO_BOT_TOKEN
        self.base_url = CRYPTO_BOT_API
        self.headers = {
            'Crypto-Pay-API-Token': self.token,
            'Content-Type': 'application/json'
        }
    
    def create_invoice(self, amount, description="Пополнение баланса VanishCasino"):
        url = f"{self.base_url}/api/createInvoice"
        payload = {
            "asset": "USDT",
            "amount": str(amount),
            "description": description,
            "paid_btn_name": "viewItem",
            "paid_btn_url": "https://t.me/VanishCasinoBot"
        }

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            print(f"Create invoice response: {response.status_code} - {response.text}")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Ошибка API: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Ошибка создания инвойса: {e}")
        return None
    
    def get_invoices(self, invoice_ids=None):
        url = f"{self.base_url}/api/getInvoices"
        params = {}
        if invoice_ids:
            params["invoice_ids"] = ','.join(invoice_ids)

        print(f"Запрос инвойсов: {params}")  # Отладка

        try:
            response = requests.get(url, params=params, headers=self.headers)
            print(f"Ответ от Crypto Bot: {response.status_code}")  # Отладка
            if response.status_code == 200:
                result = response.json()
                print(f"Данные инвойсов: {result}")  # Отладка
                return result
        except Exception as e:
            print(f"Ошибка получения инвойсов: {e}")
        return None

    def create_transfer(self, user_id, asset="USDT", amount=None, spend_id=None, comment=None, disable_send_notification=None):
        """Создание перевода средств между пользователями бота"""
        url = f"{self.base_url}/api/transfer"
        payload = {
            "user_id": user_id,
            "asset": asset,
            "amount": str(amount) if amount is not None else None,
            "spend_id": spend_id,
            "comment": comment,
            "disable_send_notification": disable_send_notification
        }

        # Убираем None значения
        payload = {k: v for k, v in payload.items() if v is not None}

        print(f"Создание перевода: {payload}")  # Отладка

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            print(f"Ответ от Crypto Bot: {response.status_code}")  # Отладка
            if response.status_code == 200:
                result = response.json()
                print(f"Результат перевода: {result}")  # Отладка
                return result
            else:
                # Обработка ошибок HTTP
                try:
                    error_data = response.json()
                    print(f"Ошибка API: {error_data}")
                    return {"error": error_data}
                except:
                    print(f"Ошибка HTTP {response.status_code}: {response.text}")
                    return {"error": f"HTTP {response.status_code}: {response.text}"}

        except requests.exceptions.RequestException as e:
            print(f"Ошибка сети при создании перевода: {e}")
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            print(f"Неожиданная ошибка создания перевода: {e}")
            return {"error": f"Unexpected error: {str(e)}"}
        return None

    def get_balance(self, asset="USDT"):
        """Получение баланса бота"""
        url = f"{self.base_url}/api/getBalance"
        params = {"asset": asset}

        try:
            response = requests.get(url, params=params, headers=self.headers)
            print(f"Баланс бота: {response.status_code}")  # Отладка
            if response.status_code == 200:
                result = response.json()
                print(f"Баланс: {result}")  # Отладка
                return result
        except Exception as e:
            print(f"Ошибка получения баланса: {e}")
        return None

    def create_check(self, amount, description="Пополнение баланса VanishCasino"):
        """Создание чека для оплаты"""
        url = f"{self.base_url}/createCheck"
        payload = {
            "asset": "TON",
            "amount": str(amount),
            "description": description
        }

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            print(f"Create check response: {response.status_code} - {response.text}")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Ошибка API: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Ошибка создания чека: {e}")
        return None

    def get_checks(self, check_ids=None):
        """Получение информации о чеках"""
        url = f"{self.base_url}/getChecks"
        params = {}
        if check_ids:
            params["check_ids"] = ','.join(check_ids)

        try:
            response = requests.get(url, params=params, headers=self.headers)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Ошибка получения чеков: {e}")
        return None

    def set_webhook(self, webhook_url):
        """Установка вебхука для получения уведомлений о платежах"""
        url = f"{self.base_url}/api/setWebhook"
        payload = {
            "url": webhook_url
        }

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            print(f"Set webhook response: {response.status_code} - {response.text}")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Ошибка установки вебхука: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Ошибка установки вебхука: {e}")
        return None

    def delete_webhook(self):
        """Удаление вебхука"""
        url = f"{self.base_url}/api/deleteWebhook"

        try:
            response = requests.post(url, headers=self.headers)
            print(f"Delete webhook response: {response.status_code} - {response.text}")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Ошибка удаления вебхука: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Ошибка удаления вебхука: {e}")
        return None

    def get_wallet_address(self):
        """Получение адреса кошелька бота для внешних переводов"""
        # В реальной ситуации здесь нужно получить адрес кошелька бота
        # из настроек или API Crypto Bot
        # Пока возвращаем заглушку
        return "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWZh"  # Пример TRC20 адреса

    def process_webhook_data(self, webhook_data):
        """Обработка данных webhook от CryptoBot"""
        try:
            print(f"Получены данные webhook: {webhook_data}")

            # Извлекаем данные из webhook
            invoice_id = webhook_data.get('payload', {}).get('invoice_id')
            status = webhook_data.get('payload', {}).get('status')
            amount = webhook_data.get('payload', {}).get('amount')

            if not invoice_id or not status:
                print("Отсутствуют обязательные поля в webhook данных")
                return {"success": False, "error": "Missing required fields"}

            # Импортируем функцию process_webhook_payment из bot.py
            # Это нужно делать внутри функции, чтобы избежать циклических импортов
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))

            # Импортируем функцию асинхронно
            from bot import process_webhook_payment

            # Запускаем обработку платежа асинхронно
            import asyncio
            result = asyncio.run(process_webhook_payment(invoice_id, status, amount))

            print(f"Результат обработки webhook: {result}")
            return result

        except Exception as e:
            print(f"Ошибка обработки webhook данных: {e}")
            return {"success": False, "error": str(e)}

crypto_bot = CryptoBotAPI()