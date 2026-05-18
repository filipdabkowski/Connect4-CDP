from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import transaction
from django.db.models import F
from rest_framework_simplejwt.authentication import JWTAuthentication
from urllib.parse import parse_qs

from .models import Room
from .game_logic import (
	GameMoveError,
	PLAYER_ONE,
	ROOM_STATUS_FINISHED,
	drop_piece,
	get_opponent_symbol,
	get_valid_moves,
	has_winning_line,
	process_room_move,
)
from .minimax_bot import suggest_bot_move
from .serializers import RoomErrorSerializer, RoomPlayerSerializer, RoomSerializer
from player.models import Player

import json


class GameConsumer(AsyncWebsocketConsumer):
	"""Websocket consumer that broadcasts room state and accepts player moves.

	Input: websocket connections scoped to /ws/game/<room_code>/ with a JWT query token.
	Returns: JSON room events and errors over the websocket connection.
	"""

	def __init__(self, *args, **kwargs):
		"""Initialize per-connection room and player fields.

		Input: positional and keyword arguments passed by Channels.
		Returns: None after setting connection state placeholders.
		"""

		super().__init__(*args, **kwargs)
		self.room_code = None
		self.room_name = None
		self.player_id = None

	async def connect(self):
		"""Authenticate the socket and join the room broadcast group.

		Input: connection scope containing room_code and optional token query parameter.
		Returns: None; accepts the socket or closes it when the player is not allowed.
		"""

		self.room_code = self.scope["url_route"]["kwargs"]["room_code"]
		self.room_name = f"room_{self.room_code}"
		self.player_id = await self._get_player_id_from_token(self._get_token())

		if not await self._player_can_connect_to_room(self.room_code, self.player_id):
			await self.close()
			return

		await self.channel_layer.group_add(self.room_name, self.channel_name)
		await self.accept()

		await self.channel_layer.group_send(
			self.room_name,
			{
				"type": "broadcast_state",
				"message_type": "room_state",
			},
		)

	async def disconnect(self, close_code):
		"""Leave the room group when the websocket closes.

		Input: websocket close code from Channels.
		Returns: None after discarding the channel from the room group.
		"""

		if self.room_name:
			await self.channel_layer.group_discard(self.room_name, self.channel_name)

	async def receive(self, text_data=None, bytes_data=None):
		"""Handle inbound websocket messages.

		Input: text JSON payloads from the client; binary payloads are ignored.
		Returns: None after dispatching player moves or room messages.
		"""

		if not text_data:
			return

		try:
			data = json.loads(text_data)
		except json.JSONDecodeError:
			await self.send_error("Could not read that socket message.")
			return

		message_type = data.get("type", "room_message")
		message = data.get("message")

		if message_type == "player_move":
			await self._handle_player_move(data)
			return

		await self.channel_layer.group_send(
			self.room_name,
			{
				"type": "broadcast_state",
				"message_type": message_type,
				"message": message,
			},
		)

	async def broadcast_state(self, event):
		"""Send the latest room state for a group event.

		Input: a Channels event containing message_type and optional message.
		Returns: None after serializing and sending the room event.
		"""

		await self.send_room_event(
			message_type=event["message_type"],
			message=event.get("message"),
		)

	async def broadcast_payload(self, event):
		"""Forward a pre-built payload to this socket.

		Input: a Channels event with a payload key.
		Returns: None after JSON-encoding the payload.
		"""

		await self.send(text_data=json.dumps(event["payload"]))

	async def send_room_event(self, message_type, message=None):
		"""Serialize the current room state and send it to the client.

		Input: event type and optional message text.
		Returns: None; skips sending if the room no longer exists.
		"""

		payload = await self._serialize_room_event(self.room_code, message_type, message)
		if not payload:
			return

		await self.send(text_data=json.dumps(payload))

	async def send_error(self, message):
		"""Send a room_error payload to the client.

		Input: user-facing error message.
		Returns: None after writing the serialized error to the socket.
		"""

		await self.send(text_data=json.dumps(RoomErrorSerializer(
			{"message": message}
		).data))

	async def _handle_player_move(self, data):
		"""Apply a player move and broadcast the resulting payload.

		Input: decoded websocket payload containing a column field.
		Returns: None after sending an error to the caller or broadcasting the room state.
		"""

		payload = await self._apply_player_move(
			self.room_code,
			self.player_id,
			data.get("column"),
		)
		if not payload:
			return

		if payload["type"] == "room_error":
			await self.send(text_data=json.dumps(payload))
			return

		await self.channel_layer.group_send(
			self.room_name,
			{
				"type": "broadcast_payload",
				"payload": payload,
			},
		)

	def _get_token(self):
		"""Read the JWT token from the websocket query string.

		Input: no arguments; reads the Channels connection scope.
		Returns: token string or None when absent.
		"""

		query_string = self.scope.get("query_string", b"").decode()
		values = parse_qs(query_string).get("token", [])
		return values[0] if values else None

	@staticmethod
	@database_sync_to_async
	def _get_player_id_from_token(token):
		"""Validate a JWT and resolve the associated Player id.

		Input: access token string or None.
		Returns: player primary key, or None when validation fails.
		"""

		if not token:
			return None

		try:
			authenticator = JWTAuthentication()
			validated_token = authenticator.get_validated_token(token)
			user = authenticator.get_user(validated_token)
			return user.player.pk
		except Exception:
			return None

	@staticmethod
	@database_sync_to_async
	def _player_can_connect_to_room(code, player_id):
		"""Check whether a player belongs to the requested room.

		Input: room code and player id.
		Returns: True when the player occupies player_1 or player_2 in the room.
		"""

		if not player_id:
			return False

		return Room.objects.filter(code=code).filter(
			player_1_id=player_id
		).exists() or Room.objects.filter(code=code).filter(
			player_2_id=player_id
		).exists()

	@staticmethod
	@database_sync_to_async
	def _serialize_room_event(code, message_type, message=None):
		"""Load and serialize the room for a websocket event.

		Input: room code, event type, and optional message.
		Returns: RoomSerializer data or None when the room no longer exists.
		"""

		try:
			room = Room.objects.select_related("player_1__user", "player_2__user", "winner__user").get(code=code)
		except Room.DoesNotExist:
			return None

		return RoomSerializer(
			room,
			context={
				"message_type": message_type,
				"message": message,
			},
		).data

	@staticmethod
	@database_sync_to_async
	def _apply_player_move(code, player_id, column):
		"""Apply a human move and optional immediate bot response atomically.

		Input: room code, moving player id, and zero-based column.
		Returns: serialized room state or room error data.
		"""

		try:
			with transaction.atomic():
				room = Room.objects.select_for_update().select_related().get(code=code)

				# The lock keeps simultaneous socket messages from interleaving turn changes.
				status_changed = room.sync_status()
				try:
					move_result = process_room_move(room, player_id, column)
				except GameMoveError as exc:
					return RoomErrorSerializer(
						{"message": str(exc)}
					).data

				room.board = move_result.board
				last_move = {
					"player": RoomPlayerSerializer.from_room(room, move_result.player_symbol),
					"column": move_result.column,
				}
				message_type = move_result.message_type
				message = move_result.message
				update_fields = ["board", "current_turn"]
				if status_changed:
					update_fields.append("game_status")

				if move_result.winner_symbol:
					finish_room_with_winner(room, move_result.winner_symbol, update_fields)
					message = f"{last_move['player']['username'] or 'Player'} wins."
				elif move_result.is_draw:
					finish_room_as_draw(room, update_fields)
				else:
					room.current_turn = move_result.next_turn

					if room.is_bot_game and room.current_turn == room.bot_symbol:
						# Bot games respond in the same transaction so clients see one consistent turn result.
						try:
							bot_suggestion = suggest_bot_move(
								board=room.board,
								bot_symbol=room.bot_symbol,
								depth=6,
								use_multiprocessing=True,
								max_workers=4,
							)
						except ValueError as exc:
							return RoomErrorSerializer(
								{"message": str(exc)}
							).data

						room.board = drop_piece(room.board, bot_suggestion.column, room.bot_symbol)
						last_move = {
							"player": RoomPlayerSerializer.from_room(room, room.bot_symbol),
							"column": bot_suggestion.column,
						}
						message_type = "player_move"
						message = f"Bot played column {bot_suggestion.column + 1}."

						if has_winning_line(room.board, room.bot_symbol):
							finish_room_with_winner(room, room.bot_symbol, update_fields)
							message_type = "game_over"
							message = f"{last_move['player']['username'] or 'Bot'} wins."
						elif not get_valid_moves(room.board):
							finish_room_as_draw(room, update_fields)
							message_type = "game_over"
							message = "Game ended in a draw."
						else:
							room.current_turn = get_opponent_symbol(room.bot_symbol)

				room.save(update_fields=update_fields)
		except Room.DoesNotExist:
			return RoomErrorSerializer(
				{"message": "Room does not exist."}
			).data

		return RoomSerializer(
			room,
			context={
				"message_type": message_type,
				"message": message,
				"last_move": last_move,
			},
		).data


