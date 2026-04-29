from django.db import IntegrityError, transaction
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Room
from .serializers import build_room_response
from player.models import Player

import json


class CreateRoomView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		body = json.loads(request.body or "{}")
		room_code = (body.get("code") or "").strip().upper() or None
		player = get_object_or_404(Player, user__username=request.user.username)

		try:
			with transaction.atomic():
				room = Room.objects.create(code=room_code or "", player_1=player)
		except IntegrityError:
			return Response(
				{
					"type": "room_error",
					"room": None,
					"message": {
						"kind": "system",
						"actor": request.user.username,
						"text": "A room with that code already exists.",
					},
				},
				status=status.HTTP_400_BAD_REQUEST,
			)

		return Response(
			build_room_response(
				room=room,
				message_type="room_state",
				text="Room created. Waiting for another player to join.",
				actor=request.user.username,
			),
			status=status.HTTP_201_CREATED,
		)


class JoinRoomView(APIView):
	permission_classes = [IsAuthenticated]
	
	def post(self, request, code):
		body = json.loads(request.body or "{}")
		room_code = (code or body.get("code") or "").strip().upper()
		player = get_object_or_404(Player, user__username=request.user.username)

		if not room_code:
			return Response(
				{
					"type": "room_error",
					"room": None,
					"message": {
						"kind": "system",
						"actor": request.user.username,
						"text": "Room code is required.",
					},
				},
				status=status.HTTP_400_BAD_REQUEST,
			)

		room = get_object_or_404(Room, code=room_code)

		if room.player_1_id == player.pk or room.player_2_id == player.pk:
			return Response(
				build_room_response(
					room=room,
					message_type="room_joined",
					text="Player already belongs to this room.",
					actor=request.user.username,
				),
				status=status.HTTP_200_OK,
			)

		if room.player_2 and room.player_2_id != player.pk:
			return Response(
				build_room_response(
					room=room,
					message_type="room_error",
					text="This room is already full.",
					actor=request.user.username,
				),
				status=status.HTTP_400_BAD_REQUEST,
			)

		room.player_2 = player
		room.save(update_fields=["player_2"])

		return Response(
			build_room_response(
				room=room,
				message_type="room_joined",
				text="Player joined the room.",
				actor=request.user.username,
			),
			status=status.HTTP_200_OK,
		)
