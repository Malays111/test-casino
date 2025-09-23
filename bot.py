from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.filters.state import StateFilter
from config import TELEGRAM_TOKEN, DEPOSIT_AMOUNTS, CASINO_NAME, DUEL_FAQ_URL, DICE_FAQ_URL, BASKETBALL_FAQ_URL, SLOTS_FAQ_URL, BLACKJACK_FAQ_URL, DARTS_FAQ_URL, BACKGROUND_IMAGE_URL, ADMIN_IDS, REFERRAL_BONUS, REFERRAL_MIN_DEPOSIT, DAILY_TASKS, GROUPS

# URL изображений для результатов игр
WIN_IMAGE_URL = "https://www.dropbox.com/scl/fi/7g0gaxdpd9yib3njcvknv/winsvanish.png?rlkey=gkm3ifwgtlndkelab9mqla57h&st=ym57ciur&dl=0"
LOSE_IMAGE_URL = "https://www.dropbox.com/scl/fi/7djvu9ovgiy5yxgx8wi3i/losevanish.png?rlkey=1tjmth9haf4dcjnnfcba6kyt3&st=p10ekrvb&dl=0"
from async_database import AsyncDatabase

# Создаем экземпляр базы данных
async_db = AsyncDatabase()
from crypto_bot import crypto_bot
import asyncio
import random
import time
from datetime import date, datetime

# Глобальные переменные
bot = None
dp = None
results_group_id = None  # ID группы для отправки результатов игр
vip_group_id = None  # ID VIP группы для отправки выплат

# Кэш топов
top_deposited_cache = []
top_spent_cache = []
top_referrals_cache = []
last_cache_update = 0
CACHE_UPDATE_INTERVAL = 120  # 2 минуты в секундах
top_cache_lock = asyncio.Lock()  # Защита от race conditions

# Кэш балансов пользователей
user_balance_cache = {}
user_cache_expiry = {}
BALANCE_CACHE_TTL = 30  # 30 секунд
balance_cache_lock = asyncio.Lock()  # Защита от race conditions

# Кэш статистики пользователей
user_stats_cache = {}
user_stats_cache_expiry = {}
STATS_CACHE_TTL = 60  # 60 секунд
stats_cache_lock = asyncio.Lock()  # Защита от race conditions

# Rate limiting для ежедневного бонуса
daily_bonus_attempts = {}
DAILY_BONUS_COOLDOWN = 0  # Убрана задержка для мгновенного отклика

# Rate limiting для команд
command_rate_limits = {}
COMMAND_COOLDOWN = 0.0  # Убрана задержка для мгновенного отклика

# Rate limiting для callback
callback_rate_limits = {}
CALLBACK_COOLDOWN = 0.0  # Убрана задержка для мгновенного отклика

async def check_command_rate_limit(user_id, command):
    """Проверка rate limiting для команд"""
    current_time = time.time()
    key = f"{user_id}_{command}"

    last_use = command_rate_limits.get(key, 0)
    if current_time - last_use < COMMAND_COOLDOWN:
        return False

    command_rate_limits[key] = current_time
    return True

async def check_callback_rate_limit(user_id, callback_data):
    """Проверка rate limiting для callback"""
    current_time = time.time()
    key = f"{user_id}_{callback_data}"

    last_use = callback_rate_limits.get(key, 0)
    if current_time - last_use < CALLBACK_COOLDOWN:
        return False

    callback_rate_limits[key] = current_time
    return True

# Очередь для отправки сообщений в группы
group_message_queue = asyncio.Queue()
group_message_lock = asyncio.Lock()

# Асинхронная отправка результатов игры в группу (без блокировки)
async def send_game_result_to_group(game_name, username, bet, result_text, winnings_label, winnings):
    """Асинхронная отправка результата игры в группу"""
    if not results_group_id:
        return

    try:
        group_text = f"""📎 Игра: {game_name}
📱 Пользователь: {username}
💰 Ставка: {bet}$
⚡Результат: {result_text}
💲 {winnings_label}: {winnings}"""

        photo_url = WIN_IMAGE_URL if winnings_label == "Выигрыш" else LOSE_IMAGE_URL

        # Отправляем без ожидания
        asyncio.create_task(
            bot.send_photo(chat_id=results_group_id, photo=photo_url, caption=group_text)
        )
    except Exception as e:
        print(f"Ошибка отправки в группу: {e}")

# Асинхронные функции БД (используем async_db напрямую)
async def async_get_user(telegram_id):
    """Получение пользователя из БД"""
    return await async_db.get_user(telegram_id)

async def async_get_user_by_username(username):
    """Получение пользователя по username из БД"""
    return await async_db.get_user_by_username(username)

async def async_create_user(telegram_id, username, referrer_id=None):
    """Создание пользователя в БД"""
    await async_db.create_user(telegram_id, username, referrer_id)

async def async_update_balance(telegram_id, amount):
    """Обновление баланса пользователя"""
    await async_db.update_balance(telegram_id, amount)

async def async_update_referral_balance(telegram_id, amount):
    """Обновление реферального баланса"""
    await async_db.update_referral_balance(telegram_id, amount)

async def async_get_top_deposited(limit=5):
    """Получение топа по пополнениям"""
    return await async_db.get_top_deposited(limit)

async def async_get_top_spent(limit=5):
    """Получение топа по тратам"""
    return await async_db.get_top_spent(limit)

async def async_get_top_referrals(limit=5):
    """Получение топа по рефералам"""
    return await async_db.get_top_referrals(limit)

async def async_load_all_game_settings():
    """Загрузка всех настроек игр"""
    return await async_db.load_all_game_settings()

async def async_save_game_setting(key, value):
    """Сохранение настройки игры"""
    await async_db.save_game_setting(key, value)

async def async_save_setting(key, value):
    """Сохранение текстовой настройки"""
    await async_db.save_setting(key, value)

async def async_create_withdrawal(user_id, amount, wallet_address):
    """Создание заявки на вывод"""
    return await async_db.create_withdrawal(user_id, amount, wallet_address)

async def async_update_withdrawal_status(withdrawal_id, status, transfer_id=None):
    """Обновление статуса вывода"""
    await async_db.update_withdrawal_status(withdrawal_id, status, transfer_id)

async def async_create_promo_code(code, reward_amount, max_activations, expires_at, created_by):
    """Создание промокода"""
    return await async_db.create_promo_code(code, reward_amount, max_activations, expires_at, created_by)

async def async_get_promo_code(code):
    """Получение промокода по коду"""
    return await async_db.get_promo_code(code)

async def async_activate_promo_code(promo_code_id, user_id):
    """Активация промокода пользователем"""
    return await async_db.activate_promo_code(promo_code_id, user_id)

async def async_get_all_promo_codes():
    """Получение всех промокодов"""
    return await async_db.get_all_promo_codes()

async def async_log_action(telegram_id, action, amount=0, reason=""):
    """Логирование действия пользователя"""
    await async_db.log_action(telegram_id, action, amount, reason)

async def async_get_user_logs(telegram_id=None, limit=50):
    """Получение логов пользователя"""
    return await async_db.get_user_logs(telegram_id, limit)

async def async_get_user_stats(limit=50):
    """Получение статистики пользователей"""
    # Получаем пользователей с балансами и рефералами через async_db
    users = []
    # Используем прямой SQL запрос через async_db для статистики
    result = await asyncio.to_thread(async_db._execute_query,
        "SELECT username, balance, referral_count FROM users ORDER BY balance DESC LIMIT ?",
        (limit,), fetchall=True)
    return result

async def async_get_user_logs_by_username(username=None, limit=50):
    """Получение логов по username"""
    if not username:
        return await async_get_user_logs(limit=limit)
    # Получаем telegram_id по username через async_db
    user = await async_get_user(username)
    if user:
        telegram_id = user[1]  # telegram_id находится в user[1]
        return await async_get_user_logs(telegram_id, limit)
    else:
        return []

async def async_get_payment_by_invoice(invoice_id):
    """Получение платежа по invoice_id"""
    return await async_db.get_payment_by_invoice(invoice_id)

async def async_get_telegram_id_by_user_id(user_id):
    """Получение telegram_id по user_id"""
    return await async_db.get_telegram_id_by_user_id(user_id)

async def async_get_pending_payments(telegram_id):
    """Получение pending платежей пользователя"""
    return await async_db.get_pending_payments(telegram_id)

async def async_get_payment_amount_by_invoice(invoice_id):
    """Получение суммы платежа по invoice_id"""
    return await async_db.get_payment_amount_by_invoice(invoice_id)

async def async_get_setting(key, default_value=None):
    """Получение текстовой настройки"""
    return await async_db.get_setting(key, default_value)

async def async_update_games_played(telegram_id):
    """Обновление счетчика игр"""
    await async_db.update_games_played(telegram_id)

async def async_update_payment_status(invoice_id, status):
    """Обновление статуса платежа"""
    await async_db.update_payment_status(invoice_id, status)

# Функция предварительной загрузки данных
async def preload_data():
    """Предварительная загрузка часто используемых данных для ускорения работы"""
    global top_deposited_cache, top_spent_cache, top_referrals_cache, last_cache_update

    try:
        # Загружаем топы сразу
        async with top_cache_lock:
            top_deposited_cache = await async_get_top_deposited(5)
            top_spent_cache = await async_get_top_spent(5)
            top_referrals_cache = await async_get_top_referrals(5)
            last_cache_update = time.time()

        # Загружаем настройки игр
        global settings
        settings = await async_load_all_game_settings()

        # Запускаем очистку rate limiting кэша
        asyncio.create_task(cleanup_rate_limit_cache())

        # Запускаем обработчик очереди сообщений в группы
        asyncio.create_task(process_group_message_queue())

        print("✅ Предварительная загрузка завершена")
    except Exception as e:
        print(f"⚠️ Ошибка предзагрузки: {e}")

# Функция обновления кэша топов
async def update_top_cache():
    global top_deposited_cache, top_spent_cache, top_referrals_cache, last_cache_update
    while True:
        current_time = time.time()
        if current_time - last_cache_update >= CACHE_UPDATE_INTERVAL:
            async with top_cache_lock:
                top_deposited_cache = await async_get_top_deposited(5)
                top_spent_cache = await async_get_top_spent(5)
                top_referrals_cache = await async_get_top_referrals(5)
                last_cache_update = current_time
                print("Кэш топов обновлен")
        await asyncio.sleep(30)  # Проверяем каждые 30 секунд

# Функция получения топов из кэша
async def get_cached_tops():
    global top_deposited_cache, top_spent_cache, top_referrals_cache, last_cache_update
    current_time = time.time()
    if current_time - last_cache_update >= CACHE_UPDATE_INTERVAL:
        # Если кэш устарел, обновляем асинхронно
        async with top_cache_lock:
            top_deposited_cache = await async_get_top_deposited(5)
            top_spent_cache = await async_get_top_spent(5)
            top_referrals_cache = await async_get_top_referrals(5)
            last_cache_update = current_time
    return top_deposited_cache, top_spent_cache, top_referrals_cache

# Функция получения баланса из кэша (асинхронная)
async def get_cached_balance(user_id):
    async with balance_cache_lock:
        global user_balance_cache, user_cache_expiry
        current_time = time.time()

        # Очищаем устаревший кэш
        expired_users = [uid for uid, expiry in user_cache_expiry.items() if current_time > expiry]
        for uid in expired_users:
            user_balance_cache.pop(uid, None)
            user_cache_expiry.pop(uid, None)

        # Проверяем кэш
        if user_id in user_balance_cache and current_time <= user_cache_expiry.get(user_id, 0):
            return user_balance_cache[user_id]

        # Загружаем из БД и кэшируем
        user_data = await async_get_user(user_id)
        if user_data:
            balance = round(float(user_data[3]), 2) if user_data[3] is not None else 0
            referral_balance = round(float(user_data[5]), 2) if user_data[5] is not None else 0
            user_balance_cache[user_id] = (balance, referral_balance)
            user_cache_expiry[user_id] = current_time + BALANCE_CACHE_TTL
            return balance, referral_balance

        return 0, 0

# Функция получения статистики из кэша (асинхронная)
async def get_cached_user_stats(user_id):
    async with stats_cache_lock:
        global user_stats_cache, user_stats_cache_expiry
        current_time = time.time()

        # Очищаем устаревший кэш
        expired_users = [uid for uid, expiry in user_stats_cache_expiry.items() if current_time > expiry]
        for uid in expired_users:
            user_stats_cache.pop(uid, None)
            user_stats_cache_expiry.pop(uid, None)

        # Проверяем кэш
        if user_id in user_stats_cache and current_time <= user_stats_cache_expiry.get(user_id, 0):
            return user_stats_cache[user_id]

        # Загружаем из БД и кэшируем
        user_data = await async_get_user(user_id)
        if user_data:
            username = user_data[2] or "Не указан"
            balance = round(float(user_data[3]), 2) if user_data[3] is not None else 0
            referral_count = user_data[4] if user_data[4] is not None else 0
            referral_balance = round(float(user_data[5]), 2) if user_data[5] is not None else 0
            total_deposited = round(float(user_data[6]), 2) if user_data[6] is not None else 0
            total_spent = round(float(user_data[7]), 2) if user_data[7] is not None else 0
            games_played = user_data[8] if user_data[8] is not None else 0
            created_at = user_data[12] if len(user_data) > 12 and user_data[12] else "Неизвестно"

            # Вычисляем дополнительные метрики
            net_profit = total_deposited - total_spent
            win_rate = 0
            if games_played > 0:
                win_rate = min(100, max(0, (balance + total_spent - total_deposited) / max(1, total_spent) * 100))
            avg_bet = total_spent / max(1, games_played)
            profit_per_game = (total_deposited - total_spent) / max(1, games_played)

            stats = {
                'username': username,
                'balance': balance,
                'referral_count': referral_count,
                'referral_balance': referral_balance,
                'total_deposited': total_deposited,
                'total_spent': total_spent,
                'games_played': games_played,
                'created_at': created_at,
                'net_profit': net_profit,
                'win_rate': win_rate,
                'avg_bet': avg_bet,
                'profit_per_game': profit_per_game
            }

            user_stats_cache[user_id] = stats
            user_stats_cache_expiry[user_id] = current_time + STATS_CACHE_TTL
            return stats

        return None

# Функция инвалидации кэша баланса при изменении
async def invalidate_balance_cache(user_id):
    async with balance_cache_lock:
        global user_balance_cache, user_cache_expiry
        user_balance_cache.pop(user_id, None)
        user_cache_expiry.pop(user_id, None)

# Функция инвалидации кэша статистики при изменении
async def invalidate_stats_cache(user_id):
    async with stats_cache_lock:
        global user_stats_cache, user_stats_cache_expiry
        user_stats_cache.pop(user_id, None)
        user_stats_cache_expiry.pop(user_id, None)

# Функция получения задания дня
def get_daily_task():
    today = date.today()
    day_index = (today.toordinal() - date(2025, 9, 19).toordinal()) % len(DAILY_TASKS)
    return DAILY_TASKS[day_index]

# Функция очистки rate limiting кэша
async def cleanup_rate_limit_cache():
    while True:
        current_time = time.time()
        # Удаляем записи старше 5 минут
        expired_users = [uid for uid, timestamp in daily_bonus_attempts.items()
                        if current_time - timestamp > 300]
        for uid in expired_users:
            del daily_bonus_attempts[uid]

        # Очищаем общий rate limiting кэш команд
        expired_commands = [key for key, timestamp in command_rate_limits.items()
                           if current_time - timestamp > 300]
        for key in expired_commands:
            del command_rate_limits[key]

        await asyncio.sleep(300)  # Очищаем каждые 5 минут

# Функция обработки очереди сообщений в группы
async def process_group_message_queue():
    """Асинхронная обработка очереди сообщений в группы"""
    while True:
        try:
            # Получаем сообщение из очереди
            message_data = await group_message_queue.get()

            if message_data['type'] == 'game_result':
                group_id = message_data['group_id']
                photo_url = message_data['photo_url']
                caption = message_data['caption']

                try:
                    await bot.send_photo(chat_id=group_id, photo=photo_url, caption=caption)
                    print(f"Результат игры отправлен в группу {group_id}")
                except Exception as e:
                    print(f"Ошибка отправки в группу {group_id}: {e}")

            elif message_data['type'] == 'withdrawal_result':
                group_id = message_data['group_id']
                text = message_data['text']

                try:
                    await bot.send_message(chat_id=group_id, text=text)
                    print(f"Результат вывода отправлен в группу {group_id}")
                except Exception as e:
                    print(f"Ошибка отправки в VIP группу {group_id}: {e}")

            group_message_queue.task_done()

        except Exception as e:
            print(f"Ошибка обработки очереди сообщений: {e}")
            await asyncio.sleep(1)  # Небольшая пауза при ошибке

# Функция добавления сообщения в очередь
async def queue_group_message(message_data):
    """Добавление сообщения в очередь для отправки в группу"""
    await group_message_queue.put(message_data)

# Функция проверки выполнения задания
def check_daily_task_completion(user_data, task):
    if task["type"] == "referrals":
        return user_data[4] >= task["target"]  # referral_count
    elif task["type"] == "spent":
        return user_data[7] >= task["target"]  # total_spent
    elif task["type"] == "deposited":
        return user_data[6] >= task["target"]  # total_deposited
    elif task["type"] == "games":
        return user_data[8] >= task["target"]  # games_played
    return False

