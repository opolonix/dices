from flask import request, Blueprint, Response
from db import session, Room, Client, Player, as_dict, Step

from tools.template import env
from tools.funcs import get_auth_data
from tools.announcer import announcer
from tools.funcs import get_auth_data, find_combo, serial, resp

import random
import json

router = Blueprint('game-api', __name__)


@router.route('/listen', methods=['GET'])
def listen():
    client_id, is_admin = get_auth_data(request)
    if client_id:
        messages = announcer.listen(client_id)
        def stream():
            yield 'retry: 1000\n' 
            while True:
                yield "data: " + messages.get().replace("\n\n", "") + "\n\n"

        return Response(stream(), mimetype='text/event-stream', headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
            'Content-Type': 'text/event-stream'
        })
    
    return Response(json.dumps({"ok": False}), 400)


@router.route('/game/state', methods=['POST'])
def getState():

    """

    Полное текущее состояние игры
    :room_key - ссылка на комнату

    """

    client_id, is_admin = get_auth_data(request)
    data = json.loads(request.data)

    room_key = data.get("room_key")
    fields = data.get("fields")

    if not client_id: 
        return resp(None, "Пользователь не авторизован / токен авторизации истек", False, 400)

    if not (room_key := data.get("room_key")):
        return resp(None, "Комната не найдена", False, 400)

    client, room, player = is_player(room_key, client_id)

    if not client:
        return resp(None, "Игрок не пренадлежит этой комнате, либо комнаты не существует", False, 400)

    if room.stage == 0:
        return resp(None, "Рано, игра еще не началась", False, 400)

    active_player = session.query(Player).filter(Player.room_id == room.id, Player.is_active == True).first()

    c = find_combo(room.dices)
    c.sort(key=lambda x: -x['score'])
    combos = []
    combo_ids = set()

    for combo in c:
        if len([d for d in combo['dices'] if d.id in combo_ids]) == 0:
            for d in combo['dices']:
                d.in_combo = True
                combo_ids.add(d.id)
            session.commit()
            combos.append({"score": serial(combo['dices']), "dices": [as_dict(d) for d in combo['dices']]})

    result = {
        "room": as_dict(room),
        "player": as_dict(player, player.client),
        "active_player": as_dict(active_player, active_player.client),
        "players": [as_dict(p, p.client) for p in room.players],
        "steps": [as_dict(s) for s in room.steps],
        "dices": [as_dict(d) for d in room.dices],
        "combinations": combos
    }
    
    return resp(result, "Текущее состояние комнаты")

@router.route('/game/new-step', methods=['POST'])
def newStep():
    """
    
    Запрашивает новый ход, работает когда пользователь выбирает перебросить кости вместо завершения хода
    :room_key - ссылка на комнату

    returns:
        step - новый шаг
        combo - массив комбинаций
    
    """

    client_id, is_admin = get_auth_data(request)
    data = json.loads(request.data)

    room_key = data.get("room_key")

    if not client_id: 
        return resp(None, "Пользователь не авторизован / токен авторизации истек", False, 400)

    if not (room_key := data.get("room_key")):
        return resp(None, "Комната не найдена", False, 400)

    client, room, player = is_player(room_key, client_id)

    this_step = session.query(Step).filter(Step.room_id == room.id).order_by(desc(Step.time)).first()

    # if not (this_step.tray_updated and this_step.stage == 3) and not (this_step.stage == 4):
    #     return resp(None, "Недопустимое действие", False, 400)

    for dice in room.dices:
        if not dice.in_combo:
            dice.face = random.randint(1, 5)


    c = find_combo([d for d in room.dices if not d.in_combo])
    c.sort(key=lambda x: -x['score'])
    combos = []
    combo_ids = set()

    step = Step(is_bolt = len(c) == 0, player_id = player.id, room_id = room.id)
    session.add(step)
    session.commit()

    if len(c) == 0:
        step.is_bolt = True

    for combo in c:
        if len([d for d in combo['dices'] if d.id in combo_ids]) == 0:
            for d in combo['dices']:
                d.in_combo = True
                combo_ids.add(d.id)
            combos.append({"score": serial(combo['dices']), "dices": [as_dict(d) for d in combo['dices']]})

    session.commit()
    

    announcer.announce(
        "new-step", 
        {"step": as_dict(step), "combinations": combos},
        [player.client.telegram_id for player in room.players]
    )

    announcer.announce(
        "dices-update",
        {"dices": [as_dict(d) for d in room.dices]},
        [player.client.telegram_id for player in room.players]
    )


    return resp(None, "Анонс разослан")

