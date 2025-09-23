# VanishCasino Telegram Bot

Казино бот для Telegram с играми и криптовалютными платежами.

## 🚀 Быстрый запуск

### Локальная разработка

1. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Настройте переменные окружения:**
   - Скопируйте `.env` и настройте токены

3. **Запустите бота:**
   ```bash
   python main.py
   ```

### Развертывание на Railway (Рекомендуется)

1. **Создайте аккаунт** на [railway.app](https://railway.app)

2. **Создайте новый проект:**
   - Нажмите "New Project"
   - Выберите "Deploy from GitHub" или загрузите файлы вручную

3. **Настройте переменные окружения** в разделе "Variables":
   ```
   TELEGRAM_TOKEN=ваш_телеграм_токен
   CRYPTO_BOT_TOKEN=ваш_крипто_бот_токен
   ADMIN_IDS=ваш_telegram_id
   ENVIRONMENT=production
   LOG_LEVEL=INFO
   ```

4. **Разверните приложение:**
   - Railway автоматически соберет и запустит бота
   - Дождитесь завершения сборки (обычно 2-3 минуты)

5. **Проверьте работу:**
   - Перейдите в раздел "Deployments"
   - Проверьте логи в "Logs"

### Развертывание на Heroku

1. **Создайте приложение на Heroku:**
   ```bash
   heroku create your-app-name
   ```

2. **Настройте переменные окружения:**
   ```bash
   heroku config:set TELEGRAM_TOKEN=your_token
   heroku config:set CRYPTO_BOT_TOKEN=your_crypto_token
   heroku config:set ADMIN_IDS=your_admin_ids
   ```

3. **Разверните приложение:**
   ```bash
   git push heroku main
   ```

4. **Запустите бота:**
   ```bash
   heroku ps:scale web=1
   ```

### Развертывание на PythonAnywhere

1. **Создайте аккаунт на PythonAnywhere**
2. **Создайте новое Web App**
3. **Настройте виртуальное окружение:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Настройте WSGI файл:**
   ```python
   import os
   import sys

   path = '/path/to/your/app'
   if path not in sys.path:
       sys.path.append(path)

   os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

   from app import main
   application = main()
   ```

## 📋 Требования

- Python 3.11+
- Telegram Bot Token
- Crypto Bot Token
- SQLite база данных

## 🎮 Доступные игры

- 🎲 Кости (Duel)
- 🎳 Кубики (Dice)
- 🏀 Баскетбол
- 🎰 Слоты
- 🃏 BlackJack

## 🔧 Команды администратора

- `/panel` - Админ панель
- `/give @username amount` - Выдать деньги
- `/set @username amount` - Установить баланс
- `/stats` - Статистика пользователей
- `/setgroup group_id` - Установить группу результатов
- `/setvip group_id` - Установить VIP группу

## 📊 Функции

- 💰 Система баланса
- 👥 Реферальная программа
- 🎁 Ежедневные задания
- 🎫 Промокоды
- 💸 Вывод средств
- 📈 Статистика и топы

## 🔒 Безопасность

- Rate limiting
- Валидация всех операций
- Логирование действий
- Защита от SQL инъекций

## 📝 Лицензия

MIT License