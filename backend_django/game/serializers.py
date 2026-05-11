from rest_framework import serializers

from .models import Room
from .minimax_bot import PLAYER_ONE, PLAYER_TWO, create_empty_board


class RoomPlayerSerializer(serializers.Serializer):
	symbol = serializers.IntegerField(min_value=PLAYER_ONE, max_value=PLAYER_TWO)
	slot = serializers.CharField()
	username = serializers.CharField(allow_null=True)

	@staticmethod
	def from_room(room: Room, symbol: int):
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

	@staticmethod
	def from_symbol(symbol: int, username: str | None):
		return {
			"symbol": PLAYER_TWO if symbol == PLAYER_TWO else PLAYER_ONE,
			"slot": "player2" if symbol == PLAYER_TWO else "player1",
			"username": username,
		}


class GameResultSerializer(serializers.Serializer):
	winner = RoomPlayerSerializer(allow_null=True)
	isDraw = serializers.BooleanField()


class LastMoveSerializer(serializers.Serializer):
	player = RoomPlayerSerializer()
	column = serializers.IntegerField(min_value=0)


class RoomErrorSerializer(serializers.Serializer):
	type = serializers.SerializerMethodField()
	message = serializers.CharField()

	def get_type(self, payload):
		return "room_error"


class RoomSerializer(serializers.ModelSerializer):
	type = serializers.SerializerMethodField()
	roomCode = serializers.CharField(source="code", read_only=True)
	status = serializers.SerializerMethodField()
	player1 = serializers.SerializerMethodField()
	player2 = serializers.SerializerMethodField()
	board = serializers.SerializerMethodField()
	currentPlayer = serializers.SerializerMethodField()
	gameResult = serializers.SerializerMethodField()
	message = serializers.SerializerMethodField()
	lastMove = serializers.SerializerMethodField()

	class Meta:
		model = Room
		fields = (
			"type",
			"roomCode",
			"status",
			"player1",
			"player2",
			"board",
			"currentPlayer",
			"gameResult",
			"message",
			"lastMove",
		)

	def get_type(self, room):
		return self.context.get("message_type", "room_state")
	
	@staticmethod
	def get_status(room):
		return room.status

	@staticmethod
	def get_player1(room):
		return room.player_1.user.username if room.player_1 else None

	@staticmethod
	def get_player2(room):
		return room.player_2.user.username if room.player_2 else None

	@staticmethod
	def get_board(room):
		return room.board or create_empty_board()

	@staticmethod
	def get_currentPlayer(room):
		return RoomPlayerSerializer(RoomPlayerSerializer.from_room(room, room.current_turn)).data

	@staticmethod
	def get_gameResult(room):
		if room.status != Room.STATUS_FINISHED:
			return None

		if not room.winner_id or not room.winner_symbol:
			return GameResultSerializer(
				{
					"winner": None,
					"isDraw": True,
				}
			).data

		winner_username = None
		if room.winner:
			winner_username = room.winner.user.username
		elif room.winner_symbol == PLAYER_ONE and room.player_1:
			winner_username = room.player_1.user.username
		elif room.winner_symbol == PLAYER_TWO and room.player_2:
			winner_username = room.player_2.user.username

		return GameResultSerializer(
			{
				"winner": RoomPlayerSerializer.from_symbol(room.winner_symbol, winner_username),
				"isDraw": False,
			}
		).data

	def get_message(self, room):
		return self.context.get("message")

	def get_lastMove(self, room):
		last_move = self.context.get("last_move")
		if not last_move:
			return None

		return LastMoveSerializer(last_move).data

	def to_representation(self, room):
		payload = dict(super().to_representation(room))

		if payload.get("message") is None:
			payload.pop("message", None)

		if payload.get("lastMove") is None:
			payload.pop("lastMove", None)

		return payload
