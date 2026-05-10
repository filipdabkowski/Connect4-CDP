from django.db import migrations, models
import game.minimax_bot


class Migration(migrations.Migration):

	dependencies = [
		("game", "0001_initial"),
	]

	operations = [
		migrations.AddField(
			model_name="room",
			name="board",
			field=models.JSONField(default=game.minimax_bot.create_empty_board),
		),
		migrations.AddField(
			model_name="room",
			name="current_turn",
			field=models.PositiveSmallIntegerField(default=1),
		),
	]
