from django.db import IntegrityError, transaction
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Room
from .game_logic import PLAYER_ONE, PLAYER_TWO, create_empty_board
from .minimax_bot import suggest_bot_move
from .serializers import RoomErrorSerializer, RoomSerializer
from player.models import Player


def parse_bool(value):
	if isinstance(value, bool):
		return value

	if isinstance(value, str):
		return value.lower() in {"1", "true", "yes", "on"}

	return bool(value)


def broadcast_room_state(room, message_type="room_state", message=None):
	channel_layer = get_channel_layer()
	if not channel_layer:
		return

	async_to_sync(channel_layer.group_send)(
		f"room_{room.code}",
		{
			"type": "broadcast_state",
			"message_type": message_type,
			"message": message,
		},
	)


def get_room_with_players(room_id):
	return Room.objects.select_related("player_1__user", "player_2__user", "winner__user").get(pk=room_id)


def remove_player_from_room(room, player_id):
	update_fields = []

	if room.player_1_id == player_id:
		room.player_1 = None
		update_fields.append("player_1")

		if room.is_bot_game and room.game_status != Room.STATUS_FINISHED:
			room.is_bot_game = False
			update_fields.append("is_bot_game")

	if room.player_2_id == player_id:
		room.player_2 = None
		update_fields.append("player_2")

	if not update_fields:
		return False

	if room.sync_status():
		update_fields.append("game_status")

	room.save(update_fields=update_fields)
	return True


def add_player_to_room(room, player):
	if room.is_bot_game:
		return False

	if room.player_1_id == player.pk or room.player_2_id == player.pk:
		return False

	if not room.player_1_id:
		room.player_1 = player
		update_fields = ["player_1"]
		if room.sync_status():
			update_fields.append("game_status")
		room.save(update_fields=update_fields)
		return True

	if not room.player_2_id:
		room.player_2 = player
		update_fields = ["player_2"]
		if room.sync_status():
			update_fields.append("game_status")
		room.save(update_fields=update_fields)
		return True

	return False


def start_bot_game(room, player):
	if room.player_1_id != player.pk:
		raise ValueError("Only the room creator can start a bot game.")

	if room.status == Room.STATUS_FINISHED:
		raise ValueError("This game is already finished.")

	if room.player_2_id:
		raise ValueError("Another player has already joined this room.")

	if room.is_bot_game:
		return False

	room.is_bot_game = True
	room.bot_symbol = PLAYER_TWO
	room.current_turn = PLAYER_ONE
	room.game_status = Room.STATUS_READY
	room.save(update_fields=["is_bot_game", "bot_symbol", "current_turn", "game_status"])
	return True


def reset_room_game(room, player):
	if room.player_1_id != player.pk and room.player_2_id != player.pk:
		raise ValueError("Only players in this room can reset the game.")

	if room.status != Room.STATUS_FINISHED:
		raise ValueError("Only finished games can be reset.")

	room.board = create_empty_board()
	room.current_turn = PLAYER_ONE
	room.winner = None
	room.winner_symbol = None
	room.game_status = Room.STATUS_READY if room.player_1_id and (room.player_2_id or room.is_bot_game) else Room.STATUS_WAITING
	room.save(update_fields=["board", "current_turn", "winner", "winner_symbol", "game_status"])


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
				RoomErrorSerializer(
					{"message": "Room code already exists."}
				).data,
				status=status.HTTP_400_BAD_REQUEST,
			)

		return Response(
			RoomSerializer(room, context={"message_type": "room_state"}).data,
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
				RoomErrorSerializer(
					{"message": "Room code is required."}
				).data,
				status=status.HTTP_400_BAD_REQUEST,
			)

		with transaction.atomic():
			room = get_object_or_404(
				Room.objects.select_for_update(),
				code=room_code,
			)
			room_id = room.pk
			already_in_room = room.player_1_id == player.pk or room.player_2_id == player.pk

			if already_in_room:
				message_type = "room_joined"
				should_broadcast = False
			elif room.status == Room.STATUS_FINISHED:
				message_type = "room_error"
				should_broadcast = False
			elif room.is_bot_game:
				message_type = "room_error"
				should_broadcast = False
			else:
				should_broadcast = add_player_to_room(room, player)
				message_type = "room_joined" if should_broadcast else "room_error"
			response_status = status.HTTP_200_OK if message_type == "room_joined" else status.HTTP_400_BAD_REQUEST
			response_message = None
			if message_type == "room_error":
				if room.status == Room.STATUS_FINISHED:
					response_message = "This game is already finished."
				elif room.is_bot_game:
					response_message = "This room is playing against the bot and cannot be joined."
				else:
					response_message = "Room is full."

		room = get_room_with_players(room_id)

		if should_broadcast:
			broadcast_room_state(room)

		return Response(
			RoomSerializer(
				room,
				context={
					"message_type": message_type,
					"message": response_message,
				},
			).data,
			status=response_status,
		)


class LeaveRoomView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, code):
		room_code = (code or "").strip().upper()
		player = get_object_or_404(Player, user__username=request.user.username)

		with transaction.atomic():
			room = get_object_or_404(
				Room.objects.select_for_update(),
				code=room_code,
			)
			room_id = room.pk
			should_broadcast = remove_player_from_room(room, player.pk)

		room = get_room_with_players(room_id)

		if should_broadcast:
			broadcast_room_state(room)

		return Response(
			RoomSerializer(room, context={"message_type": "room_state"}).data,
			status=status.HTTP_200_OK,
		)


class StartBotGameView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, code):
		room_code = (code or "").strip().upper()
		player = get_object_or_404(Player, user__username=request.user.username)

		try:
			with transaction.atomic():
				room = get_object_or_404(
					Room.objects.select_for_update(),
					code=room_code,
				)
				room_id = room.pk
				should_broadcast = start_bot_game(room, player)
		except ValueError as exc:
			return Response(
				RoomErrorSerializer({"message": str(exc)}).data,
				status=status.HTTP_400_BAD_REQUEST,
			)

		room = get_room_with_players(room_id)

		if should_broadcast:
			broadcast_room_state(room)

		return Response(
			RoomSerializer(
				room,
				context={
					"message_type": "bot_game_started",
					"message": "Bot game started. This room is now closed to other players.",
				},
			).data,
			status=status.HTTP_200_OK,
		)


class ResetRoomGameView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, code):
		room_code = (code or "").strip().upper()
		player = get_object_or_404(Player, user__username=request.user.username)

		try:
			with transaction.atomic():
				room = get_object_or_404(
					Room.objects.select_for_update(),
					code=room_code,
				)
				room_id = room.pk
				reset_room_game(room, player)
		except ValueError as exc:
			return Response(
				RoomErrorSerializer({"message": str(exc)}).data,
				status=status.HTTP_400_BAD_REQUEST,
			)

		room = get_room_with_players(room_id)
		broadcast_room_state(room, message_type="room_reset", message="New round started.")

		return Response(
			RoomSerializer(
				room,
				context={
					"message_type": "room_reset",
					"message": "New round started.",
				},
			).data,
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
