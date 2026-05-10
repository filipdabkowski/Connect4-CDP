from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from game.minimax_bot import create_empty_board, drop_piece, suggest_bot_move
from game.models import Room


class RoomApiTests(APITestCase):
	def setUp(self):
		user_model = get_user_model()
		self.host_user = user_model.objects.create_user(username="host", password="password123")
		self.guest_user = user_model.objects.create_user(username="guest", password="password123")
		self.third_user = user_model.objects.create_user(username="third", password="password123")

	def test_create_room_creates_database_record(self):
		self.client.force_authenticate(user=self.host_user)

		response = self.client.post("/api/game/rooms/create/", {"code": "alpha123"}, format="json")

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(response.data["type"], "room_state")
		self.assertEqual(response.data["room"]["code"], "ALPHA123")
		self.assertTrue(Room.objects.filter(code="ALPHA123", player_1__user=self.host_user).exists())

	def test_join_room_assigns_second_player(self):
		room = Room.objects.create(code="BETA123", player_1=self.host_user.player)
		self.client.force_authenticate(user=self.guest_user)

		response = self.client.post("/api/game/rooms/BETA123/join/", {"code": "BETA123"}, format="json")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		room.refresh_from_db()
		self.assertEqual(response.data["type"], "room_joined")
		self.assertEqual(response.data["room"], "BETA123")
		self.assertEqual(room.player_2, self.guest_user.player)

	def test_join_room_rejects_full_room(self):
		room = Room.objects.create(code="GAMMA123", player_1=self.host_user.player, player_2=self.guest_user.player)
		self.client.force_authenticate(user=self.third_user)

		response = self.client.post(f"/api/game/rooms/{room.code}/join/", {"code": room.code}, format="json")

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(response.data["type"], "room_error")


class MinimaxBotTests(APITestCase):
	def setUp(self):
		user_model = get_user_model()
		self.user = user_model.objects.create_user(username="bot-tester", password="password123")

	def test_suggest_bot_move_picks_winning_column(self):
		board = create_empty_board()
		board = drop_piece(board, 0, 2)
		board = drop_piece(board, 1, 2)
		board = drop_piece(board, 2, 2)

		suggestion = suggest_bot_move(board=board, bot_symbol=2, depth=2)

		self.assertEqual(suggestion.column, 3)

	def test_suggest_bot_move_blocks_opponent_win(self):
		board = create_empty_board()
		board = drop_piece(board, 0, 1)
		board = drop_piece(board, 1, 1)
		board = drop_piece(board, 2, 1)

		suggestion = suggest_bot_move(board=board, bot_symbol=2, depth=2)

		self.assertEqual(suggestion.column, 3)

	def test_suggest_bot_move_can_evaluate_root_moves_in_processes(self):
		board = create_empty_board()
		board = drop_piece(board, 0, 2)
		board = drop_piece(board, 1, 2)
		board = drop_piece(board, 2, 2)

		suggestion = suggest_bot_move(
			board=board,
			bot_symbol=2,
			depth=2,
			use_multiprocessing=True,
			max_workers=2,
		)

		self.assertEqual(suggestion.column, 3)

	def test_bot_move_suggestion_endpoint_returns_column(self):
		board = create_empty_board()
		board = drop_piece(board, 0, 2)
		board = drop_piece(board, 1, 2)
		board = drop_piece(board, 2, 2)
		self.client.force_authenticate(user=self.user)

		response = self.client.post(
			"/api/game/bot/suggest-move/",
			{"board": board, "botSymbol": 2, "depth": 2},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["type"], "bot_move_suggestion")
		self.assertEqual(response.data["column"], 3)

	def test_bot_move_suggestion_endpoint_rejects_invalid_board(self):
		self.client.force_authenticate(user=self.user)

		response = self.client.post(
			"/api/game/bot/suggest-move/",
			{"board": [[0]], "botSymbol": 2},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(response.data["type"], "bot_move_error")