# Загрузка настроек из базы данных (асинхронно)
async def load_initial_settings():
    global settings, results_group_id, vip_group_id
    try:
        settings = await async_load_all_game_settings()
        results_group_id_raw = await async_get_setting('results_group_id')
        print(f"Загружено из БД results_group_id: '{results_group_id_raw}', type: {type(results_group_id_raw)}")
        if results_group_id_raw:
            try:
                results_group_id = int(results_group_id_raw)
                print(f"Загружена группа для результатов: {results_group_id}")
            except ValueError:
                print(f"Ошибка преобразования results_group_id: {results_group_id_raw}")
                results_group_id = None
        else:
            print("❌ Группа для результатов не установлена!")
            print("📋 Для отправки результатов игр в группу используйте команду:")
            print("   /setgroup <ID_группы>")
            print("   Или отправьте эту команду в нужной группе")
            results_group_id = None

        # Загрузка ID VIP группы из базы данных
        vip_group_id_raw = await async_get_setting('vip_group_id')
        print(f"Загружено из БД vip_group_id: '{vip_group_id_raw}', type: {type(vip_group_id_raw)}")
        if vip_group_id_raw:
            try:
                vip_group_id = int(vip_group_id_raw)
                print(f"Загружена VIP группа: {vip_group_id}")
            except ValueError:
                print(f"Ошибка преобразования vip_group_id: {vip_group_id_raw}")
                vip_group_id = None
        else:
            print("❌ VIP группа не установлена!")
            print("💎 Для отправки результатов выплат в VIP группу используйте команду:")
            print("   /setvip <ID_VIP_группы>")
            print("   Или отправьте эту команду в нужной VIP группе")
            vip_group_id = None
    except Exception as e:
        print(f"Ошибка загрузки настроек: {e}")

# Синхронная заглушка для обратной совместимости
settings = {}

# Шансы выигрыша (в процентах)
DUEL_WIN_CHANCE = settings.get('duel_win_chance', 25.0)
DICE_WIN_CHANCE = settings.get('dice_win_chance', 30.0)
BASKETBALL_WIN_CHANCE = settings.get('basketball_win_chance', 10.0)
SLOTS_WIN_CHANCE = settings.get('slots_win_chance', 15.0)
BLACKJACK_WIN_CHANCE = settings.get('blackjack_win_chance', 40.0)

# Множители выигрыша
DUEL_MULTIPLIER = settings.get('duel_multiplier', 1.8)
DICE_MULTIPLIER = settings.get('dice_multiplier', 5.0)
BASKETBALL_MULTIPLIER = settings.get('basketball_multiplier', 1.5)
SLOTS_MULTIPLIER = settings.get('slots_multiplier', 8.0)
BLACKJACK_MULTIPLIER = settings.get('blackjack_multiplier', 2.0)

# Состояния для FSM
class DepositStates(StatesGroup):
    waiting_for_amount = State()

class DuelStates(StatesGroup):
    waiting_for_bet = State()

class DiceStates(StatesGroup):
    waiting_for_number = State()
    waiting_for_bet = State()

class AdminStates(StatesGroup):
    waiting_for_duel_chance = State()
    waiting_for_dice_chance = State()
    waiting_for_basketball_chance = State()
    waiting_for_slots_chance = State()
    waiting_for_blackjack_chance = State()
    waiting_for_duel_multiplier = State()
    waiting_for_dice_multiplier = State()
    waiting_for_basketball_multiplier = State()
    waiting_for_slots_multiplier = State()
    waiting_for_blackjack_multiplier = State()

class WithdrawStates(StatesGroup):
    waiting_for_wallet_address = State()
    waiting_for_withdraw_amount = State()

class PromoStates(StatesGroup):
    waiting_for_promo_code = State()
    waiting_for_promo_amount = State()
    waiting_for_promo_max_activations = State()
    waiting_for_promo_expires = State()

class BasketballStates(StatesGroup):
    waiting_for_bet = State()

class SlotsStates(StatesGroup):
    waiting_for_bet = State()

class BlackjackStates(StatesGroup):
    waiting_for_bet = State()

# Главное меню
def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎮 Играть", callback_data="play"),
            InlineKeyboardButton(text="👥 Реферальная система", callback_data="referral")
        ],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
            InlineKeyboardButton(text="📊 Рейтинг", callback_data="rating")
        ],
        [
            InlineKeyboardButton(text="💰 Пополнить", callback_data="deposit"),
            InlineKeyboardButton(text="💸 Вывести", callback_data="withdraw")
        ],
        [
            InlineKeyboardButton(text="🎁 Ежедневный бонус", callback_data="daily_bonus"),
            InlineKeyboardButton(text="👥 Группы", callback_data="groups")
        ],
        [InlineKeyboardButton(text="🎫 Промокоды", callback_data="promo_codes")]
    ])
    return keyboard

def get_admin_panel():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Шансы", callback_data="admin_chances")],
        [InlineKeyboardButton(text="⚡ Множитель", callback_data="admin_multiplier")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="💰 Установить баланс", callback_data="admin_set_balance")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    return keyboard

# Кнопки пополнения
def get_deposit_menu():
    buttons = [InlineKeyboardButton(text=f"💲 {amount}$", callback_data=f"dep_{amount}") for amount in DEPOSIT_AMOUNTS]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [buttons[0], buttons[1]],
        [buttons[2], buttons[3]],
        [InlineKeyboardButton(text="📝 Ввести сумму", callback_data="dep_custom")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    return keyboard

# Кнопка назад
def get_back_button():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]])
    return keyboard

# Меню игр
def get_games_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎲 Кости", callback_data="game_duel"),
            InlineKeyboardButton(text="🎁 Кубикии", callback_data="game_dice"),
            InlineKeyboardButton(text="🏀 Баскетбол", callback_data="game_basketball")
        ],
        [
            InlineKeyboardButton(text="🎰 Слоты", callback_data="game_slots"),
            InlineKeyboardButton(text="🃏 BlackJack", callback_data="game_blackjack"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
        ]
    ])
    return keyboard

def get_deposit_back_button():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="deposit")]])
    return keyboard

# Меню групп
def get_groups_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"👥 {group['name']}", url=group['url'])] for group in GROUPS
    ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]])
    return keyboard

# Меню промокодов
def get_promo_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎫 Активировать промокод", callback_data="activate_promo")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    return keyboard

async def get_welcome_text(user):
    """Генерирует приветственное сообщение"""
    # Получаем данные пользователя из кэша
    balance, referral_balance = await get_cached_balance(user.id)
    print(f"cached balance for {user.id}: balance={balance}, referral={referral_balance}")

    # Формируем приветствие
    if user.username:
        greeting = f"Привет, @<b><u>{user.username}</u></b> !"
    elif user.first_name:
        greeting = f"Привет, <b>{user.first_name}</b>!"
    else:
        greeting = "Привет!"

    print(f"Баланс пользователя {user.id}: основной {balance}, реферальный {referral_balance}")

    # Получаем задание дня
    task = get_daily_task()

    welcome_text = f"""<b>🎁 Ежедневное задание:</b>
  <blockquote>{task['description']} - Награда: {task['reward']}$</blockquote>

  {greeting} ты попал в <b> {CASINO_NAME} </b> — Самое лучшее казино в телеграмме ♥️
  🍀Баланс: {balance}$
  ⚡Реферальный баланс: {referral_balance}$ """

    return welcome_text, "HTML"

# Обработчик /start и /restart
async def start_command(message: types.Message):
    user = message.from_user

    # Проверяем реферальную ссылку
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        potential_referrer_id = int(args[1])
        # Проверяем, что пользователь не приглашает сам себя
        if potential_referrer_id != user.id:
            referrer_id = potential_referrer_id

    await async_create_user(user.id, user.username, referrer_id)

    welcome_text, parse_mode = await get_welcome_text(user)
    await message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=welcome_text, reply_markup=get_main_menu(), parse_mode=parse_mode)

# Обработчик /give для админов
async def give_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ У вас нет прав администратора")
        return

    # Rate limiting
    if not await check_command_rate_limit(message.from_user.id, 'give'):
        await message.reply("⏳ Подождите перед повторным использованием команды")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.reply("Использование: /give @username amount или /give telegram_id amount\nПример: /give @testuser 10.5 или /give 123456789 10.5")
        return

    identifier = args[1]
    telegram_id = None
    username = None

    # Определяем, username или telegram_id
    if identifier.isdigit():
        telegram_id = int(identifier)
    else:
        username = identifier
        if username.startswith('@'):
            username = username[1:]  # Убрать @

    try:
        amount = float(args[2])
    except ValueError:
        await message.reply("❌ Неверная сумма")
        return

    # Найти user
    try:
        if telegram_id:
            user_data = await async_get_user(telegram_id)
        else:
            user_data = await async_get_user_by_username(username)
        if not user_data:
            await message.reply("❌ Пользователь не найден")
            return

        user_telegram_id = user_data[1]  # telegram_id
        user_username = user_data[2] or f"ID:{user_telegram_id}"  # username

        await async_update_balance(user_telegram_id, amount)
        # Логируем выдачу денег админом
        await async_log_action(user_telegram_id, "admin_give", amount, f"Выдано админом {message.from_user.id}")
        await message.reply(f"✅ Выдано {amount}$ пользователю @{user_username}")
    except Exception as e:
        await message.reply(f"❌ Ошибка базы данных: {e}")

# Обработчик /stats для админов
async def stats_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    # Rate limiting
    if not await check_command_rate_limit(message.from_user.id, 'stats'):
        await message.reply("⏳ Подождите перед повторным использованием команды")
        return

    # Получаем всех пользователей асинхронно
    try:
        users = await async_get_user_stats(limit=50)

        if not users:
            await message.reply("📊 Статистика пользователей:\n\n❌ Пользователей не найдено")
            return

        stats_text = "📊 Статистика пользователей:\n\n"
        for i, (username, balance, referral_count) in enumerate(users, 1):
            username = username or f"User{i}"
            balance = round(float(balance), 2) if balance is not None else 0
            referral_count = referral_count or 0
            stats_text += f"{i}. @{username} - Баланс: {balance}$ - Рефералы: {referral_count}\n"

        await message.reply(stats_text)
    except Exception as e:
        await message.reply(f"❌ Ошибка получения статистики: {e}")

# Обработчик /set для админов
async def set_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ У вас нет прав администратора")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.reply("Использование: /set @username amount или /set telegram_id amount\nПример: /set @testuser 500 или /set 123456789 500")
        return

    identifier = args[1]
    telegram_id = None
    username = None

    # Определяем, username или telegram_id
    if identifier.isdigit():
        telegram_id = int(identifier)
    else:
        username = identifier
        if username.startswith('@'):
            username = username[1:]  # Убрать @

    try:
        amount = float(args[2])
    except ValueError:
        await message.reply("❌ Неверная сумма")
        return

    # Найти user
    try:
        if telegram_id:
            user_data = await async_get_user(telegram_id)
        else:
            user_data = await async_get_user_by_username(username)
        if not user_data:
            await message.reply("❌ Пользователь не найден")
            return

        user_telegram_id = user_data[1]  # telegram_id
        current_balance = user_data[3]  # balance
        user_username = user_data[2] or f"ID:{user_telegram_id}"  # username

        # Устанавливаем новый баланс (amount - current_balance даст нужную разницу)
        balance_diff = amount - (current_balance if current_balance is not None else 0)
        await async_update_balance(user_telegram_id, balance_diff)
        # Логируем установку баланса админом
        await async_log_action(user_telegram_id, "admin_set_balance", balance_diff, f"Баланс установлен админом {message.from_user.id} на {amount}$")
        await message.reply(f"✅ Баланс пользователя @{user_username} установлен на {amount}$")
    except Exception as e:
        await message.reply(f"❌ Ошибка базы данных: {e}")

# Обработчик /panel для админов
async def panel_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    panel_text = """🔧 <b>Админ панель</b>

📋 <b>Доступные команды:</b>

<b>💰 Управление балансом:</b>
• <code>/give @username 10.5</code> - выдать деньги пользователю
• <code>/set @username 500</code> - установить баланс пользователю

<b>🎮 Управление играми:</b>
• <code>/panel</code> - открыть админ панель

<b>📊 Статистика:</b>
• <code>/stats</code> - просмотреть статистику всех пользователей
• <code>/tasks</code> - просмотреть ежедневные задания

<b>👥 Группы:</b>
• <code>/setgroup 123456789</code> - установить группу для результатов
• <code>/setvip 123456789</code> - установить VIP группу для выплат
• <code>/getgroup</code> - посмотреть текущую группу
• <code>/getvip</code> - посмотреть текущую VIP группу

<b>🎫 Промокоды:</b>
• <code>/createpromo WELCOME 5.0 100</code> - создать промокод
• <code>/listpromo</code> - список всех промокодов

<b>💡 Шаблоны команд:</b>
• Выдача денег: <code>/give @username сумма</code>
• Установка баланса: <code>/set @username сумма</code>
• Создание промокода: <code>/createpromo КОД СУММА МАКС_АКТИВАЦИЙ</code>
• Установка группы: <code>/setgroup ID_ГРУППЫ</code>"""

    await message.reply(panel_text, reply_markup=get_admin_panel(), parse_mode="HTML")

# Обработчик /tasks для админов - просмотр списка заданий
async def tasks_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    tasks_text = "📋 Список ежедневных заданий:\n\n"
    for i, task in enumerate(DAILY_TASKS, 1):
        tasks_text += f"{i}. {task['description']} - Награда: {task['reward']}$\n"

    await message.reply(tasks_text)

# Обработчик /setgroup для админов - установка группы для результатов
async def setgroup_command(message: types.Message):
    global results_group_id
    if message.from_user.id not in ADMIN_IDS:
        return

    # Получаем ID группы из текста сообщения или из chat.id если это группа
    args = message.text.split()
    if len(args) > 1:
        try:
            group_id = int(args[1])
            results_group_id = group_id
            await async_save_setting('results_group_id', str(group_id))
            print(f"Группа установлена: {group_id}")
            await message.reply(f"✅ Группа для результатов установлена: {group_id}")
        except ValueError:
            await message.reply("❌ Неверный формат ID группы")
    elif message.chat.type in ['group', 'supergroup']:
        results_group_id = message.chat.id
        await async_save_setting('results_group_id', str(message.chat.id))
        print(f"Группа установлена из чата: {message.chat.id}")
        await message.reply(f"✅ Группа для результатов установлена: {message.chat.id}")
    else:
        await message.reply("❌ Использование: /setgroup <group_id> или отправьте команду в группе")

# Обработчик /setvip для админов - установка VIP группы для выплат
async def setvip_command(message: types.Message):
    global vip_group_id
    if message.from_user.id not in ADMIN_IDS:
        return

    # Получаем ID группы из текста сообщения или из chat.id если это группа
    args = message.text.split()
    if len(args) > 1:
        try:
            group_id = int(args[1])
            vip_group_id = group_id
            result = await async_save_setting('vip_group_id', str(group_id))
            print(f"VIP группа установлена: {group_id}, результат сохранения: {result}")
            await message.reply(f"✅ VIP группа установлена: {group_id}")
        except ValueError:
            await message.reply("❌ Неверный формат ID группы")
    elif message.chat.type in ['group', 'supergroup']:
        vip_group_id = message.chat.id
        result = await async_save_setting('vip_group_id', str(message.chat.id))
        print(f"VIP группа установлена из чата: {message.chat.id}, результат сохранения: {result}")
        await message.reply(f"✅ VIP группа установлена: {message.chat.id}")
    else:
        await message.reply("❌ Использование: /setvip <group_id> или отправьте команду в группе")

# Обработчик /getgroup для админов - проверка текущей группы
async def getgroup_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    if results_group_id:
        await message.reply(f"📋 Текущая группа для результатов: {results_group_id}")
    else:
        await message.reply("❌ Группа для результатов не установлена")

# Обработчик /getvip для админов - проверка текущей VIP группы
async def getvip_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    if vip_group_id:
        await message.reply(f"💎 Текущая VIP группа: {vip_group_id}")
    else:
        await message.reply("❌ VIP группа не установлена")

# Обработчик /getgroups для админов - проверка всех групп
async def getgroups_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    response = "📋 <b>Текущие настройки групп:</b>\n\n"

    if results_group_id:
        response += f"📊 Группа результатов: <code>{results_group_id}</code>\n"
    else:
        response += "📊 Группа результатов: <i>Не установлена</i>\n"

    if vip_group_id:
        response += f"💎 VIP группа: <code>{vip_group_id}</code>\n"
    else:
        response += "💎 VIP группа: <i>Не установлена</i>\n"

    response += "\n💡 <b>Команды для настройки:</b>\n"
    response += "• <code>/setgroup <ID></code> - установить группу результатов\n"
    response += "• <code>/setvip <ID></code> - установить VIP группу\n"
    response += "• <code>/getgroups</code> - показать текущие настройки"

    await message.reply(response, parse_mode="HTML")

# Обработчик /createpromo для админов - создание промокода
async def createpromo_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    args = message.text.split()
    if len(args) != 4:
        await message.reply("Использование: /createpromo <код> <сумма> <макс_активаций>\nПример: /createpromo WELCOME 5.0 100")
        return

    code = args[1].upper()
    try:
        reward_amount = float(args[2])
        max_activations = int(args[3])
    except ValueError:
        await message.reply("❌ Неверный формат суммы или количества активаций")
        return

    if reward_amount <= 0 or max_activations <= 0:
        await message.reply("❌ Сумма и количество активаций должны быть больше 0")
        return

    # Создаем промокод без срока действия
    promo_id = await async_create_promo_code(code, reward_amount, max_activations, None, message.from_user.id)

    if promo_id:
        await message.reply(f"✅ Промокод создан!\n\n🎫 Код: <code>{code}</code>\n💰 Сумма: {reward_amount}$\n🔢 Макс. активаций: {max_activations}", parse_mode="HTML")
    else:
        await message.reply("❌ Ошибка создания промокода")

# Обработчик /listpromo для админов - список промокодов
async def listpromo_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    promo_codes = await async_get_all_promo_codes()

    if not promo_codes:
        await message.reply("📋 Промокоды не найдены")
        return

    promo_text = "📋 <b>Список промокодов:</b>\n\n"
    for promo in promo_codes:
        promo_id, code, reward_amount, max_activations, current_activations, expires_at, created_by, created_at = promo
        status = "✅ Активен" if current_activations < max_activations else "❌ Исчерпан"
        expires = f" (до {expires_at})" if expires_at else ""
        promo_text += f"🎫 <code>{code}</code>\n💰 {reward_amount}$ | {current_activations}/{max_activations} | {status}{expires}\n\n"

    await message.reply(promo_text, parse_mode="HTML")

