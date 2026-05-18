from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Player


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_player_profile(sender, instance, created, **kwargs):
	"""Create the matching Player profile for each new user.

	Input: Django post_save signal arguments for the configured auth user model.
	Returns: None after creating a Player when the user is newly created.
	"""

	if created:
		# Registration only creates a User; gameplay code always expects a Player row.
		Player.objects.create(user=instance)
