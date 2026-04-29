from django.db import models

from player.models import Player

import uuid


class Room(models.Model):
	code = models.CharField(max_length=12, unique=True, default="", blank=True)
	player_1 = models.ForeignKey(Player, on_delete=models.SET_NULL, blank=True, null=True, related_name='rooms_player_1')
	player_2 = models.ForeignKey(Player, on_delete=models.SET_NULL, blank=True, null=True, related_name='rooms_player_2')
	created_at = models.DateTimeField(auto_now_add=True)

	def save(self, *args, **kwargs):
		if not self.code:
			self.code = uuid.uuid4().hex[:8]
		super().save(*args, **kwargs)

	@property
	def status(self):
		return "ready" if self.player_1 and self.player_2 else "waiting"

	def __str__(self):
		return f"Room({self.code})"
