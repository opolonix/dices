from flask import redirect, request, render_template, Blueprint

from db import session, Room, Client

from tools.funcs import get_auth_data
from tools.template import env

"""
Страница /results?<ключ комнаты>
Показывает результат завершенной игры
"""


router = Blueprint('results', __name__)

@router.route('/', methods=['GET'])
def resultsPage():

    client_id, is_admin = get_auth_data(request)
    if not client_id:
        return redirect(f"/auth?lobby?{request.query_string.decode()}")
    

    client = session.query(Client).filter(Client.telegram_id == client_id).first()
    if not client: return redirect(f"/auth?results?{request.query_string.decode()}")

    room_key = request.query_string.decode()
    if room_key == "":
        t = env.get_template("error.html")
        return render_template(t, message="Упс, с ссылкой что-то не то!")

    room = session.query(Room).filter(Room.room_key == room_key).first()

    if not room: 
        t = env.get_template("error.html")
        return render_template(t, message="Похоже комната уже закрылась!")
    
    if room.stage == 0: return redirect(f"/lobby?{room_key}")
    if room.stage == 1: return redirect(f"/game?{room_key}")

    players = sorted(room.players, key=lambda x: x.score)

    t = env.get_template("results.html")
    return render_template(t, client=client, room=room, players=players)