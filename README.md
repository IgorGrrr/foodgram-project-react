# Продуктовый помощник

![Build Status](https://github.com/IgorGrrr/foodgram-project-react/actions/workflows/foodgram_workflow.yml/badge.svg)

Сайт позволяет пользователям публиковать рецепты блюд, добавлять понравившиеся рецепты в избранное, подписываться на пользователей и скачивать список ингредиентов для покупок

Бэкенд реализован на Django 4.1.6 и Django REST Framework 3.14.0

## Как запустить проект

+ Клонировать репозиторий и перейти в него в командной строке:

```
git clone https://github.com/IgorGrrr/foodgram-project-react.git
```

```
cd foodgram-project-react
```

+ Перейти в папку infra и запустить docker-compose.yaml

```
cd infra
```

```
docker-compose up -d --build
```

+ В контейнере web выполнить миграции, создать суперпользователя и собрать статику с помощью следующих команд

```
docker-compose exec web python manage.py migrate
```

```
docker-compose exec web python manage.py createsuperuser
```

```
docker-compose exec web python manage.py collectstatic --no-input
```

+ Проект запущен и доступен по [адресу](http://84.201.178.0/)
