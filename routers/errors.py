from flask import Blueprint, request, render_template
from tools.template import env
import urllib

router = Blueprint('error', __name__)

@router.route('/', methods=['GET']) # вывод любого сообщения об ошибке
def errorPage():
    t = env.get_template("error.html")
    return render_template(t, message=urllib.parse.unquote(request.query_string.decode()))