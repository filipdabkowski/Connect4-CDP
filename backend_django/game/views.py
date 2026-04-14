from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Room
from player.models import Player

import json


class CreateRoomView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		body = json.loads(request.body or "{}")
		room_code = body.get("code", None)
		player = get_object_or_404(Player, user__username=request.user.username)
	
		room = Room.objects.create(code=room_code, player_1=player)
	
		return Response({
			"roomCode": room.code,
			"symbol": "O",
		})


class JoinRoomView(APIView):
	permission_classes = [IsAuthenticated]
	
	def post(self, request):
		body = json.loads(request.body or "{}")
		username = body.get("username", "Player")
