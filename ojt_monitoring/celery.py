import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ojt_monitoring.settings')

app = Celery('ojt_monitoring')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(['apps.core'])
