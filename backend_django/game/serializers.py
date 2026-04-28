from .models import Room


def serialize_room(room: Room):
	return {
		"code": room.code,
		"status": room.status,
		"player1": room.player_1.user.username if room.player_1 else None,
		"player2": room.player_2.user.username if room.player_2 else None,
		"players": [
			username
			for username in [
				room.player_1.user.username if room.player_1 else None,
				room.player_2.user.username if room.player_2 else None,
			]
			if username
		],
		"createdAt": room.created_at.isoformat() if room.created_at else None,
	}


def build_room_event(*, room: Room, message_type: str, text: str, actor: str):
	return {
		"type": message_type,
		"room": serialize_room(room),
		"message": {
			"kind": "system",
			"actor": actor,
			"text": text,
		},
	}


def build_room_response(*, room: Room, message_type: str, text: str, actor: str):
	payload = build_room_event(room=room, message_type=message_type, text=text, actor=actor)
	payload["roomCode"] = room.code
	return payload
