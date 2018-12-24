**Starting hasker app**

`docker-compose up`

**Required python packages**

`django, 2.1.3`

`mysqlclient, 1.3.14`

`django-rest-swagger, 2.2.0`

`djangorestframework, 3.9.0`

`djangorestframework-jwt, 1.11.0`

`pillow, 5.3.0`

**Environment parameter for production**

`DJANGO_SETTINGS_MODULE=hasker.settings.prod`

**Environment parameter for development**

`DJANGO_SETTINGS_MODULE=hasker.settings.dev`

**Running unit tests**

`docker-compose exec django_web python manage.py test`

**Api usage**

We use swagger to test and describe API.

Specification: `http://127.0.0.1:9000/swagger/`