# Обработчик /logs для админов - просмотр логов
async def logs_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    # Rate limiting
    if not await check_command_rate_limit(message.from_user.id, 'logs'):
        await message.reply("⏳ Подождите перед повторным использованием команды")
        return

    args = message.text.split()
    limit = 20  # По умолчанию 20 записей
    username = None

    if len(args) > 1:
        try:
            if args[1].startswith('@'):
                username = args[1][1:]  # Убрать @
            else:
                limit = int(args[1])
        except ValueError:
            await message.reply("❌ Неверный формат. Используйте: /logs [username|@username] [limit]")
            return

    if len(args) > 2:
        try:
            limit = int(args[2])
        except ValueError:
            await message.reply("❌ Неверный limit")
            return

    logs = await async_get_user_logs_by_username(username, limit)

    if not logs:
        await message.reply("📋 Логи не найдены")
        return

    logs_text = "📋 <b>Логи действий пользователей:</b>\n\n"
    for log in logs:
        telegram_id, action, amount, reason, created_at = log
        # Получить username асинхронно
        user_data = await async_get_user(telegram_id)
        username_display = user_data[2] if user_data and user_data[2] else f"ID:{telegram_id}"
        amount_str = f" {amount}$" if amount != 0 else ""
        logs_text += f"👤 @{username_display}\n⚡ {action}{amount_str}\n💬 {reason}\n🕒 {created_at}\n\n"

    await message.reply(logs_text, parse_mode="HTML")
# Обработчик главного меню
async def back_to_main(callback_query: types.CallbackQuery):
    welcome_text, parse_mode = await get_welcome_text(callback_query.from_user)
    try:
        await callback_query.message.edit_text(welcome_text, reply_markup=get_main_menu(), parse_mode=parse_mode)
    except:
        try:
            media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=welcome_text, parse_mode=parse_mode)
            await callback_query.message.edit_media(media=media, reply_markup=get_main_menu())
        except:
            # Если не удается редактировать, отправить новое сообщение с фото
            await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=welcome_text, reply_markup=get_main_menu(), parse_mode=parse_mode)
    try:
        await callback_query.answer()
    except:
        pass  # Игнорировать ошибку устаревшего callback


# Обработчик кнопки "🎁 Ежедневный бонус"
async def daily_bonus_handler(callback_query: types.CallbackQuery):
    user = callback_query.from_user
    current_time = time.time()

    # Проверка на бота
    if user.is_bot:
        await callback_query.answer("❌ Боты не могут получать бонусы", show_alert=True)
        return

    # Rate limiting: не чаще чем раз в минуту
    last_attempt = daily_bonus_attempts.get(user.id, 0)
    if current_time - last_attempt < DAILY_BONUS_COOLDOWN:
        remaining = int(DAILY_BONUS_COOLDOWN - (current_time - last_attempt))
        await callback_query.answer(f"⏳ Подождите {remaining} сек перед следующей попыткой", show_alert=True)
        return

    daily_bonus_attempts[user.id] = current_time

    # Логируем попытку
    await async_log_action(user.id, "daily_bonus_attempt", 0, f"Попытка получения ежедневного бонуса")

    user_data = await async_get_user(user.id)
    task = get_daily_task()
    today = date.today()

    # Проверяем в транзакции
    try:
        # Получаем актуальные данные
        user_data = await async_get_user(user.id)
        last_completed = user_data[11] if user_data and len(user_data) > 11 else None

        if last_completed and last_completed == str(today):
            bonus_text = f"""🎁 Ежедневный бонус

✅ Задание на сегодня выполнено!

💰 Награда получена: {task['reward']}$

Завтра новое задание!"""
        else:
            # Проверяем выполнение задания
            completed = check_daily_task_completion(user_data, task) if user_data else False

            if completed:
                # Начисляем награду и обновляем дату в одной транзакции
                await async_update_balance(user.id, task['reward'])
                # Обновляем дату выполнения задания
                await async_db.log_action(user.id, "daily_task_completed", task['reward'], f"Выполнено задание: {task['description']}")

                # Логируем получение бонуса
                await async_log_action(user.id, "daily_bonus", task['reward'], f"Выполнено задание: {task['description']}")

                bonus_text = f"""🎁 Ежедневный бонус

✅ Задание выполнено!

💰 Награда: {task['reward']}$

🏆 {task['description']}
Награда: {task['reward']}$"""
            else:
                # Показываем прогресс
                progress = 0
                if task["type"] == "referrals":
                    progress = user_data[4] if user_data else 0  # referral_count
                elif task["type"] == "spent":
                    progress = user_data[7] if user_data else 0  # total_spent
                elif task["type"] == "deposited":
                    progress = user_data[6] if user_data else 0  # total_deposited
                elif task["type"] == "games":
                    progress = user_data[8] if user_data else 0  # games_played

                bonus_text = f"""🎁 Ежедневный бонус

🏆 {task['description']}
Награда: {task['reward']}$

🔜 Ваш прогресс: {progress}/{task['target']}

💡 Выполните задание, чтобы получить награду!"""

    except Exception as e:
        print(f"Ошибка в daily_bonus_handler: {e}")
        bonus_text = "❌ Произошла ошибка. Попробуйте позже."

    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=bonus_text)
        await callback_query.message.edit_media(media=media, reply_markup=get_back_button())
    except:
        await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=bonus_text, reply_markup=get_back_button())

    await callback_query.answer()


# Обработчик кнопки "👥 Реферальная система"
async def referral_handler(callback_query: types.CallbackQuery):
    user = callback_query.from_user
    user_data = await async_get_user(user.id)
    referral_count = user_data[4] if user_data else 0
    referral_balance = round(float(user_data[5]), 2) if user_data and user_data[5] is not None else 0

    referral_text = f"""👥 Реферальная система
    
    🎯 Приглашенных друзей: {referral_count}
    💰 Реферальный баланс: {referral_balance}$
    
    💡 Приглашай друзей и зарабатывай! Получай 0.3$ за первое пополнение баланса каждым твоим рефералом на сумму от 2$!
    
    🔗 Ваша реферальная ссылка:
    https://t.me/VanishCasinoBot?start={user.id}"""

    referral_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Вывести реферальные", callback_data="withdraw_referral")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=referral_text)
        await callback_query.message.edit_media(media=media, reply_markup=referral_keyboard)
    except:
        await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=referral_text, reply_markup=referral_keyboard)
    await callback_query.answer()

# Обработчик кнопки "👤 Профиль"
async def profile_handler(callback_query: types.CallbackQuery):
    user = callback_query.from_user
    stats = await get_cached_user_stats(user.id)

    if not stats:
        await callback_query.answer("❌ Профиль не найден", show_alert=True)
        return

    # Получаем задание дня
    task = get_daily_task()

    profile_text = f"""🎭 <b>ЛИЧНЫЙ ПРОФИЛЬ</b> 🎭

🎁 <b>ЕЖЕДНЕВНОЕ ЗАДАНИЕ</b>
<blockquote>{task['description']} - Награда: {task['reward']}$</blockquote>

┌─ <b>👤 ОСНОВНАЯ ИНФОРМАЦИЯ</b>
│ 👨‍💻 Пользователь: @{stats['username']}
└─📅 Регистрация: {stats['created_at']}


┌─ <b>💰 ФИНАНСОВАЯ СТАТИСТИКА</b> ─┐
│ 💵 Основной баланс: <code>{stats['balance']}$</code>
│ 💎 Реферальный баланс: <code>{stats['referral_balance']}$</code>
│ 💳 Всего пополнено: <code>{stats['total_deposited']}$</code>
│ 💸 Всего потрачено: <code>{stats['total_spent']}$</code>
└─📈 Чистая прибыль: <code>{stats['net_profit']}$</code>

┌─ <b>🎮 ИГРОВАЯ АКТИВНОСТЬ</b> ─┐
│ 🎲 Сыграно игр: <code>{stats['games_played']}</code>
│ 🎯 Примерный винрейт: <code>{stats['win_rate']:.1f}%</code>
│ 💰 Средняя ставка: <code>{stats['avg_bet']:.2f}$</code>
│ 📈 Прибыль на игру: <code>{stats['profit_per_game']:.2f}$</code>
└─🏆 Лучший результат: <i>В разработке</i>

┌─ <b>👥 РЕФЕРАЛЬНАЯ СИСТЕМА</b> ─┐
│ 🎯 Приглашенных друзей: <code>{stats['referral_count']}</code>
│ 💰 Заработано с рефералов: <code>{stats['referral_balance']}$</code>
│ 📝 Мин. пополнение: <code>2$</code>
└─🔗 Реферальная ссылка: <i>В профиле</i>"""

    profile_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main")]
    ])

    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=profile_text, parse_mode="HTML")
        await callback_query.message.edit_media(media=media, reply_markup=profile_keyboard)
    except:
        await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=profile_text, reply_markup=profile_keyboard, parse_mode="HTML")
    await callback_query.answer()

# Обработчик кнопки "📝 Изменить профиль"
async def edit_profile_handler(callback_query: types.CallbackQuery):
    edit_text = """📝 <b>Изменение профиля</b>

Выберите, что хотите изменить:"""

    edit_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Изменить имя", callback_data="change_username")],
        [InlineKeyboardButton(text="🎨 Изменить аватар", callback_data="change_avatar")],
        [InlineKeyboardButton(text="🔙 Назад в профиль", callback_data="profile")]
    ])

    try:
        await callback_query.message.edit_text(edit_text, reply_markup=edit_keyboard, parse_mode="HTML")
    except:
        await callback_query.message.answer(edit_text, reply_markup=edit_keyboard, parse_mode="HTML")
    await callback_query.answer()

# Обработчик кнопки "📊 Детальная статистика"
async def detailed_stats_handler(callback_query: types.CallbackQuery):
    user = callback_query.from_user
    user_data = await async_get_user(user.id)

    if not user_data:
        await callback_query.answer("❌ Данные не найдены", show_alert=True)
        return

    # Получаем детальную статистику
    games_played = user_data[8] if user_data[8] is not None else 0
    total_deposited = round(float(user_data[6]), 2) if user_data[6] is not None else 0
    total_spent = round(float(user_data[7]), 2) if user_data[7] is not None else 0

    # Примерные расчеты (можно доработать)
    avg_bet = total_spent / max(1, games_played)
    profit_per_game = (total_deposited - total_spent) / max(1, games_played)

    stats_text = f"""📊 <b>ДЕТАЛЬНАЯ СТАТИСТИКА</b> 📊

┌─ <b>🎮 ИГРОВАЯ СТАТИСТИКА</b> ─┐
│ 🎲 Всего игр: <code>{games_played}</code>
│ 💰 Средняя ставка: <code>{avg_bet:.2f}$</code>
│ 📈 Прибыль на игру: <code>{profit_per_game:.2f}$</code>
│ 🏆 Лучшая серия побед: <i>В разработке</i>
└─────────────────────────────┘

┌─ <b>💰 ФИНАНСОВЫЕ ПОКАЗАТЕЛИ</b> ─┐
│ 💳 Общий депозит: <code>{total_deposited}$</code>
│ 💸 Общие расходы: <code>{total_spent}$</code>
│ 📊 ROI: <code>{(total_spent / max(1, total_deposited) * 100):.1f}%</code>
│ 🎯 Эффективность: <i>Высокая</i>
└─────────────────────────────┘

💡 <i>Статистика обновляется в реальном времени</i>"""

    stats_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Графики прогресса", callback_data="progress_charts")],
        [InlineKeyboardButton(text="🔙 Назад в профиль", callback_data="profile")]
    ])

    try:
        await callback_query.message.edit_text(stats_text, reply_markup=stats_keyboard, parse_mode="HTML")
    except:
        await callback_query.message.answer(stats_text, reply_markup=stats_keyboard, parse_mode="HTML")
    await callback_query.answer()

# Заглушки для остальных функций профиля
async def transaction_history_handler(callback_query: types.CallbackQuery):
    await callback_query.answer("📜 История транзакций в разработке", show_alert=True)

async def profile_settings_handler(callback_query: types.CallbackQuery):
    await callback_query.answer("⚙️ Настройки профиля в разработке", show_alert=True)

async def change_username_handler(callback_query: types.CallbackQuery):
    await callback_query.answer("👤 Изменение имени в разработке", show_alert=True)

async def change_avatar_handler(callback_query: types.CallbackQuery):
    await callback_query.answer("🎨 Изменение аватара в разработке", show_alert=True)

async def progress_charts_handler(callback_query: types.CallbackQuery):
    await callback_query.answer("📈 Графики прогресса в разработке", show_alert=True)

# Обработчик кнопки "📊 Рейтинг"
async def rating_handler(callback_query: types.CallbackQuery):
    # Получаем топы из кэша
    top_deposited, top_spent, top_referrals = await get_cached_tops()

    rating_text = "📊 Рейтинг игроков:\n\n"

    rating_text += "💰 Топ пополнивших:\n"
    for i, (username, amount) in enumerate(top_deposited, 1):
        username = username or f"User{i}"
        rating_text += f"{i}. {username} - {amount}$\n"

    rating_text += "\n💸 Топ потративших:\n"
    for i, (username, amount) in enumerate(top_spent, 1):
        username = username or f"User{i}"
        rating_text += f"{i}. {username} - {amount}$\n"

    rating_text += "\n👥 Топ пригласивших:\n"
    for i, (username, count) in enumerate(top_referrals, 1):
        username = username or f"User{i}"
        rating_text += f"{i}. {username} - {count} чел.\n"

    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=rating_text)
        await callback_query.message.edit_media(media=media, reply_markup=get_back_button())
    except:
        await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=rating_text, reply_markup=get_back_button())
    await callback_query.answer()

# Обработчик кнопки "📈 Шансы"
async def chances_handler(callback_query: types.CallbackQuery):
    chances_text = f"""📈 Шансы выигрыша в играх:

🎲 Кости: {DUEL_WIN_CHANCE}% (x{DUEL_MULTIPLIER})
🏀 Баскетбол: {BASKETBALL_WIN_CHANCE}% (x{BASKETBALL_MULTIPLIER})
🎯 Дартс: 30% (x2.0) [faq]({DARTS_FAQ_URL})
🎰 Слоты: {SLOTS_WIN_CHANCE}% (x{SLOTS_MULTIPLIER})
🎳 Кубикии: {DICE_WIN_CHANCE}% (x{DICE_MULTIPLIER})
🃏 BlackJack: {BLACKJACK_WIN_CHANCE}% (x{BLACKJACK_MULTIPLIER})

💡 Шансы приблизительные и могут меняться.
🏀 Баскетбол - игра на предсказание результата броска.
🎰 Слоты - классическая игра с тремя барабанами.
🃏 BlackJack - классическая игра с дилером."""

    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=chances_text)
        await callback_query.message.edit_media(media=media, reply_markup=get_back_button())
    except:
        await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=chances_text, reply_markup=get_back_button())
    await callback_query.answer()

# Обработчик админ панели шансов
async def admin_chances_handler(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Доступ запрещен", show_alert=True)
        return

    chances_text = f"""🔧 Управление шансами выигрыша:

🎲 Кости: {DUEL_WIN_CHANCE}%
🏀 Баскетбол: {BASKETBALL_WIN_CHANCE}%
🎰 Слоты: {SLOTS_WIN_CHANCE}%
🎳 Кубики: {DICE_WIN_CHANCE}%
🃏 BlackJack: {BLACKJACK_WIN_CHANCE}%

Выберите игру для изменения шансов:"""

    chances_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Кости", callback_data="edit_chance_duel")],
        [InlineKeyboardButton(text="🏀 Баскетбол", callback_data="edit_chance_basketball")],
        [InlineKeyboardButton(text="🎰 Слоты", callback_data="edit_chance_slots")],
        [InlineKeyboardButton(text="🎳 Кубики", callback_data="edit_chance_dice")],
        [InlineKeyboardButton(text="🃏 BlackJack", callback_data="edit_chance_blackjack")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ])

    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=chances_text)
        await callback_query.message.edit_media(media=media, reply_markup=chances_keyboard)
    except:
        await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=chances_text, reply_markup=chances_keyboard)
    await callback_query.answer()

# Обработчик редактирования шанса дуэли
async def edit_chance_duel_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Доступ запрещен", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_duel_chance)
    try:
        await callback_query.message.edit_text(f"🎲 Введите новый шанс выигрыша для Дуэли (текущий: {DUEL_WIN_CHANCE}%):", reply_markup=get_back_button())
    except:
        await callback_query.message.answer(f"🎲 Введите новый шанс выигрыша для Дуэли (текущий: {DUEL_WIN_CHANCE}%):", reply_markup=get_back_button())
    await callback_query.answer()

# Обработчик редактирования шанса Кубикиа
async def edit_chance_dice_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Доступ запрещен", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_dice_chance)
    try:
        await callback_query.message.edit_text(f"🎳 Введите новый шанс выигрыша для Кубикиа (текущий: {DICE_WIN_CHANCE}%):", reply_markup=get_back_button())
    except:
        await callback_query.message.answer(f"🎳 Введите новый шанс выигрыша для Кубикиа (текущий: {DICE_WIN_CHANCE}%):", reply_markup=get_back_button())
    await callback_query.answer()

# Обработчик редактирования шанса баскетбола
async def edit_chance_basketball_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Доступ запрещен", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_basketball_chance)
    try:
        await callback_query.message.edit_text(f"🏀 Введите новый шанс выигрыша для Баскетбола (текущий: {BASKETBALL_WIN_CHANCE}%):", reply_markup=get_back_button())
    except:
        await callback_query.message.answer(f"🏀 Введите новый шанс выигрыша для Баскетбола (текущий: {BASKETBALL_WIN_CHANCE}%):", reply_markup=get_back_button())
    await callback_query.answer()

# Обработчик редактирования шанса слотов
async def edit_chance_slots_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Доступ запрещен", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_slots_chance)
    try:
        await callback_query.message.edit_text(f"🎰 Введите новый шанс выигрыша для Слотов (текущий: {SLOTS_WIN_CHANCE}%):", reply_markup=get_back_button())
    except:
        await callback_query.message.answer(f"🎰 Введите новый шанс выигрыша для Слотов (текущий: {SLOTS_WIN_CHANCE}%):", reply_markup=get_back_button())
    await callback_query.answer()

# Обработчик редактирования шанса blackjack
async def edit_chance_blackjack_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Доступ запрещен", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_blackjack_chance)
    try:
        await callback_query.message.edit_text(f"🃏 Введите новый шанс выигрыша для BlackJack (текущий: {BLACKJACK_WIN_CHANCE}%):", reply_markup=get_back_button())
    except:
        await callback_query.message.answer(f"🃏 Введите новый шанс выигрыша для BlackJack (текущий: {BLACKJACK_WIN_CHANCE}%):", reply_markup=get_back_button())
    await callback_query.answer()

