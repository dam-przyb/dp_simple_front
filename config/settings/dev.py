"""
Development settings — used on your local machine.
Never use in production.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

SECRET_KEY = 'django-insecure-local-dev-key-not-used-in-production'

ALLOWED_HOSTS = ['localhost', '127.0.0.1']
