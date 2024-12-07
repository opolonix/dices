from flask import Flask, render_template, jsonify
from flask_sse import sse
from threading import Lock

import json


app = Flask(__name__)
app.register_blueprint(sse, url_prefix='/stream')

class MessageAnnouncer:
    """Рассылка клиентам, подключенным к /listen"""

    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.__initialized = False
            return cls._instance

    def __init__(self):
        if self.__initialized:
            return
        self.listeners = {}  # Словарь: client_id -> очередь сообщений
        self.__initialized = True

    def listen(self, client_id):
        """Принимает ID клиента и добавляет его в список слушателей"""
        if client_id not in self.listeners:
            self.listeners[client_id] = []
        return self.listeners[client_id]

    def announce(self, event_type: str, data: dict | list = None, channel: str = "sse"):
        sse.publish({"data": data}, type=event_type, channel=channel)

announcer = MessageAnnouncer()