@router.route('/game/end-step', methods=['POST'])
def endStep():

    """
    Завершает цикл бросков и передает ход следующему игроку. Обнуляет трей
    :room_key - ссылка на комнату

    Делает два анонса о смене игрока и о новом шаге

    """
    client_id, is_admin = get_auth_data(request)
    data = json.loads(request.data)

    room_key = data.get("room_key")
    fields = data.get("fields")

    if not client_id: 
        return resp(None, "Пользователь не авторизован / токен авторизации истек", False, 400)

    if not (room_key := data.get("room_key")):
        return resp(None, "Комната не найдена", False, 400)

    client, room, player = is_player(room_key, client_id)
    this_step = session.query(Step).filter(Step.room_id == room.id).order_by(desc(Step.time)).first()

    if not (this_step.tray_updated or not this_step.is_bolt):
        return resp(None, "Недопустимое действие", False, 400)
    
    player.score += this_step.score
    session.commit()


    new_player = session.query(Player).filter(Player.room_id == room.id, Player.join_at > player.join_at).first()
    if not new_player: new_player = session.query(Player).filter(Player.room_id == room.id).order_by(Player.join_at).first()
    
    step = Step(player_id = new_player.id, room_id = room.id)
    session.add(step)
    session.commit()

    new_player.is_active = True
    player.is_active = False

    for dice in room.dices:
        dice.face = random.randint(1, 5)
        dice.in_combo = False
        dice.in_tray = False

    c = find_combo(room.dices)
    c.sort(key=lambda x: -x['score'])
    combos = []
    combo_ids = set()

    if len(c) == 0:
        step.is_bolt = True

    for combo in c:
        if len([d for d in combo['dices'] if d.id in combo_ids]) == 0:
            for d in combo['dices']:
                d.in_combo = True
                combo_ids.add(d.id)
            combos.append({"score": serial(combo['dices']), "dices": [as_dict(d) for d in combo['dices']]})

    session.commit()
    

    announcer.announce(
        "change-player", 
        {"active_player": as_dict(new_player, new_player.client), "player": as_dict(player, client)},
        [player.client.telegram_id for player in room.players]
    )

    announcer.announce(
        "new-step", 
        {"step": as_dict(step), "combinations": combos},
        [player.client.telegram_id for player in room.players]
    )

    announcer.announce(
        "dices-update",
        {"dices": [as_dict(d) for d in room.dices]},
        [player.client.telegram_id for player in room.players]
    )

    return resp(None, "Анонс разослан")

@router.route('/game/tray-add', methods=['POST'])
def trayAdd():
    """
    Перемещает кубики в трей

    :dices - list[int] массив кубиков для переноса в трей
    :room_key - ссылка на комнату

    """

    client_id, is_admin = get_auth_data(request)
    data = json.loads(request.data)

    room_key = data.get("room_key")

    if not client_id: return resp(None, "Пользователь не авторизован / токен авторизации истек", False, 400)

    if not (room_key := data.get("room_key")):
        return resp(None, "Комната не найдена", False, 400)

    client, room, player = is_player(room_key, client_id)

    step = session.query(Step).filter(Step.room_id == room.id).order_by(desc(Step.time)).first()
    dices = session.query(Dice).filter(Dice.room_id == room.id, Dice.in_tray == False, Dice.id.in_(data.get("dices", []))).all()

    score = serial(dices) # переписать, подсчитывать счет нужно когда ход заканчивается по трею

    if score != 0:
        step.tray_updated = True
        for d in dices:
            d.in_tray = True
    step.score += score
    session.commit()

    if player.score + step.score >= 1000:
        room.stage = 2
        session.commit()
        announcer.announce(
            "redirect", 
            {"target": f"/results?{room.room_key}"},
            [p.client.telegram_id for p in room.players]
        )
        
        return resp(None, "Конец игры")

    announcer.announce(
        "dices-update", 
        {"dices": [as_dict(d) for d in room.dices]},
        [p.client.telegram_id for p in room.players if p.id != player.id]
    )

    announcer.announce(
        "score-update", 
        {"score": step.score},
        [p.client.telegram_id for p in room.players]
    )

    return resp({"dices": [as_dict(d) for d in room.dices]}, "Анонс разослан")

