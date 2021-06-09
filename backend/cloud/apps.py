from django.apps import AppConfig


class CloudConfig(AppConfig):
    name = "cloud"

    def ready(self):
        """
        docstring
        """
        from cloud import signals
