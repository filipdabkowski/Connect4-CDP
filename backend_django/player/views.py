from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import Player
from .serializers import PlayerSerializer


class PlayerView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, username):
		player = get_object_or_404(Player, user__username=username)

		serializer = PlayerSerializer(player)
		return Response(serializer.data)


class PlayerMeView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		player = get_object_or_404(Player, user__username=request.user.username)

		serializer = PlayerSerializer(player)
		return Response(serializer.data)
