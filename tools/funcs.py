from db import Dice, Client, Room, Player, session
from flask import Request, make_response, Response, request
from tools.config import config
import itertools, json, time, jwt


def resp(data: dict = None, descr = None, status = 200):
    out = {"ok": status == 200}
    if descr is not None:
        out["description"] = descr
    if data is not None:
        out["result"] = data
        
    return make_response(Response(json.dumps(out, ensure_ascii=False), status=status))

def serial(area: list[Dice]) -> int: # возвращает подсчет ценности комбинации
    if len(area) == 1:
        match area[0].face:
            case 1: return 10
            case 5: return 5
    elif len(set(a.face for a in area)) == 1:
        ch = int(area[0].face)
        multiplier = 10
        if ch == 1: multiplier = 100
        match len(area): # подсчет последовательных комбинаций из одинаковых элементов
            case 3: return multiplier*ch
            case 4: return multiplier*ch*2
            case 5: return multiplier*ch*10
    else:
        area = sorted(area, key = lambda a: a.face)
        print(''.join(str(a.face) for a in area))
        match ''.join(str(a.face) for a in area):
            case "12345": return 125
            case "23456": return 250
    return 0

def is_player(room_key: str, client_id: int) -> tuple[Client, Room, Player]:
    client = session.query(Client).filter(Client.telegram_id == client_id).first()
    if not client: return None, None, None

    room = session.query(Room).filter(Room.room_key == room_key).first()
    if not room: return None, None, None

    player = session.query(Player).filter(Player.room_id == room.id, Player.client_id == client.id).first()
    if not player: return None, None, None

    return client, room, player

def find_combo(area: list[Dice]):
    
    all_combinations = []
    
    for length in range(1, len(area) + 1):
        combinations = itertools.combinations(area, length)
        all_combinations.extend(combinations)

    combinations = [{"dices": c, "score": r} for c in all_combinations if (r := serial(c)) != 0]
    return combinations

def get_auth_data(r: Request) -> tuple[int, bool]:
    try:
        data = jwt.decode(
            request.cookies.get("tg-auth-token", ""), 
            config['bot']['token'], 
            algorithms=["HS256"]
        )
    except: return None, False

    if (data['exp'] < time.time()):
        return None, False

    return data['id'], data.get("is_admin", False)
