from django.db import models
from django.conf import settings


class Player(models.Model):
	"""Game profile attached one-to-one to a Django user.

	Input: a user relation plus cumulative game counters.
	Returns: Player instances used for matchmaking and statistics.
	"""

	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="player",
		primary_key=True
	)

	games_played = models.PositiveIntegerField(default=0)
	wins = models.PositiveIntegerField(default=0)
	losses = models.PositiveIntegerField(default=0)
	draws = models.PositiveIntegerField(default=0)

	def __str__(self):
		"""Return a concise admin/debug label for the player.

		Input: no arguments.
		Returns: string containing the related username.
		"""

		return f"Player({self.user.username})"
