import os
import sys

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(__file__))

from api.crypto_webhook import app

# Настройка для production
app.config['DEBUG'] = False