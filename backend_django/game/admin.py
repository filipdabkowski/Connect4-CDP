from django.contrib import admin
from .models import Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
	"""Admin configuration for inspecting rooms and participants.

	Input: Room model records in Django admin.
	Returns: searchable room list columns and read-only creation timestamps.
	"""

	list_display = ("code", "player_1", "player_2", "created_at", "status")
	search_fields = ("code", "player_1__user__username", "player_2__user__username")
	readonly_fields = ("created_at",)
