from django.apps import AppConfig
import asyncio

class BotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.Bot"

    def ready(self):
        # Signalni Django yuklanayotganda ishga tushiradigan qism:
        import apps.Bot.signals