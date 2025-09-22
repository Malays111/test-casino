from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import TELEGRAM_TOKEN
import bot
import asyncio
import threading
import sys

# Глобальные переменные
bot_instance = None
dp = None
storage = None

def initialize_bot():
    """Инициализация бота"""
    global bot_instance, dp, storage
    
    # Создаем бота и диспетчер с MemoryStorage
    bot_instance = Bot(token=TELEGRAM_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Передаем dp и bot в bot.py
    bot.bot = bot_instance
    bot.dp = dp
    bot.setup_handlers()

def console_input(loop):
    """Функция для обработки ввода в консоли"""
    while True:
        try:
            command = input().strip().lower()
            if command == 'stop':
                print("🛑 Остановка бота...")
                loop.call_soon_threadsafe(loop.stop)
                break
            elif command == 'restart':
                print("🔄 Перезапуск бота...")
                loop.call_soon_threadsafe(loop.stop)
                break
        except:
            pass

async def on_startup():
    # Инициализация базы данных
    try:
        await bot.async_db.initialize()
    except Exception as e:
        pass

    # Предварительная загрузка данных для ускорения работы
    try:
        await bot.preload_data()
    except Exception as e:
        pass

async def on_shutdown():
    print("🛑 Бот остановлен!")

async def run_bot():
    """Запуск бота"""
    global bot_instance, dp

    # Инициализируем бота
    initialize_bot()

    # Регистрируем handlers для startup/shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Запускаем задачу обновления кэша топов
    asyncio.create_task(bot.update_top_cache())

    # Запускаем поток для чтения команд из консоли
    loop = asyncio.get_event_loop()
    console_thread = threading.Thread(target=console_input, args=(loop,), daemon=True)
    console_thread.start()

    try:
        # Запускаем бота без пропуска обновлений для более быстрой реакции
        await dp.start_polling(bot_instance, skip_updates=False)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем!")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

async def main():
    """Основная функция с возможностью перезапуска"""
    while True:
        await run_bot()
        
        # Спрашиваем, хочет ли пользователь перезапустить
        print("\nБот остановлен. Выберите действие:")
        print("1. Перезапустить (введите 'r')")
        print("2. Выйти (введите 'q')")
        print("3. Или просто введите 'r' или 'q':")
        
        try:
            choice = input().strip().lower()
            if choice in ['q', 'quit', 'exit', '2']:
                print("👋 До свидания!")
                break
            elif choice in ['r', 'restart', '1', '']:
                print("🔄 Перезапуск...")
                continue
            else:
                print("🔄 Перезапуск...")
                continue
        except (EOFError, KeyboardInterrupt):
            print("\n👋 До свидания!")
            break

if __name__ == '__main__':
    asyncio.run(main())