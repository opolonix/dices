from flask import redirect, request, render_template, Blueprint
from sqlalchemy import or_
from db import session, Client, Player, DiceModel, ClientDice

from tools.funcs import get_auth_data, resp, datetimeToInt
from tools.template import env
from tools.wallet import collections

import json

router = Blueprint('index', __name__)


@router.route("/", methods=["GET"])
def index():

    client_id, is_admin = get_auth_data(request)
    if not client_id:
        return redirect("/auth")

    client = session.query(Client).filter(Client.telegram_id == client_id).first()
    if not client: return redirect("/auth")

    models = collections(client.wallet)
    allowed_models = session.query(DiceModel).filter(or_(DiceModel.collection.in_([d['address'] for d in models]), DiceModel.collection == None)).all()

    mapped = {m['address']: m for m in models}

    for m in allowed_models:
        if not m.collection or not m.auto_update: continue
        m.title = mapped[m.collection]['name']
        m.description = mapped[m.collection]['description']

    client_dices = session.query(ClientDice).filter(ClientDice.client_id == client.id).all()
    if len(client_dices) != 5:
        for i in range(len(client_dices), 5):
            session.add(ClientDice(client_id = client.id, index = i + 1))

    session.commit()


    player = session.query(Player).filter(Player.client_id == client.id).first()
    if player and player.room.stage == 1:
        return redirect(f"/lobby?{player.room.room_key}")

    t = env.get_template("index.html")
    return render_template(t, client=client, models=allowed_models, datetimeToInt=datetimeToInt)

@router.route("/setDice", methods=["POST"])
def setDice():
    """
        Принимает model_id как ссылку на модельку кубика, а также index - номер кубика, к которому применится моделька
    """

    client_id, is_admin = get_auth_data(request)
    if not client_id:
        return resp(descr="Авторизация", status=403)

    data = json.loads(request.data)

    client = session.query(Client).filter(Client.telegram_id == client_id).first()
    
    model_id = data.get("model_id")
    dice_index = data.get("dice_id")

    models = collections(client.wallet)
    model = session.query(DiceModel).filter(DiceModel.collection.in_([d['address'] for d in models]), DiceModel.id == model_id).first()

    if not model:
        return resp(descr="Эту модельку нельзя применить", status=400)

    session.query(ClientDice).filter(ClientDice.index == dice_index, ClientDice.client_id == client.id).update({ClientDice.model_id: model.id})
    session.commit()

    return resp()

@router.route("/rules", methods=["GET"])
def rules():

    client_id, is_admin = get_auth_data(request)
    if not client_id:
        return redirect("/auth?rules")

    client = session.query(Client).filter(Client.telegram_id == client_id).first()
    if not client: return redirect("/auth?rules")

    t = env.get_template("rules.html")
    return render_template(t, client=client)