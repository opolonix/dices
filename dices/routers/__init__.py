from flask import Flask
from db import db
from tools.config import config
from flask_migrate import Migrate
import logging

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config['server']['db']
migrate = Migrate()

db.init_app(app)
# migrate.init_app(app, db) # пока не работает

from . import auth, errors, game_api, game, index, lobby, results, static

app.register_blueprint(auth.router, url_prefix='/auth')
app.register_blueprint(errors.router, url_prefix='/error')
app.register_blueprint(game_api.router, url_prefix='/game')
app.register_blueprint(game.router, url_prefix='/game')
app.register_blueprint(lobby.router, url_prefix='/lobby')
app.register_blueprint(results.router, url_prefix='/results')
app.register_blueprint(index.router, url_prefix='/')
app.register_blueprint(static.router, url_prefix='/')


handler = logging.FileHandler('logs/flask.log')
app.logger.addHandler(handler)

handler = logging.StreamHandler()
app.logger.addHandler(handler)

app.logger.setLevel(logging.DEBUG)