# Обработчик ввода нового шанса дуэли
async def set_duel_chance_handler(message: types.Message, state: FSMContext):
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        new_chance = float(message.text.strip())
        if not 0 <= new_chance <= 100:
            await message.answer("❌ Шанс должен быть от 0 до 100", reply_markup=get_back_button())
            return

        global DUEL_WIN_CHANCE
        DUEL_WIN_CHANCE = new_chance
        await async_save_game_setting('duel_win_chance', new_chance)
        try:
            await message.answer(f"✅ Шанс выигрыша в Дуэли изменен на {new_chance}%", reply_markup=get_admin_panel())
        except:
            pass
        await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректное число", reply_markup=get_back_button())

# Обработчик ввода нового шанса Кубикиа
async def set_dice_chance_handler(message: types.Message, state: FSMContext):
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        new_chance = float(message.text.strip())
        if not 0 <= new_chance <= 100:
            await message.answer("❌ Шанс должен быть от 0 до 100", reply_markup=get_back_button())
            return

        global DICE_WIN_CHANCE
        DICE_WIN_CHANCE = new_chance
        await async_save_game_setting('dice_win_chance', new_chance)
        try:
            await message.answer(f"✅ Шанс выигрыша в Кубикие изменен на {new_chance}%", reply_markup=get_admin_panel())
        except:
            pass
        await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректное число", reply_markup=get_back_button())

# Обработчик ввода нового шанса баскетбола
async def set_basketball_chance_handler(message: types.Message, state: FSMContext):
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        new_chance = float(message.text.strip())
        if not 0 <= new_chance <= 100:
            await message.answer("❌ Шанс должен быть от 0 до 100", reply_markup=get_back_button())
            return

        global BASKETBALL_WIN_CHANCE
        BASKETBALL_WIN_CHANCE = new_chance
        await async_save_game_setting('basketball_win_chance', new_chance)
        try:
            await message.answer(f"✅ Шанс выигрыша в Баскетболе изменен на {new_chance}%", reply_markup=get_admin_panel())
        except:
            pass
        await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректное число", reply_markup=get_back_button())

# Обработчик ввода нового шанса слотов
async def set_slots_chance_handler(message: types.Message, state: FSMContext):
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        new_chance = float(message.text.strip())
        if not 0 <= new_chance <= 100:
            await message.answer("❌ Шанс должен быть от 0 до 100", reply_markup=get_back_button())
            return

        global SLOTS_WIN_CHANCE
        SLOTS_WIN_CHANCE = new_chance
        await async_save_game_setting('slots_win_chance', new_chance)
        try:
            await message.answer(f"✅ Шанс выигрыша в Слотах изменен на {new_chance}%", reply_markup=get_admin_panel())
        except:
            pass
        await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректное число", reply_markup=get_back_button())

# Обработчик ввода нового шанса blackjack
async def set_blackjack_chance_handler(message: types.Message, state: FSMContext):
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        new_chance = float(message.text.strip())
        if not 0 <= new_chance <= 100:
            await message.answer("❌ Шанс должен быть от 0 до 100", reply_markup=get_back_button())
            return

        global BLACKJACK_WIN_CHANCE
        BLACKJACK_WIN_CHANCE = new_chance
        await async_save_game_setting('blackjack_win_chance', new_chance)
        try:
            await message.answer(f"✅ Шанс выигрыша в BlackJack изменен на {new_chance}%", reply_markup=get_admin_panel())
        except:
            pass
        await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректное число", reply_markup=get_back_button())

# Обработчик админ панели множителей
async def admin_multiplier_handler(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Доступ запрещен", show_alert=True)
        return

    multiplier_text = f"""⚡ Управление множителями выигрыша:

🎲 Кости: x{DUEL_MULTIPLIER}
🏀 Баскетбол: x{BASKETBALL_MULTIPLIER}
🎰 Слоты: x{SLOTS_MULTIPLIER}
🎳 Кубики: x{DICE_MULTIPLIER}
🃏 BlackJack: x{BLACKJACK_MULTIPLIER}

Выберите игру для изменения множителя:"""

    multiplier_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Кости", callback_data="edit_multiplier_duel")],
        [InlineKeyboardButton(text="🏀 Баскетбол", callback_data="edit_multiplier_basketball")],
        [InlineKeyboardButton(text="🎰 Слоты", callback_data="edit_multiplier_slots")],
        [InlineKeyboardButton(text="🎳 Кубики", callback_data="edit_multiplier_dice")],
        [InlineKeyboardButton(text="🃏 BlackJack", callback_data="edit_multiplier_blackjack")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ])

    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=multiplier_text)
        await callback_query.message.edit_media(media=media, reply_markup=multiplier_keyboard)
    except:
        await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=multiplier_text, reply_markup=multiplier_keyboard)
    await callback_query.answer()

# Обработчик возврата в админ панель
async def admin_panel_handler(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Доступ запрещен", show_alert=True)
        return

    media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption="🔧 Админ панель")
    await callback_query.message.edit_media(media=media, reply_markup=get_admin_panel())
    await callback_query.answer()

# Обработчик кнопки "📊 Статистика"
async def admin_stats_handler(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Доступ запрещен", show_alert=True)
        return

    # Получаем всех пользователей асинхронно
    users = await async_get_user_stats(limit=50)

    if not users:
        stats_text = "📊 <b>Статистика пользователей</b>\n\n❌ Пользователей не найдено"
    else:
        stats_text = "📊 <b>Статистика пользователей</b>\n\n"
        for i, (username, balance, referral_count) in enumerate(users, 1):
            username = username or f"User{i}"
            balance = round(float(balance), 2) if balance is not None else 0
            referral_count = referral_count or 0
            stats_text += f"{i}. @{username} - Баланс: {balance}$ - Рефералы: {referral_count}\n"

    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=stats_text, parse_mode="HTML")
        await callback_query.message.edit_media(media=media, reply_markup=get_back_button())
    except:
        await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=stats_text, reply_markup=get_back_button(), parse_mode="HTML")
    await callback_query.answer()

# Обработчик кнопки "💰 Установить баланс"
async def admin_set_balance_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Доступ запрещен", show_alert=True)
        return

    set_text = """💰 <b>Установка баланса</b>

Введите команду в формате:
/set @username сумма

Пример: /set @testuser 500

Или используйте команду /set напрямую в чате."""

    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=set_text, parse_mode="HTML")
        await callback_query.message.edit_media(media=media, reply_markup=get_back_button())
    except:
        await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=set_text, reply_markup=get_back_button(), parse_mode="HTML")
    await callback_query.answer()

# Обработчик редактирования множителя дуэли
async def edit_multiplier_duel_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Доступ запрещен", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_duel_multiplier)
    try:
        await callback_query.message.edit_text(f"🎲 Введите новый множитель для Дуэли (текущий: x{DUEL_MULTIPLIER}):", reply_markup=get_back_button())
    except:
        await callback_query.message.answer(f"🎲 Введите новый множитель для Дуэли (текущий: x{DUEL_MULTIPLIER}):", reply_markup=get_back_button())
    await callback_query.answer()

# Обработчик редактирования множителя Кубикиа
async def edit_multiplier_dice_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Доступ запрещен", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_dice_multiplier)
    try:
        await callback_query.message.edit_text(f"🎳 Введите новый множитель для Кубикиа (текущий: x{DICE_MULTIPLIER}):", reply_markup=get_back_button())
    except:
        await callback_query.message.answer(f"🎳 Введите новый множитель для Кубикиа (текущий: x{DICE_MULTIPLIER}):", reply_markup=get_back_button())
    await callback_query.answer()

# Обработчик редактирования множителя баскетбола
async def edit_multiplier_basketball_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Доступ запрещен", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_basketball_multiplier)
    try:
        await callback_query.message.edit_text(f"🏀 Введите новый множитель для Баскетбола (текущий: x{BASKETBALL_MULTIPLIER}):", reply_markup=get_back_button())
    except:
        await callback_query.message.answer(f"🏀 Введите новый множитель для Баскетбола (текущий: x{BASKETBALL_MULTIPLIER}):", reply_markup=get_back_button())
    await callback_query.answer()

# Обработчик редактирования множителя слотов
async def edit_multiplier_slots_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Доступ запрещен", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_slots_multiplier)
    try:
        await callback_query.message.edit_text(f"🎰 Введите новый множитель для Слотов (текущий: x{SLOTS_MULTIPLIER}):", reply_markup=get_back_button())
    except:
        await callback_query.message.answer(f"🎰 Введите новый множитель для Слотов (текущий: x{SLOTS_MULTIPLIER}):", reply_markup=get_back_button())
    await callback_query.answer()

# Обработчик редактирования множителя blackjack
async def edit_multiplier_blackjack_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Доступ запрещен", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_blackjack_multiplier)
    try:
        await callback_query.message.edit_text(f"🃏 Введите новый множитель для BlackJack (текущий: x{BLACKJACK_MULTIPLIER}):", reply_markup=get_back_button())
    except:
        await callback_query.message.answer(f"🃏 Введите новый множитель для BlackJack (текущий: x{BLACKJACK_MULTIPLIER}):", reply_markup=get_back_button())
    await callback_query.answer()

# Обработчик ввода нового множителя дуэли
async def set_duel_multiplier_handler(message: types.Message, state: FSMContext):
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        new_multiplier = float(message.text.strip())
        if new_multiplier <= 0:
            await message.answer("❌ Множитель должен быть больше 0", reply_markup=get_back_button())
            return

        global DUEL_MULTIPLIER
        DUEL_MULTIPLIER = new_multiplier
        await async_save_game_setting('duel_multiplier', new_multiplier)
        try:
            await message.answer(f"✅ Множитель выигрыша в Дуэли изменен на x{new_multiplier}", reply_markup=get_admin_panel())
        except:
            pass
        await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректное число", reply_markup=get_back_button())

# Обработчик ввода нового множителя Кубикиа
async def set_dice_multiplier_handler(message: types.Message, state: FSMContext):
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        new_multiplier = float(message.text.strip())
        if new_multiplier <= 0:
            await message.answer("❌ Множитель должен быть больше 0", reply_markup=get_back_button())
            return

        global DICE_MULTIPLIER
        DICE_MULTIPLIER = new_multiplier
        await async_save_game_setting('dice_multiplier', new_multiplier)
        try:
            await message.answer(f"✅ Множитель выигрыша в Кубикие изменен на x{new_multiplier}", reply_markup=get_admin_panel())
        except:
            pass
        await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректное число", reply_markup=get_back_button())

# Обработчик ввода нового множителя баскетбола
async def set_basketball_multiplier_handler(message: types.Message, state: FSMContext):
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        new_multiplier = float(message.text.strip())
        if new_multiplier <= 0:
            await message.answer("❌ Множитель должен быть больше 0", reply_markup=get_back_button())
            return

        global BASKETBALL_MULTIPLIER
        BASKETBALL_MULTIPLIER = new_multiplier
        await async_save_game_setting('basketball_multiplier', new_multiplier)
        try:
            await message.answer(f"✅ Множитель выигрыша в Баскетболе изменен на x{new_multiplier}", reply_markup=get_admin_panel())
        except:
            pass
        await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректное число", reply_markup=get_back_button())

# Обработчик ввода нового множителя слотов
async def set_slots_multiplier_handler(message: types.Message, state: FSMContext):
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        new_multiplier = float(message.text.strip())
        if new_multiplier <= 0:
            await message.answer("❌ Множитель должен быть больше 0", reply_markup=get_back_button())
            return

        global SLOTS_MULTIPLIER
        SLOTS_MULTIPLIER = new_multiplier
        await async_save_game_setting('slots_multiplier', new_multiplier)
        try:
            await message.answer(f"✅ Множитель выигрыша в Слотах изменен на x{new_multiplier}", reply_markup=get_admin_panel())
        except:
            pass
        await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректное число", reply_markup=get_back_button())

# Обработчик ввода нового множителя blackjack
async def set_blackjack_multiplier_handler(message: types.Message, state: FSMContext):
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        new_multiplier = float(message.text.strip())
        if new_multiplier <= 0:
            await message.answer("❌ Множитель должен быть больше 0", reply_markup=get_back_button())
            return

        global BLACKJACK_MULTIPLIER
        BLACKJACK_MULTIPLIER = new_multiplier
        await async_save_game_setting('blackjack_multiplier', new_multiplier)
        try:
            await message.answer(f"✅ Множитель выигрыша в BlackJack изменен на x{new_multiplier}", reply_markup=get_admin_panel())
        except:
            pass
        await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректное число", reply_markup=get_back_button())

# Обработчик кнопки "🎮 Играть"
async def play_handler(callback_query: types.CallbackQuery):
    games_text = "🎮 Выберите игру:"
    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=games_text)
        await callback_query.message.edit_media(media=media, reply_markup=get_games_menu())
    except:
        await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=games_text, reply_markup=get_games_menu())
    await callback_query.answer()

# Обработчик кнопки "Кости"
async def duel_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(DuelStates.waiting_for_bet)

    user = callback_query.from_user
    user_data = await async_get_user(user.id)
    balance = round(float(user_data[3]), 2) if user_data and user_data[3] is not None else 0

    duel_text = f"""💎 Баланс: {balance}$

🎲 Кости [faq]({DUEL_FAQ_URL})

♻️ Множитель: x{DUEL_MULTIPLIER}

💰 Введите ставку в $:"""

    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=duel_text, parse_mode="Markdown")
        await callback_query.message.edit_media(media=media, reply_markup=get_back_button())
        message_id = callback_query.message.message_id
    except:
        new_msg = await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=duel_text, reply_markup=get_back_button(), parse_mode="Markdown")
        message_id = new_msg.message_id

    await state.update_data(message_id=message_id, chat_id=callback_query.message.chat.id)
    await callback_query.answer()

# Обработчик кнопки "Кубики"
async def dice_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(DiceStates.waiting_for_bet)

    user = callback_query.from_user
    user_data = await async_get_user(user.id)
    balance = round(float(user_data[3]), 2) if user_data and user_data[3] is not None else 0

    dice_text = f"""💎 Баланс: {balance}$

🎳 Кубики [faq]({DICE_FAQ_URL})

♻️ Множитель: x{DICE_MULTIPLIER}

💰 Введите ставку в $:"""

    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=dice_text, parse_mode="Markdown")
        await callback_query.message.edit_media(media=media, reply_markup=get_back_button())
        message_id = callback_query.message.message_id
    except:
        new_msg = await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=dice_text, reply_markup=get_back_button(), parse_mode="Markdown")
        message_id = new_msg.message_id

    await state.update_data(message_id=message_id, chat_id=callback_query.message.chat.id)
    await callback_query.answer()



# Обработчик ввода ставки в дуэли
async def duel_bet_handler(message: types.Message, state: FSMContext):
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    try:
        bet = float(message.text.strip())
        if bet < 1.0:
            # Получаем данные для редактирования
            data = await state.get_data()
            message_id = data.get('message_id')
            chat_id = data.get('chat_id')

            error_text = """❌ <b>Ошибка ставки</b>

Ставка должна быть не менее 1.0$"""

            if message_id and chat_id:
                try:
                    media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=error_text, parse_mode="HTML")
                    await bot.edit_message_media(
                        chat_id=chat_id,
                        message_id=message_id,
                        media=media,
                        reply_markup=get_back_button()
                    )
                except Exception as e:
                    print(f"Ошибка редактирования сообщения: {e}")
                    await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
            else:
                await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
            return

        user_data = await async_get_user(message.from_user.id)
        balance = round(float(user_data[3]), 2) if user_data and user_data[3] is not None else 0

        if bet > balance:
            await message.answer("❌ Недостаточно средств", reply_markup=get_back_button())
            return

        data = await state.get_data()
        message_id = data.get('message_id')

        confirm_text = f"""💎 Баланс: {balance}$

🎲 Кости [faq]({DUEL_FAQ_URL})

♻️ Множитель: x{DUEL_MULTIPLIER}

💰 Ставка: {bet}$"""

        confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Бросить кости", callback_data=f"duel_confirm_{bet}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="game_duel")]
        ])

        # Редактируем сообщение с подтверждением ставки
        if message_id:
            media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=confirm_text, parse_mode="Markdown")
            await bot.edit_message_media(
                chat_id=message.chat.id,
                message_id=message_id,
                media=media,
                reply_markup=confirm_keyboard
            )
        else:
            await message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=confirm_text, reply_markup=confirm_keyboard, parse_mode="Markdown")

        await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректную сумму", reply_markup=get_back_button())

# Обработчик кнопки "Баскетбол"
async def basketball_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(BasketballStates.waiting_for_bet)

    user = callback_query.from_user
    user_data = await async_get_user(user.id)
    balance = round(float(user_data[3]), 2) if user_data and user_data[3] is not None else 0

    basketball_text = f"""💎 Баланс: {balance}$

🏀 Баскетбол [faq]({BASKETBALL_FAQ_URL})

🎯 Угадайте результат броска мяча в кольцо
♻️ Множитель: x{BASKETBALL_MULTIPLIER}

💰 Введите ставку в $:"""

    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=basketball_text, parse_mode="Markdown")
        await callback_query.message.edit_media(media=media, reply_markup=get_back_button())
        message_id = callback_query.message.message_id
    except:
        new_msg = await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=basketball_text, reply_markup=get_back_button(), parse_mode="Markdown")
        message_id = new_msg.message_id

    await state.update_data(message_id=message_id, chat_id=callback_query.message.chat.id)
    # Отправить результат в группу
    if results_group_id:
        try:
            group_text = f"🃏 BlackJack\n👤 {user.first_name or user.username}\n💰 Ставка: {bet}$\nПеребор! -{bet}$"
            await bot.send_message(chat_id=results_group_id, text=group_text)
        except:
            pass

    await callback_query.answer()

