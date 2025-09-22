# Токены ботов
TELEGRAM_TOKEN = "8398207757:AAHqH5mZSwL7rxx6FGZFu-0ZzfIHQ00_I7M"
CRYPTO_BOT_TOKEN = "458530:AA2k6GJxJ6VXSa13SjZIVFziqJL4Sgg0oe3"

# API URLs
CRYPTO_BOT_API = "https://pay.crypt.bot"
# WEBHOOK_URL = "https://test-casino-taupe.vercel.app/api/crypto-webhook"  # URL для webhook уведомлений (закомментирован из-за ошибки 405)
WEBHOOK_URL = "https://api.your-casino.com/api/crypto-webhook"  # Custom domain webhook URL

# Кнопки пополнения
CASINO_NAME = "VanishCasino"
DEPOSIT_AMOUNTS = []  # Пустой список - стандартные суммы убраны

# Ссылки на FAQ для игр
DUEL_FAQ_URL = "https://t.me/VanishCasino/10"  # Замените на ссылку для дуэли (кости)
DICE_FAQ_URL = "https://t.me/VanishCasino/11"  # Замените на ссылку для кубиков
BASKETBALL_FAQ_URL = "https://t.me/VanishCasino/12"  # Замените на ссылку для баскетбола
SLOTS_FAQ_URL = "https://t.me/VanishCasino/13"  # Замените на ссылку для слотов
BLACKJACK_FAQ_URL = "https://t.me/VanishCasino/14"  # Замените на ссылку для blackjack
DARTS_FAQ_URL = "https://example.com/darts-faq"  # Замените на ссылку для дартс

# Ссылки на группы
GROUPS = [
    {"name": "Vanish Casino", "url": "https://t.me/VanishCasino"},
    {"name": "Выплаты", "url": "https://t.me/+TjSS6Sl3WDEzNzUy"},
    {"name": "Игры", "url": "https://t.me/+wxU6EuBO8ZA4NGFi"}
]


# Фото
BACKGROUND_IMAGE_URL = "https://www.dropbox.com/scl/fi/av3hb4j7dfwgryxbp6oxp/1.jpg?rlkey=mhtlfwpfm87r4xdzr7xmvlwha&st=hkaodc7f&dl=0"

# Админы
ADMIN_IDS = [8217088275, 1076328217]  # Замените на ID админов

# Реферальная система
REFERRAL_BONUS = 0.3  # 0.3$ за каждого реферала, который пополнил баланс на сумму >= REFERRAL_MIN_DEPOSIT
REFERRAL_MIN_DEPOSIT = 2.0  # Минимальная сумма пополнения для получения реферального бонуса

# Система уровней рефералов
REFERRAL_LEVELS = {
    1: {"bonus": 0.3, "required_referrals": 0, "name": "Новичок"},
    2: {"bonus": 0.5, "required_referrals": 2, "name": "Бронза"},
    3: {"bonus": 0.8, "required_referrals": 5, "name": "Серебро"},
    4: {"bonus": 1.0, "required_referrals": 9, "name": "Золото"},
    5: {"bonus": 1.5, "required_referrals": 15, "name": "Платина"},
    6: {"bonus": 2.0, "required_referrals": 25, "name": "Алмаз"},
    7: {"bonus": 2.5, "required_referrals": 35, "name": "Мастер"},
    8: {"bonus": 2.9, "required_referrals": 40, "name": "Грандмастер"},
    9: {"bonus": 3.5, "required_referrals": 45, "name": "Легенда"},
    10: {"bonus": 5.0, "required_referrals": 100, "name": "БОГ"}
}

# Ежедневные задания
DAILY_TASKS = [
    {"description": "Потрать 15$", "reward": 1.0, "type": "spent", "target": 15.0},
    {"description": "Пополни баланс на 10$", "reward": 5.0, "type": "deposited", "target": 10.0},
    {"description": "Сыграй 10 игр", "reward": 2.0, "type": "games", "target": 10},
    {"description": "Пригласи 10 друзей", "reward": 10.0, "type": "referrals", "target": 10},
    {"description": "Потрать 50$", "reward": 3.0, "type": "spent", "target": 50.0},
    {"description": "Пополни баланс на 25$", "reward": 7.0, "type": "deposited", "target": 25.0},
]