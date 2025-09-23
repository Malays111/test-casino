#!/bin/bash

# Скрипт автоматического развертывания на Heroku

echo "🚀 Начинаем развертывание VanishCasino Bot на Heroku..."

# Проверяем, установлен ли Heroku CLI
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI не установлен. Установите его с https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

# Проверяем, авторизованы ли мы в Heroku
if ! heroku auth:whoami &> /dev/null; then
    echo "❌ Необходимо авторизоваться в Heroku CLI"
    echo "Выполните: heroku login"
    exit 1
fi

# Создаем приложение на Heroku (если не существует)
APP_NAME="vanishcasino-bot"
if ! heroku apps:info $APP_NAME &> /dev/null; then
    echo "📦 Создание приложения $APP_NAME..."
    heroku create $APP_NAME
else
    echo "📦 Приложение $APP_NAME уже существует"
fi

# Настройка переменных окружения
echo "⚙️ Настройка переменных окружения..."

# Читаем .env файл и устанавливаем переменные
if [ -f .env ]; then
    while IFS='=' read -r key value; do
        # Пропускаем комментарии и пустые строки
        [[ $key =~ ^#.*$ ]] && continue
        [[ -z $key ]] && continue

        # Убираем кавычки и пробелы
        key=$(echo $key | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        value=$(echo $value | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

        # Устанавливаем переменную в Heroku
        heroku config:set $key="$value" -a $APP_NAME
    done < .env
else
    echo "⚠️ Файл .env не найден. Установите переменные окружения вручную."
fi

# Развертывание
echo "📤 Развертывание приложения..."
git add .
git commit -m "Deploy to Heroku"
git push heroku main

# Масштабирование
echo "🔧 Запуск приложения..."
heroku ps:scale web=1 -a $APP_NAME

# Проверка статуса
echo "✅ Проверка статуса приложения..."
heroku ps -a $APP_NAME

echo ""
echo "🎉 Развертывание завершено!"
echo "🌐 Ваш бот доступен по адресу: https://$APP_NAME.herokuapp.com"
echo ""
echo "📋 Следующие шаги:"
echo "1. Убедитесь, что веб-хуки отключены в BotFather"
echo "2. Бот будет работать в режиме polling"
echo "3. Проверьте логи: heroku logs -a $APP_NAME --tail"