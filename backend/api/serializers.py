from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from drf_writable_nested import WritableNestedModelSerializer
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

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ['id', 'name', 'amount', 'measurement_unit']


class RecipeSerializer(serializers.ModelSerializer):
    """ Сериализатор просмотра модели Рецепт. """

    tags = TagSerializer(many=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = serializers.SerializerMethodField()
    image = Base64ImageField(max_length=None, use_url=True)
    is_favorited = serializers.SerializerMethodField(
        method_name='get_is_favorited')
    is_in_shopping_cart = serializers.SerializerMethodField(
        method_name='get_is_in_shopping_cart')

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

    @staticmethod
    def get_ingredients(obj):
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


class CreateRecipeSerializer(WritableNestedModelSerializer, serializers.ModelSerializer):
    """ Сериализатор создания и изменения рецепта. """

    author = CustomUserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField(max_length=None, use_url=True)

    class Meta:
        model = Recipe
        fields = [
            'id',
            'author',
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time'
        ]

        def validate(self, data):
            ingredients = self.initial_data.get('ingredients')
            ingredients_id = []
            for ingredient in ingredients:
                amount = ingredient['amount']
                if int(amount) < 1:
                    raise serializers.ValidationError({
                        'amount': 'Количество не может быть меньше 1'
                    })
                if ingredient['id'] in ingredients_id:
                    raise serializers.ValidationError({
                        'ingredient': 'Ингредиент не может повторяться'
                    })
                ingredients_id.append(ingredient['id'])
            return data

        @staticmethod
        def create_ingredients(ingredients, recipe):
            for ingredient in ingredients:
                ingredient = Ingredient.objects.get(id=ingredient['id'])
                RecipeIngredient.objects.create(
                    ingredient=ingredient,
                    recipe=recipe,
                    amount=ingredient['amount']
                )

        def create(self, validated_data):
            ingredients = validated_data.pop('ingredients')
            tags = validated_data.pop('tags')
            recipe = Recipe.objects.create(**validated_data)
            recipe.tags.set(tags)
            self.create_ingredients(recipe, ingredients)
            return recipe

        def update(self, instance, validated_data):
            recipe = instance
            instance.name = validated_data.get('name', instance.name)
            instance.text = validated_data.get('text', instance.text)
            instance.cooking_time = validated_data.get(
                'cooking_time',
                instance.cooking_time
            )
            instance.tags.clear()
            tags = validated_data.get('tags')
            instance.tags.set(tags)
            RecipeIngredient.objects.filter(recipe=recipe).all().delete()
            ingredients = validated_data.get('ingredients')
            self.create_ingredients(recipe, ingredients)
            instance.save()
            return instance

        def to_representation(self, instance):
            return RecipeSerializer(
                instance,
                context={'request': self.context.get('request')}
            ).data


class ShowFavoriteSerializer(serializers.ModelSerializer):
    """ Сериализатор для отображения избранного. """

    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']


class FavoriteSerializer(serializers.ModelSerializer):
    """ Сериализатор модели Избранное. """

    class Meta:
        model = Favorite
        fields = ['user', 'recipe']

    def to_representation(self, instance):
        return ShowFavoriteSerializer(instance.recipe, context={
            'request': self.context.get('request')
        }).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    """ Сериализатор для списка покупок. """

    class Meta:
        model = ShoppingCart
        fields = ['user', 'recipe']

    def to_representation(self, instance):
        return ShowFavoriteSerializer(instance.recipe, context={
            'request': self.context.get('request')
        }).data


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
        recipes = Recipe.objects.filter(author=obj)
        limit = request.query_params.get('recipes_limit')
        if limit:
            recipes = recipes[:int(limit)]
        return ShowFavoriteSerializer(
            recipes, many=True, context={'request': request}).data

    @staticmethod
    def get_recipes_count(obj):
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
        return ShowSubscriptionsSerializer(instance.author, context={
            'request': self.context.get('request')
        }).data
