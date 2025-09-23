# Токены ботов
TELEGRAM_TOKEN = "8385343502:AAFxLxYG5OcrhdMlWJgIkZGZcf8zCyoTejY"
CRYPTO_BOT_TOKEN = "458530:AA2k6GJxJ6VXSa13SjZIVFziqJL4Sgg0oe3"

# API URLs
CRYPTO_BOT_API = "https://pay.crypt.bot/api"

# Кнопки пополнения
DEPOSIT_AMOUNTS = [5, 10, 15, 20]
CASINO_NAME = "VanishCasino"

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

# Ежедневные задания
DAILY_TASKS = [
    {"description": "Пригласи 50 друзей", "reward": 20.0, "type": "referrals", "target": 50},
    {"description": "Потрать 15$", "reward": 1.0, "type": "spent", "target": 15.0},
    {"description": "Пополни баланс на 10$", "reward": 5.0, "type": "deposited", "target": 10.0},
    {"description": "Сыграй 10 игр", "reward": 2.0, "type": "games", "target": 10},
    {"description": "Пригласи 10 друзей", "reward": 10.0, "type": "referrals", "target": 10},
    {"description": "Потрать 50$", "reward": 3.0, "type": "spent", "target": 50.0},
    {"description": "Пополни баланс на 25$", "reward": 7.0, "type": "deposited", "target": 25.0},
]