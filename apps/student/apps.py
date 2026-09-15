from django.apps import AppConfig


class StudentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.student'
    verbose_name = 'Student'

    def ready(self):
        # Warm up InsightFace model at startup so first attendance isn't slow
        try:
            from .face_utils import _get_face_app
            _get_face_app()
        except Exception:
            pass
