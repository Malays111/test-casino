# 🚀 Быстрый запуск VanishCasino Bot

## 📦 Что создано для вас

Я создал полную конфигурацию для развертывания бота на хостинге без веб-хуков:

### ✅ Созданные файлы:
- `railway.toml` - конфигурация для Railway
- `Dockerfile` - Docker образ для Railway
- `RAILWAY-DEPLOY.md` - подробная инструкция для Railway
- `Procfile` - конфигурация для Heroku/PythonAnywhere
- `runtime.txt` - версия Python (3.11.0)
- `requirements.txt` - зависимости с python-dotenv и gunicorn
- `.env` - переменные окружения
- `app.py` - продакшен скрипт запуска
- `.gitignore` - исключения для Git
- `README.md` - полная документация
- `deploy.sh` - скрипт автоматического развертывания
- `start.sh` - скрипт запуска
- `TROUBLESHOOTING.md` - руководство по устранению проблем

## 🎯 Варианты развертывания

### Вариант 1: Railway (Рекомендуется ⭐)

1. **Создайте аккаунт** на [railway.app](https://railway.app)

2. **Создайте новый проект:**
   - Нажмите "New Project" → "Deploy from GitHub"
   - Подключите ваш GitHub репозиторий
   - Или загрузите файлы вручную через "Empty Project"

3. **Настройте переменные окружения:**
   В разделе "Variables" добавьте:
   ```
   TELEGRAM_TOKEN=ваш_телеграм_токен
   CRYPTO_BOT_TOKEN=ваш_крипто_бот_токен
   ADMIN_IDS=ваш_telegram_id
   ENVIRONMENT=production
   LOG_LEVEL=INFO
   ```

4. **Разверните:**
   - Railway автоматически соберет и запустит бота
   - Дождитесь завершения деплоя (2-3 минуты)

5. **Проверьте:**
   - Логи доступны в разделе "Logs"
   - Бот должен быть активен через 1-2 минуты

### Вариант 2: Heroku

1. **Установите Heroku CLI:**
   ```bash
   # Windows
   winget install --id Heroku.HerokuCLI

   # macOS
   brew install heroku/brew/heroku

   # Linux
   curl https://cli-assets.heroku.com/install.sh | sh
   ```

2. **Авторизуйтесь:**
   ```bash
   heroku login
   ```

3. **Разверните бота:**
   ```bash
   ./deploy.sh
   ```

### Вариант 2: PythonAnywhere

1. **Создайте аккаунт** на [pythonanywhere.com](https://pythonanywhere.com)

2. **Создайте Web App:**
   - Выберите "Manual configuration"
   - Укажите Python 3.11
   - В WSGI файл добавьте:
   ```python
   import os
   import sys

   path = '/home/yourusername/your-app-path'
   if path not in sys.path:
       sys.path.append(path)

   from app import main
   application = main()
   ```

3. **Настройте переменные окружения** в dashboard

4. **Загрузите файлы** через dashboard или git

### Вариант 3: VPS/Server

1. **Установите Python 3.11+ и pip**

2. **Склонируйте репозиторий:**
   ```bash
   git clone your-repo-url
   cd your-repo
   ```

3. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Настройте .env файл** с вашими токенами

5. **Запустите бота:**
   ```bash
   python app.py
   ```

## 🔧 Настройка перед запуском

### 1. Получите токены:
- **Telegram Bot Token:** от @BotFather в Telegram
- **Crypto Bot Token:** от @CryptoBot в Telegram

### 2. Обновите .env файл:
```env
TELEGRAM_TOKEN=ваш_телеграм_токен
CRYPTO_BOT_TOKEN=ваш_крипто_токен
ADMIN_IDS=ваш_telegram_id
```

### 3. Настройте Crypto Bot:
- Перейдите в @CryptoBot
- Создайте приложение
- Включите методы "Transfer" и "Invoice"
- Получите токен приложения

## 🚨 Важные моменты

1. **Без веб-хуков:** Бот использует polling режим, который идеален для хостинга
2. **База данных:** SQLite работает автоматически, создается при первом запуске
3. **Логирование:** Все действия логируются для отладки
4. **Безопасность:** Rate limiting и валидация всех операций

## 📊 После запуска

1. **Проверьте работу бота** в Telegram
2. **Настройте группы** командами:
   - `/setgroup` - группа для результатов игр
   - `/setvip` - VIP группа для выплат
3. **Добавьте админов** в ADMIN_IDS
4. **Протестируйте все функции**

## 🆘 Если возникли проблемы

Смотрите `TROUBLESHOOTING.md` для решения распространенных проблем или проверьте логи:

```bash
# Railway
railway logs --follow

# Heroku
heroku logs -a your-app-name --tail

# Локально
python app.py  # и проверьте вывод в консоли
```

## 🎮 Готовые команды

После запуска бота доступны команды:
- `/start` - начать работу с ботом
- `/panel` - админ панель (для администраторов)
- Все игровые функции через кнопки меню

Удачи с вашим казино ботом! 🎰