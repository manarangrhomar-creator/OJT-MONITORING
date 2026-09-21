import os
import sys

# Add the project directory to the Python path
# Adjust 'ojt_monitoring' if your project folder has a different name
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ojt_monitoring.settings')

# Activate the virtual environment if needed
# Uncomment and adjust the path if your cPanel uses a virtualenv
# virtualenv_path = os.path.join(PROJECT_DIR, 'venv', 'Lib', 'site-packages')
# sys.path.insert(0, virtualenv_path)
//uhuhuhuhuh

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
