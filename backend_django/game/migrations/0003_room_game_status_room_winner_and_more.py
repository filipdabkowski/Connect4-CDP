from django.db import migrations, models
import django.db.models.deletion


def mark_existing_ready_rooms(apps, schema_editor):
	"""Backfill ready status for rooms that already had two players.

	Input: historical app registry and schema editor provided by Django migrations.
	Returns: None after updating matching historical Room rows.
	"""

	room_model = apps.get_model("game", "Room")
	room_model.objects.filter(
		player_1__isnull=False,
		player_2__isnull=False,
		game_status="waiting",
	).update(game_status="ready")


class Migration(migrations.Migration):

	dependencies = [
		("game", "0002_room_board_room_current_turn"),
		("player", "0002_remove_player_id_alter_player_user"),
	]

	operations = [
		migrations.AddField(
			model_name="room",
			name="game_status",
			field=models.CharField(
				choices=[
					("waiting", "Waiting"),
					("ready", "Ready"),
					("finished", "Finished"),
				],
				default="waiting",
				max_length=16,
			),
		),
		migrations.AddField(
			model_name="room",
			name="winner",
			field=models.ForeignKey(
				blank=True,
				null=True,
				on_delete=django.db.models.deletion.SET_NULL,
				related_name="won_rooms",
				to="player.player",
			),
		),
		migrations.AddField(
			model_name="room",
			name="winner_symbol",
			field=models.PositiveSmallIntegerField(blank=True, null=True),
		),
		migrations.RunPython(mark_existing_ready_rooms, migrations.RunPython.noop),
	]
