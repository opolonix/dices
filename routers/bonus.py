from flask import redirect, request, render_template, Blueprint
from db import session, Client

from tools.funcs import get_auth_data, resp, datetimeToInt
from tools.template import env

import json

router = Blueprint('bonus', __name__)


@router.route("/bonus", methods=["GET"])
def bonusPage():

    client_id, is_admin = get_auth_data(request)
    if not client_id:
        return redirect("/auth")

    client = session.query(Client).filter(Client.telegram_id == client_id).first()
    if not client: return redirect("/auth?bonus")

    t = env.get_template("bonus.html")
    return render_template(t, client=client, datetimeToInt=datetimeToInt)
