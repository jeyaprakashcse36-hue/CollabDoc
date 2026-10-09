from django.apps import AppConfig


class CollabdocConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "collabdoc"

    def ready(self):
        import collabdoc.signals