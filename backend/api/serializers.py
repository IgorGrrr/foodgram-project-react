from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from users.models import Subscription, User


class CustomUserCreateSerializer(UserCreateSerializer):
    """ Сериализатор создания пользователя. """

    class Meta:
        model = User
        fields = [
            'email',
            'username',
            'first_name',
            'last_name',
            'password'
        ]


class CustomUserSerializer(UserSerializer):
    """ Сериализатор модели Пользователя. """

    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed'
        ]

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if obj == user or user.is_anonymous:
            return False
        return Subscription.objects.filter(
            author=obj, user=user).exists()


class AccountSerializer(CustomUserSerializer):
    """ Сериализатор роли пользователя. """

    role = serializers.CharField(read_only=True)


class TagSerializer(serializers.ModelSerializer):
    """ Сериализатор просмотра модели Тэг. """

    class Meta:
        model = Tag
        fields = ['id', 'name', 'color', 'slug']


class IngredientSerializer(serializers.ModelSerializer):
    """ Сериализатор просмотра модели Ингредиенты. """

    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """ Сериализатор модели связывающей ингредиент и рецепт. """

    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount',)


class RecipeSerializer(serializers.ModelSerializer):
    """ Сериализатор просмотра модели Рецепт. """

    tags = TagSerializer(many=True)
    author = CustomUserSerializer()
    ingredients = serializers.SerializerMethodField()
    image = Base64ImageField(max_length=None, use_url=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        ]

    def get_ingredients(self, obj):
        ingredients = RecipeIngredient.objects.filter(recipe=obj)
        return RecipeIngredientSerializer(ingredients, many=True).data

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return Favorite.objects.filter(
            user=request.user, recipe_id=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(
            user=request.user, recipe_id=obj
        ).exists()


class RecipeIngredientEditSerializer(serializers.ModelSerializer):
    """ Сериализатор добавления ингредиента в рецепт. """

    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ['id', 'amount']


class CreateRecipeSerializer(serializers.ModelSerializer):
    """ Сериализатор создания и изменения рецепта. """

    ingredients = RecipeIngredientSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    image = Base64ImageField(max_length=None, use_url=True)

    class Meta:
        model = Recipe
        fields = [
            'author',
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time'
        ]

        def create(self, validated_data):
            ingredients_data = validated_data.pop('ingredients')
            tags_data = validated_data.pop('tags')
            recipe = Recipe.objects.create(**validated_data)
            for ingredient in ingredients_data:
                amount = ingredient['amount']
                id = ingredient['id']
                RecipeIngredient.objects.create(
                    ingredient=get_object_or_404(Ingredient, id=id),
                    recipe=recipe, amount=amount
                )
            for tag in tags_data:
                recipe.tags.add(tag)
            return recipe

        def validate(self, data):
            ingredients_data = data['ingredients']
            ingredients_set = set()
            for ingredient in ingredients_data:
                if ingredient['amount'] <= 0:
                    raise serializers.ValidationError(
                        'Вес ингредиента должен быть больше 0'
                    )
                if ingredient['id'] in ingredients_set:
                    raise serializers.ValidationError(
                        'Ингредиент в рецепте не должен повторяться.'
                    )
                ingredients_set.add(ingredient['id'])
            return data

        def update(self, instance, validated_data):
            ingredients_data = validated_data.pop('ingredients')
            tags_data = validated_data.pop('tags')
            instance.name = validated_data.get('name', instance.name)
            instance.text = validated_data.get('text', instance.text)
            instance.image = validated_data.get('image', instance.image)
            instance.cooking_time = validated_data.get(
                'cooking_time', instance.cooking_time
            )

            RecipeIngredient.objects.filter(recipe=instance).delete()
            for ingredient in ingredients_data:
                amount = ingredient['amount']
                id = ingredient['id']
                RecipeIngredient.objects.create(
                    ingredient=get_object_or_404(Ingredient, id=id),
                    recipe=instance, amount=amount
                )
            instance.save()
            instance.tags.set(tags_data)
            return instance

        def to_representation(self, instance):
            return RecipeSerializer(
                instance,
                context={
                    'request': self.context.get('request')
                }).data


class ShowFavoriteSerializer(serializers.ModelSerializer):
    """ Сериализатор для отображения избранного. """

    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']


class FavAndShoppingCartSerializer(serializers.ModelSerializer):
    """ Сериализатор для отображения избранного и корзины. """

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time',)


class ShowSubscriptionsSerializer(serializers.ModelSerializer):
    """ Сериализатор для отображения подписок пользователя. """

    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count'
        ]

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return Subscription.objects.filter(
            user=request.user, author=obj).exists()

    def get_recipes(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        context = {'request': request}
        recipes = obj.recipes.all()
        limit = request.query_params.get('recipes_limit')
        if limit:
            recipes = recipes[:int(limit)]
        return FavAndShoppingCartSerializer(
            recipes, many=True, context=context).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()


class SubscriptionSerializer(serializers.ModelSerializer):
    """ Сериализатор подписок. """

    class Meta:
        model = Subscription
        fields = ['user', 'author']
        validators = [
            UniqueTogetherValidator(
                queryset=Subscription.objects.all(),
                fields=['user', 'author'],
            )
        ]

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}
        return ShowSubscriptionsSerializer(
            instance.author, context=context).data
