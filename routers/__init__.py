from flask import Flask, request
from flask_sse import sse

from db import db
from tools.funcs import get_auth_data, resp
from tools.config import config

import logging

app = Flask(__name__)

app.config["REDIS_URL"] = "redis://localhost"
app.config['SQLALCHEMY_DATABASE_URI'] = config['server']['db']

db.init_app(app)

from . import auth, errors, game_api, game, index, lobby, results, static, bonus

app.register_blueprint(index.router, url_prefix='/')
app.register_blueprint(bonus.router, url_prefix='/')
app.register_blueprint(static.router, url_prefix='/')

app.register_blueprint(auth.router, url_prefix='/auth')
app.register_blueprint(game.router, url_prefix='/game')
app.register_blueprint(lobby.router, url_prefix='/lobby')
app.register_blueprint(errors.router, url_prefix='/error')
app.register_blueprint(results.router, url_prefix='/results')
app.register_blueprint(game_api.router, url_prefix='/game')

@app.route('/listen', methods=['GET'])
def listen(): # еще нужно фильтровать к каким каналам может подключаться клиент
    client_id, is_admin = get_auth_data(request)
    if client_id: return sse.stream()
    return resp(status=401)

handler = logging.FileHandler('logs/flask.log')
app.logger.addHandler(handler)

handler = logging.StreamHandler()
app.logger.addHandler(handler)

app.logger.setLevel(logging.INFO)