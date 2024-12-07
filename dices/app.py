from routers import app
from bot import dp, bot
from tools.config import config

import asyncio
import threading
import logging

logging.basicConfig(level=logging.ERROR)

async def main():
    flask_thread = threading.Thread(target=run_asgi_server, daemon=True)
    flask_thread.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(config['server']['port']), reload=True)