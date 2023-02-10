from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import UniqueConstraint
from django.core.validators import RegexValidator


class User(AbstractUser):
    USER_ROLE = 'user'
    ADMIN_ROLE = 'admin'

    ROLES = (
        (USER_ROLE, 'Аутентифицированный'),
        (ADMIN_ROLE, 'Администратор'),
    )

    email = models.EmailField(
        max_length=254,
        unique=True,
        verbose_name='Почта'
    )
    username = models.CharField(
        max_length=150,
        validators=[RegexValidator(r'^[\w.@+-]')],
        verbose_name='Ник пользователя',
    )
    role = models.CharField(
        choices=ROLES,
        max_length=10,
        default=USER_ROLE,
        verbose_name='Роль',
    )
    first_name = models.CharField(
        max_length=150,
        verbose_name='Имя',
    )
    last_name = models.CharField(
        max_length=150,
        verbose_name='Фамилия')
    password = models.CharField(
        max_length=150,
        verbose_name='Пароль',
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        constraints = [
            UniqueConstraint(fields=['email', ], name='email'),
            UniqueConstraint(fields=['username', ], name='username')
        ]

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_user(self):
        return self.role == 'user'
