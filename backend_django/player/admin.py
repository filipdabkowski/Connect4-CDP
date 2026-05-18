from django.contrib import admin

from .models import Player


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
	"""Admin configuration for player statistics.

	Input: Player model records in Django admin.
	Returns: list columns, search fields, and related-user query optimization.
	"""

	list_display = (
		"user",
		"games_played",
		"wins",
		"losses",
		"draws",
	)

	search_fields = ("user__username",)

	list_select_related = ("user",)
