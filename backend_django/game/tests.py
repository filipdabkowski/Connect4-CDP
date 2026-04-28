from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

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
		self.assertEqual(response.data["room"]["status"], "ready")
		self.assertEqual(room.player_2, self.guest_user.player)

	def test_join_room_rejects_full_room(self):
		room = Room.objects.create(code="GAMMA123", player_1=self.host_user.player, player_2=self.guest_user.player)
		self.client.force_authenticate(user=self.third_user)

		response = self.client.post(f"/api/game/rooms/{room.code}/join/", {"code": room.code}, format="json")

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(response.data["type"], "room_error")
