### Use this file to import django into your .py files.
### Do not import main.py directly
import os
from django import setup

# https://stackoverflow.com/a/32590521
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cwageodjango.config.settings")


setup()
