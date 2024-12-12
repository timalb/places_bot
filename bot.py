import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from config import load_config
from database import Database
from geocoder import Geocoder
import os
import folium
from folium import plugins
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from PIL import Image
import aiohttp

logging.basicConfig(level=logging.INFO)

config = load_config()
bot = Bot(token=config["tg_bot"]["token"])
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
db = Database()
geocoder = Geocoder()

class UserState(StatesGroup):
    waiting_for_city = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    try:
        await db.add_user(message.from_user.id)
        await message.answer(
            "Привет! Я бот для сохранения и отображения интересных мест на карте. "
            "Для начала работы мне нужно знать ваш город по умолчанию. "
            "Пожалуйста, напишите название вашего города:"
        )
        await state.set_state(UserState.waiting_for_city)
    except Exception as e:
        logging.error(f"Error in start command: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

@dp.message(UserState.waiting_for_city)
async def process_city(message: types.Message, state: FSMContext):
    try:
        city = message.text
        await db.set_user_city(message.from_user.id, city)
        await message.answer(f"Отлично! Ваш город по умолчанию установлен: {city}")
        await state.clear()
    except Exception as e:
        logging.error(f"Error processing city: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
    Доступные команды:
    /start - Начать работу с ботом и указать город по умолчанию
    /help - Показать это сообщение
    /places - Показать список всех сохраненных мест
    /map - Показать все места на карте
    
    Чтобы добавить новое место, просто отправьте сообщение в формате:
    Название места - адрес
    Например: "Кофейня У Петра - ул. Ленина, 1"
    """
    await message.answer(help_text)

@dp.message(Command("places"))
async def cmd_places(message: types.Message):
    try:
        places = await db.get_user_places(message.from_user.id)
        if not places:
            await message.answer("У вас пока нет сохраненных мест")
            return
        
        places_text = "Ваши сохраненные места:\n\n"
        for place_name, address in places:
            places_text += f"📍 {place_name}\n🏠 {address}\n\n"
        
        await message.answer(places_text)
    except Exception as e:
        logging.error(f"Error getting places: {e}")
        await message.answer("Произошла ошибка при получении списка мест")

@dp.message(Command("map"))
async def cmd_map(message: types.Message):
    try:
        places = await db.get_user_places_with_coords(message.from_user.id)
        if not places:
            await message.answer("У вас пока нет сохраненных мест")
            return

        # Создаем HTML карту для интерактивного просмотра
        m = folium.Map(location=[55.7558, 37.6173], zoom_start=12)
        bounds = []

        # Сначала отправляем каждое место как отдельную точку на карте
        await message.answer("Ваши сохраненные места:")
        
        for place_name, address, lat, lon in places:
            if lat and lon:
                # Добавляем маркер на HTML карту
                folium.Marker(
                    location=[lat, lon],
                    popup=f"<b>{place_name}</b><br>{address}",
                    icon=folium.Icon(color='red', icon='info-sign')
                ).add_to(m)
                bounds.append([lat, lon])
                
                # Отправляем место через Telegram
                await message.answer_venue(
                    latitude=lat,
                    longitude=lon,
                    title=place_name,
                    address=address
                )

        if bounds:
            m.fit_bounds(bounds)

        # Сохраняем и отправляем HTML версию для просмотра в браузере
        os.makedirs('data/temp', exist_ok=True)
        map_file = f"data/temp/map_{message.from_user.id}.html"
        m.save(map_file)
        
        await message.answer_document(
            document=types.FSInputFile(map_file),
            caption="Интерактивная версия карты (HTML) для просмотра в браузере"
        )
        
        # Удаляем временный файл
        os.remove(map_file)

    except Exception as e:
        logging.error(f"Error generating map: {e}", exc_info=True)
        await message.answer("Произошла ошибка при создании карты")

@dp.message(F.text)
async def process_place(message: types.Message, state: FSMContext):
    try:
        text = message.text
        if '-' not in text:
            await message.answer("Пожалуйста, укажите место в формате: 'Название места - адрес'")
            return

        place_name, address = text.split('-', 1)
        place_name = place_name.strip()
        address = address.strip()

        # Получаем город пользователя
        user_city = await db.get_user_city(message.from_user.id)
        if not user_city:
            await message.answer("Пожалуйста, сначала укажите ваш город через команду /start")
            return

        full_address = f"{address}, {user_city}"
        coordinates = await geocoder.geocode(full_address)
        
        if coordinates:
            latitude, longitude = coordinates
            await db.add_place(
                user_id=message.from_user.id,
                place_name=place_name,
                address=full_address,
                latitude=latitude,
                longitude=longitude
            )
            await message.answer(
                f"Место сохранено:\n"
                f"📍 {place_name}\n"
                f"🏠 {full_address}"
            )
        else:
            await message.answer("Не удалось определить адрес. Пожалуйста, проверьте правильность написания.")
    except Exception as e:
        logging.error(f"Error processing place: {e}")
        await message.answer("Произошла ошибка при сохранении места")

async def main():
    await db.init()
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Error starting bot: {e}")
        raise
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main()) 