# Обработчик ввода ставки в баскетбол
async def basketball_bet_handler(message: types.Message, state: FSMContext):
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    try:
        bet = float(message.text.strip())
        if bet < 1.0:
            # Получаем данные для редактирования
            data = await state.get_data()
            message_id = data.get('message_id')
            chat_id = data.get('chat_id')

            error_text = """❌ <b>Ошибка ставки</b>

Ставка должна быть не менее 1.0$"""

            if message_id and chat_id:
                try:
                    media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=error_text, parse_mode="HTML")
                    await bot.edit_message_media(
                        chat_id=chat_id,
                        message_id=message_id,
                        media=media,
                        reply_markup=get_back_button()
                    )
                except Exception as e:
                    print(f"Ошибка редактирования сообщения: {e}")
                    await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
            else:
                await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
            return

        user_data = await async_get_user(message.from_user.id)
        balance = round(float(user_data[3]), 2) if user_data and user_data[3] is not None else 0

        if bet > balance:
            await message.answer("❌ Недостаточно средств", reply_markup=get_back_button())
            return

        data = await state.get_data()
        message_id = data.get('message_id')

        confirm_text = f"""💎 Баланс: {balance}$

🏀 Баскетбол [faq]({BASKETBALL_FAQ_URL})

♻️ Множитель: x{BASKETBALL_MULTIPLIER}
💰 Ставка: {bet}$

🎯 Выберите предсказание:"""

        confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏀 Бросок", callback_data=f"basketball_predict_hit_{bet}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="game_basketball")]
        ])

        # Редактируем сообщение с подтверждением ставки
        if message_id:
            media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=confirm_text, parse_mode="Markdown")
            await bot.edit_message_media(
                chat_id=message.chat.id,
                message_id=message_id,
                media=media,
                reply_markup=confirm_keyboard
            )
        else:
            await message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=confirm_text, reply_markup=confirm_keyboard, parse_mode="Markdown")

        await state.clear()

    except ValueError:
        # Получаем данные для редактирования
        data = await state.get_data()
        message_id = data.get('message_id')
        chat_id = data.get('chat_id')

        error_text = """❌ <b>Ошибка ввода</b>

Введите корректную сумму (например: 5 или 5.5)"""

        if message_id and chat_id:
            try:
                media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=error_text, parse_mode="HTML")
                await bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message_id,
                    media=media,
                    reply_markup=get_back_button()
                )
            except Exception as e:
                print(f"Ошибка редактирования сообщения: {e}")
                await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
        else:
            await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")

# Обработчик предсказания "Попадет"
async def basketball_predict_hit_handler(callback_query: types.CallbackQuery):
    await process_basketball_prediction(callback_query, "hit")


# Основная функция обработки предсказания в баскетбол
async def process_basketball_prediction(callback_query: types.CallbackQuery, prediction: str):
    data = callback_query.data.split("_")
    bet = float(data[3])  # bet находится на позиции 3 (basketball_predict_hit_123.45)

    user = callback_query.from_user

    print(f"Начало баскетбола: user={user.id}, bet={bet}, prediction={prediction}")

    # Генерация случайного результата броска (50/50 с rigged логикой)
    # Rigged логика: шанс выигрыша игрока BASKETBALL_WIN_CHANCE%
    actual_result = "hit" if random.random() < (BASKETBALL_WIN_CHANCE / 100) else "miss"

    # Определяем, правильно ли предсказал игрок
    prediction_correct = (prediction == actual_result)

    # Имитация броска с разными исходами
    if actual_result == "hit":
        result_emoji = "🎉"
        result_text = "ГОЛ! Мяч в кольце! 🏀"
    else:
        result_emoji = "😞"
        result_text = "Мимо! Мяч не попал в кольцо 🏀"

    # Увеличиваем счетчик игр
    await async_update_games_played(user.id)

    # Определение результата игры
    if prediction_correct:
        # Выигрыш - предсказание верное
        winnings = bet * BASKETBALL_MULTIPLIER
        await async_update_balance(user.id, winnings)
        game_result = f"✅ Вы угадали! +{winnings}$"
        status_emoji = "🎉"
    else:
        # Проигрыш - предсказание неверное
        await async_update_balance(user.id, -bet)
        game_result = f"❌ Не угадали! -{bet}$"
        status_emoji = "😞"

    # Показать предсказание игрока
    prediction_text = "🎯 Попадет"

    print(f"Результат баскетбола: actual_result={actual_result}, prediction_correct={prediction_correct}, game_result={game_result}")

    # Отправить результат в группу
    print(f"Проверка отправки в группу: results_group_id = {results_group_id}")
    if results_group_id:
        print(f"Отправка результата баскетбола в группу {results_group_id}")
        try:
            username = f"@{user.username}" if user.username else user.first_name or "Неизвестно"
            if "+" in game_result:
                winnings = game_result.split()[-1]
                winnings_label = "Выигрыш"
            elif "-" in game_result:
                winnings = f"-{bet}$"
                winnings_label = "Проигрыш"
            else:
                winnings = "0$"
                winnings_label = "Выигрыш"
            group_text = f"""📎 Игра: Баскетбол
📱 Пользователь: {username}
💰 Ставка: {bet}$
⚡Результат: {result_text} {game_result}
💲 {winnings_label}: {winnings}"""
            photo_url = WIN_IMAGE_URL if winnings_label == "Выигрыш" else LOSE_IMAGE_URL
            await bot.send_photo(chat_id=results_group_id, photo=photo_url, caption=group_text)
            print("Результат баскетбола отправлен успешно")
        except Exception as e:
            print(f"Ошибка отправки в группу: {e}")
            pass
    else:
        print("Группа для результатов не установлена")

    # Текст с результатом броска
    game_text = f"""{result_text}

Вы предсказали: {prediction_text}

{game_result}"""

    # Клавиатура для итогов
    result_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏀 Играть еще", callback_data="game_basketball")],
        [InlineKeyboardButton(text="🔙 В меню игр", callback_data="play")]
    ])

    # Показать результат сразу
    photo_url = WIN_IMAGE_URL if prediction_correct else LOSE_IMAGE_URL
    try:
        media = InputMediaPhoto(media=photo_url, caption=game_text)
        await bot.edit_message_media(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            media=media,
            reply_markup=result_keyboard
        )
    except:
        await callback_query.message.answer_photo(photo=photo_url, caption=game_text, reply_markup=result_keyboard)


    await callback_query.answer()

# Обработчик кнопки "Слоты"
async def slots_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(SlotsStates.waiting_for_bet)

    user = callback_query.from_user
    user_data = await async_get_user(user.id)
    balance = round(float(user_data[3]), 2) if user_data and user_data[3] is not None else 0

    slots_text = f"""💎 Баланс: {balance}$

🎰 Слоты [faq]({SLOTS_FAQ_URL})

♻️ Множитель: x{SLOTS_MULTIPLIER}

💰 Введите ставку в $:"""

    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=slots_text, parse_mode="Markdown")
        await callback_query.message.edit_media(media=media, reply_markup=get_back_button())
        message_id = callback_query.message.message_id
    except:
        new_msg = await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=slots_text, reply_markup=get_back_button(), parse_mode="Markdown")
        message_id = new_msg.message_id

    await state.update_data(message_id=message_id, chat_id=callback_query.message.chat.id)
    await callback_query.answer()

# Обработчик кнопки "BlackJack"
async def blackjack_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(BlackjackStates.waiting_for_bet)

    user = callback_query.from_user
    user_data = await async_get_user(user.id)
    balance = round(float(user_data[3]), 2) if user_data and user_data[3] is not None else 0

    blackjack_text = f"""💎 Баланс: {balance}$

🃏 BlackJack [faq]({BLACKJACK_FAQ_URL})

♻️ Множитель: x{BLACKJACK_MULTIPLIER}

💰 Введите ставку в $:"""

    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=blackjack_text, parse_mode="Markdown")
        await callback_query.message.edit_media(media=media, reply_markup=get_back_button())
        message_id = callback_query.message.message_id
    except:
        new_msg = await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=blackjack_text, reply_markup=get_back_button(), parse_mode="Markdown")
        message_id = new_msg.message_id

    await state.update_data(message_id=message_id, chat_id=callback_query.message.chat.id)
    await callback_query.answer()

# Обработчик ввода ставки в слоты
async def slots_bet_handler(message: types.Message, state: FSMContext):
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    try:
        bet = float(message.text.strip())
        if bet < 1.0:
            # Получаем данные для редактирования
            data = await state.get_data()
            message_id = data.get('message_id')
            chat_id = data.get('chat_id')

            error_text = """❌ <b>Ошибка ставки</b>

Ставка должна быть не менее 1.0$"""

            if message_id and chat_id:
                try:
                    media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=error_text, parse_mode="HTML")
                    await bot.edit_message_media(
                        chat_id=chat_id,
                        message_id=message_id,
                        media=media,
                        reply_markup=get_back_button()
                    )
                except Exception as e:
                    print(f"Ошибка редактирования сообщения: {e}")
                    await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
            else:
                await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
            return

        user_data = await async_get_user(message.from_user.id)
        balance = round(float(user_data[3]), 2) if user_data and user_data[3] is not None else 0

        if bet > balance:
            # Получаем данные для редактирования
            data = await state.get_data()
            message_id = data.get('message_id')
            chat_id = data.get('chat_id')

            error_text = f"""❌ <b>Недостаточно средств</b>

Ваш баланс: <code>{balance}$</code>
Запрошенная ставка: <code>{bet}$</code>"""

            if message_id and chat_id:
                try:
                    media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=error_text, parse_mode="HTML")
                    await bot.edit_message_media(
                        chat_id=chat_id,
                        message_id=message_id,
                        media=media,
                        reply_markup=get_back_button()
                    )
                except Exception as e:
                    print(f"Ошибка редактирования сообщения: {e}")
                    await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
            else:
                await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
            return

        data = await state.get_data()
        message_id = data.get('message_id')

        confirm_text = f"""💎 Баланс: {balance}$

🎰 Слоты [faq]({SLOTS_FAQ_URL})

♻️ Множитель: x{SLOTS_MULTIPLIER}

💰 Ставка: {bet}$"""

        confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎰 Крутить", callback_data=f"slots_spin_{bet}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="game_slots")]
        ])

        # Редактируем сообщение с подтверждением ставки
        if message_id:
            media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=confirm_text, parse_mode="Markdown")
            await bot.edit_message_media(
                chat_id=message.chat.id,
                message_id=message_id,
                media=media,
                reply_markup=confirm_keyboard
            )
        else:
            await message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=confirm_text, reply_markup=confirm_keyboard, parse_mode="Markdown")

        await state.clear()

    except ValueError:
        # Получаем данные для редактирования
        data = await state.get_data()
        message_id = data.get('message_id')
        chat_id = data.get('chat_id')

        error_text = """❌ <b>Ошибка ввода</b>

Введите корректную сумму (например: 5 или 5.5)"""

        if message_id and chat_id:
            try:
                media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=error_text, parse_mode="HTML")
                await bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message_id,
                    media=media,
                    reply_markup=get_back_button()
                )
            except Exception as e:
                print(f"Ошибка редактирования сообщения: {e}")
                await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
        else:
            await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")

# Обработчик ввода ставки в blackjack
async def blackjack_bet_handler(message: types.Message, state: FSMContext):
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    try:
        bet = float(message.text.strip())
        if bet < 1.0:
            # Получаем данные для редактирования
            data = await state.get_data()
            message_id = data.get('message_id')
            chat_id = data.get('chat_id')

            error_text = """❌ <b>Ошибка ставки</b>

Ставка должна быть не менее 1.0$"""

            if message_id and chat_id:
                try:
                    media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=error_text, parse_mode="HTML")
                    await bot.edit_message_media(
                        chat_id=chat_id,
                        message_id=message_id,
                        media=media,
                        reply_markup=get_back_button()
                    )
                except Exception as e:
                    print(f"Ошибка редактирования сообщения: {e}")
                    await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
            else:
                await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
            return

        user_data = await async_get_user(message.from_user.id)
        balance = round(float(user_data[3]), 2) if user_data and user_data[3] is not None else 0

        if bet > balance:
            # Получаем данные для редактирования
            data = await state.get_data()
            message_id = data.get('message_id')
            chat_id = data.get('chat_id')

            error_text = f"""❌ <b>Недостаточно средств</b>

Ваш баланс: <code>{balance}$</code>
Запрошенная ставка: <code>{bet}$</code>"""

            if message_id and chat_id:
                try:
                    media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=error_text, parse_mode="HTML")
                    await bot.edit_message_media(
                        chat_id=chat_id,
                        message_id=message_id,
                        media=media,
                        reply_markup=get_back_button()
                    )
                except Exception as e:
                    print(f"Ошибка редактирования сообщения: {e}")
                    await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
            else:
                await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
            return

        data = await state.get_data()
        message_id = data.get('message_id')

        # Начало игры blackjack
        # Раздаем карты
        deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4  # Упрощенная колода
        random.shuffle(deck)

        player_cards = [deck.pop(), deck.pop()]
        dealer_cards = [deck.pop(), deck.pop()]

        player_score = sum(player_cards)
        dealer_score = sum(dealer_cards)

        game_text = f"""💎 Баланс: {balance}$

🃏 BlackJack [faq]({BLACKJACK_FAQ_URL})

♻️ Множитель: x{BLACKJACK_MULTIPLIER}
💰 Ставка: {bet}$

Ваши карты: {player_cards} (Ваши карты: {player_score})
Карта дилера: {dealer_cards[0]} (Карты диллера: ?)"""

        game_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🃏 Еще карту", callback_data=f"blackjack_hit_{bet}_{player_cards[0]}_{player_cards[1]}_{dealer_cards[0]}_{dealer_cards[1]}"),
                InlineKeyboardButton(text="⏹️ Стоп", callback_data=f"blackjack_stand_{bet}_{player_cards[0]}_{player_cards[1]}_{dealer_cards[0]}_{dealer_cards[1]}")
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="game_blackjack")]
        ])

        # Редактируем сообщение с игрой
        if message_id:
            media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=game_text, parse_mode="Markdown")
            await bot.edit_message_media(
                chat_id=message.chat.id,
                message_id=message_id,
                media=media,
                reply_markup=game_keyboard
            )
        else:
            await message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=game_text, reply_markup=game_keyboard, parse_mode="Markdown")

        await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректную сумму", reply_markup=get_back_button())

# Обработчик "Еще карту" в blackjack
async def blackjack_hit_handler(callback_query: types.CallbackQuery):
    data = callback_query.data.split("_")
    bet = float(data[2])
    player_cards = [int(x) for x in data[3:-2]]
    dealer_cards = [int(data[-2]), int(data[-1])]

    user = callback_query.from_user

    print(f"Начало blackjack hit: user={user.id}, bet={bet}, player_cards={player_cards}, dealer_cards={dealer_cards}")

    # Добавляем карту игроку
    deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
    random.shuffle(deck)
    # Убираем уже розданные карты
    for card in player_cards + dealer_cards:
        if card in deck:
            deck.remove(card)

    new_card = deck.pop()
    player_cards.append(new_card)
    player_score = sum(player_cards)

    if player_score > 21:
        # Перебор
        await async_update_games_played(user.id)
        await async_update_balance(user.id, -bet)
        result_text = f"Перебор! -{bet}$"
        result_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🃏 Играть еще", callback_data="game_blackjack")],
            [InlineKeyboardButton(text="🔙 В меню игр", callback_data="play")]
        ])

        photo_url = LOSE_IMAGE_URL
        game_caption = f"""Ваши карты: {player_cards} (Очки: {player_score})
Карты дилера: {dealer_cards} (Очки: {sum(dealer_cards)})

{result_text}"""
        media = InputMediaPhoto(media=photo_url, caption=game_caption, parse_mode="Markdown")
        await bot.edit_message_media(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            media=media,
            reply_markup=result_keyboard
        )

        print(f"Результат blackjack hit (перебор): player_score={player_score}, result_text={result_text}")

        # Отправить результат в группу
        print(f"Проверка отправки в группу: results_group_id = {results_group_id}")
        if results_group_id:
            print(f"Отправка результата blackjack в группу {results_group_id}")
            try:
                username = f"@{user.username}" if user.username else user.first_name or "Неизвестно"
                if "+" in result_text:
                    winnings = result_text.split()[-1]
                    winnings_label = "Выигрыш"
                elif "-" in result_text:
                    winnings = f"-{bet}$"
                    winnings_label = "Проигрыш"
                else:
                    winnings = "0$"
                    winnings_label = "Выигрыш"
                group_text = f"""📎 Игра: BlackJack
📱 Пользователь: {username}
💰 Ставка: {bet}$
⚡Результат: {result_text}
💲 {winnings_label}: {winnings}"""
                photo_url = WIN_IMAGE_URL if winnings_label == "Выигрыш" else LOSE_IMAGE_URL
                await bot.send_photo(chat_id=results_group_id, photo=photo_url, caption=group_text)
                print("Результат blackjack отправлен успешно")
            except Exception as e:
                print(f"Ошибка отправки в группу: {e}")
                pass
        else:
            print("Группа для результатов не установлена")
    else:
        # Продолжаем игру
        game_text = f"""Ваши карты: {player_cards} (Очки: {player_score})
Карта дилера: {dealer_cards[0]} (Очки: ?)"""

        game_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🃏 Еще карту", callback_data=f"blackjack_hit_{bet}_{'_'.join(map(str, player_cards))}_{dealer_cards[0]}_{dealer_cards[1]}"),
                InlineKeyboardButton(text="⏹️ Стоп", callback_data=f"blackjack_stand_{bet}_{'_'.join(map(str, player_cards))}_{dealer_cards[0]}_{dealer_cards[1]}")
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="game_blackjack")]
        ])
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=game_text, parse_mode="Markdown")
        await bot.edit_message_media(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            media=media,
            reply_markup=game_keyboard
        )

    await callback_query.answer()