def finish_room_with_winner(room, winner_symbol, update_fields):
	"""Mark a room as finished with a winner and update player records.

	Input: a Room instance, winning symbol, and mutable update_fields list.
	Returns: None after mutating room fields and extending update_fields.
	"""

	room.game_status = ROOM_STATUS_FINISHED
	room.winner = room.player_1 if winner_symbol == PLAYER_ONE else room.player_2
	room.winner_symbol = winner_symbol
	update_player_records(room, winner_symbol)
	include_update_fields(update_fields, "game_status", "winner", "winner_symbol")


def finish_room_as_draw(room, update_fields):
	"""Mark a room as finished without a winner and update draw records.

	Input: a Room instance and mutable update_fields list.
	Returns: None after mutating room fields and extending update_fields.
	"""

	room.game_status = ROOM_STATUS_FINISHED
	room.winner = None
	room.winner_symbol = None
	update_draw_records(room)
	include_update_fields(update_fields, "game_status", "winner", "winner_symbol")


def include_update_fields(update_fields, *fields):
	"""Append field names while preserving uniqueness.

	Input: mutable update_fields list and any number of field names.
	Returns: None after adding missing field names.
	"""

	for field in fields:
		if field not in update_fields:
			update_fields.append(field)


def update_player_records(room, winner_symbol):
	"""Increment win/loss counters for a completed room.

	Input: a Room instance and winning symbol.
	Returns: None after issuing database updates for winner and loser.
	"""

	winner_id = room.player_1_id if winner_symbol == PLAYER_ONE else room.player_2_id
	loser_id = room.player_2_id if winner_symbol == PLAYER_ONE else room.player_1_id

	Player.objects.filter(pk=winner_id).update(
		games_played=F("games_played") + 1,
		wins=F("wins") + 1,
	)
	Player.objects.filter(pk=loser_id).update(
		games_played=F("games_played") + 1,
		losses=F("losses") + 1,
	)


def update_draw_records(room):
	"""Increment draw counters for both room participants.

	Input: a Room instance with player_1_id and player_2_id.
	Returns: None after issuing a bulk database update.
	"""

	Player.objects.filter(pk__in=[room.player_1_id, room.player_2_id]).update(
		games_played=F("games_played") + 1,
		draws=F("draws") + 1,
	)
