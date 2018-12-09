from django.contrib.auth.models import AbstractUser

from django.db import models


class User(AbstractUser):
    nickname = models.CharField(max_length=100)
    avatar = models.ImageField(upload_to='avatars/', blank=True)
