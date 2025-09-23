# 🚀 Развертывание на Railway

## 📋 Шаги по развертыванию на Railway

### 1. Подготовка

Убедитесь, что у вас есть:
- ✅ Аккаунт на [railway.app](https://railway.app)
- ✅ Telegram Bot Token от @BotFather
- ✅ Crypto Bot Token от @CryptoBot
- ✅ Ваш Telegram ID для ADMIN_IDS

### 2. Создание проекта

1. **Перейдите на Railway:**
   - Зайдите в [railway.app](https://railway.app)
   - Нажмите **"New Project"**

2. **Выберите способ развертывания:**
   - **Рекомендуется:** "Deploy from GitHub"
     - Подключите ваш GitHub репозиторий
     - Railway автоматически обнаружит конфигурацию
   - **Альтернатива:** "Empty Project"
     - Загрузите файлы вручную

### 3. Настройка переменных окружения

В разделе **"Variables"** добавьте следующие переменные:

```
TELEGRAM_TOKEN=ваш_телеграм_токен_от_botfather
CRYPTO_BOT_TOKEN=ваш_крипто_бот_токен
ADMIN_IDS=ваш_telegram_id
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### 4. Развертывание

1. **Запустите развертывание:**
   - Railway автоматически начнет сборку
   - Процесс занимает 2-3 минуты

2. **Проверьте статус:**
   - Перейдите в раздел **"Deployments"**
   - Дождитесь статуса "Success"

3. **Проверьте логи:**
   - Откройте раздел **"Logs"**
   - Убедитесь, что бот запустился без ошибок

### 5. Проверка работы

1. **Проверьте бота в Telegram:**
   - Отправьте `/start` вашему боту
   - Должно появиться главное меню

2. **Настройте группы (опционально):**
   - Создайте группы для результатов игр
   - Используйте команды `/setgroup` и `/setvip`

## 🔧 Конфигурационные файлы

### railway.toml
```toml
[build]
builder = "DOCKERFILE"

[deploy]
healthcheckPath = "/"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

[services.main]
processes = ["python app.py"]
```

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

CMD ["python", "app.py"]
```

## 📊 Мониторинг

### Просмотр логов
```bash
# Через Railway CLI
railway logs --follow

# Через веб-интерфейс
# Railway Dashboard → ваш проект → Logs
```

### Проверка статуса
```bash
# Через Railway CLI
railway status

# Через веб-интерфейс
# Railway Dashboard → ваш проект → Deployments
```

### Перезапуск сервиса
```bash
# Через Railway CLI
railway service restart

# Через веб-интерфейс
# Railway Dashboard → ваш проект → Settings → Restart
```

## 🆘 Устранение проблем

### Бот не отвечает
1. Проверьте логи на наличие ошибок
2. Убедитесь, что токены указаны правильно
3. Проверьте, что бот не заблокирован в Telegram

### Ошибки сборки
1. Убедитесь, что все файлы загружены
2. Проверьте `requirements.txt` на корректность
3. Убедитесь, что Python версия 3.11+

### Проблемы с базой данных
1. База данных SQLite создается автоматически
2. Проверьте права доступа к файлам
3. В случае проблем удалите `casino.db` и перезапустите

## 🚨 Важные моменты

- **Railway автоматически масштабируется** - никаких дополнительных настроек не требуется
- **База данных сохраняется** между развертываниями
- **Логи доступны в реальном времени** через веб-интерфейс
- **SSL сертификат** настраивается автоматически

## 📈 Преимущества Railway

- ✅ **Бесплатный тариф** с щедрыми лимитами
- ✅ **Автоматическое масштабирование**
- ✅ **Простой веб-интерфейс**
- ✅ **Встроенный мониторинг**
- ✅ **Поддержка GitHub интеграции**
- ✅ **Быстрое развертывание**

## 🎯 Следующие шаги после развертывания

1. **Протестируйте бота** в Telegram
2. **Настройте группы** для результатов игр
3. **Добавьте промокоды** через админ панель
4. **Настройте мониторинг** в Railway Dashboard
5. **Создайте резервную копию** базы данных при необходимости

Удачи с вашим ботом на Railway! 🎰