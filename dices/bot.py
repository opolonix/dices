from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from db import Client, Room, Player, Step, Dice
from tools.config import config

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import asyncio

engine = create_engine(config['server']['db'])

Session = sessionmaker(bind=engine)
session = Session()


bot = Bot(token=config['bot']['token'], default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

@dp.message()
async def handler(message: Message):

    if message.text == "/start":

        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Главная", web_app=WebAppInfo(url="https://holey.opolo.me/"))]])

        await message.reply("Добро пожаловать!", reply_markup=kb)

    elif message.text.startswith("/start"):

        invite = message.text.split(" ")[-1]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Играть", web_app=WebAppInfo(url=f"https://holey.opolo.me/lobby?{invite}"))],
        ])

        await message.reply(f"Вот ваше приглашение! {invite}", reply_markup=kb)

    if message.text == "/drop": # существует только для тестов
        session.query(Dice).delete()
        session.commit()
        session.query(Step).delete()
        session.commit()
        session.query(Player).delete()
        session.commit()
        session.query(Room).delete()
        session.commit()
        await message.reply(f"Все комнаты очищены")



async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())