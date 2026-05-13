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
	process_room_move,
)
from .serializers import RoomErrorSerializer, RoomPlayerSerializer, RoomSerializer
from player.models import Player

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
		if self.room_name:
			await self.channel_layer.group_discard(self.room_name, self.channel_name)

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
		await self.send_room_event(
			message_type=event["message_type"],
			message=event.get("message"),
		)

	async def broadcast_payload(self, event):
		await self.send(text_data=json.dumps(event["payload"]))

	async def send_room_event(self, message_type, message=None):
		payload = await self._serialize_room_event(self.room_code, message_type, message)
		if not payload:
			return

		await self.send(text_data=json.dumps(payload))

	async def send_error(self, message):
		await self.send(text_data=json.dumps(RoomErrorSerializer(
			{"message": message}
		).data))

	async def _handle_player_move(self, data):
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
		query_string = self.scope.get("query_string", b"").decode()
		values = parse_qs(query_string).get("token", [])
		return values[0] if values else None

	@staticmethod
	@database_sync_to_async
	def _get_player_id_from_token(token):
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
		try:
			with transaction.atomic():
				room = Room.objects.select_for_update().select_related().get(code=code)

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
					room.game_status = ROOM_STATUS_FINISHED
					room.winner = room.player_1 if move_result.winner_symbol == PLAYER_ONE else room.player_2
					room.winner_symbol = move_result.winner_symbol
					message = f"{last_move['player']['username'] or 'Player'} wins."
					update_player_records(room, move_result.winner_symbol)
					for field in ["game_status", "winner", "winner_symbol"]:
						if field not in update_fields:
							update_fields.append(field)
				elif move_result.is_draw:
					room.game_status = ROOM_STATUS_FINISHED
					room.winner = None
					room.winner_symbol = None
					update_draw_records(room)
					for field in ["game_status", "winner", "winner_symbol"]:
						if field not in update_fields:
							update_fields.append(field)
				else:
					room.current_turn = move_result.next_turn

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


def update_player_records(room, winner_symbol):
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
	Player.objects.filter(pk__in=[room.player_1_id, room.player_2_id]).update(
		games_played=F("games_played") + 1,
		draws=F("draws") + 1,
	)
