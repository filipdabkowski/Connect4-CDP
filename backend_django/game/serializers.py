from .models import Room


def build_error_response(message: str):
	return {
		"type": "room_error",
		"message": message,
	}


def build_room_event(*, room: Room, message_type: str, message: str | None = None):
	payload = {
		"type": message_type,
		"roomCode": room.code,
		"status": room.status,
		"player1": room.player_1.user.username if room.player_1 else None,
		"player2": room.player_2.user.username if room.player_2 else None,
	}

	if message:
		payload["message"] = message

	return payload


def build_room_response(*, room: Room, message_type: str, message: str | None = None):
	return build_room_event(room=room, message_type=message_type, message=message)
