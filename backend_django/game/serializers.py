from .models import Room
from .minimax_bot import PLAYER_ONE, PLAYER_TWO, create_empty_board


def build_error_response(message: str):
	return {
		"type": "room_error",
		"message": message,
	}


def build_player_payload(room: Room, symbol: int):
	if symbol == PLAYER_ONE:
		player = room.player_1
		slot = "player1"
	else:
		player = room.player_2
		slot = "player2"

	return {
		"symbol": PLAYER_TWO if symbol == PLAYER_TWO else PLAYER_ONE,
		"slot": slot,
		"username": player.user.username if player else None,
	}


def build_symbol_payload(symbol: int, username: str | None):
	return {
		"symbol": PLAYER_TWO if symbol == PLAYER_TWO else PLAYER_ONE,
		"slot": "player2" if symbol == PLAYER_TWO else "player1",
		"username": username,
	}


def build_game_result(room: Room):
	if room.status != Room.STATUS_FINISHED:
		return None

	if not room.winner_id or not room.winner_symbol:
		return {
			"winner": None,
			"isDraw": True,
		}

	winner_username = None
	if room.winner:
		winner_username = room.winner.user.username
	elif room.winner_symbol == PLAYER_ONE and room.player_1:
		winner_username = room.player_1.user.username
	elif room.winner_symbol == PLAYER_TWO and room.player_2:
		winner_username = room.player_2.user.username

	return {
		"winner": build_symbol_payload(
			room.winner_symbol,
			winner_username,
		),
		"isDraw": False,
	}


def build_room_event(
	*,
	room: Room,
	message_type: str,
	message: str | None = None,
	last_move: dict | None = None,
):
	payload = {
		"type": message_type,
		"roomCode": room.code,
		"status": room.status,
		"player1": room.player_1.user.username if room.player_1 else None,
		"player2": room.player_2.user.username if room.player_2 else None,
		"board": room.board or create_empty_board(),
		"currentPlayer": build_player_payload(room, room.current_turn),
		"gameResult": build_game_result(room),
	}

	if message:
		payload["message"] = message

	if last_move:
		payload["lastMove"] = last_move

	return payload


def build_room_response(*, room: Room, message_type: str, message: str | None = None):
	return build_room_event(room=room, message_type=message_type, message=message)
