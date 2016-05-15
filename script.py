import os, sys

proj_path = "/home/watergunwars/Centennial"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Centennial.settings")
sys.path.append(proj_path)

os.chdir(proj_path)

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

from django.core import management

management.call_command('eliminate_late')