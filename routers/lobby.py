from flask import redirect, request, render_template, Blueprint

from db import session, Room, Client, Player, Dice, Step

from tools.game import set_bet, remove_player, uptdate_dices
from tools.funcs import get_auth_data, resp
from tools.template import env
from tools.announcer import announcer

import json
import random

router = Blueprint('lobby', __name__)


"""
Страница /lobby?<ключ комнаты>
Лобби игры, доступно только игре со stage == 1, иначе редирект на /game либо на /results
"""



@router.route('/', methods=['GET'])
def lobbyPage():

    client_id, is_admin = get_auth_data(request)
    if not client_id:
        return redirect(f"/auth?lobby?{request.query_string.decode()}")
    

    client = session.query(Client).filter(Client.telegram_id == client_id).first()
    if not client: return redirect(f"/auth?lobby?{request.query_string.decode()}")

    room_key = request.query_string.decode()
    if room_key == "":

        player = session.query(Player).filter( Player.client_id == client.id).first()
        if player and player.room.stage < 3: # если игра то перебрасываем в него
            return redirect(f"/lobby?{player.room.room_key}")
        else:
            room = Room(owner_id = client.id, name = f"Лобби игрока {client.first_name}")
            session.add(room)
            session.commit()
            session.add(Player(is_owner=True, room_id=room.id, client_id=client.id))
            session.commit()

            return redirect(f"/lobby?{room.room_key}")

    room = session.query(Room).filter(Room.room_key == room_key).first()

    if not room: 
        t = env.get_template("error.html")
        return render_template(t, message="Похоже комната уже закрылась!")
    
    if room.stage == 2: return redirect(f"/game?{room_key}")
    if room.stage == 3: return redirect(f"/results?{room_key}")

    players = sorted(room.players, key=lambda x: x.join_at)
    player = session.query(Player).filter(Player.room_id == room.id, Player.client_id == client.id).first()

    if not player:

        if client.balance < room.bet:
            t = env.get_template("error.html")
            return render_template(t, message=f"Кажется ставка в комнате слишком высока!")

        announcer.announce(
            "new_player",
            {'player': {"id": client.id, "name": client.first_name, "avatar": client.avatar}},
            room.room_key
        )

        player = Player(room_id=room.id, client_id=client.id)
        session.add(player)
        session.commit()

        players.append(player)

    t = env.get_template("lobby.html")
    return render_template(t, client=client, room=room, players=players)

# несколько методов для лобби
@router.route('/set/bet', methods=['POST'])
def setBet():

    client_id, is_admin = get_auth_data(request)
    room_key = request.query_string.decode()

    if not (client_id or room_key):
        return resp(descr="Кажется стоит авторизоваться", status=401)
    
    client = session.query(Client).filter(Client.telegram_id == client_id).first()
    room = session.query(Room).filter(Room.room_key == room_key, Room.owner_id == client.id).first()
    if not room: return 

    data = json.loads(request.data)
    bet = data['bet'] if data['bet'] else 0

    set_bet(bet, room)

    return resp(descr="Анонс разослан")
    
@router.route('/leave', methods=['POST'])
def leave():

    client_id, is_admin = get_auth_data(request)
    room_key = request.query_string.decode()

    if not (client_id or room_key):
        return resp(descr="Кажется стоит авторизоваться", status=401)
    
    client = session.query(Client).filter(Client.telegram_id == client_id).first()
    room = session.query(Room).filter(Room.room_key == room_key).first()
    if not room:
        return resp(descr="Ключ комнаты неверный", status=400)

    remove_player(client, room)

    return resp(descr="Анонс разослан")

@router.route('/set/name', methods=['POST'])
def setName():

    client_id, is_admin = get_auth_data(request)
    room_key = request.query_string.decode()

    if not (client_id or room_key):
        return resp(descr="Кажется стоит авторизоваться", status=401)
    
    client = session.query(Client).filter(Client.telegram_id == client_id).first()
    room = session.query(Room).filter(Room.room_key == room_key, Room.owner_id == client.id).first()
    if not room: return 

    data = json.loads(request.data)
    name = data['name']

    room.name = name
    session.commit()

    announcer.announce(
        "update_name",
        {'name': name},
        room.room_key
    )

    return resp(descr="Анонс разослан")

@router.route('/start', methods=['POST'])
def startGame():
    """
    
    Эта ручка гененрирует первый шаг, устанавливает room.started = True и активного игрока и делает редирект на страницу игры
    
    """

    client_id, is_admin = get_auth_data(request)
    data = json.loads(request.data)

    room_key = data.get("room_key")

    if not (client_id or room_key):
        return resp(descr="Кажется стоит авторизоваться", status=401)

    if not (room_key := data.get("room_key")):
        return resp(descr="Комната не найдена", status=400)

    
    client = session.query(Client).filter(Client.telegram_id == client_id).first()
    room = session.query(Room).filter(Room.room_key == room_key, Room.owner_id == client.id).first()
    player = session.query(Player).filter(Player.client_id == client.id, Player.room_id == room.id).first()
    
    if not room or not player: 
        return resp(descr="Чтото пошло не так, комнаты нет либо пользователь не валаделец комнаты", status=400)

    player.is_active = True
    room.stage = 1
    step = Step(player_id = player.id, room_id= room.id)
    session.add(step)
    session.commit()

    dices = []

    for r in range(1, 6):
        d = Dice(room_id = room.id, index = r, face = random.randint(1, 6), step_id = step.id)
        session.add(d)
        dices.append(d)

    session.commit()

    is_bolt = uptdate_dices(room)
    step.is_bolt = is_bolt
    session.commit()

    announcer.announce(
        "redirect",
        {'target': f"/game?{room_key}"},
        room.room_key
    )

    return resp(descr="Редирект, игра началась")