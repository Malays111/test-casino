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
        url = f"{self.base_url}/createInvoice"
        payload = {
            "asset": "USDT",
            "amount": str(amount),
            "description": description,
            "paid_btn_name": "viewItem",
            "paid_btn_url": "https://t.me/VanishCasinoBot"
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Ошибка создания инвойса: {e}")
        return None
    
    def get_invoices(self, invoice_ids=None):
        url = f"{self.base_url}/getInvoices"
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
        url = f"{self.base_url}/transfer"
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
        url = f"{self.base_url}/getBalance"
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

    def get_wallet_address(self):
        """Получение адреса кошелька бота для внешних переводов"""
        # В реальной ситуации здесь нужно получить адрес кошелька бота
        # из настроек или API Crypto Bot
        # Пока возвращаем заглушку
        return "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWZh"  # Пример TRC20 адреса

crypto_bot = CryptoBotAPI()