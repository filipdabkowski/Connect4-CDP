from django.db import models

from .game_logic import (
	PLAYER_ONE,
	PLAYER_TWO,
	ROOM_STATUS_CHOICES,
	ROOM_STATUS_FINISHED,
	ROOM_STATUS_READY,
	ROOM_STATUS_WAITING,
	create_empty_board,
)
from player.models import Player

import uuid


class Room(models.Model):
	STATUS_WAITING = ROOM_STATUS_WAITING
	STATUS_READY = ROOM_STATUS_READY
	STATUS_FINISHED = ROOM_STATUS_FINISHED
	STATUS_CHOICES = ROOM_STATUS_CHOICES

	code = models.CharField(max_length=12, unique=True, default="", blank=True)
	player_1 = models.ForeignKey(Player, on_delete=models.SET_NULL, blank=True, null=True, related_name='rooms_player_1')
	player_2 = models.ForeignKey(Player, on_delete=models.SET_NULL, blank=True, null=True, related_name='rooms_player_2')
	board = models.JSONField(default=create_empty_board)
	current_turn = models.PositiveSmallIntegerField(default=PLAYER_ONE)
	is_bot_game = models.BooleanField(default=False)
	bot_symbol = models.PositiveSmallIntegerField(default=PLAYER_TWO)
	game_status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_WAITING)
	winner = models.ForeignKey(Player, on_delete=models.SET_NULL, blank=True, null=True, related_name="won_rooms")
	winner_symbol = models.PositiveSmallIntegerField(blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def save(self, *args, **kwargs):
		if not self.code:
			self.code = uuid.uuid4().hex[:8]
		super().save(*args, **kwargs)

	@property
	def status(self):
		if self.game_status == self.STATUS_FINISHED:
			return self.STATUS_FINISHED

		has_opponent = self.player_2_id or self.is_bot_game
		return self.STATUS_READY if self.player_1_id and has_opponent else self.STATUS_WAITING

	def sync_status(self):
		if self.game_status == self.STATUS_FINISHED:
			return False

		has_opponent = self.player_2_id or self.is_bot_game
		next_status = self.STATUS_READY if self.player_1_id and has_opponent else self.STATUS_WAITING
		if self.game_status == next_status:
			return False

		self.game_status = next_status
		return True

	def __str__(self):
		return f"Room({self.code})"