# Обработчик "Стоп" в blackjack
async def blackjack_stand_handler(callback_query: types.CallbackQuery):
    data = callback_query.data.split("_")
    bet = float(data[2])
    player_cards = [int(x) for x in data[3:-2]]
    dealer_cards = [int(data[-2]), int(data[-1])]

    user = callback_query.from_user

    print(f"Начало blackjack stand: user={user.id}, bet={bet}, player_cards={player_cards}, dealer_cards={dealer_cards}")

    # Дилер берет карты до 17
    deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
    random.shuffle(deck)
    # Убираем уже розданные карты
    for card in player_cards + dealer_cards:
        if card in deck:
            deck.remove(card)

    dealer_score = sum(dealer_cards)
    while dealer_score < 17:
        new_card = deck.pop()
        dealer_cards.append(new_card)
        dealer_score = sum(dealer_cards)

    player_score = sum(player_cards)

    await async_update_games_played(user.id)

    if dealer_score > 21 or player_score > dealer_score:
        # Выигрыш игрока
        winnings = bet * BLACKJACK_MULTIPLIER
        await async_update_balance(user.id, winnings)
        result_text = f"🎉 Вы выиграли! +{winnings}$"
    elif player_score == dealer_score:
        # Ничья
        result_text = f"🤝 Ничья! Ставка возвращена"
    else:
        # Проигрыш
        await async_update_balance(user.id, -bet)
        result_text = f"😞 Вы проиграли! -{bet}$"

    result_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🃏 Играть еще", callback_data="game_blackjack")],
        [InlineKeyboardButton(text="🔙 В меню игр", callback_data="play")]
    ])

    photo_url = WIN_IMAGE_URL if dealer_score > 21 or player_score > dealer_score else LOSE_IMAGE_URL if player_score < dealer_score else WIN_IMAGE_URL  # Ничья как выигрыш
    game_caption = f"""Ваши карты: {player_cards} (Очки: {player_score})
Карты дилера: {dealer_cards} (Очки: {dealer_score})

{result_text}"""
    media = InputMediaPhoto(media=photo_url, caption=game_caption, parse_mode="Markdown")
    await bot.edit_message_media(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        media=media,
        reply_markup=result_keyboard
    )

    print(f"Результат blackjack stand: player_score={player_score}, dealer_score={dealer_score}, result_text={result_text}")

    # Отправить результат в группу
    print(f"Проверка отправки в группу: results_group_id = {results_group_id}")
    if results_group_id:
        print(f"Отправка результата blackjack в группу {results_group_id}")
        try:
            username = f"@{user.username}" if user.username else user.first_name or "Неизвестно"
            if "+" in result_text:
                winnings = result_text.split()[-1]
                winnings_label = "Выигрыш"
            elif "-" in result_text:
                winnings = f"-{bet}$"
                winnings_label = "Проигрыш"
            else:
                winnings = "0$"
                winnings_label = "Выигрыш"
            group_text = f"""📎 Игра: BlackJack
📱 Пользователь: {username}
💰 Ставка: {bet}$
⚡Результат: {result_text}
💲 {winnings_label}: {winnings}"""
            photo_url = WIN_IMAGE_URL if winnings_label == "Выигрыш" else LOSE_IMAGE_URL
            await bot.send_photo(chat_id=results_group_id, photo=photo_url, caption=group_text)
            print("Результат blackjack отправлен успешно")
        except Exception as e:
            print(f"Ошибка отправки в группу: {e}")
            pass
    else:
        print("Группа для результатов не установлена")

    await callback_query.answer()

# Обработчик крутки слотов
async def slots_spin_handler(callback_query: types.CallbackQuery):
    data = callback_query.data.split("_")
    bet = float(data[2])

    user = callback_query.from_user

    print(f"Начало слотов: user={user.id}, bet={bet}")

    # Генерация результата слотов
    # Rigged логика: шанс выигрыша SLOTS_WIN_CHANCE%
    win_chance = random.random() < (SLOTS_WIN_CHANCE / 100)

    # Символы для слотов
    symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎", "7️⃣"]

    if win_chance:
        # Выигрыш - все три символа одинаковые
        winning_symbol = random.choice(symbols)
        result = [winning_symbol, winning_symbol, winning_symbol]
    else:
        # Проигрыш - разные символы
        result = []
        for _ in range(3):
            symbol = random.choice(symbols)
            # Избегаем трех одинаковых в проигрыше
            while len(result) == 2 and result[0] == result[1] == symbol:
                symbol = random.choice(symbols)
            result.append(symbol)

    # Увеличиваем счетчик игр
    await async_update_games_played(user.id)

    # Определение результата
    if win_chance:
        # Выигрыш
        winnings = bet * SLOTS_MULTIPLIER
        await async_update_balance(user.id, winnings)
        result_text = f"🎉 ДЖЕКПОТ! +{winnings}$"
        status_emoji = "🎰"
    else:
        # Проигрыш
        await async_update_balance(user.id, -bet)
        result_text = f"😞 Попробуй еще! -{bet}$"
        status_emoji = "💸"

    print(f"Результат слотов: win_chance={win_chance}, result={result}, result_text={result_text}")

    # Отправить результат в группу
    print(f"Проверка отправки в группу: results_group_id = {results_group_id}")
    if results_group_id:
        print(f"Отправка результата слотов в группу {results_group_id}")
        try:
            username = f"@{user.username}" if user.username else user.first_name or "Неизвестно"
            if "+" in result_text:
                winnings = result_text.split()[-1]
                winnings_label = "Выигрыш"
            elif "-" in result_text:
                winnings = f"-{bet}$"
                winnings_label = "Проигрыш"
            else:
                winnings = "0$"
                winnings_label = "Выигрыш"
            group_text = f"""📎 Игра: Слоты
📱 Пользователь: {username}
💰 Ставка: {bet}$
⚡Результат: {result_text}
💲 {winnings_label}: {winnings}"""
            photo_url = WIN_IMAGE_URL if winnings_label == "Выигрыш" else LOSE_IMAGE_URL
            await bot.send_photo(chat_id=results_group_id, photo=photo_url, caption=group_text)
            print("Результат слотов отправлен успешно")
        except Exception as e:
            print(f"Ошибка отправки в группу: {e}")
            pass
    else:
        print("Группа для результатов не установлена")

    # Показываем результат мгновенно
    final_result = f"🎰 | {result[0]} | {result[1]} | {result[2]} |\n\n{result_text}"

    # Клавиатура для итогов
    result_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Крутить еще", callback_data="game_slots")],
        [InlineKeyboardButton(text="🔙 В меню игр", callback_data="play")]
    ])

    # Финальное сообщение
    photo_url = WIN_IMAGE_URL if win_chance else LOSE_IMAGE_URL
    final_caption = f"🎰 <b>РЕЗУЛЬТАТ:</b>\n\n{final_result}"
    try:
        media = InputMediaPhoto(media=photo_url, caption=final_caption, parse_mode="HTML")
        await bot.edit_message_media(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            media=media,
            reply_markup=result_keyboard
        )
    except:
        await callback_query.message.answer_photo(photo=photo_url, caption=final_caption, reply_markup=result_keyboard, parse_mode="HTML")

    await callback_query.answer()

# Обработчик ввода ставки в Кубикие
async def dice_bet_handler(message: types.Message, state: FSMContext):
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    try:
        bet = float(message.text.strip())
        if bet < 1.0:
            # Получаем данные для редактирования
            data = await state.get_data()
            message_id = data.get('message_id')
            chat_id = data.get('chat_id')

            error_text = """❌ <b>Ошибка ставки</b>

Ставка должна быть не менее 1.0$"""

            if message_id and chat_id:
                try:
                    media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=error_text, parse_mode="HTML")
                    await bot.edit_message_media(
                        chat_id=chat_id,
                        message_id=message_id,
                        media=media,
                        reply_markup=get_back_button()
                    )
                except Exception as e:
                    print(f"Ошибка редактирования сообщения: {e}")
                    await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
            else:
                await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
            return

        user_data = await async_get_user(message.from_user.id)
        balance = round(float(user_data[3]), 2) if user_data and user_data[3] is not None else 0

        if bet > balance:
            await message.answer("❌ Недостаточно средств", reply_markup=get_back_button())
            return

        data = await state.get_data()
        message_id = data.get('message_id')

        select_text = f"""💎 Баланс: {balance}$

🎳 Кубики [faq]({DICE_FAQ_URL})

♻️ Множитель: x{DICE_MULTIPLIER}

💰 Ставка: {bet}$

Выберите цвет Кубикиа:"""

        color_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔴 Красный", callback_data=f"dice_color_red_{bet}"),
                InlineKeyboardButton(text="🟢 Зеленый", callback_data=f"dice_color_green_{bet}"),
                InlineKeyboardButton(text="🔵 Синий", callback_data=f"dice_color_blue_{bet}")
            ],
            [
                InlineKeyboardButton(text="🟣 Розовый", callback_data=f"dice_color_pink_{bet}"),
                InlineKeyboardButton(text="⚫ Черный", callback_data=f"dice_color_black_{bet}"),
                InlineKeyboardButton(text="🟤 Коричневый", callback_data=f"dice_color_brown_{bet}")
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="game_dice")]
        ])

        # Редактируем сообщение с выбором цвета Кубикиа
        if message_id:
            media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=select_text, parse_mode="Markdown")
            await bot.edit_message_media(
                chat_id=message.chat.id,
                message_id=message_id,
                media=media,
                reply_markup=color_keyboard
            )
        else:
            await message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=select_text, reply_markup=color_keyboard, parse_mode="Markdown")

        await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректную сумму", reply_markup=get_back_button())

# Обработчик подтверждения дуэли
async def duel_confirm_handler(callback_query: types.CallbackQuery):
    data = callback_query.data.split("_")
    bet = float(data[2])

    user = callback_query.from_user

    print(f"Начало дуэли: user={user.id}, bet={bet}")

    # Генерация Кубикиов
    user_dice = random.randint(1, 6)
    bot_dice = random.randint(1, 6)

    # Rigged логика: шанс выигрыша DUEL_WIN_CHANCE%
    win_chance = random.random() < (DUEL_WIN_CHANCE / 100)

    if win_chance:
        # Гарантировать выигрыш
        if user_dice <= bot_dice:
            user_dice = bot_dice + random.randint(1, 6 - bot_dice) if bot_dice < 6 else 6
    else:
        # Гарантировать проигрыш
        if user_dice >= bot_dice:
            bot_dice = user_dice + random.randint(1, 6 - user_dice) if user_dice < 6 else 6

    # Увеличиваем счетчик игр
    await async_update_games_played(user.id)

    # Определение результата
    if user_dice > bot_dice:
        # Выигрыш
        winnings = bet * DUEL_MULTIPLIER
        await async_update_balance(user.id, winnings)
        result_text = f"🎉 Вы выиграли! +{winnings}$"
    else:
        # Проигрыш
        await async_update_balance(user.id, -bet)
        result_text = f"😞 Вы проиграли! -{bet}$"

    print(f"Результат дуэли: user_dice={user_dice}, bot_dice={bot_dice}, result={result_text}")

    # Отправить результат в группу
    print(f"Проверка отправки в группу: results_group_id = {results_group_id}")
    if results_group_id:
        print(f"Отправка результата дуэли в группу {results_group_id}")
        try:
            username = f"@{user.username}" if user.username else user.first_name or "Неизвестно"
            if "+" in result_text:
                winnings = result_text.split()[-1]
                winnings_label = "Выигрыш"
            elif "-" in result_text:
                winnings = f"-{bet}$"
                winnings_label = "Проигрыш"
            else:
                winnings = "0$"
                winnings_label = "Выигрыш"
            group_text = f"""📎 Игра: Дуэль
📱 Пользователь: {username}
💰 Ставка: {bet}$
⚡Результат: {result_text}
💲 {winnings_label}: {winnings}"""
            photo_url = WIN_IMAGE_URL if winnings_label == "Выигрыш" else LOSE_IMAGE_URL
            await bot.send_photo(chat_id=results_group_id, photo=photo_url, caption=group_text)
            print("Результат дуэли отправлен успешно")
        except Exception as e:
            print(f"Ошибка отправки в группу: {e}")
            pass
    else:
        print("Группа для результатов не установлена")

    # Текст с кубиками
    game_text = f"""🎲 Ваш кубик: {user_dice}
🎲 Кубик бота: {bot_dice}

{result_text}"""

    # Клавиатура для итогов
    result_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Играть еще", callback_data="game_duel")],
        [InlineKeyboardButton(text="🔙 В меню игр", callback_data="play")]
    ])

    # Показать результат сразу
    photo_url = WIN_IMAGE_URL if user_dice > bot_dice else LOSE_IMAGE_URL
    try:
        media = InputMediaPhoto(media=photo_url, caption=game_text)
        await bot.edit_message_media(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            media=media,
            reply_markup=result_keyboard
        )
    except:
        await callback_query.message.answer_photo(photo=photo_url, caption=game_text, reply_markup=result_keyboard)

    # Отправить результат в группу
    if results_group_id:
        try:
            username = f"@{user.username}" if user.username else user.first_name or "Неизвестно"
            if "+" in game_result:
                winnings = game_result.split()[-1]
                winnings_label = "Выигрыш"
            elif "-" in game_result:
                winnings = f"-{bet}$"
                winnings_label = "Проигрыш"
            else:
                winnings = "0$"
                winnings_label = "Выигрыш"
            group_text = f"""📎 Игра: Баскетбол
📱 Пользователь: {username}
💰 Ставка: {bet}$
⚡Результат: {result_text} {game_result}
💲 {winnings_label}: {winnings}"""
            photo_url = WIN_IMAGE_URL if winnings_label == "Выигрыш" else LOSE_IMAGE_URL
            await bot.send_photo(chat_id=results_group_id, photo=photo_url, caption=group_text)
            print("Результат баскетбола отправлен успешно")
        except Exception as e:
            print(f"Ошибка отправки в группу: {e}")
            pass
    else:
        print("Группа для результатов не установлена")

    await callback_query.answer()

# Обработчик кнопки "💰 Пополнить"
async def deposit_handler(callback_query: types.CallbackQuery):
    deposit_text = """💰 Выберите сумму пополнения:

Быстрые суммы:"""

    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=deposit_text)
        await callback_query.message.edit_media(media=media, reply_markup=get_deposit_menu())
    except:
        await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=deposit_text, reply_markup=get_deposit_menu())
    await callback_query.answer()

# Обработчик быстрых сумм
async def deposit_amount_handler(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data
    if data == "dep_custom":
        custom_text = "📝 Введите сумму пополнения в $:"
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=custom_text)
        await callback_query.message.edit_media(media=media, reply_markup=get_deposit_back_button())
        await state.set_state(DepositStates.waiting_for_amount)
        return
    
    amount = int(data.split("_")[1])
    await process_deposit(callback_query, amount)

# Обработчик ввода суммы
async def process_custom_amount(message: types.Message, state: FSMContext):
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    print(f"Получено сообщение: {message.text}")

    try:
        # Очистка текста от символов, кроме цифр и точки
        clean_text = ''.join(c for c in message.text.strip() if c.isdigit() or c == '.')

        if not clean_text:
            await message.answer("❌ Введите корректную сумму", reply_markup=get_deposit_back_button())
            return

        amount = float(clean_text)
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0", reply_markup=get_deposit_back_button())
            return

        # Завершаем состояние
        await state.clear()

        # Создаем фейковый callback_query для совместимости
        class FakeCallback:
            def __init__(self, message):
                self.message = message
                self.from_user = message.from_user

        fake_callback = FakeCallback(message)
        try:
            await process_deposit(fake_callback, amount)
        except:
            await message.answer(f"✅ Пополнение на {amount}$ создано", reply_markup=get_main_menu())

    except ValueError as e:
        print(f"Ошибка парсинга: {e}")
        await message.answer("❌ Введите корректную сумму (например: 5, 5.5, 5$)", reply_markup=get_deposit_back_button())

# Процесс создания платежа
async def process_deposit(callback_query, amount):
    user_telegram_id = callback_query.from_user.id
    user_db = await async_get_user(user_telegram_id)

    if not user_db:
        try:
            if hasattr(callback_query, 'message') and callback_query.message:
                await callback_query.message.answer("❌ Ошибка: пользователь не найден", reply_markup=get_back_button())
            else:
                await callback_query.message.answer("❌ Ошибка: пользователь не найден", reply_markup=get_back_button())
        except:
            await callback_query.message.answer("❌ Ошибка: пользователь не найден", reply_markup=get_back_button())
        return

    user_id = user_db[0]

    # Создаем инвойс через Crypto Bot
    invoice = crypto_bot.create_invoice(amount)

    if not invoice or not invoice.get('result'):
        try:
            if hasattr(callback_query, 'message') and callback_query.message:
                await callback_query.message.answer("❌ Ошибка создания платежа", reply_markup=get_back_button())
            else:
                await callback_query.message.answer("❌ Ошибка создания платежа", reply_markup=get_back_button())
        except:
            await callback_query.message.answer("❌ Ошибка создания платежа", reply_markup=get_back_button())
        return

    invoice_data = invoice['result']
    invoice_id = invoice_data['invoice_id']
    pay_url = invoice_data['pay_url']

    # Сохраняем платеж в БД
    await async_db.create_payment(user_id, amount, invoice_id)

    # Отправляем чек пользователю
    pay_text = f"""💰 Пополнение баланса на {amount}$

Для оплаты перейдите по кнопке ниже:
После оплаты средства будут автоматически зачислены на ваш баланс."""

    pay_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=pay_url)],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_{invoice_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="deposit")]
    ])

    # Проверяем, можем ли мы редактировать сообщение
    try:
        if hasattr(callback_query, 'message') and callback_query.message:
            media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=pay_text, parse_mode="Markdown")
            await callback_query.message.edit_media(media=media, reply_markup=pay_keyboard)
        else:
            await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=pay_text, reply_markup=pay_keyboard, parse_mode="Markdown")
    except:
        try:
            await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=pay_text, reply_markup=pay_keyboard, parse_mode="Markdown")
        except:
            if hasattr(callback_query, 'message') and callback_query.message:
                await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=pay_text, reply_markup=pay_keyboard, parse_mode="Markdown")

