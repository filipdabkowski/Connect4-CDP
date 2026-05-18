from django.contrib.auth.models import User
from rest_framework import serializers


class RegisterSerializer(serializers.ModelSerializer):
	"""Validate and create Django users for registration.

	Input: username and password fields from the registration endpoint.
	Returns: a new User instance with a hashed password.
	"""

	password = serializers.CharField(write_only=True, min_length=8)

	class Meta:
		model = User
		fields = ("username", "password")

	def validate_username(self, value):
		"""Ensure usernames stay unique before creating a user.

		Input: proposed username string.
		Returns: the username when available.
		Raises: serializers.ValidationError when the username is already taken.
		"""

		if User.objects.filter(username=value).exists():
			raise serializers.ValidationError("Username already taken.")
		return value

	def create(self, validated_data):
		"""Create a user with Django's password hashing.

		Input: validated username and password data.
		Returns: the created User instance.
		"""

		return User.objects.create_user(
			username=validated_data["username"],
			password=validated_data["password"],
		)