@router.route('/game/commit-step', methods=['POST'])
def commitStep():
    """
    Комиитит степ (т.е бросок завершен)

    если шаг с болтом то делается анонс о смене игрока
    """

    client_id, is_admin = get_auth_data(request)
    data = json.loads(request.data)

    room_key = data.get("room_key")

    if not client_id: return resp(None, "Пользователь не авторизован / токен авторизации истек", False, 400)

    if not (room_key := data.get("room_key")):
        return resp(None, "Комната не найдена", False, 400)

    client, room, player = is_player(room_key, client_id)

    step = session.query(Step).filter(Step.room_id == room.id).order_by(desc(Step.time)).first()
    dices = session.query(Dice).filter(Dice.room_id == room.id, Dice.in_tray == False, Dice.id.in_(data.get("dices", []))).all()
    score = serial(dices) # переписать, подсчитывать счет нужно когда ход заканчивается по трею

    if score != 0:
        step.tray_updated = True
    step.score += score
    step.stage = 4 if step.is_bolt else 2
    session.commit()

    announcer.announce(
        "commit-step", 
        {"step": as_dict(step)},
        [p.client.telegram_id for p in room.players]
    )

    if step.is_bolt:
        new_player = session.query(Player).filter(Player.room_id == room.id, Player.join_at > player.join_at).first()
        if not new_player: new_player = session.query(Player).filter(Player.room_id == room.id).order_by(Player.join_at).first()


        for dice in room.dices:
            dice.face = random.randint(1, 5)

        combo = find_combo([d for d in room.dices if not d.in_tray])
        new_step = Step(is_bolt = len(combo) == 0, player_id = new_player.id, room_id = room.id)
        session.add(new_step)

        new_player.is_active = True
        player.is_active = False
        player.bolts += 1
        session.commit()

        combo.sort(key=lambda x: -x['score'])
        combos = []
        combo_ids = set()

        if len(combo) == 0:
            new_step.is_bolt = True

        for combo in combo:
            if len([d for d in combo['dices'] if d.id in combo_ids]) == 0:
                for d in combo['dices']:
                    d.in_combo = True
                    combo_ids.add(d.id)
                combos.append({"score": serial(combo['dices']), "dices": [as_dict(d) for d in combo['dices']]})

        announcer.announce(
            "change-player", 
            {"active_player": as_dict(new_player, new_player.client), "player": as_dict(player, client)},
            [player.client.telegram_id for player in room.players]
        )

        announcer.announce(
            "new-step", 
            {"step": as_dict(new_step), "combinations": combos},
            [player.client.telegram_id for player in room.players]
        )

        announcer.announce(
            "dices-update", 
            {"dices": [as_dict(d) for d in room.dices]},
            [player.client.telegram_id for player in room.players]
        )
    
    return resp(None, "Анонс разослан")

@router.route('/game/dice-meta', methods=['POST'])
def diceMeta():

    """
    У каждого кубика есть метаданные, предполагается что они используются для сохранения позиции кубика

    :dice_id - int
    :meta - строка
    :room_key - ссылка на комнату

    """

    client_id, is_admin = get_auth_data(request)
    data = json.loads(request.data)

    room_key = data.get("room_key")

    if not client_id: 
        return resp(None, "Пользователь не авторизован / токен авторизации истек", False, 400)

    if not (room_key := data.get("room_key")):
        return resp(None, "Комната не найдена", False, 400)

    client, room, player = is_player(room_key, client_id)

    if player.is_active:
        dice = session.query(Dice).filter(Dice.room_id == room.id, Dice.id == data.get("dice_id")).first()
        if dice:
            dice.meta = data.get("meta")
            session.commit()
        return resp({"dice": as_dict(dice)}, "Метаданные кубика обновлены")

    return resp(None, "Только текущий игрок может установить мету для кубика", False, 400)

@router.route('/game/announce', methods=['POST'])
def gameAnonce():

    """
    Генерирует анонс от активного пользователя, временное решение для разработки.

    :room_key - str
    :data - содержимое анонса
    :event - не обязательный, по умолчанию "announce"
    
    """

    client_id, is_admin = get_auth_data(request)
    data = json.loads(request.data)

    room_key = data.get("room_key")
    fields = data.get("fields")

    if not client_id: return resp(None, "Пользователь не авторизован / токен авторизации истек", False, 400)

    if not (room_key := data.get("room_key")):
        return resp(None, "Комната не найдена", False, 400)

    client, room, player = is_player(room_key, client_id)

    if player.is_active:
        announcer.announce(
            data.get("event", "announce"),
            data.get("data", {}),
            [p.client.telegram_id for p in room.players if p.id != player.id]
        )
        return make_response(Response(json.dumps({"ok": True, "description": "Анонс разослан. Чтобы отправить ивент с определенным именем нужно передать поле event"}), status=200))

    return make_response(Response(json.dumps({"ok": False, "description": "Анонс доступен только активному игроку"}), status=400))

"""
нужно текущее состояние игры /game/state

анонсы сервера
    обьявить новый ход - new-step - step
    игрок сделал свайп - commit-step - step
    обьявить о смене игрока - change-player - Player (обьект нового игрока)
    добавить кубики в трей(соответственно убрать кубики с игрового поля) dices-update - list[Dice] - массив кубиков, нужно для обновления состояния
    обнулить содержимое трея (соответственно вернуть кубики на поле) - tray-drop

сервисные анонсы
    redirect - url
    message - text
    
ручки клиента

    запросить новый ход /game/new-step
    подтвердить ход /game/commit-step
    запросить переход к следующему /game/end-step

    переместить кубик в трей /game/tray-add
    установить метаданные кубика /game/dice-meta

    функция anonce для текущего игрока /game/anonce

запрашиваем ход (в первый раз этот этап пропускается, так как ход генерируется принудительно и не может быть пропущен)
игрок делает свайп > устанавливаем мету для кубиков и фронт делает коммит шага
по ходу определяем у нас болт, в таком случае прилетает событие change-player, либо вариант закончить ход / продолжить бросать, либо обязан сделать бросок
переходит на первый пункт / сменя игрока
"""