# Проверка оплаты - ИСПРАВЛЕННАЯ ВЕРСИЯ
async def check_payment(callback_query: types.CallbackQuery):
    invoice_id = callback_query.data.split("_")[1]

    # Получаем статус инвойса
    invoices_data = crypto_bot.get_invoices([invoice_id])

    if not invoices_data or not invoices_data.get('result') or not invoices_data['result'].get('items'):
        await callback_query.answer("❌ Ошибка проверки платежа", show_alert=True)
        return

    invoice_item = invoices_data['result']['items'][0]
    invoice_status = invoice_item['status']

    if invoice_status == 'paid':
        print(f"Платеж подтвержден: invoice_id={invoice_id}")

        # Получаем платеж из БД по invoice_id асинхронно
        payment = await async_get_payment_by_invoice(invoice_id)

        if not payment:
            print(f"Платеж не найден в БД: invoice_id={invoice_id}")
            await callback_query.answer("❌ Платеж не найден", show_alert=True)
            return

        user_id, amount, payment_status = payment
        print(f"Найден платеж: user_id={user_id}, amount={amount}, status={payment_status}")

        # Проверяем, не был ли платеж уже обработан
        if payment_status == 'paid':
            print(f"Платеж уже обработан: invoice_id={invoice_id}")
            await callback_query.answer("✅ Платеж уже подтвержден", show_alert=True)
            return

        # Получаем telegram_id по user_id асинхронно
        telegram_id = await async_get_telegram_id_by_user_id(user_id)

        if not telegram_id:
            print(f"Пользователь не найден: user_id={user_id}")
            await callback_query.answer("❌ Пользователь не найден", show_alert=True)
            return

        print(f"Найден telegram_id: {telegram_id}")

        # Проверяем, что пользователь тот же
        if telegram_id != callback_query.from_user.id:
            print(f"Несовпадение telegram_id: expected {telegram_id}, got {callback_query.from_user.id}")
            await callback_query.answer("❌ Это не ваш платеж", show_alert=True)
            return

        # Начисляем средства на баланс через db
        await async_update_balance(telegram_id, amount)
        await invalidate_balance_cache(telegram_id)

        # Проверяем, есть ли реферер, и начисляем ему реферальный бонус (0.3$ только за первое пополнение реферала на сумму >= 2$)
        user_data = await async_get_user(telegram_id)
        if (user_data and len(user_data) > 9 and user_data[9] and  # referrer_id exists
            (len(user_data) <= 10 or user_data[10] == 0) and    # referral_bonus_given == 0
            amount >= REFERRAL_MIN_DEPOSIT):                    # сумма пополнения >= минимальной
            referrer_id = user_data[9]  # Исправлено: referrer_id находится в user_data[9]
            referral_bonus = REFERRAL_BONUS
            await async_update_referral_balance(referrer_id, referral_bonus)
            # Логируем реферальный бонус
            await async_log_action(referrer_id, "referral_bonus", referral_bonus, f"Бонус за реферала {telegram_id} пополнившего {amount}$")
            # Отмечаем, что бонус уже начислен для этого реферала
            await async_mark_referral_bonus_given(telegram_id)
            print(f"Реферальный бонус начислен: referrer_id={referrer_id}, bonus={referral_bonus}, deposit_amount={amount}")

        # Обновляем статус платежа в БД
        await async_update_payment_status(invoice_id, 'paid')

        print(f"Средства начислены: telegram_id={telegram_id}, amount={amount}")

        # Показываем сообщение об успешной оплате
        success_text = f"""✅ <b>ОПЛАТА УСПЕШНО ПОДТВЕРЖДЕНА!</b>

💰 Сумма: <code>{amount}$</code>
💎 Средства зачислены на ваш баланс

<i>Добро пожаловать в главное меню!</i>"""

        try:
            # Обновляем сообщение с новым балансом и перенаправляем в меню
            welcome_text, parse_mode = await get_welcome_text(callback_query.from_user)
            media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=welcome_text, parse_mode=parse_mode)
            await callback_query.message.edit_media(media=media, reply_markup=get_main_menu())
        except Exception as e:
            print(f"Ошибка обновления сообщения: {e}")
            # Если не удалось обновить, отправляем новое сообщение
            welcome_text, parse_mode = await get_welcome_text(callback_query.from_user)
            await callback_query.message.answer_photo(
                photo=BACKGROUND_IMAGE_URL,
                caption=welcome_text,
                reply_markup=get_main_menu(),
                parse_mode=parse_mode
            )

        await callback_query.answer("✅ Платеж подтвержден! Средства зачислены", show_alert=True)

    else:
        await callback_query.answer("⏳ Платеж еще не подтвержден", show_alert=True)

# Обработчик вывода реферальных средств
async def withdraw_referral_handler(callback_query: types.CallbackQuery):
    user = callback_query.from_user
    user_data = await async_get_user(user.id)
    referral_balance = round(float(user_data[5]), 2) if user_data and user_data[5] is not None else 0

    if referral_balance <= 0:
        await callback_query.answer("❌ Недостаточно реферальных средств", show_alert=True)
        return

    # Переводим реферальные средства на основной баланс
    await async_update_balance(user.id, referral_balance)
    await async_update_referral_balance(user.id, -referral_balance)
    # Логируем перевод реферальных средств
    await async_log_action(user.id, "referral_withdraw", referral_balance, f"Перевод реферальных средств на основной баланс")

    await callback_query.answer(f"✅ Реферальные средства ({referral_balance}$) переведены на основной баланс", show_alert=True)

    # Обновляем сообщение
    await referral_handler(callback_query)

# Обработчик кнопки "👥 Группы"
async def groups_handler(callback_query: types.CallbackQuery):
    groups_text = """👥 <b>Наши группы и каналы</b>

Присоединяйтесь к нашим сообществам для получения актуальной информации, новостей и общения с другими игроками!
<blockquote>ps: там дают часто промокоды</blockquote>"""

    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=groups_text, parse_mode="HTML")
        await callback_query.message.edit_media(media=media, reply_markup=get_groups_menu())
    except:
        await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=groups_text, reply_markup=get_groups_menu(), parse_mode="HTML")
    await callback_query.answer()

# Обработчик кнопки "🎫 Промокоды"
async def promo_codes_handler(callback_query: types.CallbackQuery):
    promo_text = """🎫 <b>Промокоды</b>

Активируйте промокод и получите бонус на баланс!

💡 <i>Промокоды можно получить в наших группах или от администрации</i>"""

    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=promo_text, parse_mode="HTML")
        await callback_query.message.edit_media(media=media, reply_markup=get_promo_menu())
    except:
        await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=promo_text, reply_markup=get_promo_menu(), parse_mode="HTML")
    try:
        await callback_query.answer()
    except:
        pass  # Игнорировать ошибку устаревшего callback

# Обработчик кнопки "🎫 Активировать промокод"
async def activate_promo_handler(callback_query: types.CallbackQuery, state: FSMContext):
    activate_text = """🎫 <b>Активация промокода</b>

Введите код промокода:"""

    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=activate_text, parse_mode="HTML")
        await callback_query.message.edit_media(media=media, reply_markup=get_back_button())
        message_id = callback_query.message.message_id
    except:
        new_msg = await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=activate_text, reply_markup=get_back_button(), parse_mode="HTML")
        message_id = new_msg.message_id

    await state.set_state(PromoStates.waiting_for_promo_code)
    await state.update_data(message_id=message_id)
    await callback_query.answer()

# Обработчик кнопки "💸 Вывести"
async def withdraw_handler(callback_query: types.CallbackQuery, state: FSMContext):
    user = callback_query.from_user
    user_data = await async_get_user(user.id)
    balance = round(float(user_data[3]), 2) if user_data and user_data[3] is not None else 0

    if balance <= 0:
        await callback_query.answer("❌ Недостаточно средств для вывода", show_alert=True)
        return

    await state.set_state(WithdrawStates.waiting_for_withdraw_amount)

    withdraw_text = f"""💸 <b>Вывод средств</b>

    💰 Ваш баланс: <code>{balance}$</code>

    📝 Введите сумму для вывода в $:

    <i>Минимальная сумма: 2$</i>
    <i>Обязательно: сыграть хотя бы 1 игру</i>
    <i>Средства будут отправлены на ваш баланс в @CryptoBot</i>"""

    try:
        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=withdraw_text, parse_mode="HTML")
        await callback_query.message.edit_media(media=media, reply_markup=get_back_button())
        message_id = callback_query.message.message_id
    except:
        new_msg = await callback_query.message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=withdraw_text, reply_markup=get_back_button(), parse_mode="HTML")
        message_id = new_msg.message_id

    await state.update_data(message_id=message_id)
    await callback_query.answer()

# Обработчик ввода суммы вывода
async def withdraw_amount_handler(message: types.Message, state: FSMContext):
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    try:
        amount = float(message.text.strip())
        if amount <= 0:
            # Получаем ID сообщения для редактирования
            data = await state.get_data()
            message_id = data.get('message_id')

            error_text = """❌ <b>Ошибка ввода</b>

Сумма должна быть больше 0"""

            if message_id:
                try:
                    media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=error_text, parse_mode="HTML")
                    await bot.edit_message_media(
                        chat_id=message.chat.id,
                        message_id=message_id,
                        media=media,
                        reply_markup=get_back_button()
                    )
                except Exception as e:
                    print(f"Ошибка редактирования сообщения: {e}")
                    await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
            else:
                await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
            return

        if amount < 2:
            # Получаем ID сообщения для редактирования
            data = await state.get_data()
            message_id = data.get('message_id')

            error_text = """❌ <b>Минимальная сумма вывода: 2$</b>

Введите сумму не менее 2$"""

            if message_id:
                try:
                    media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=error_text, parse_mode="HTML")
                    await bot.edit_message_media(
                        chat_id=message.chat.id,
                        message_id=message_id,
                        media=media,
                        reply_markup=get_back_button()
                    )
                except Exception as e:
                    print(f"Ошибка редактирования сообщения: {e}")
                    await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
            else:
                await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
            return

    except ValueError:
        # Получаем ID сообщения для редактирования
        data = await state.get_data()
        message_id = data.get('message_id')

        error_text = """❌ <b>Ошибка ввода</b>

Введите корректную сумму (например: 5 или 5.5)"""

        if message_id:
            try:
                media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=error_text, parse_mode="HTML")
                await bot.edit_message_media(
                    chat_id=message.chat.id,
                    message_id=message_id,
                    media=media,
                    reply_markup=get_back_button()
                )
            except Exception as e:
                print(f"Ошибка редактирования сообщения: {e}")
                await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
        else:
            await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
        return

    # Получаем баланс пользователя
    user_data = await async_get_user(message.from_user.id)
    balance = round(float(user_data[3]), 2) if user_data and user_data[3] is not None else 0

    # Проверяем, что пользователь сыграл хотя бы 1 игру
    games_played = user_data[8] if user_data and len(user_data) > 8 and user_data[8] is not None else 0
    if games_played < 1:
        # Получаем ID сообщения для редактирования
        data = await state.get_data()
        message_id = data.get('message_id')

        error_text = """❌ <b>Требование не выполнено</b>

Для вывода средств необходимо сыграть хотя бы 1 игру

<i>Сыграйте в любую игру и попробуйте снова</i>"""

        if message_id:
            try:
                media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=error_text, parse_mode="HTML")
                await bot.edit_message_media(
                    chat_id=message.chat.id,
                    message_id=message_id,
                    media=media,
                    reply_markup=get_back_button()
                )
            except Exception as e:
                print(f"Ошибка редактирования сообщения: {e}")
                await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
        else:
            await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
        return

    if amount > balance:
        # Получаем ID сообщения для редактирования
        data = await state.get_data()
        message_id = data.get('message_id')

        error_text = f"""❌ <b>Недостаточно средств</b>

Ваш баланс: <code>{balance}$</code>
Запрошенная сумма: <code>{amount}$</code>

<i>Недостаточно средств для вывода</i>"""

        if message_id:
            try:
                media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=error_text, parse_mode="HTML")
                await bot.edit_message_media(
                    chat_id=message.chat.id,
                    message_id=message_id,
                    media=media,
                    reply_markup=get_back_button()
                )
            except Exception as e:
                print(f"Ошибка редактирования сообщения: {e}")
                await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
        else:
            await message.answer(error_text, reply_markup=get_back_button(), parse_mode="HTML")
        return

    # Создаем заявку на вывод
    user_id = user_data[0]
    withdrawal_id = await async_create_withdrawal(user_id, amount, "crypto_bot_wallet")

    # Проверяем баланс бота перед выводом
    bot_balance = crypto_bot.get_balance("USDT")
    if bot_balance and bot_balance.get('result'):
        # result - это список словарей, находим USDT
        usdt_balance = None
        for currency in bot_balance['result']:
            if currency.get('currency_code') == 'USDT':
                usdt_balance = currency
                break

        if usdt_balance:
            available_balance = float(usdt_balance.get('available', 0))
            if available_balance < amount:
                # Недостаточно средств у бота
                await async_update_withdrawal_status(withdrawal_id, 'failed')
                error_text = """❌ <b>Ошибка вывода</b>

У бота недостаточно средств для вывода.
Попробуйте позже или обратитесь в поддержку.

Средства возвращены на ваш баланс."""

                # Получаем ID сообщения для редактирования
                data = await state.get_data()
                message_id = data.get('message_id')

                if message_id:
                    try:
                        media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=error_text, parse_mode="HTML")
                        await bot.edit_message_media(
                            chat_id=message.chat.id,
                            message_id=message_id,
                            media=media,
                            reply_markup=get_main_menu()
                        )
                    except Exception as e:
                        print(f"Ошибка редактирования сообщения: {e}")
                        await message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=error_text, reply_markup=get_main_menu(), parse_mode="HTML")
                else:
                    await message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=error_text, reply_markup=get_main_menu(), parse_mode="HTML")
                return
        else:
            # Не найден баланс USDT
            print("Не найден баланс USDT в ответе API")

    # Списываем средства с баланса
    await async_update_balance(message.from_user.id, -amount)
    await invalidate_balance_cache(message.from_user.id)

    print(f"Попытка перевода: user_id={message.from_user.id}, amount={amount}, withdrawal_id={withdrawal_id}")

    # Создаем перевод через Crypto Bot на внутренний баланс пользователя
    # Используем telegram_id как user_id для Crypto Bot
    transfer_result = crypto_bot.create_transfer(
        user_id=message.from_user.id,  # ID пользователя в Telegram как ID в Crypto Bot
        asset="USDT",
        amount=amount,  # Без str(), передаем как число
        spend_id=f"withdraw_{withdrawal_id}",
        comment=None,  # Убираем комментарий из-за ограничения для новых приложений
        disable_send_notification=False
    )

    print(f"Результат перевода: {transfer_result}")

    if transfer_result and isinstance(transfer_result, dict) and transfer_result.get('result'):
        transfer_data = transfer_result['result']
        transfer_id = transfer_data.get('transfer_id')
        await async_update_withdrawal_status(withdrawal_id, 'completed', transfer_id)

        success_text = f"""✅ <b>Вывод успешно выполнен!</b>

💰 Сумма: <code>{amount}$</code>
🤖 Средства отправлены на ваш баланс в @CryptoBot

📋 ID транзакции: <code>{withdrawal_id}</code>

💡 <b>Средства автоматически отправлены на ваш счет</b>"""

        # Получаем ID сообщения для редактирования
        data = await state.get_data()
        message_id = data.get('message_id')

        if message_id:
            try:
                media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=success_text, parse_mode="HTML")
                await bot.edit_message_media(
                    chat_id=message.chat.id,
                    message_id=message_id,
                    media=media,
                    reply_markup=get_main_menu()
                )
            except Exception as e:
                print(f"Ошибка редактирования сообщения: {e}")
                await message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=success_text, reply_markup=get_main_menu(), parse_mode="HTML")
        else:
            await message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=success_text, reply_markup=get_main_menu(), parse_mode="HTML")
    else:
        # Если перевод не удался, возвращаем средства
        await async_update_balance(message.from_user.id, amount)
        await invalidate_balance_cache(message.from_user.id)
        await async_update_withdrawal_status(withdrawal_id, 'failed')

        # Показываем детали ошибки
        error_details = transfer_result if isinstance(transfer_result, str) else "Неизвестная ошибка"

        # Проверяем тип ошибки
        if "METHOD_DISABLED" in error_details:
            solution = """1. Перейдите в @CryptoBot
2. Зайдите в настройки бота
3. Включите метод "Transfer" в разделе ограничений
4. Попробуйте вывести средства снова"""
        else:
            solution = """1. Перейдите в @CryptoBot
2. Создайте кошелек
3. Попробуйте вывести средства снова"""

        error_text = f"""❌ <b>Ошибка вывода</b>

Не удалось отправить средства.
<b>Детали ошибки:</b> {error_details}

💡 <b>Решение:</b>
{solution}

Средства возвращены на ваш баланс."""

        # Получаем ID сообщения для редактирования
        data = await state.get_data()
        message_id = data.get('message_id')

        if message_id:
            try:
                media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=error_text, parse_mode="HTML")
                await bot.edit_message_media(
                    chat_id=message.chat.id,
                    message_id=message_id,
                    media=media,
                    reply_markup=get_main_menu()
                )
            except Exception as e:
                print(f"Ошибка редактирования сообщения: {e}")
                await message.answer(error_text, reply_markup=get_main_menu(), parse_mode="HTML")
        else:
            await message.answer(error_text, reply_markup=get_main_menu(), parse_mode="HTML")

    # Отправить результат в VIP группу только при успешном выводе
    print(f"Проверка условия отправки: transfer_result={transfer_result}, type={type(transfer_result)}")
    if transfer_result and isinstance(transfer_result, dict) and transfer_result.get('result'):
        print(f"Условие выполнено, проверка VIP группы: vip_group_id = {vip_group_id}, type = {type(vip_group_id)}")
        if vip_group_id:
            print(f"Отправка результата вывода в VIP группу {vip_group_id}")
            try:
                username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name or "Неизвестно"
                winnings = f"{amount}$"
                winnings_label = "Вывод"
                group_text = f"""💸 Вывод средств
📱 Пользователь: {username}
💰 Сумма: {amount}$
⚡Результат: Успешно
💲 {winnings_label}: {winnings}"""
                print(f"Отправка сообщения в группу {vip_group_id} с текстом: {group_text}")
                result = await bot.send_message(chat_id=vip_group_id, text=group_text)
                print(f"Результат отправки: {result}")
                print("Результат вывода отправлен успешно")
            except Exception as e:
                print(f"Ошибка отправки в VIP группу: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("VIP группа не установлена")
    else:
        print("Условие отправки не выполнено")

    await state.clear()

# Асинхронная функция для обработки платежей в фоне
async def process_payment_async(telegram_id, amount):
    """Асинхронная обработка платежа для ускорения отклика"""
    try:
        # Начисляем средства
        await async_update_balance(telegram_id, amount)
        await invalidate_balance_cache(telegram_id)

        # Проверяем реферер
        user_data = await async_get_user(telegram_id)
        if (user_data and len(user_data) > 9 and user_data[9] and  # referrer_id exists
            (len(user_data) <= 10 or user_data[10] == 0) and    # referral_bonus_given == 0
            amount >= REFERRAL_MIN_DEPOSIT):                    # сумма пополнения >= минимальной
            referrer_id = user_data[9]  # Исправлено: referrer_id находится в user_data[9]
            referral_bonus = REFERRAL_BONUS
            await async_update_referral_balance(referrer_id, referral_bonus)
            # Отмечаем, что бонус уже начислен для этого реферала
            await async_mark_referral_bonus_given(telegram_id)
            print(f"Реферальный бонус начислен асинхронно: referrer_id={referrer_id}, bonus={referral_bonus}, deposit_amount={amount}")

        print(f"Средства начислены асинхронно: telegram_id={telegram_id}, amount={amount}")
    except Exception as e:
        print(f"Ошибка асинхронной обработки платежа: {e}")

async def async_mark_referral_bonus_given(telegram_id):
    """Отметка реферального бонуса как начисленного"""
    await async_db.mark_referral_bonus_given(telegram_id)

# Проверка pending платежей пользователя
async def check_pending_payments(telegram_id):
    pending_payments = await async_get_pending_payments(telegram_id)

    for (invoice_id,) in pending_payments:
        # Проверяем статус инвойса
        invoices_data = crypto_bot.get_invoices([invoice_id])

        if invoices_data and invoices_data.get('result') and invoices_data['result'].get('items'):
            invoice_item = invoices_data['result']['items'][0]
            invoice_status = invoice_item['status']

            if invoice_status == 'paid':
                # Получаем данные платежа асинхронно
                amount = await async_get_payment_amount_by_invoice(invoice_id)

                if amount is not None:
                    # Запускаем асинхронную обработку платежа
                    asyncio.create_task(process_payment_async(telegram_id, amount))
                    await async_update_payment_status(invoice_id, 'paid')
                    print(f"Платеж отправлен на асинхронную обработку: telegram_id={telegram_id}, amount={amount}")

# Заглушка для остальных кнопок
async def other_callbacks(callback_query: types.CallbackQuery):
    await callback_query.answer("🔧 Функция в разработке", show_alert=True)


# Обработчик выбора цвета Кубикиа
async def dice_color_handler(callback_query: types.CallbackQuery):
    data = callback_query.data.split("_")
    color = data[2]
    bet = float(data[3])

    user = callback_query.from_user

    print(f"Начало кубиков: user={user.id}, bet={bet}, color={color}")

    # Цвета и их соответствия
    color_to_number = {
        "red": 1,
        "green": 2,
        "blue": 3,
        "pink": 4,
        "black": 5,
        "brown": 6
    }
    number_to_color = {
        1: ("🔴 Красный", "red"),
        2: ("🟢 Зеленый", "green"),
        3: ("🔵 Синий", "blue"),
        4: ("🟣 Розовый", "pink"),
        5: ("⚫ Черный", "black"),
        6: ("🟤 Коричневый", "brown")
    }

    chosen_number = color_to_number[color]
    chosen_color_text = number_to_color[chosen_number][0]

    # Бросок Кубикиа
    dice_result = random.randint(1, 6)

    # Rigged логика: шанс выигрыша DICE_WIN_CHANCE%
    win_chance = random.random() < (DICE_WIN_CHANCE / 100)

    if win_chance:
        # Гарантировать выигрыш
        dice_result = chosen_number
    else:
        # Гарантировать проигрыш
        if dice_result == chosen_number:
            dice_result = (chosen_number % 6) + 1

    result_color_text = number_to_color[dice_result][0]

    # Увеличиваем счетчик игр
    await async_update_games_played(user.id)

    # Определение результата
    if dice_result == chosen_number:
        # Выигрыш
        winnings = bet * DICE_MULTIPLIER
        await async_update_balance(user.id, winnings)
        result_text = f"🎉 Вы выиграли! +{winnings}$"
    else:
        # Проигрыш
        await async_update_balance(user.id, -bet)
        result_text = f"😞 Вы проиграли! -{bet}$"

    print(f"Результат кубиков: chosen_number={chosen_number}, dice_result={dice_result}, result_text={result_text}")

    # Отправить результат в группу
    print(f"Проверка отправки в группу: results_group_id = {results_group_id}")
    if results_group_id:
        print(f"Отправка результата кубиков в группу {results_group_id}")
        try:
            username = f"@{user.username}" if user.username else user.first_name or "Неизвестно"
            if "+" in result_text:
                winnings = result_text.split()[-1]
                winnings_label = "Выигрыш"
            elif "-" in result_text:
                winnings = f"-{bet}$"
                winnings_label = "Проигрыш"
            else:
                winnings = "0$"
                winnings_label = "Выигрыш"
            group_text = f"""📎 Игра: Кубики
📱 Пользователь: {username}
💰 Ставка: {bet}$
⚡Результат: {result_text}
💲 {winnings_label}: {winnings}"""
            photo_url = WIN_IMAGE_URL if winnings_label == "Выигрыш" else LOSE_IMAGE_URL
            await bot.send_photo(chat_id=results_group_id, photo=photo_url, caption=group_text)
            print("Результат кубиков отправлен успешно")
        except Exception as e:
            print(f"Ошибка отправки в группу: {e}")
            pass
    else:
        print("Группа для результатов не установлена")

    # Текст с Кубикиом
    game_text = f"""🎲 Верный Кубики: {result_color_text}
♻️ Вы выбрали: {chosen_color_text}

{result_text}"""

    # Клавиатура для итогов
    result_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Играть еще", callback_data="game_dice")],
        [InlineKeyboardButton(text="🔙 В меню игр", callback_data="play")]
    ])

    # Показать результат сразу
    photo_url = WIN_IMAGE_URL if dice_result == chosen_number else LOSE_IMAGE_URL
    try:
        media = InputMediaPhoto(media=photo_url, caption=game_text)
        await bot.edit_message_media(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            media=media,
            reply_markup=result_keyboard
        )
    except:
        await callback_query.message.answer_photo(photo=photo_url, caption=game_text, reply_markup=result_keyboard)

    await callback_query.answer()

