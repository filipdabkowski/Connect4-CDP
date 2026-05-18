from rest_framework import serializers

from .models import Room
from .game_logic import PLAYER_ONE, PLAYER_TWO, BOT_USERNAME, create_empty_board


class RoomPlayerSerializer(serializers.Serializer):
	"""Serialize one room participant in the frontend's player shape.

	Input: symbol, slot, and username values.
	Returns: validated serializer data for player references in room payloads.
	"""

	symbol = serializers.IntegerField(min_value=PLAYER_ONE, max_value=PLAYER_TWO)
	slot = serializers.CharField()
	username = serializers.CharField(allow_null=True)

	@staticmethod
	def from_room(room: Room, symbol: int):
		"""Build player metadata from a room slot.

		Input: a Room instance and the requested PLAYER_ONE or PLAYER_TWO symbol.
		Returns: a dict containing symbol, frontend slot name, and display username.
		"""

		if symbol == PLAYER_ONE:
			player = room.player_1
			slot = "player1"
		else:
			player = room.player_2
			slot = "player2"

		return {
			"symbol": PLAYER_TWO if symbol == PLAYER_TWO else PLAYER_ONE,
			"slot": slot,
			"username": BOT_USERNAME if symbol == room.bot_symbol and room.is_bot_game else
			player.user.username if player else None,
		}

	@staticmethod
	def from_symbol(symbol: int, username: str | None):
		"""Build player metadata when only a symbol and username are known.

		Input: a player symbol and optional username.
		Returns: a dict matching the RoomPlayerSerializer contract.
		"""

		return {
			"symbol": PLAYER_TWO if symbol == PLAYER_TWO else PLAYER_ONE,
			"slot": "player2" if symbol == PLAYER_TWO else "player1",
			"username": username,
		}


class GameResultSerializer(serializers.Serializer):
	"""Serialize the final game outcome.

	Input: a nullable winner payload and draw flag.
	Returns: serializer data used when room status is finished.
	"""

	winner = RoomPlayerSerializer(allow_null=True)
	isDraw = serializers.BooleanField()


class LastMoveSerializer(serializers.Serializer):
	"""Serialize the most recent move for UI feedback.

	Input: player metadata and the zero-based column that was played.
	Returns: serializer data for transient websocket/API messages.
	"""

	player = RoomPlayerSerializer()
	column = serializers.IntegerField(min_value=0)


class RoomErrorSerializer(serializers.Serializer):
	"""Serialize room-level errors in the same envelope as socket events.

	Input: a user-facing error message.
	Returns: data with type='room_error' and the message.
	"""

	type = serializers.SerializerMethodField()
	message = serializers.CharField()

	def get_type(self, payload):
		"""Return the fixed error event type.

		Input: the serializer payload.
		Returns: the literal room_error event type.
		"""

		return "room_error"


class RoomSerializer(serializers.ModelSerializer):
	"""Serialize a Room into the event contract consumed by React.

	Input: a Room model plus optional context keys for event type, message, and last move.
	Returns: room state data using camelCase keys expected by the frontend.
	"""

	type = serializers.SerializerMethodField()
	roomCode = serializers.CharField(source="code", read_only=True)
	status = serializers.SerializerMethodField()
	player1 = serializers.SerializerMethodField()
	player2 = serializers.SerializerMethodField()
	board = serializers.SerializerMethodField()
	currentPlayer = serializers.SerializerMethodField()
	isBotGame = serializers.SerializerMethodField()
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
			"isBotGame",
			"gameResult",
			"message",
			"lastMove",
		)

	def get_type(self, room):
		"""Return the websocket/API event type for this payload.

		Input: the serialized Room instance.
		Returns: context message_type or the default room_state.
		"""

		return self.context.get("message_type", "room_state")

	@staticmethod
	def get_status(room):
		"""Return the derived gameplay status.

		Input: a Room instance.
		Returns: waiting, ready, or finished.
		"""

		return room.status

	@staticmethod
	def get_player1(room):
		"""Return player 1's display username.

		Input: a Room instance.
		Returns: username or None when the slot is empty.
		"""

		return room.player_1.user.username if room.player_1 else None

	@staticmethod
	def get_player2(room):
		"""Return player 2's display username.

		Input: a Room instance.
		Returns: the bot display name, human username, or None when empty.
		"""

		if room.is_bot_game and room.bot_symbol == PLAYER_TWO:
			return BOT_USERNAME
		return room.player_2.user.username if room.player_2 else None

	@staticmethod
	def get_board(room):
		"""Return the room board or a safe empty default.

		Input: a Room instance.
		Returns: a 6x7 board matching the frontend BoardState type.
		"""

		return room.board or create_empty_board()

	@staticmethod
	def get_currentPlayer(room):
		"""Return metadata for the player whose turn it is.

		Input: a Room instance.
		Returns: serialized RoomPlayer data for room.current_turn.
		"""

		return RoomPlayerSerializer(RoomPlayerSerializer.from_room(room, room.current_turn)).data

	@staticmethod
	def get_isBotGame(room):
		"""Return whether this room is controlled by the bot opponent.

		Input: a Room instance.
		Returns: True for bot games, otherwise False.
		"""

		return room.is_bot_game

	@staticmethod
	def get_gameResult(room):
		"""Return final winner/draw data for finished rooms.

		Input: a Room instance.
		Returns: None for active rooms, otherwise serialized GameResult data.
		"""

		if room.status != Room.STATUS_FINISHED:
			return None

		if not room.winner_symbol:
			return GameResultSerializer(
				{
					"winner": None,
					"isDraw": True,
				}
			).data

		winner_username = None
		# Prefer the stored winner relation, but fall back to symbols for bot or reset edge cases.
		if room.winner:
			winner_username = room.winner.user.username
		elif room.is_bot_game and room.winner_symbol == room.bot_symbol:
			winner_username = BOT_USERNAME
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
		"""Return optional event text from serializer context.

		Input: a Room instance.
		Returns: message text or None.
		"""

		return self.context.get("message")

	def get_lastMove(self, room):
		"""Return optional last-move payload from serializer context.

		Input: a Room instance.
		Returns: serialized last move data or None.
		"""

		last_move = self.context.get("last_move")
		if not last_move:
			return None

		return LastMoveSerializer(last_move).data

	def to_representation(self, room):
		"""Remove absent transient fields from the final payload.

		Input: a Room instance.
		Returns: a dict without null message or lastMove keys.
		"""

		payload = dict(super().to_representation(room))

		if payload.get("message") is None:
			payload.pop("message", None)

		if payload.get("lastMove") is None:
			payload.pop("lastMove", None)

		return payload
