from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import transaction
from rest_framework_simplejwt.authentication import JWTAuthentication
from urllib.parse import parse_qs

from .models import Room
from .minimax_bot import (
	COLUMNS,
	PLAYER_ONE,
	PLAYER_TWO,
	drop_piece,
	get_opponent_symbol,
	is_terminal_node,
	normalize_board,
)
from .serializers import build_error_response, build_player_payload, build_room_event

import json


class GameConsumer(AsyncWebsocketConsumer):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.room_code = None
		self.room_name = None
		self.player_id = None

	async def connect(self):
		self.room_code = self.scope["url_route"]["kwargs"]["room_code"]
		self.room_name = f"room_{self.room_code}"
		self.player_id = await self.get_player_id_from_token(self.get_token())

		if not await self.room_exists(self.room_code):
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
		if self.room_name:
			await self.channel_layer.group_discard(self.room_name, self.channel_name)

		if self.room_name and self.player_id:
			payload = await self.remove_player_from_room(self.room_code, self.player_id)
			if payload:
				await self.channel_layer.group_send(
					self.room_name,
					{
						"type": "broadcast_payload",
						"payload": payload,
					},
				)

	async def receive(self, text_data=None, bytes_data=None):
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
			await self.handle_player_move(data)
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
		await self.send_room_event(
			message_type=event["message_type"],
			message=event.get("message"),
		)

	async def broadcast_payload(self, event):
		await self.send(text_data=json.dumps(event["payload"]))

	async def send_room_event(self, message_type, message=None):
		payload = await self.build_room_event(self.room_code, message_type, message)
		if not payload:
			return

		await self.send(text_data=json.dumps(payload))

	async def send_error(self, message):
		await self.send(text_data=json.dumps(build_error_response(message)))

	async def handle_player_move(self, data):
		payload = await self.apply_player_move(
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

	def get_token(self):
		query_string = self.scope.get("query_string", b"").decode()
		values = parse_qs(query_string).get("token", [])
		return values[0] if values else None

	@staticmethod
	@database_sync_to_async
	def get_player_id_from_token(token):
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
	def room_exists(code):
		return Room.objects.filter(code=code).exists()

	@staticmethod
	@database_sync_to_async
	def build_room_event(code, message_type, message=None):
		try:
			room = Room.objects.select_related("player_1__user", "player_2__user").get(code=code)
		except Room.DoesNotExist:
			return None

		return build_room_event(
			room=room,
			message_type=message_type,
			message=message,
		)

	@staticmethod
	@database_sync_to_async
	def apply_player_move(code, player_id, column):
		if not player_id:
			return build_error_response("You must be signed in to make a move.")

		try:
			column = int(column)
		except (TypeError, ValueError):
			return build_error_response("Select a valid column.")

		if column not in range(COLUMNS):
			return build_error_response("Selected column is outside the board.")

		try:
			with transaction.atomic():
				room = Room.objects.select_for_update().select_related().get(code=code)

				if not room.player_1_id or not room.player_2_id:
					return build_error_response("Wait for another player before making a move.")

				if room.player_1_id == player_id:
					player_symbol = PLAYER_ONE
				elif room.player_2_id == player_id:
					player_symbol = PLAYER_TWO
				else:
					return build_error_response("You are not a player in this room.")

				if room.current_turn != player_symbol:
					return build_error_response("It is not your turn.")

				board = normalize_board(room.board)
				if is_terminal_node(board):
					return build_error_response("This game is already finished.")

				try:
					room.board = drop_piece(board, column, player_symbol)
				except ValueError as exc:
					return build_error_response(str(exc))

				last_move = {
					"player": build_player_payload(room, player_symbol),
					"column": column,
				}
				room.current_turn = get_opponent_symbol(player_symbol)
				room.save(update_fields=["board", "current_turn"])
		except Room.DoesNotExist:
			return build_error_response("Room does not exist.")

		return build_room_event(
			room=room,
			message_type="player_move",
			last_move=last_move,
		)

	@staticmethod
	@database_sync_to_async
	def remove_player_from_room(code, player_id):
		try:
			room = Room.objects.select_related("player_1__user", "player_2__user").get(code=code)
		except Room.DoesNotExist:
			return None

		update_fields = []
		if room.player_1_id == player_id:
			room.player_1 = None
			update_fields.append("player_1")

		if room.player_2_id == player_id:
			room.player_2 = None
			update_fields.append("player_2")

		if not update_fields:
			return None

		room.save(update_fields=update_fields)
		return build_room_event(room=room, message_type="room_state")
