#!/bin/bash

# Скрипт запуска бота в продакшене

echo "🚀 Запуск VanishCasino Bot..."

# Проверяем переменные окружения
if [ -f .env ]; then
    echo "📄 Загружаем переменные окружения из .env"
    export $(grep -v '^#' .env | xargs)
else
    echo "⚠️ Файл .env не найден. Убедитесь, что переменные окружения установлены."
fi

# Создаем базу данных если её нет
if [ ! -f casino.db ]; then
    echo "🗄️ Создание базы данных..."
    python -c "from database import db; print('База данных инициализирована')"
fi

# Запускаем бота
echo "🎮 Запуск бота..."
python app.py