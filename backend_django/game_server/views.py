from rest_framework import generics, permissions
from .serializers import RegisterSerializer


class RegisterView(generics.CreateAPIView):
	"""Create users through the public registration endpoint.

	Input: anonymous POST request with username and password.
	Returns: serializer response for the created user or validation errors.
	"""

	serializer_class = RegisterSerializer
	permission_classes = [permissions.AllowAny]
