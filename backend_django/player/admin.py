from django.contrib import admin

from .models import Player


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
	list_display = (
		"user",
		"games_played",
		"wins",
		"losses",
		"draws",
	)

	search_fields = ("user__username",)

	list_select_related = ("user",)
