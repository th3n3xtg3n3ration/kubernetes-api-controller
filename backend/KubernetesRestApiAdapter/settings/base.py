# https://docs.djangoproject.com/en/1.10/ref/settings/

import os

BASE_DIR = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))


SETTINGS_PATH = os.path.dirname(os.path.dirname(__file__))
from decouple import config  # noqa


def base_dir_join(*args):
    return os.path.join(BASE_DIR, *args)


SITE_ID = 1

DEBUG = True

SECURE_HSTS_PRELOAD = not DEBUG

ADMINS = (("Admin", "foo@example.com"),)

AUTH_USER_MODEL = "users.User"

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_js_reverse",
    "webpack_loader",
    'rest_framework',
    "import_export",
    'django_celery_beat',
    'corsheaders',
    "api",
    "cloud",
    "common",
    "users",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    'corsheaders.middleware.CorsMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "cloud.middlewares.TimezoneMiddleware",
]

ROOT_URLCONF = "KubernetesRestApiAdapter.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(SETTINGS_PATH, 'templates')],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            
        },
    },
]

WSGI_APPLICATION = "KubernetesRestApiAdapter.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator", },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator", },
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator", },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Europe/Istanbul"

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATICFILES_DIRS = (base_dir_join("../frontend"),)

# Webpack
WEBPACK_LOADER = {
    "DEFAULT": {
        "CACHE": False,  # on DEBUG should be False
        "STATS_FILE": base_dir_join("../webpack-stats.json"),
        "POLL_INTERVAL": 0.1,
        "IGNORE": [".+\.hot-update.js", ".+\.map"],
    }
}

# CELERY STUFF
CELERY_BROKER_URL = config('CELERY_BROKER_URL')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Sentry
SENTRY_DSN = config("SENTRY_DSN", default="")
COMMIT_SHA = config("HEROKU_SLUG_COMMIT", default="")

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        # 'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny'
    ],
}


CORS_ORIGIN_ALLOW_ALL = True


LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '{levelname} - {asctime} - {module} - {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} - {asctime} - {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': base_dir_join('debug', 'debug.log'),
            'when': 'midnight',
            'backupCount': 10,
            'formatter': 'verbose'
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True
        },
        'cloud': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True
        }
    }
}


