from flask import redirect, request, render_template, Blueprint
from tools.template import env
from tools.funcs import get_auth_data
from db import session, Room, Client, Player
from tools.funcs import get_auth_data

import json
import random

router = Blueprint('game', __name__)

@router.route('/', methods=['GET'])
def gamePage():

    client_id, is_admin = get_auth_data(request)
    if not client_id:
        return redirect(f"/auth?game?{request.query_string.decode()}")
    
    client = session.query(Client).filter(Client.telegram_id == client_id).first()
    if not client: return redirect(f"/auth?game?{request.query_string.decode()}")

    room_key = request.query_string.decode()
    if room_key == "": 
        t = env.get_template("error.html")
        return render_template(t, message=f"Стоит попробовать начать!")

    room = session.query(Room).filter(Room.room_key == room_key).first()
    if not room: 
        t = env.get_template("error.html")
        return render_template(t, message=f"Комнаты не существует!")

    if room.stage == 0:
        return redirect(f"/lobby?{room_key}")
    if room.stage == 2: 
        return redirect(f"/results?{room_key}")

    player = session.query(Player).filter(Player.room_id == room.id, Player.client_id == client.id).first()

    t = env.get_template("game.html")

    return render_template(
        t,
        room_key=request.query_string.decode(),
        room=room,
        player=player
    )
