from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
	initial = True

	dependencies = [
		("player", "0002_remove_player_id_alter_player_user"),
	]

	operations = [
		migrations.CreateModel(
			name="Room",
			fields=[
				("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
				("code", models.CharField(blank=True, default="", max_length=12, unique=True)),
				("created_at", models.DateTimeField(auto_now_add=True)),
				("player_1", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="rooms_player_1", to="player.player")),
				("player_2", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="rooms_player_2", to="player.player")),
			],
		),
	]
