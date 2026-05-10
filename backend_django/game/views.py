from django.db import IntegrityError, transaction
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Room
from .minimax_bot import suggest_bot_move
from .serializers import build_error_response, build_room_response
from player.models import Player


def parse_bool(value):
	if isinstance(value, bool):
		return value

	if isinstance(value, str):
		return value.lower() in {"1", "true", "yes", "on"}

	return bool(value)


class CreateRoomView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		body = request.data
		room_code = (body.get("code") or "").strip().upper() or None
		player = get_object_or_404(Player, user__username=request.user.username)

		try:
			with transaction.atomic():
				room = Room.objects.create(code=room_code or "", player_1=player)
		except IntegrityError:
			return Response(
				build_error_response("Room code already exists."),
				status=status.HTTP_400_BAD_REQUEST,
			)

		return Response(
			build_room_response(
				room=room,
				message_type="room_state",
			),
			status=status.HTTP_201_CREATED,
		)


class JoinRoomView(APIView):
	permission_classes = [IsAuthenticated]
	
	def post(self, request, code):
		body = request.data
		room_code = (code or body.get("code") or "").strip().upper()
		player = get_object_or_404(Player, user__username=request.user.username)

		if not room_code:
			return Response(
				build_error_response("Room code is required."),
				status=status.HTTP_400_BAD_REQUEST,
			)

		room = get_object_or_404(Room, code=room_code)

		if room.player_1_id == player.pk or room.player_2_id == player.pk:
			return Response(
				build_room_response(
					room=room,
					message_type="room_joined",
				),
				status=status.HTTP_200_OK,
			)

		if room.player_2 and room.player_2_id != player.pk:
			return Response(
				build_room_response(
					room=room,
					message_type="room_error",
					message="Room is full.",
				),
				status=status.HTTP_400_BAD_REQUEST,
			)

		room.player_2 = player
		room.save(update_fields=["player_2"])

		return Response(
			build_room_response(
				room=room,
				message_type="room_joined",
			),
			status=status.HTTP_200_OK,
		)


class BotMoveSuggestionView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		try:
			suggestion = suggest_bot_move(
				board=request.data.get("board"),
				bot_symbol=request.data.get("botSymbol", 2),
				depth=request.data.get("depth", 4),
				use_multiprocessing=parse_bool(request.data.get("parallel", False)),
				max_workers=request.data.get("maxWorkers"),
			)
		except ValueError as exc:
			return Response(
				{
					"type": "bot_move_error",
					"message": str(exc),
				},
				status=status.HTTP_400_BAD_REQUEST,
			)

		return Response(
			{
				"type": "bot_move_suggestion",
				"column": suggestion.column,
				"score": suggestion.score,
				"validMoves": suggestion.valid_moves,
			},
			status=status.HTTP_200_OK,
		)
