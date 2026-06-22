from django.apps import AppConfig


class CoordinatorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.coordinator'
    verbose_name = 'Coordinator'

    def ready(self):
        import apps.coordinator.signals
