from rest_framework import serializers
from .models import Player


class PlayerSerializer(serializers.ModelSerializer):
	username = serializers.CharField(source="user.username", read_only=True)
	games_played = serializers.IntegerField(min_value=0)

	class Meta:
		model = Player
		fields = ("username", "games_played")
