from flask import Blueprint, request, send_from_directory
import os

router = Blueprint('static', __name__)

# статический роутинг
@router.route('/images/<path:path>', methods=['GET'])
def staticImages(path):
    response = send_from_directory("images", path)
    return response

@router.route('/dices/<path:path>', methods=['GET'])
def staticDices(path):
    if os.path.exists(os.path.join("dices", path)):
        response = send_from_directory("dices", path)
    else:
        response = send_from_directory("dices/def", path.split("/")[-1])
    return response

@router.route('/<path:path>', methods=['GET'])
def staticFiles(path):
    response = send_from_directory("html", path)
    return response
