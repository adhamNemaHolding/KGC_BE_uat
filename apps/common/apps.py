from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"
    label = "common"

    def ready(self) -> None:
        # Import the Spectacular auth extension so it registers at startup.
        import apps.common.spectacular  # noqa: F401
