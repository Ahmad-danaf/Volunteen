from django.apps import AppConfig


class TeenappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'teenApp'

    def ready(self):
        import teenApp.signals
