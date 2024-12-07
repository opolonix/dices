from db import session, Dice, Step, Client, Player, Room
from tools.announcer import announcer

def is_player(room_key: str, client_id: int) -> tuple[Client, Room, Player]:
    client = session.query(Client).filter(Client.telegram_id == client_id).first()
    if not client: return None, None, None

    room = session.query(Room).filter(Room.room_key == room_key).first()
    if not room: return None, None, None

    player = session.query(Player).filter(Player.room_id == room.id, Player.client_id == client.id).first()
    if not player: return None, None, None

    return client, room, player

def remove_player(client: Client, room: Room):
    if client.id != room.owner_id:
        announcer.announce(
            "leave_player", {'player': {"id": client.id}},
            [player.client.telegram_id for player in room.players if player.client.telegram_id != client.id]
        )
        session.query(Player).filter(Player.client_id == client.id, Player.room_id == room.id).delete()
        session.commit()

        # когда игрок поидает комнату, пересчитываем ставку

        min_bet = 0
        max_bet = 0
        
        for player in room.players:
            if client.id != player.client_id:
                max_bet = min(max_bet, player.client.balance)

        bet = min(max_bet, bet) # отклонить ставку больше максимальной
        bet = max(min_bet, bet) # отклонить ставку больше минимальной

        announcer.announce(
            "update_bet",
            {'bet': room.bet, "max": max_bet, "min": min_bet},
            [player.client.telegram_id for player in room.players]
        )
        session.commit()

    else:
        announcer.announce(
            "close_room", {},
            [player.client.telegram_id for player in room.players if player.client.telegram_id != client.id]
        )

        session.delete(room)
        session.commit()

def set_bet(bet: int, room: Room):

    min_bet = 0
    max_bet = 0

    for player in room.players:
        max_bet = min(max_bet, player.client.balance)

    bet = min(max_bet, bet) # отклонить ставку больше максимальной
    bet = max(min_bet, bet) # отклонить ставку больше минимальной

    announcer.announce(
        "update_bet",
        {'bet': bet, "max": max_bet, "min": min_bet},
        [player.client.telegram_id for player in room.players]
    )

    room.bet = bet
    session.commit()