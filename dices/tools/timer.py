"Синхронный таймер"

import threading


def setTimeout(callback, delay: int, *args, **kwargs) -> threading.Timer:
    timer = threading.Timer(delay / 1000, callback, args=args, kwargs=kwargs)
    timer.start()
    return timer

def clearTimeout(timer: threading.Timer) -> None:
    if timer:
        timer.cancel()