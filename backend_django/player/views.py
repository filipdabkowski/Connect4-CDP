from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import Player
from .serializers import PlayerSerializer


class PlayerView(APIView):
	"""Return profile data for a named player.

	Input: authenticated GET request and username path parameter.
	Returns: serialized Player data or 404 when no profile exists.
	"""

	permission_classes = [IsAuthenticated]

	def get(self, request, username):
		"""Handle player profile lookups by username.

		Input: request and username path parameter.
		Returns: DRF Response with PlayerSerializer data.
		"""

		player = get_object_or_404(Player, user__username=username)

		serializer = PlayerSerializer(player)
		return Response(serializer.data)


class PlayerMeView(APIView):
	"""Return profile data for the authenticated player.

	Input: authenticated GET request.
	Returns: serialized Player data for request.user.
	"""

	permission_classes = [IsAuthenticated]

	def get(self, request):
		"""Handle current-player profile lookups.

		Input: authenticated request.
		Returns: DRF Response with PlayerSerializer data.
		"""

		player = get_object_or_404(Player, user__username=request.user.username)

		serializer = PlayerSerializer(player)
		return Response(serializer.data)
