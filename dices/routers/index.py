from flask import redirect, request, render_template, Blueprint
from tools.template import env
from tools.funcs import get_auth_data
from db import session, Client, Player


router = Blueprint('index', __name__)


@router.route("/", methods=["GET"])
def index():

    client_id, is_admin = get_auth_data(request)
    if not client_id:
        return redirect("/auth")

    client = session.query(Client).filter(Client.telegram_id == client_id).first()
    if not client: return redirect("/auth")

    player = session.query(Player).filter(Player.client_id == client.id).first()
    if player and player.room.stage != 2:
        return redirect(f"/lobby?{player.room.room_key}")

    t = env.get_template("index.html")
    return render_template(t, client=client)