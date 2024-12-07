from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
session = db.session

from typing import List
from sqlalchemy import Column, Boolean, String, Integer, DateTime, ForeignKey, BigInteger, Text
from sqlalchemy.orm import relationship, Mapped

from datetime import datetime, timedelta
import random, string

class Client(db.Model):
    __tablename__ = 'clients'
    
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id: int = Column(BigInteger, unique=True)
 
    is_premium: bool = Column(Boolean)
    allows_write: bool = Column(Boolean)
    language_code: str = Column(String(16))
    username: str = Column(String(32))
    last_name: str = Column(String(128))
    first_name: str = Column(String(128))
    avatar: str = Column(String(128), default=None)

    join_at: datetime = Column(DateTime, default=datetime.now)
    last_visit: datetime = Column(DateTime, default=datetime.now)
    
    banned: bool = Column(Boolean, default=False)
    balance: int = Column(Integer, default=500)
    wallet: str = Column(String(253), default=None)

class Room(db.Model):
    __tablename__ = 'rooms'
    
    id: int = Column(Integer, primary_key=True, autoincrement=True)

    room_key: str = Column(String(16), default=lambda: ''.join(random.choices(string.ascii_letters, k=9)))
    name: str = Column(String(128))

    owner_id: int = Column(Integer, ForeignKey(Client.id))
    created_at: datetime = Column(DateTime, default=datetime.now)
    player_limit: int = Column(Integer, default=5)
    players: Mapped[List["Player"]] = relationship(back_populates="room", cascade="all, delete")
    steps: Mapped[List["Step"]] = relationship(cascade="all, delete")

    is_public: bool = Column(Boolean, default=False)
    stage: int = Column(Integer, default=0) # 0 - лобби 1 - игра 2 - завершена

    bet: int = Column(Integer, default = 100)
    dices: Mapped[List['Dice']] = relationship(cascade="all, delete")

class Player(db.Model):
    __tablename__ = 'players'
    
    id: int = Column(Integer, primary_key=True, autoincrement=True)

    client_id: int = Column(Integer, ForeignKey(Client.id))
    client: Mapped[Client] = relationship()

    room_id: int = Column(Integer, ForeignKey(Room.id))
    room: Mapped[Room] = relationship()
    steps: Mapped[List["Step"]] = relationship(cascade="all, delete")

    is_owner: bool = Column(Boolean, default=False)
    is_active: bool = Column(Boolean, default=False)
    join_at: datetime = Column(DateTime, default=datetime.now)

    
    score: int = Column(Integer, default = 0)
    bolts: int = Column(Integer, default = 0)

class Step(db.Model):
    __tablename__ = 'steps'

    id: int = Column(Integer, primary_key=True, autoincrement=True)

    must_play: bool = Column(Boolean, default=True) # сначала пользователь обязан сделать бросок
    tray_updated: bool = Column(Boolean, default=False) # изменится на True и значит сможет сделать новый ход

    score: int = Column(Integer, default = 0)
    is_bolt: bool = Column(Boolean, default=False)

    stage: int = Column(Integer, default = 1) # 1 - бросок разослан; 2 - бросок подтвержен; 3 - собираем трей; 4 - ход является завершенным
    expire: datetime = Column(DateTime, default=lambda: datetime.now() + timedelta(seconds=15)) # время истечения текущего шага, 15 секунд на то, чтобы игрок сделал свайп

    player_id: int = Column(Integer, ForeignKey(Player.id))
    room_id: int = Column(Integer, ForeignKey(Room.id))
    time: datetime = Column(DateTime, default=datetime.now)

class Dice(db.Model): # к каждой комнате привыязано по пять кубиков
    __tablename__ = 'dices'

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    room_id: int = Column(Integer, ForeignKey(Room.id))
    index: int = Column(Integer)
    face: int = Column(Integer)
    glb: str = Column(String(200), default = "def")
    meta: str = Column(Text) # сюда моджно сложить метаданные кубика по типу позиции на экране
    in_tray: bool = Column(Boolean, default=False)
    in_combo: bool = Column(Boolean, default=False)

class JoinTask(db.Model):
    __tablename__ = 'join_tasks'
    
    id: int = Column(Integer, primary_key=True, autoincrement=True)

    url: str = Column(String(253), comment="юрл подписки") # юрл подписки
    checks: int = Column(Integer, default = 1, comment="колво дней в течение которых будет начисляться бонус") # колво дней которые нужно осуществлять проверку подписки
    bonus: int = Column(Integer, comment="Общий бонус за подписку")
    active: bool = Column(Boolean, default = True, comment="По")
    expire: datetime = Column(DateTime, default=lambda: datetime.now() + timedelta(days=365*15))

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id: int = Column(Integer, primary_key=True, autoincrement=True)

    task_id = Column(Integer, ForeignKey(JoinTask.id))
    client_id = Column(Integer, ForeignKey(Client.id))

    checks_count: int = Column(Integer) # колво исполненных раз проверки
    last_check: datetime = Column(DateTime, default=datetime.now) # вермя последней проверки

def ch(data, datatypes: list) -> bool:
    for dt in datatypes:
        if isinstance(data, dt): return True
    return False

def as_dict(*slas) -> dict:
    result = {}
    for sla in slas:
        names = [c.name for c in sla.__table__.columns] if sla.__table__.name != "clients" else ['first_name', 'avatar']
        for c in names:
            data = getattr(sla, c)
            if ch(data, [str, bool, int, float]):
                result[c] = data
            elif ch(data, [datetime]):
                result[c] = data.timestamp()
    return result