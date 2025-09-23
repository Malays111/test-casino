import os
import asyncio
import logging
from dotenv import load_dotenv
from main import run_bot

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция для запуска в продакшене"""
    try:
        logger.info("🚀 Запуск VanishCasino Bot в продакшене...")
        await run_bot()
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise

if __name__ == '__main__':
    # Запускаем бота
    asyncio.run(main())