# Обработчик ввода кода промокода
async def promo_code_handler(message: types.Message, state: FSMContext):
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    promo_code = message.text.strip().upper()

    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

    # Получаем ID сообщения для редактирования
    data = await state.get_data()
    message_id = data.get('message_id')

    # Проверяем промокод
    promo_data = await async_get_promo_code(promo_code)

    if not promo_data:
        error_text = """❌ <b>Промокод не найден</b>

Проверьте правильность написания кода и попробуйте еще раз."""

        # Всегда редактируем существующее сообщение
        if message_id:
            try:
                media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=error_text, parse_mode="HTML")
                await bot.edit_message_media(
                    chat_id=message.chat.id,
                    message_id=message_id,
                    media=media,
                    reply_markup=get_promo_menu()
                )
            except Exception as e:
                print(f"Ошибка редактирования сообщения: {e}")
                # Если редактирование не удалось, отправляем новое сообщение
                await message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=error_text, reply_markup=get_promo_menu(), parse_mode="HTML")
        else:
            await message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=error_text, reply_markup=get_promo_menu(), parse_mode="HTML")

        await state.clear()
        return

    promo_id, code, reward_amount, max_activations, current_activations, expires_at, created_by, created_at = promo_data

    # Активируем промокод
    success, amount_or_error = await async_activate_promo_code(promo_id, message.from_user.id)

    if success:
        # Начисляем бонус
        await async_update_balance(message.from_user.id, amount_or_error)
        # Логируем активацию промокода
        await async_log_action(message.from_user.id, "promo_activation", amount_or_error, f"Активация промокода {promo_code}")

        success_text = f"""🎫 <b>Вы успешно активировали промокод!</b>

💰 Вы получили: <code>{amount_or_error}$</code>

🎯 Баланс обновлен автоматически."""

        # Всегда редактируем существующее сообщение
        if message_id:
            try:
                media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=success_text, parse_mode="HTML")
                await bot.edit_message_media(
                    chat_id=message.chat.id,
                    message_id=message_id,
                    media=media,
                    reply_markup=get_promo_menu()
                )
            except Exception as e:
                print(f"Ошибка редактирования сообщения: {e}")
                # Если редактирование не удалось, отправляем новое сообщение
                await message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=success_text, reply_markup=get_promo_menu(), parse_mode="HTML")
        else:
            await message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=success_text, reply_markup=get_promo_menu(), parse_mode="HTML")
    else:
        error_text = f"""❌ <b>Ошибка активации</b>

{amount_or_error}

Попробуйте другой промокод или обратитесь в поддержку."""

        # Всегда редактируем существующее сообщение
        if message_id:
            try:
                media = InputMediaPhoto(media=BACKGROUND_IMAGE_URL, caption=error_text, parse_mode="HTML")
                await bot.edit_message_media(
                    chat_id=message.chat.id,
                    message_id=message_id,
                    media=media,
                    reply_markup=get_promo_menu()
                )
            except Exception as e:
                print(f"Ошибка редактирования сообщения: {e}")
                # Если редактирование не удалось, отправляем новое сообщение
                await message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=error_text, reply_markup=get_promo_menu(), parse_mode="HTML")
        else:
            await message.answer_photo(photo=BACKGROUND_IMAGE_URL, caption=error_text, reply_markup=get_promo_menu(), parse_mode="HTML")

    await state.clear()

# Заглушка для игр в разработке
async def game_placeholder_handler(callback_query: types.CallbackQuery):
    game = callback_query.data.split("_")[1]
    game_names = {
        "dice": "Кубики",
        "darts": "Дартс"
    }
    game_name = game_names.get(game, game.capitalize())
    await callback_query.answer(f"🎮 {game_name} в разработке", show_alert=True)

# Регистрация обработчиков
def setup_handlers():
    if dp:
        # Команды
        dp.message.register(start_command, Command(commands=['start', 'restart']))
        dp.message.register(give_command, Command(commands=['give']))
        dp.message.register(panel_command, Command(commands=['panel']))
        dp.message.register(tasks_command, Command(commands=['tasks']))
        dp.message.register(setgroup_command, Command(commands=['setgroup']))
        dp.message.register(setvip_command, Command(commands=['setvip']))
        dp.message.register(getgroup_command, Command(commands=['getgroup']))
        dp.message.register(getvip_command, Command(commands=['getvip']))
        dp.message.register(getgroups_command, Command(commands=['getgroups']))
        dp.message.register(createpromo_command, Command(commands=['createpromo']))
        dp.message.register(listpromo_command, Command(commands=['listpromo']))
        dp.message.register(logs_command, Command(commands=['logs']))
        dp.message.register(stats_command, Command(commands=['stats']))
        dp.message.register(set_command, Command(commands=['set']))

        # Callback кнопок
        dp.callback_query.register(back_to_main, lambda c: c.data == "back_to_main")
        dp.callback_query.register(daily_bonus_handler, lambda c: c.data == "daily_bonus")
        dp.callback_query.register(profile_handler, lambda c: c.data == "profile")
        dp.callback_query.register(play_handler, lambda c: c.data == "play")
        dp.callback_query.register(referral_handler, lambda c: c.data == "referral")
        dp.callback_query.register(rating_handler, lambda c: c.data == "rating")
        dp.callback_query.register(chances_handler, lambda c: c.data == "chances")
        dp.callback_query.register(admin_panel_handler, lambda c: c.data == "admin_panel")
        dp.callback_query.register(admin_chances_handler, lambda c: c.data == "admin_chances")
        dp.callback_query.register(admin_multiplier_handler, lambda c: c.data == "admin_multiplier")
        dp.callback_query.register(admin_stats_handler, lambda c: c.data == "admin_stats")
        dp.callback_query.register(admin_set_balance_handler, lambda c: c.data == "admin_set_balance")
        dp.callback_query.register(edit_chance_duel_handler, lambda c: c.data == "edit_chance_duel")
        dp.callback_query.register(edit_chance_dice_handler, lambda c: c.data == "edit_chance_dice")
        dp.callback_query.register(edit_chance_basketball_handler, lambda c: c.data == "edit_chance_basketball")
        dp.callback_query.register(edit_chance_slots_handler, lambda c: c.data == "edit_chance_slots")
        dp.callback_query.register(edit_chance_blackjack_handler, lambda c: c.data == "edit_chance_blackjack")
        dp.callback_query.register(edit_multiplier_duel_handler, lambda c: c.data == "edit_multiplier_duel")
        dp.callback_query.register(edit_multiplier_basketball_handler, lambda c: c.data == "edit_multiplier_basketball")
        dp.callback_query.register(edit_multiplier_slots_handler, lambda c: c.data == "edit_multiplier_slots")
        dp.callback_query.register(edit_multiplier_dice_handler, lambda c: c.data == "edit_multiplier_dice")
        dp.callback_query.register(edit_multiplier_blackjack_handler, lambda c: c.data == "edit_multiplier_blackjack")
        dp.callback_query.register(duel_handler, lambda c: c.data == "game_duel")
        dp.callback_query.register(dice_handler, lambda c: c.data == "game_dice")
        dp.callback_query.register(dice_color_handler, lambda c: c.data.startswith("dice_color_"))
        dp.callback_query.register(basketball_handler, lambda c: c.data == "game_basketball")
        dp.callback_query.register(basketball_predict_hit_handler, lambda c: c.data.startswith("basketball_predict_hit_"))
        dp.callback_query.register(slots_handler, lambda c: c.data == "game_slots")
        dp.callback_query.register(blackjack_handler, lambda c: c.data == "game_blackjack")
        dp.callback_query.register(slots_spin_handler, lambda c: c.data.startswith("slots_spin_"))
        dp.callback_query.register(blackjack_hit_handler, lambda c: c.data.startswith("blackjack_hit_"))
        dp.callback_query.register(blackjack_stand_handler, lambda c: c.data.startswith("blackjack_stand_"))
        dp.callback_query.register(game_placeholder_handler, lambda c: c.data.startswith("game_") and c.data not in ["game_duel", "game_dice", "game_slots", "game_basketball", "game_blackjack"])
        dp.callback_query.register(duel_confirm_handler, lambda c: c.data.startswith("duel_confirm_"))
        dp.callback_query.register(withdraw_referral_handler, lambda c: c.data == "withdraw_referral")
        dp.callback_query.register(deposit_handler, lambda c: c.data == "deposit")
        dp.callback_query.register(deposit_amount_handler, lambda c: c.data.startswith("dep_"))
        dp.callback_query.register(check_payment, lambda c: c.data.startswith("check_"))
        dp.callback_query.register(withdraw_handler, lambda c: c.data == "withdraw")
        dp.callback_query.register(groups_handler, lambda c: c.data == "groups")
        dp.callback_query.register(promo_codes_handler, lambda c: c.data == "promo_codes")
        dp.callback_query.register(activate_promo_handler, lambda c: c.data == "activate_promo")

        # Обработчики профиля
        dp.callback_query.register(edit_profile_handler, lambda c: c.data == "edit_profile")
        dp.callback_query.register(detailed_stats_handler, lambda c: c.data == "detailed_stats")
        dp.callback_query.register(transaction_history_handler, lambda c: c.data == "transaction_history")
        dp.callback_query.register(profile_settings_handler, lambda c: c.data == "profile_settings")
        dp.callback_query.register(change_username_handler, lambda c: c.data == "change_username")
        dp.callback_query.register(change_avatar_handler, lambda c: c.data == "change_avatar")
        dp.callback_query.register(progress_charts_handler, lambda c: c.data == "progress_charts")

        dp.callback_query.register(other_callbacks)

        # Обработчик ввода суммы
        dp.message.register(process_custom_amount, StateFilter(DepositStates.waiting_for_amount))

        # Обработчик ввода ставки в дуэли
        dp.message.register(duel_bet_handler, StateFilter(DuelStates.waiting_for_bet))

        # Обработчик ввода ставки в баскетбол
        dp.message.register(basketball_bet_handler, StateFilter(BasketballStates.waiting_for_bet))

        # Обработчик ввода ставки в слоты
        dp.message.register(slots_bet_handler, StateFilter(SlotsStates.waiting_for_bet))

        # Обработчик ввода ставки в blackjack
        dp.message.register(blackjack_bet_handler, StateFilter(BlackjackStates.waiting_for_bet))

        # Обработчик ввода ставки в Кубикие
        dp.message.register(dice_bet_handler, StateFilter(DiceStates.waiting_for_bet))

        # Обработчики ввода шансов для админов
        dp.message.register(set_duel_chance_handler, StateFilter(AdminStates.waiting_for_duel_chance))
        dp.message.register(set_basketball_chance_handler, StateFilter(AdminStates.waiting_for_basketball_chance))
        dp.message.register(set_slots_chance_handler, StateFilter(AdminStates.waiting_for_slots_chance))
        dp.message.register(set_blackjack_chance_handler, StateFilter(AdminStates.waiting_for_blackjack_chance))
        dp.message.register(set_dice_chance_handler, StateFilter(AdminStates.waiting_for_dice_chance))

        # Обработчики ввода множителей для админов
        dp.message.register(set_duel_multiplier_handler, StateFilter(AdminStates.waiting_for_duel_multiplier))
        dp.message.register(set_basketball_multiplier_handler, StateFilter(AdminStates.waiting_for_basketball_multiplier))
        dp.message.register(set_slots_multiplier_handler, StateFilter(AdminStates.waiting_for_slots_multiplier))
        dp.message.register(set_blackjack_multiplier_handler, StateFilter(AdminStates.waiting_for_blackjack_multiplier))
        dp.message.register(set_dice_multiplier_handler, StateFilter(AdminStates.waiting_for_dice_multiplier))

        # Обработчики вывода средств
        dp.message.register(withdraw_amount_handler, StateFilter(WithdrawStates.waiting_for_withdraw_amount))

        # Обработчики промокодов
        dp.message.register(promo_code_handler, StateFilter(PromoStates.waiting_for_promo_code))

# Вызываем регистрацию обработчиков
setup_handlers()