from django.apps import AppConfig


class PlayerConfig(AppConfig):
	"""Configure the player app and register signal handlers.

	Input: Django app-loading lifecycle.
	Returns: AppConfig metadata used during project startup.
	"""

	default_auto_field = 'django.db.models.BigAutoField'
	name = 'player'

	def ready(self):
		"""Import signal receivers once Django's app registry is ready.

		Input: no arguments.
		Returns: None after registering player signal handlers.
		"""

		import player.signals
