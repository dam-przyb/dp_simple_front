"""
Base settings shared across all environments.
"""

from pathlib import Path

# Project root — three levels up from config/settings/base.py
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ------------------------------------------------------------------ #
# Application definition
# ------------------------------------------------------------------ #

INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'viewer',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'viewer.context_processors.remote_user',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ------------------------------------------------------------------ #
# Database — not used, but Django requires this key to exist
# ------------------------------------------------------------------ #

DATABASES = {}

# ------------------------------------------------------------------ #
# Static files
# ------------------------------------------------------------------ #

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ------------------------------------------------------------------ #
# JSON data directory
# ------------------------------------------------------------------ #

DATA_DIR = BASE_DIR / 'data'

# ------------------------------------------------------------------ #
# Internationalisation
# ------------------------------------------------------------------ #

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = False
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
