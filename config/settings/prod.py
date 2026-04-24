"""
Production settings — used on the Mikrus Frog VPS.
Requires environment variables to be set in .env or the OS environment.
"""

import os

from .base import *  # noqa: F401, F403

DEBUG = False

SECRET_KEY = os.environ['SECRET_KEY']

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Trust the Mikrus reverse proxy headers
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Required in Django 4+ — allow CSRF for our wykr.es subdomain
CSRF_TRUSTED_ORIGINS = ['https://frog02-21044.wykr.es']
