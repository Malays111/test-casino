# Деплой вебхука на Vercel

## Шаги:

1. **Установите Vercel CLI:**
   ```bash
   npm install -g vercel
   ```

2. **Войдите в Vercel:**
   ```bash
   vercel login
   ```

3. **Деплойте проект:**
   ```bash
   vercel
   ```

4. **Ответьте на вопросы:**
   - Link to existing project? **N**
   - Project name: **your-crypto-webhook**
   - Directory: **./** (текущая папка)

5. **Получите URL:**
   После деплоя Vercel даст вам URL типа:
   ```
   https://your-project.vercel.app
   ```

6. **Настройте вебхук в CryptoBot:**
   - Зайдите в настройки приложения CryptoBot
   - В разделе "Webhooks" укажите URL:
     ```
     https://your-project.vercel.app/api/crypto-webhook
     ```

## Структура файлов:
- `api/crypto-webhook.py` - обработчик вебхука
- `vercel.json` - конфигурация Vercel
- `requirements.txt` - зависимости Python

## Переменные окружения:
Установите в Vercel dashboard:
- `TELEGRAM_BOT_TOKEN` - токен вашего Telegram бота (для уведомлений)

Теперь платежи будут обрабатываться автоматически при активации чеков!