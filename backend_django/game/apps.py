from django.apps import AppConfig


class GameConfig(AppConfig):
    """Configure the game Django app.

    Input: Django app-loading lifecycle.
    Returns: AppConfig metadata used during project startup.
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'game'
