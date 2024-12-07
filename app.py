import subprocess
from tools.config import config
from multiprocessing import Process

def web():
    subprocess.run([
        "venv/bin/gunicorn",
        "-w", "1",
        "-b", f"127.0.0.1:{config['server']['port']}",
        "--reload",
        "--access-logfile", "-",
        "--access-logformat", '"%(r)s" -> %(s)s',
        "-k", "gevent",
        "routers:app",
    ])

def bot():
    subprocess.run([
        "venv/bin/python",
        "bot.py"
    ])

if __name__ == "__main__":
    web_server_process = Process(target=web)
    bot_process = Process(target=bot)

    web_server_process.start()
    bot_process.start()

    web_server_process.join()
    bot_process.join()