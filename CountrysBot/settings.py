import os  # noqa
from pathlib import Path

from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv, find_dotenv

from .config import *  # noqa

load_dotenv(find_dotenv(".env"))

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = os.getenv("DEBUG")
if DEBUG is not None:
    DEBUG = DEBUG.lower() in ["true", "1"]
else:
    DEBUG = False

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "cinema-counted-shorter-evaluate.trycloudflare.com"]
CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1", "https://localhost:8000", "https://cinema-counted-shorter-evaluate.trycloudflare.com"]

INSTALLED_APPS = [*THIRD_PARTY_APPS, *DEFAULT_APPS, *PROJECT_APPS]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.BrokenLinkEmailsMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "CountrysBot.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "assets/templates")],
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

WSGI_APPLICATION = "CountrysBot.wsgi.application"
ASGI_APPLICATION = "CountrysBot.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": os.getenv("POSTGRES_DB"),
#         "USER": os.getenv("POSTGRES_USER"),
#         "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
#         "HOST": os.getenv("POSTGRES_BOUNCER_HOST"),
#         "PORT": os.getenv("POSTGRES_BOUNCER_PORT"),
#     }
# }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "uz"

TIME_ZONE = "Asia/Tashkent"

USE_I18N = True

USE_TZ = True

LANGUAGES = (
    ("uz", _("Uzbek")),
    ("ru", _("Russia")),
    ("en", _("English")),
)

LOCALE_PATHS = [os.path.join(BASE_DIR, "locale")]

MODELTRANSLATION_LANGUAGES = ("uz", "ru", "en")

MODELTRANSLATION_DEFAULT_LANGUAGE = "uz"

STATIC_URL = "static/"
STATICFILES_DIRS = [str(BASE_DIR.joinpath("assets/static"))]
STATIC_ROOT = str(BASE_DIR.joinpath("assets/staticfiles"))

MEDIA_URL = "media/"
MEDIA_ROOT = str(BASE_DIR.joinpath("assets/media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOW_ALL_ORIGINS = True

LOCALE_MIDDLEWARE_EXCLUDED_PATHS = ["/media/", "/static/"]

"""
MedBot Django Settings
O'zbekiston tibbiy tahlil buyurtma tizimi
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


# ─── DATABASE ─────────────────────────────────────────────────────────────────
_db_url = os.environ.get("DATABASE_URL", "postgres://medbot:medbot@localhost:5432/medbot_db")

# DATABASE_URL ni parse qilamiz
import re
# _match = re.match(
#     r"postgres(?:ql)?://(?P<user>[^:]+):(?P<password>[^@]+)@(?P<host>[^:/]+)(?::(?P<port>\d+))?/(?P<name>.+)",
#     _db_url
# )
# if _match:
#     _d = _match.groupdict()
#     DATABASES = {
#         "default": {
#             "ENGINE": "django.db.backends.postgresql",
#             "NAME": _d["name"],
#             "USER": _d["user"],
#             "PASSWORD": _d["password"],
#             "HOST": _d["host"],
#             "PORT": _d.get("port") or "5432",
#             "OPTIONS": {
#                 "connect_timeout": 10,
#             },
#             "CONN_MAX_AGE": 60,
#         }
#     }
# else:
#     # Fallback
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": "medbot_db",
#         "USER": "medbot",
#         "PASSWORD": "medbot",
#         "HOST": "localhost",
#         "PORT": "5432",
#     }
# }




# ─── STATIC & MEDIA ───────────────────────────────────────────────────────────


STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"




# ─── REST FRAMEWORK ───────────────────────────────────────────────────────────


# ─── CORS ─────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    "https://web.telegram.org",
    "https://k.tspay.uz",
]

_webapp_url = os.environ.get("WEBAPP_URL", "https://yourdomain.com").rstrip("/")
if _webapp_url:
    CORS_ALLOWED_ORIGINS.append(_webapp_url)

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Faqat dev muhitida

# ─── TELEGRAM ─────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "-1001234567890")
TELEGRAM_ADMIN_IDS = [
    int(x.strip())
    for x in os.environ.get("TELEGRAM_ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
]
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://yourdomain.com")

# ─── TSPAY ────────────────────────────────────────────────────────────────────
TSPAY_MERCHANT_ID = os.environ.get("TSPAY_MERCHANT_ID", "0f039e001bcd4020")
TSPAY_SECRET_KEY  = os.environ.get("TSPAY_SECRET_KEY", "7bb7eb8cf4424472e1ef9fe46cc1c66565c8b445202adb01")
TSPAY_API_BASE    = os.environ.get("TSPAY_API_BASE", "https://test.tspay.uz")

# ─── CELERY ───────────────────────────────────────────────────────────────────
CELERY_BROKER_URL       = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND   = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_TASK_SERIALIZER  = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT   = ["json"]
CELERY_TIMEZONE         = TIME_ZONE
CELERY_BEAT_SCHEDULE    = {}

# ─── GEOPY ────────────────────────────────────────────────────────────────────
GEOPY_USER_AGENT = os.environ.get("GEOPY_USER_AGENT", "medbot_uz_v1")

# ─── SECURITY HEADERS (production) ───────────────────────────────────────────
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER      = True
    SECURE_CONTENT_TYPE_NOSNIFF    = True
    X_FRAME_OPTIONS                = "DENY"
    SECURE_HSTS_SECONDS            = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_SSL_REDIRECT            = True
    SESSION_COOKIE_SECURE          = True
    CSRF_COOKIE_SECURE             = True

# ─── LOGGING ─────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "apps": {"handlers": ["console"], "level": "DEBUG" if DEBUG else "INFO", "propagate": False},
        "telegram": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
