from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from .models import Room
from .serializers import build_room_event

import json


class GameConsumer(AsyncWebsocketConsumer):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.room_code = None
		self.room_name = None

	async def connect(self):
		self.room_code = self.scope["url_route"]["kwargs"]["room_code"]
		self.room_name = f"room_{self.room_code}"

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

	async def receive(self, text_data=None, bytes_data=None):
		if not text_data:
			return

		data = json.loads(text_data)
		message_type = data.get("type", "room_message")
		message = data.get("message")

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

	async def send_room_event(self, message_type, message=None):
		payload = await self.build_room_event(self.room_code, message_type, message)
		if not payload:
			return

		await self.send(text_data=json.dumps(payload))

	@staticmethod
	@database_sync_to_async
	def room_exists(code):
		return Room.objects.filter(code=code).exists()

	@staticmethod
	@database_sync_to_async
	def build_room_event(code, message_type, message=None):
		try:
			room = Room.objects.only("code", "player_1_id", "player_2_id").get(code=code)
		except Room.DoesNotExist:
			return None

		return build_room_event(
			room=room,
			message_type=message_type,
			message=message,
		)
