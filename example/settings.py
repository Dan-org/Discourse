from os.path import abspath, dirname, join

### Home Directory ###
HOME = dirname(abspath(__file__))

### Debug ###
DEBUG = TEMPLATE_DEBUG = True

### Urls ###
ROOT_URLCONF = 'example.urls'

### Apps ###
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.humanize',

    'discourse',
    'example'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

### Data ###
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'sqlite.db',
    }
}

### Media ###
MEDIA_ROOT = join(HOME, 'media')
MEDIA_URL = '/media/'
STATIC_ROOT = join(HOME, "static_collected")
STATIC_URL = "/static/"

### Security ###
SECRET_KEY = 'not-so-secret'

### Misc ###
SITE_ID = 1
