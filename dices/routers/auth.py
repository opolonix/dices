from flask import Blueprint, request, render_template
from tools.template import env
from tools.funcs import get_auth_data, resp
from tools.tgvalidate import validate
from tools.config import config
from db import session, Client

import json
import jwt
from datetime import datetime, timedelta

router = Blueprint('auth', __name__)

@router.route('/', methods=['GET']) # страница авторизации, генерирует куки
def tgAuthPage():
    t = env.get_template("auth.html")

    return render_template(t, redirect=request.query_string.decode())

# все апи методы post
@router.route('/', methods=['POST'])
def tgAuth():
    data = validate(request.data.decode(), config['bot']['token'])
    
    if data is None:
        return resp(descr="Неверные данные авторизации", status=400)

    user = json.loads(data['user'])

    print("auth", user)

    client = session.query(Client).filter(Client.telegram_id == user['id']).first()

    if not client:
        client = Client(
            telegram_id = user['id'],
 
            is_premium = user.get('is_premium', False),
            allows_write = user.get('allows_write_to_pm', False),
            language_code = user['language_code'],
            username = user.get("username", None),
            last_name = user['last_name'],
            first_name = user['first_name']
        )
        session.add(client)
        session.commit()
    else:
        client.first_name = user['first_name']
        client.is_premium = user.get('is_premium', client.is_premium)
        client.allows_write = user.get('allows_write_to_pm', client.allows_write)
        client.language_code = user['language_code']
        client.username = user.get("username", None)
        client.last_name = user['last_name']
        client.last_visit = datetime.now()
        session.commit()

    if client.banned:
        return resp(descr="Похоже вас заблокировали на этом сервисе...", status=403)

    response = resp()
    response.set_cookie(
        "tg-auth-token",
        jwt.encode({
            "id": client.telegram_id, 
            "exp": (datetime.now() + timedelta(hours=16)).timestamp(), 
            "is_admin": False
            }, 
            config['bot']['token']
        ),
        max_age=60*60*16
    )
    return response

@router.route('/wallet', methods=['POST'])
def setWallet():

    client_id, is_admin = get_auth_data(request)
    print(request.data)
    data = json.loads(request.data)

    if client_id:
        if data.get("address") and session.query(Client).filter(Client.wallet == data.get("address")).first():
            return resp(None, "Кошелек уже привязан")

        client = session.query(Client).filter(Client.telegram_id == client_id).first()
        client.wallet = data.get("address")
        session.commit()

        return resp(None, "Кошелек успешно привязан")
    
    return resp(None, "Пользователь не найден", False, 400)