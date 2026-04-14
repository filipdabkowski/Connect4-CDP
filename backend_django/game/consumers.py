from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

from .models import Room

import json


class GameConsumer(AsyncWebsocketConsumer):
	def __init__(self, *args, **kwargs):
		super().__init__(args, kwargs)
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

		# Send current state to newly connected client
		await self.send(text_data=json.dumps({
			"type": "room_state",
		}))

	async def disconnect(self, close_code):
		await self.channel_layer.group_discard(self.room_name, self.channel_name)

	async def receive(self, text_data=None, bytes_data=None):
		data = json.loads(text_data)

	async def broadcast_state(self, event):
		await self.send(text_data=json.dumps({
			"type": "room_state",
			"state": event["state"],
		}))

	@staticmethod
	@sync_to_async
	def get_room(code):
		try:
			return Room.objects.get(code=code)
		except Room.DoesNotExist:
			return None

	@staticmethod
	@sync_to_async
	def save_room(room):
		room.save()
