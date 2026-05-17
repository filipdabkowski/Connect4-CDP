from django.db import migrations, models

from game.game_logic import PLAYER_TWO


class Migration(migrations.Migration):

	dependencies = [
		("game", "0003_room_game_status_room_winner_and_more"),
	]

	operations = [
		migrations.AddField(
			model_name="room",
			name="is_bot_game",
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name="room",
			name="bot_symbol",
			field=models.PositiveSmallIntegerField(default=PLAYER_TWO),
		),
	]
