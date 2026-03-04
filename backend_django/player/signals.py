from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Player


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_player_profile(sender, instance, created, **kwargs):
	if created:
		Player.objects.create(user=instance)
