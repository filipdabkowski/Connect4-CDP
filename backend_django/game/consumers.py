from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

from .models import Room
from .serializers import build_room_event

import json


class GameConsumer(AsyncWebsocketConsumer):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.room = None
		self.room_code = None
		self.room_name = None

	async def connect(self):
		self.room_code = self.scope["url_route"]["kwargs"]["room_code"]
		self.room_name = f"room_{self.room_code}"

		self.room = await self.get_room(self.room_code)
		if not self.room:
			await self.close()
			return

		await self.channel_layer.group_add(self.room_name, self.channel_name)
		await self.accept()

		await self.send_room_event(
			message_type="room_state",
			text="Socket connected to room.",
			actor="system",
		)

		await self.channel_layer.group_send(
			self.room_name,
			{
				"type": "broadcast_state",
				"message_type": "room_message",
				"text": "A player connected to the room.",
				"actor": "system",
			},
		)

	async def disconnect(self, close_code):
		if self.room_name:
			await self.channel_layer.group_discard(self.room_name, self.channel_name)

	async def receive(self, text_data=None, bytes_data=None):
		if not text_data:
			return

		data = json.loads(text_data)
		text = data.get("message", "Example room message.")

		await self.channel_layer.group_send(
			self.room_name,
			{
				"type": "broadcast_state",
				"message_type": "room_message",
				"text": text,
				"actor": data.get("actor", "player"),
			},
		)

	async def broadcast_state(self, event):
		await self.send_room_event(
			message_type=event["message_type"],
			text=event["text"],
			actor=event["actor"],
		)

	async def send_room_event(self, message_type, text, actor):
		room = await self.get_room(self.room_code)
		if not room:
			return

		await self.send(text_data=json.dumps(
			build_room_event(
				room=room,
				message_type=message_type,
				text=text,
				actor=actor,
			)
		))

	@staticmethod
	@sync_to_async
	def get_room(code):
		try:
			return Room.objects.get(code=code)
		except Room.DoesNotExist:
			return None
