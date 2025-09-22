import sqlite3
from config import REFERRAL_LEVELS

class Database:
    def __init__(self, db_name="casino.db"):
        self.db_name = db_name
        self.init_db()
        self.enable_wal_mode()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                balance REAL DEFAULT 0,
                referral_count INTEGER DEFAULT 0,
                referral_balance REAL DEFAULT 0,
                total_deposited REAL DEFAULT 0,
                total_spent REAL DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                last_daily_task_completed DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Добавляем колонки, если их нет
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER")
        except sqlite3.OperationalError:
            pass  # Колонка уже существует

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN referral_balance REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Колонка уже существует

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN referral_bonus_given INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Колонка уже существует

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN total_deposited REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Колонка уже существует

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN total_spent REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Колонка уже существует

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN games_played INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Колонка уже существует

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN last_daily_task_completed DATE")
        except sqlite3.OperationalError:
            pass  # Колонка уже существует

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN referral_level INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass  # Колонка уже существует
        
        # Таблица платежей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                amount REAL,
                crypto_bot_invoice_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица выводов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                amount REAL,
                wallet_address TEXT,
                crypto_bot_transfer_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица настроек шансов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_settings (
                id INTEGER PRIMARY KEY,
                setting_key TEXT UNIQUE,
                setting_value REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица текстовых настроек
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS text_settings (
                id INTEGER PRIMARY KEY,
                setting_key TEXT UNIQUE,
                setting_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица промокодов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promo_codes (
                id INTEGER PRIMARY KEY,
                code TEXT UNIQUE,
                reward_amount REAL,
                max_activations INTEGER,
                current_activations INTEGER DEFAULT 0,
                expires_at TIMESTAMP,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица использованных промокодов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS used_promo_codes (
                id INTEGER PRIMARY KEY,
                promo_code_id INTEGER,
                user_id INTEGER,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (promo_code_id) REFERENCES promo_codes (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Таблица логов действий пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_logs (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER,
                action TEXT,
                amount REAL DEFAULT 0,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Инициализация настроек по умолчанию
        default_settings = [
            ('duel_house_advantage', 51.0),
            ('dice_house_advantage', 83.33),
            ('basketball_house_advantage', 51.0),
            ('slots_house_advantage', 90.0),
            ('blackjack_house_advantage', 52.0),
            ('duel_multiplier', 1.8),
            ('dice_multiplier', 5.0),
            ('basketball_multiplier', 1.5),
            ('slots_multiplier', 8.0),
            ('blackjack_multiplier', 2.0)
        ]

        for key, value in default_settings:
            cursor.execute(
                "INSERT OR IGNORE INTO game_settings (setting_key, setting_value) VALUES (?, ?)",
                (key, value)
            )

        # Миграция текстовых настроек из game_settings в text_settings
        cursor.execute("SELECT setting_key, setting_value FROM game_settings WHERE setting_key IN ('results_group_id', 'vip_group_id')")
        text_settings_to_migrate = cursor.fetchall()

        for key, value in text_settings_to_migrate:
            cursor.execute(
                "INSERT OR IGNORE INTO text_settings (setting_key, setting_value) VALUES (?, ?)",
                (key, str(value))
            )
            # Удаляем из старой таблицы
            cursor.execute("DELETE FROM game_settings WHERE setting_key = ?", (key,))
        
        conn.commit()
        conn.close()

    def enable_wal_mode(self):
        """Включить WAL режим для лучшей concurrency"""
        try:
            conn = sqlite3.connect(self.db_name)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Ошибка включения WAL режима: {e}")

    def get_user(self, telegram_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT id, telegram_id, username, balance, referral_count, COALESCE(referral_balance, 0) as referral_balance, COALESCE(total_deposited, 0) as total_deposited, COALESCE(total_spent, 0) as total_spent, COALESCE(games_played, 0) as games_played, referrer_id, referral_bonus_given, COALESCE(referral_level, 1) as referral_level, last_daily_task_completed, created_at FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        conn.close()
        if user:
            # Приводим balance и referral_balance к float для безопасности
            user = list(user)
            try:
                user[3] = float(str(user[3]).replace(',', '.')) if user[3] is not None else 0.0  # balance
            except (ValueError, TypeError):
                user[3] = 0.0
            try:
                user[5] = float(str(user[5]).replace(',', '.')) if user[5] is not None else 0.0  # referral_balance
            except (ValueError, TypeError):
                user[5] = 0.0
            user = tuple(user)
        return user  # (id, telegram_id, username, balance, referral_count, referral_balance, referrer_id, referral_bonus_given, referral_level, created_at)
    
    def create_user(self, telegram_id, username, referrer_id=None):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        level_up_info = None

        # Проверяем, существует ли пользователь
        cursor.execute("SELECT referrer_id FROM users WHERE telegram_id = ?", (telegram_id,))
        existing_user = cursor.fetchone()

        if existing_user:
            # Пользователь уже существует
            current_referrer_id = existing_user[0]
            if current_referrer_id is None and referrer_id is not None:
                # Устанавливаем referrer_id, если его нет
                cursor.execute(
                    "UPDATE users SET referrer_id = ?, referral_bonus_given = 0 WHERE telegram_id = ?",
                    (referrer_id, telegram_id)
                )
                # Обновляем счетчик рефералов
                cursor.execute(
                    "UPDATE users SET referral_count = COALESCE(referral_count, 0) + 1 WHERE telegram_id = ?",
                    (referrer_id,)
                )
                # Проверяем повышение уровня реферала
                cursor.execute("SELECT referral_count, referral_level FROM users WHERE telegram_id = ?", (referrer_id,))
                referrer_result = cursor.fetchone()
                if referrer_result:
                    new_count = referrer_result[0] or 0
                    old_level = referrer_result[1] or 1
                    new_level, bonus, name = self.calculate_referral_level(new_count)
                    if new_level > old_level:
                        cursor.execute(
                            "UPDATE users SET referral_level = ? WHERE telegram_id = ?",
                            (new_level, referrer_id)
                        )
                        level_up_info = {
                            "telegram_id": referrer_id,
                            "old_level": old_level,
                            "new_level": new_level,
                            "bonus": bonus,
                            "name": name
                        }
            # Не делаем ничего, если referrer_id уже установлен
        else:
            # Создаем нового пользователя
            try:
                cursor.execute(
                    "INSERT INTO users (telegram_id, username, referrer_id, referral_bonus_given) VALUES (?, ?, ?, 0)",
                    (telegram_id, username, referrer_id)
                )
                user_id = cursor.lastrowid

                # Если есть referrer, обновляем его счетчик рефералов и уровень
                if referrer_id:
                    # Получаем текущее количество рефералов
                    cursor.execute("SELECT referral_count, referral_level FROM users WHERE telegram_id = ?", (referrer_id,))
                    referrer_result = cursor.fetchone()
                    if referrer_result:
                        current_count = referrer_result[0] or 0
                        old_level = referrer_result[1] or 1
                        new_count = current_count + 1

                        # Обновляем счетчик рефералов
                        cursor.execute(
                            "UPDATE users SET referral_count = ? WHERE telegram_id = ?",
                            (new_count, referrer_id)
                        )

                        # Обновляем уровень реферала и проверяем повышение
                        new_level, bonus, name = self.calculate_referral_level(new_count)
                        if new_level > old_level:
                            cursor.execute(
                                "UPDATE users SET referral_level = ? WHERE telegram_id = ?",
                                (new_level, referrer_id)
                            )
                            level_up_info = {
                                "telegram_id": referrer_id,
                                "old_level": old_level,
                                "new_level": new_level,
                                "bonus": bonus,
                                "name": name
                            }
                        else:
                            cursor.execute(
                                "UPDATE users SET referral_level = ? WHERE telegram_id = ?",
                                (new_level, referrer_id)
                            )

            except sqlite3.OperationalError:
                # Если колонки нет, вставляем без них
                cursor.execute(
                    "INSERT INTO users (telegram_id, username) VALUES (?, ?)",
                    (telegram_id, username)
                )

        conn.commit()
        conn.close()
        return {"level_up_info": level_up_info} if level_up_info else None
    
    def update_balance(self, telegram_id, amount):
        print(f"Обновление баланса: telegram_id={telegram_id}, amount={amount}")  # Отладка
        try:
            amount = float(amount)  # Приводим к float для безопасности
        except (ValueError, TypeError):
            print(f"Ошибка: amount не является числом: {amount}")
            return

        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET balance = (COALESCE(CAST(balance AS REAL), 0) + ?) WHERE telegram_id = ?",
                (amount, telegram_id)
            )
            if amount > 0:
                cursor.execute(
                    "UPDATE users SET total_deposited = COALESCE(total_deposited, 0) + ? WHERE telegram_id = ?",
                    (amount, telegram_id)
                )
            elif amount < 0:
                cursor.execute(
                    "UPDATE users SET total_spent = COALESCE(total_spent, 0) + ? WHERE telegram_id = ?",
                    (-amount, telegram_id)
                )
            rows_affected = cursor.rowcount
            print(f"Баланс обновлен. Затронуто строк: {rows_affected}")  # Отладка
            if rows_affected > 0:
                cursor.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,))
                result = cursor.fetchone()
                print(f"Баланс после обновления: {result}")
                # Логирование изменения баланса
                try:
                    action = "balance_deposit" if amount > 0 else "balance_spend"
                    self.log_action(telegram_id, action, amount, f"Баланс изменен на {amount}")
                except Exception as e:
                    print(f"Ошибка логирования: {e}")
            else:
                print(f"Пользователь с telegram_id {telegram_id} не найден")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Ошибка update_balance: {e}")
    
    def update_referral_balance(self, telegram_id, amount):
        print(f"Обновление реферального баланса: telegram_id={telegram_id}, amount={amount}")  # Отладка
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            print(f"Ошибка: amount не является числом: {amount}")
            return

        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            print("Before update referral_balance")
            cursor.execute(
                "UPDATE users SET referral_balance = COALESCE(referral_balance, 0) + ? WHERE telegram_id = ?",
                (amount, telegram_id)
            )
            rows_affected = cursor.rowcount
            print(f"Реферальный баланс обновлен. Затронуто строк: {rows_affected}")  # Отладка
            if rows_affected > 0:
                cursor.execute("SELECT referral_balance FROM users WHERE telegram_id = ?", (telegram_id,))
                result = cursor.fetchone()
                print(f"Реферальный баланс после обновления: {result}")
                # Логирование изменения реферального баланса
                try:
                    self.log_action(telegram_id, "referral_balance_update", amount, f"Реферальный баланс изменен на {amount}")
                except Exception as e:
                    print(f"Ошибка логирования: {e}")
            else:
                print(f"Пользователь с telegram_id {telegram_id} не найден")
            print("Before commit referral_balance")
            conn.commit()
            print("After commit referral_balance")
            conn.close()
        except Exception as e:
            print(f"Ошибка update_referral_balance: {e}")
    
    def get_total_balance(self, telegram_id):
        """Получить общий баланс (основной + реферальный)"""
        user = self.get_user(telegram_id)
        if user:
            return user[3] + user[5]  # balance + referral_balance
        return 0
    
    def create_payment(self, user_id, amount, invoice_id):
        print(f"Создание платежа в БД: user_id={user_id}, amount={amount}, invoice_id={invoice_id}")  # Отладка
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO payments (user_id, amount, crypto_bot_invoice_id) VALUES (?, ?, ?)",
            (user_id, amount, invoice_id)
        )
        payment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        print(f"Платеж создан с ID: {payment_id}")  # Отладка
        return payment_id
    
    def update_payment_status(self, invoice_id, status):
        print(f"Обновление статуса платежа: invoice_id={invoice_id}, status={status}")  # Отладка
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE payments SET status = ? WHERE crypto_bot_invoice_id = ?",
            (status, invoice_id)
        )
        conn.commit()
        conn.close()

    def get_top_deposited(self, limit=5):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username, total_deposited FROM users ORDER BY total_deposited DESC LIMIT ?",
            (limit,)
        )
        result = cursor.fetchall()
        conn.close()
        return result

    def get_top_spent(self, limit=5):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username, total_spent FROM users ORDER BY total_spent DESC LIMIT ?",
            (limit,)
        )
        result = cursor.fetchall()
        conn.close()
        return result

    def get_top_referrals(self, limit=5):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username, referral_count FROM users ORDER BY referral_count DESC LIMIT ?",
            (limit,)
        )
        result = cursor.fetchall()
        conn.close()
        return result

    def update_games_played(self, telegram_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET games_played = COALESCE(games_played, 0) + 1 WHERE telegram_id = ?",
            (telegram_id,)
        )
        conn.commit()
        conn.close()

    def save_game_setting(self, key, value):
        """Сохранение настройки игры"""
        print(f"Сохранение настройки: {key} = {value}")
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO game_settings (setting_key, setting_value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, value)
        )
        conn.commit()
        conn.close()

    def load_game_setting(self, key, default_value=None):
        """Загрузка настройки игры"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT setting_value FROM game_settings WHERE setting_key = ?",
            (key,)
        )
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else default_value

    def load_all_game_settings(self):
        """Загрузка всех настроек игр"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT setting_key, setting_value FROM game_settings")
        settings = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return settings

    def save_setting(self, key, value):
        """Сохранение настройки (текстовой)"""
        print(f"Сохранение настройки: {key} = {value}")
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO text_settings (setting_key, setting_value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, str(value))
        )
        conn.commit()
        conn.close()

    def get_setting(self, key, default_value=None):
        """Загрузка настройки (текстовой)"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT setting_value FROM text_settings WHERE setting_key = ?",
            (key,)
        )
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else default_value

    def create_withdrawal(self, user_id, amount, wallet_address):
        """Создание заявки на вывод"""
        print(f"Создание вывода в БД: user_id={user_id}, amount={amount}, wallet={wallet_address}")
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO withdrawals (user_id, amount, wallet_address) VALUES (?, ?, ?)",
            (user_id, amount, wallet_address)
        )
        withdrawal_id = cursor.lastrowid
        conn.commit()
        conn.close()
        print(f"Вывод создан с ID: {withdrawal_id}")
        return withdrawal_id

    def update_withdrawal_status(self, withdrawal_id, status, transfer_id=None):
        """Обновление статуса вывода"""
        print(f"Обновление статуса вывода: id={withdrawal_id}, status={status}, transfer_id={transfer_id}")
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        if transfer_id:
            cursor.execute(
                "UPDATE withdrawals SET status = ?, crypto_bot_transfer_id = ? WHERE id = ?",
                (status, transfer_id, withdrawal_id)
            )
        else:
            cursor.execute(
                "UPDATE withdrawals SET status = ? WHERE id = ?",
                (status, withdrawal_id)
            )
        conn.commit()
        conn.close()

    def create_promo_code(self, code, reward_amount, max_activations, expires_at, created_by):
        """Создание промокода"""
        print(f"Создание промокода: {code}, reward={reward_amount}, max={max_activations}, expires={expires_at}")
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO promo_codes (code, reward_amount, max_activations, expires_at, created_by) VALUES (?, ?, ?, ?, ?)",
            (code.upper(), reward_amount, max_activations, expires_at, created_by)
        )
        promo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return promo_id

    def get_promo_code(self, code):
        """Получение промокода по коду"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, code, reward_amount, max_activations, current_activations, expires_at, created_by, created_at FROM promo_codes WHERE code = ?",
            (code.upper(),)
        )
        result = cursor.fetchone()
        conn.close()
        return result

    def activate_promo_code(self, promo_code_id, user_id):
        """Активация промокода пользователем"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Проверяем, не активировал ли уже пользователь этот промокод
        cursor.execute(
            "SELECT id FROM used_promo_codes WHERE promo_code_id = ? AND user_id = ?",
            (promo_code_id, user_id)
        )
        if cursor.fetchone():
            conn.close()
            return False, "Вы уже активировали этот промокод"

        # Получаем информацию о промокоде
        cursor.execute(
            "SELECT reward_amount, max_activations, current_activations, expires_at FROM promo_codes WHERE id = ?",
            (promo_code_id,)
        )
        promo = cursor.fetchone()

        if not promo:
            conn.close()
            return False, "Промокод не найден"

        reward_amount, max_activations, current_activations, expires_at = promo

        # Проверяем срок действия
        from datetime import datetime
        if expires_at and datetime.now() > datetime.fromisoformat(expires_at):
            conn.close()
            return False, "Срок действия промокода истек"

        # Проверяем лимит активаций
        if current_activations >= max_activations:
            conn.close()
            return False, "Лимит активаций промокода исчерпан"

        # Активируем промокод
        cursor.execute(
            "INSERT INTO used_promo_codes (promo_code_id, user_id) VALUES (?, ?)",
            (promo_code_id, user_id)
        )
        cursor.execute(
            "UPDATE promo_codes SET current_activations = current_activations + 1 WHERE id = ?",
            (promo_code_id,)
        )

        conn.commit()
        conn.close()
        return True, reward_amount

    def get_all_promo_codes(self):
        """Получение всех промокодов для админов"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, code, reward_amount, max_activations, current_activations, expires_at, created_by, created_at FROM promo_codes ORDER BY created_at DESC"
        )
        result = cursor.fetchall()
        conn.close()
        return result

    def delete_promo_code(self, promo_id):
        """Удаление промокода"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM used_promo_codes WHERE promo_code_id = ?", (promo_id,))
        cursor.execute("DELETE FROM promo_codes WHERE id = ?", (promo_id,))
        conn.commit()
        conn.close()

    def log_action(self, telegram_id, action, amount=0, reason=""):
        """Логирование действий пользователя"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user_logs (telegram_id, action, amount, reason) VALUES (?, ?, ?, ?)",
                (telegram_id, action, amount, reason)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            pass  # Игнорируем ошибки логирования

    def get_user_logs(self, telegram_id=None, limit=50):
        """Получение логов пользователя или всех (для админов)"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        if telegram_id:
            cursor.execute(
                "SELECT telegram_id, action, amount, reason, created_at FROM user_logs WHERE telegram_id = ? ORDER BY created_at DESC LIMIT ?",
                (telegram_id, limit)
            )
        else:
            cursor.execute(
                "SELECT telegram_id, action, amount, reason, created_at FROM user_logs ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        result = cursor.fetchall()
        conn.close()
        return result

    def calculate_referral_level(self, referral_count):
        """Расчет уровня реферала на основе количества приглашенных"""
        from config import REFERRAL_LEVELS

        for level, data in sorted(REFERRAL_LEVELS.items(), reverse=True):
            if referral_count >= data["required_referrals"]:
                return level, data["bonus"], data["name"]
        return 1, REFERRAL_LEVELS[1]["bonus"], REFERRAL_LEVELS[1]["name"]

    def update_referral_level(self, telegram_id):
        """Обновление уровня реферала"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Получаем текущее количество рефералов и уровень
        cursor.execute("SELECT referral_count, referral_level FROM users WHERE telegram_id = ?", (telegram_id,))
        result = cursor.fetchone()

        if result:
            referral_count = result[0] or 0
            old_level = result[1] or 1
            level, bonus, name = self.calculate_referral_level(referral_count)

            # Обновляем уровень
            cursor.execute(
                "UPDATE users SET referral_level = ? WHERE telegram_id = ?",
                (level, telegram_id)
            )

            conn.commit()
            conn.close()

            # Проверяем, повысился ли уровень
            if level > old_level:
                return {
                    "level": level,
                    "bonus": bonus,
                    "name": name,
                    "old_level": old_level,
                    "new_level": level,
                    "level_up": True
                }
            else:
                return {
                    "level": level,
                    "bonus": bonus,
                    "name": name,
                    "old_level": old_level,
                    "new_level": level,
                    "level_up": False
                }

        conn.close()
        return {
            "level": 1,
            "bonus": 0.3,
            "name": "Новичок",
            "old_level": 1,
            "new_level": 1,
            "level_up": False
        }

    def get_referral_level_info(self, telegram_id):
        """Получение информации об уровне реферала"""
        user_data = self.get_user(telegram_id)
        if user_data:
            referral_count = user_data[4] or 0  # referral_count
            level, bonus, name = self.calculate_referral_level(referral_count)
            return {
                "level": level,
                "name": name,
                "bonus": bonus,
                "referral_count": referral_count,
                "next_level": level + 1 if level < 10 else None,
                "next_required": REFERRAL_LEVELS.get(level + 1, {}).get("required_referrals", 0) if level < 10 else 0,
                "next_bonus": REFERRAL_LEVELS.get(level + 1, {}).get("bonus", 0) if level < 10 else 0,
                "progress": min(100, (referral_count / REFERRAL_LEVELS.get(level + 1, {}).get("required_referrals", referral_count + 1)) * 100) if level < 10 else 100
            }
        return None

db = Database()