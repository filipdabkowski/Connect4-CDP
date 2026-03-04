from django.contrib.auth.models import User
from rest_framework import serializers


class RegisterSerializer(serializers.ModelSerializer):
	password = serializers.CharField(write_only=True, min_length=8)

	class Meta:
		model = User
		fields = ("username", "password")

	def validate_username(self, value):
		if User.objects.filter(username=value).exists():
			raise serializers.ValidationError("Username already taken.")
		return value

	def create(self, validated_data):
		return User.objects.create_user(
			username=validated_data["username"],
			password=validated_data["password"],
		)
