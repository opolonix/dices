import queue
import json
from threading import Lock

class MessageAnnouncer: 
    """делает рассылку клиентам которые подключены к /listen"""

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
        self.listeners: dict[int, queue.Queue] = {}
        self.__initialized = True

    def listen(self, client_id):
        """
        Принимает телеграмный ид клиента и добавляет его в пулл для рассылок
        """
        q = queue.Queue(maxsize=5)
        self.listeners[client_id] = q
        return q

    def announce(self, event_type: str, data: dict | list = None, targets=None, exclude: set = set()):
        """
        Рассылает анонс списку пользователей / всем пользователям
        """
        if not targets:
            for k, q in self.listeners.items():
                if k in exclude: continue
                try:
                    q.put_nowait(json.dumps({"event": event_type, "data": data}))
                except queue.Full:
                    del self.listeners[k]
        else:
            for target in targets:
                if target in exclude: continue
                if (q := self.listeners.get(target)):
                    try:
                        q.put_nowait(json.dumps({"event": event_type, "data": data}))
                    except queue.Full:
                        del self.listeners[target]

announcer = MessageAnnouncer()
