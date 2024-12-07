from flask import request, Blueprint
from sqlalchemy import desc

from db import Step, Dice, session 

from tools.game import new_step, validate, get_state, calc_score, send_message, uptdate_dices
from tools.funcs import resp, serial
from tools.announcer import announcer

router = Blueprint('game-api', __name__)

@router.route('/state', methods=['POST'])
def getState():

    """

    Полное текущее состояние игры
    :room_key - ссылка на комнату

    """

    valid = validate(request)
    if not valid.ok:
        return resp(None, valid.message, valid.status)

    result = get_state(valid.room, valid.player, ["player", "active_player", "players", "steps", "area", "tray"])
    return resp(result, descr="Текущее состояние игры")

@router.route('/new-step', methods=['POST'])
def newStep():
    """
    Запрашивает новый ход, работает когда пользователь выбирает перебросить кости вместо завершения хода
    :room_key - ссылка на комнату

    returns:
        step - новый шаг
        combo - массив комбинаций
    """

    valid = validate(request)
    if not valid.ok:
        return resp(None, valid.message, valid.status)

    room = valid.room
    player = valid.player

    this_step = session.query(Step).filter(Step.room_id == room.id).order_by(desc(Step.time)).first()

    if len([d for d in room.dices if not d.in_tray]) == 0: # если трей полный то очищаем его
        # перед обнулением трея записываем счет
        this_step.score += calc_score(room.dices)
        is_bolt = uptdate_dices(room, clear_tray=True)
    else:
        is_bolt = uptdate_dices(room)

    step = Step(is_bolt = is_bolt, player_id = player.id, room_id = room.id, score=this_step.score)
    this_step.score = 0 # обнуляем счет прошлого шага
    session.add(step)
    session.commit()

    result = get_state(room, player, ["steps", "area", "tray"])
    announcer.announce("state-update", result, room.room_key)
    return resp()

@router.route('/end-step', methods=['POST'])
def endStep():

    """
    Завершает цикл бросков и передает ход следующему игроку. Обнуляет трей
    :room_key - ссылка на комнату

    Делает два анонса о смене игрока и о новом шаге

    """

    valid = validate(request)
    if not valid.ok:
        return resp(None, valid.message, valid.status)
    
    room = valid.room
    player = valid.player
    new_player = new_step(room, player)

    if player.score >= 1000:
        room.stage = 3

        # начисляем ставку
        for p in room.players:
            p.client.balance -= room.bet
        player.client.balance += room.bet * len(room.players)

        session.commit()
        announcer.announce("redirect", {"target": f"/results?{room.room_key}"}, room.room_key)
        return resp()

    result = get_state(room, new_player, ["active_player", "players", "steps", "area", "tray"])
    announcer.announce("state-update", result, room.room_key)
    return resp()

@router.route('/tray-add', methods=['POST'])
def trayAdd():
    """
    Перемещает кубики в трей

    :dices - list[int] массив кубиков для переноса в трей
    :room_key - ссылка на комнату

    """

    valid = validate(request)
    if not valid.ok:
        return resp(None, valid.message, valid.status)
    
    room = valid.room
    player = valid.player
    data = valid.data

    step = session.query(Step).filter(Step.room_id == room.id).order_by(desc(Step.time)).first()
    dices = session.query(Dice).filter(Dice.room_id == room.id, Dice.in_tray == False, Dice.id.in_(data.get("dices", []))).all()

    if len([d for d in dices if not d.in_combo]) != 0:
        return resp(descr="Это не комбинация", status=400)

    step.tray_updated = True
    for d in dices:
        d.in_tray = True

    session.commit()

    result = get_state(room, player, ["steps", "area", "tray"])
    announcer.announce("state-update", result, room.room_key)
    return resp()

@router.route('/commit-step', methods=['POST'])
def commitStep():
    """
    Комиитит степ (т.е бросок завершен)

    если шаг с болтом то делается анонс о смене игрока
    """

    valid = validate(request)
    if not valid.ok:
        return resp(None, valid.message, valid.status)
    
    room = valid.room
    player = valid.player

    step = session.query(Step).filter(Step.room_id == room.id).order_by(desc(Step.time)).first()
    step.stage = 3 if step.is_bolt else 2 # сразу завершаем шаг если болт
    player.bolts += 1 if step.is_bolt else 0

    if player.bolts == 3:
        player.score -= 50
        player.bolts = 0

    session.commit()

    if step.is_bolt: # генерируем новый шаг в случае болта
        new_player = new_step(room, player)
        result = get_state(room, new_player, ["active_player", "players", "steps", "area", "tray"])

        send_message(room, "bolt")

        announcer.announce("state-update", result, room.room_key)
        return resp()

    result = get_state(room, player, ["steps", "area", "tray"])
    announcer.announce("state-update", result, room.room_key)
    return resp()