import os

os.environ["DJANGO_SECRET_KEY"] = "a@25)**hc^rjaiagb4#&q*84hr*uscsxwr-cv#0joiwj$))obyk"
os.environ["KOBOCAT_MONGO_HOST"] = "localhost"
os.environ["CSRF_COOKIE_DOMAIN"] = "localhost"
os.environ["ENKETO_URL"] = 'http://localhost:8005'
os.environ["ENKETO_VERSION"] = 'express'
from onadata.settings.kc_environ import *
# os.environ['S3_USE_SIGV4'] = 'True'
KOBOCAT_URL = os.environ.get('KOBOCAT_URL', 'http://localhost:8001')

KOBOCAT_INTERNAL_HOSTNAME = "localhost"
# ENKETO_PROTOCOL = os.environ.get('ENKETO_PROTOCOL', 'https')
# ENKETO_PROTOCOL = os.environ.get('ENKETO_PROTOCOL', 'http')
ENKETO_PROTOCOL = 'http'
ENKETO_API_ENDPOINT_SURVEYS = '/survey'

ENKETO_URL = os.environ.get('ENKETO_URL', 'http://localhost:8005')


os.environ["ENKETO_API_TOKEN"] = 'enketorules'
# TESTING_MODE = True
# ANGULAR_URL = '/ng/'
# ANGULAR_ROOT = os.path.join(BASE_DIR, 'ng/')

# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_SSL_REDIRECT = True

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

KOBOCAT_URL = 'http://localhost:8001'
CORS_ORIGIN_ALLOW_ALL = True
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'k5',
        # 'NAME': 'app_backup1',
        'USER': 'postgres',
        'PASSWORD': 'password',
        'HOST': '192.168.1.107',
        'PORT': '5432',
    }
}

INSTALLED_APPS = list(INSTALLED_APPS)

MIDDLEWARE_CLASSES += (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    
)
INTERNAL_IPS = '127.0.0.1'
INSTALLED_APPS += ['debug_toolbar', 'fcm']
# INSTALLED_APPS += ['debug_toolbar', 'channels', 'fcm']
# INSTALLED_APPS += ['debug_toolbar', 'fcm',  'channels', 'webpack_loader']

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "asgi_redis.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("localhost", 6379)],
        },
        "ROUTING": "onadata.apps.fieldsight.routing.channel_routing",
    },
}

WEBSOCKET_URL = "ws://localhost"

WEBSOCKET_PORT = "8001"

KPI_URL = 'http://localhost:8000/'
KPI_LOGOUT_URL = KPI_URL + 'accounts/logout/'


FCM_APIKEY = "AAAA8R_cP8A:APA91bH6r8ufI3KOL2h-1CIm7fswvp88QRYgARtvP50y8zIouvu-8JsJ1Tmv62MFA9Kn1dhm7u0kxmXy" \
             "cLiQJfhvN81ItHCWmgWHUNGTwX54Ma3RN6UkILRwa9CR0qO6PHnrQFSjGYOy5vHfQ_w31J7Rk134LrsTUQ"

FCM_MAX_RECIPIENTS = 1000

# AWS_ACCESS_KEY_ID = "AKIAIZ7R3RLZHIOT3EBA"
# AWS_SECRET_ACCESS_KEY = "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"
# AWS_STORAGE_BUCKET_NAME = "fieldsighttest"
# AWS_DEFAULT_ACL = 'public-read'
# AWS_S3_REGION_NAME = 'us-east-1'
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
# AWS_QUERYSTRING_AUTH = False
# AWS_S3_USE_SSL = False
# AWS_S3_SIGNATURE_VERSION = 's3v4'


SERIALIZATION_MODULES = {
        "custom_geojson": "onadata.apps.fieldsight.serializers.GeoJSONSerializer",
}


SEND_ACTIVATION_EMAIL = True
ACCOUNT_ACTIVATION_DAYS = 30
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
DEFAULT_FROM_EMAIL = 'app.fieldsight@gmail.com'
SERVER_EMAIL = 'app.fieldsight@gmail.com'
# EMAIL_USE_TLS = True
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_HOST_USER = 'app.fieldsight@gmail.com'
# EMAIL_HOST_PASSWORD = '@app@fieldsight111'


CORS_ORIGIN_WHITELIST = (
    'dev.ona.io',
    'google.com',
    'app.fieldsight.org',
    'kpi.fieldsight.org',
    'bcss.com.np.com',
    'kc.bcss.com.np',
    'localhost:8001',
    '127.0.0.1:8000'
)

TIME_ZONE = 'Asia/Kathmandu'

from onadata.settings.common import REST_FRAMEWORK
REST_FRAMEWORK.update({'DEFAUL/users/accounts/login/?next=/T_PERMISSION_CLASSES':['rest_framework.permissions.IsAuthenticated',]})


# DEBUG_TOOLBAR_CONFIG = {
#     'INTERCEPT_REDIRECTS': True
# }

FILE_UPLOAD_HANDLERS = ("django_excel.ExcelMemoryFileUploadHandler",
                        "django_excel.TemporaryExcelFileUploadHandler")

# DEBUG = False

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'a@25)**hc^rjaiagb4#&q*84hr*uscsxwr-cv#0joiwj$))obyk')
SESSION_COOKIE_NAME = 'my_cookie'
# SESSION_COOKIE_DOMAIN = '192.168.1.164'
# SESSION_COOKIE_DOMAIN = None
DEFAULT_DEPLOYMENT_BACKEND = 'localhost'



BROKER_BACKEND = "redis"
CELERY_RESULT_BACKEND = "redis"  # telling Celery to report results to RabbitMQ
CELERY_TASK_ALWAYS_EAGER = True
BROKER_URL = 'redis://localhost:6379'

REDIS_HOST = "localhost"

ADMINS = [('Amulya', 'awemulya@gmail.com'), ('AruVan', 'mearunbhandari@gmail.com')]

# CELERY_IMPORTS = ('tasks','onadata.apps.fieldsight.tasks')

# if testing mode

FRONTEND_ENVIRONMENT_DEV_MODE = True

# STATIC_ROOT = os.path.join(ONADATA_DIR, '')
#
# STATICFILES_DIRS += (
#         os.path.join(BASE_DIR, 'static'),
#     )

# if FRONTEND_ENVIRONMENT_DEV_MODE:
#     WEBPACK_LOADER = {
#         'DEFAULT': {
#             'CACHE': False,
#             'BUNDLE_DIR_NAME': '/build/',#('/build/' if DEBUG else '/dist/'),
#             'STATS_FILE': os.path.join(BASE_DIR,'webpack', 'webpack-stats-local.json'),
#         }
#     }
# else:
#     WEBPACK_LOADER = {
#         'DEFAULT': {
#             'CACHE': False,
#             'BUNDLE_DIR_NAME': '/dist/',#('/build/' if DEBUG else '/dist/'),
#             'STATS_FILE': os.path.join(BASE_DIR,'webpack', 'webpack-stats.json'),
#         }
#     }


# STATIC_ROOT = "/home/awemulya/work/naxa/dist-kobo-devel/src/kobocat/static"
# # STATIC_ROOT = "/home/awemulya/work/naxa/dist-kobo-devel/src/kobocat-template/static"
#
# # STATIC_ROOT = os.path.join(BASE_DIR, 'astatic')
# STATICFILES_DIRS = (
#     os.path.join(BASE_DIR, "static"),
# )