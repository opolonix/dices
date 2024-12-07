from typing import Literal
from pydantic import BaseModel
from sqlalchemy import desc

from db import session, Dice, Step, Client, Player, Room, as_dict

from tools.funcs import is_player, get_auth_data, find_combo, serial
from tools.announcer import announcer

import json
import random

def set_bet(bet: int, room: Room):

    min_bet = 0
    max_bet = None


    for player in room.players:
        if not max_bet: max_bet = player.client.balance
        else: max_bet = min(max_bet, player.client.balance)

    bet = min(max_bet, bet) # отклонить ставку больше максимальной
    bet = max(min_bet, bet) # отклонить ставку больше минимальной

    announcer.announce(
        "update_bet",
        {'bet': bet, "max": max_bet, "min": min_bet},
        room.room_key
    )

    room.bet = bet
    session.commit()

def is_player(room_key: str, client_id: int) -> tuple[Client, Room, Player]:
    client = session.query(Client).filter(Client.telegram_id == client_id).first()
    if not client: return None, None, None

    room = session.query(Room).filter(Room.room_key == room_key).first()
    if not room: return None, None, None

    player = session.query(Player).filter(Player.room_id == room.id, Player.client_id == client.id).first()
    if not player: return None, None, None

    return client, room, player

def remove_player(client: Client, room: Room):
    if client.id != room.owner_id:
        announcer.announce(
            "leave_player", {'player': {"id": client.id}},
            room.room_key
        )
        session.query(Player).filter(Player.client_id == client.id, Player.room_id == room.id).delete()
        session.commit()

        # когда игрок поидает комнату, пересчитываем ставку

        min_bet = 0
        max_bet = 0
        
        for player in room.players:
            if client.id != player.client_id:
                max_bet = min(max_bet, player.client.balance)

        bet = min(max_bet, bet) # отклонить ставку больше максимальной
        bet = max(min_bet, bet) # отклонить ставку больше минимальной

        announcer.announce(
            "update_bet",
            {'bet': room.bet, "max": max_bet, "min": min_bet},
            room.room_key
        )
        session.commit()

    else:
        announcer.announce(
            "close_room", {},
            room.room_key
        )

        session.delete(room)
        session.commit()


class Error(BaseModel):
    message: str
    status: int
    ok: bool = False

class Answer(BaseModel):
    model_config = {
        "arbitrary_types_allowed": True
    }
    
    client: Client
    room: Room
    player: Player
    data: dict
    ok: bool = True


def validate(request) -> Answer:
    
    client_id, is_admin = get_auth_data(request)
    data = json.loads(request.data)
    room_key = data.get("room_key")

    if not client_id:
        return Error("Пользователь не авторизован / токен авторизации истек", 400)

    if not room_key:
        return Error("Комната не найдена", 400)

    client, room, player = is_player(room_key, client_id)

    if not client:
        return Error("Игрок не принадлежит этой комнате, либо комнаты не существует", 400)

    if room.stage == 0:
        return Error("Рано, игра еще не началась", 400)

    # Возвращаем данные, если всё прошло успешно
    return Answer(
        client = client,
        room = room,
        player = player,
        data = data
    )

def new_step(room: Room, last_player: Player) -> Player:
    # записываем текущий шаг пользователю
    this_step = session.query(Step).filter(Step.room_id == room.id).order_by(desc(Step.time)).first()
    this_step.score += calc_score(room.dices)

    last_score = last_player.score

    last_player.score += this_step.score
    last_player.is_active = False

    # ямы между 200/300 и 600/700, счет остается неизменным
    if 200 < last_score < 300 and last_player.score < 300:
        last_player.score = last_score
        send_message(room, 'pit', {"player": as_dict(last_player, last_player.client)})

    if 600 < last_score < 700 and last_player.score < 700:
        last_player.score = last_score
        send_message(room, 'pit', {"player": as_dict(last_player, last_player.client)})
        

    if last_score > 900 and last_player.score < 1000:
        last_player.barrels += 1
        last_player.score -= 60
        send_message(room, 'barrel', {"player": as_dict(last_player, last_player.client)})

    if last_player.barrels == 3:
        last_player.barrels = 0
        last_player.score = 0

    overtake = session.query(Player).filter(Player.score == last_player.score - 5).first() # обработка обгона
    if overtake:
        players = session.query(Player).filter(Player.score <= last_player.score - 5).all()
        for player in players:
            player.score -= 50
        send_message(room, 'overtake')
        session.commit()

    new_player = session.query(Player).filter(Player.room_id == room.id, Player.join_at > last_player.join_at).first()
    if not new_player: new_player = session.query(Player).filter(Player.room_id == room.id).order_by(Player.join_at).first()

    # делаем все шаги завершенными
    session.query(Step).filter(Step.room_id == room.id).update({Step.stage: 3})
    

    step = Step(player_id = new_player.id, room_id = room.id)
    is_bolt = uptdate_dices(room, clear_tray=True)
    step.is_bolt = is_bolt
    session.add(step)

    new_player.is_active = True

    session.commit()

    return new_player

def get_state(room: Room, player: Player, fields = []) -> dict:

    result = {}

    if (n := "room") in fields: result[n] = as_dict(room)
    if (n := "player") in fields: result[n] = as_dict(player, player.client)
    if (n := "active_player") in fields: 
        active_player = session.query(Player).filter(Player.room_id == room.id, Player.is_active == True).first()
        result[n] = as_dict(active_player, active_player.client)
    if (n := "players") in fields: result[n] = [as_dict(p, p.client) for p in room.players]
    if (n := "steps") in fields: 
        steps = session.query(Step).filter(Step.stage != 3).order_by(Step.time).all()
        result[n] = [as_dict(s) for s in steps]

    if (n := "area") in fields: result[n] = [as_dict(d) for d in room.dices if not d.in_tray]
    if (n := "tray") in fields: result[n] = [as_dict(d) for d in room.dices if d.in_tray]

    return result

def calc_score(dices: list[Dice]) -> int:
    
    score = 0
    c = find_combo(dices)
    c.sort(key=lambda x: -x['score'])


    combo_ids = set()
    
    for combo in c:
        if len(combo_ids) == len(dices): break
        
        if len([d for d in combo['dices'] if d.id in combo_ids]) == 0: # если все кости комбинации не еще не пренадлежат ни одной другой комбинации то...
            for d in combo['dices']:
                d.in_combo = True
                combo_ids.add(d.id)    
            score += serial(combo['dices'])
    
    session.commit()

    return score

def send_message(room: Room, msgtype: Literal["bolt", "barrel", "overtake", "pit"], data: dict = {}) -> None:
    announcer.announce(
        "message", {'type': msgtype, 'data': data},
        room.room_key
    )
    
def uptdate_dices(room: Room, clear_tray = False) -> bool:
    """
        Пересобирает трей, возвращает болт
    """
    for dice in room.dices:
        dice.in_tray = False if clear_tray else dice.in_tray
        dice.in_combo = False
        if not dice.in_tray:
            dice.face = random.randint(1, 6)

    c = find_combo([d for d in room.dices if not d.in_combo])
    c.sort(key=lambda x: -x['score'])
    combo_ids = set()
    combos = []
    for combo in c:
        if len([d for d in combo['dices'] if d.id in combo_ids]) == 0:
            for d in combo['dices']:
                d.in_combo = True
                combo_ids.add(d.id)
            combos.append({"score": serial(combo['dices']), "dices": [as_dict(d) for d in combo['dices']]})
    
    session.commit()

    return len(find_combo([d for d in room.dices if not d.in_tray])) == 0 # проверяем существует ли комбинация из доступных костей
