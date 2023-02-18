from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from recipes.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from requests import Response
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (SAFE_METHODS, AllowAny,
                                        IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.views import APIView
from users.models import Subscription, User

from .filters import IngredientSearchFilter, RecipeFilter
from .mixins import ListRetrieveViewSet
from .pagination import FoodGramPagination
from .permissions import IsAdminOrReadOnly, IsAuthorOnly
from .serializers import (AccountSerializer, CreateRecipeSerializer,
                          CustomUserSerializer, FavoriteSerializer,
                          IngredientSerializer, RecipeSerializer,
                          ShoppingCartSerializer, SubscriptionSerializer,
                          TagSerializer)
from .utils import download_ingredients_txt


class CustomUserViewSet(UserViewSet):
    """ Вьюсет для отображения пользователей """

    serializer_class = CustomUserSerializer
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    lookup_field = 'id'
    pagination_class = FoodGramPagination
    http_method_names = ['get', 'head', 'post']

    @action(
        methods=('GET', 'PATCH',),
        detail=False,
        url_path='me',
        serializer_class=AccountSerializer,
        permission_classes=(IsAuthenticated,)
    )
    def me(self, request):
        user = request.user
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            serializer.data,
            status=status.HTTP_200_OK)


class SubscriptionViewSet(generics.ListAPIView):
    """ Вьюсет для отображения подписок """

    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = (IsAuthorOnly,)
    pagination_class = FoodGramPagination
    http_method_names = ('get', )

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user.id)


class SubscribeView(APIView):
    """ Операция подписки/отписки. """

    permission_classes = [IsAuthenticated, ]

    @staticmethod
    def post(request, id):
        data = {
            'user': request.user.id,
            'author': id
        }
        serializer = SubscriptionSerializer(
            data=data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def delete(request, id):
        author = get_object_or_404(User, id=id)
        if Subscription.objects.filter(
           user=request.user, author=author).exists():
            subscription = get_object_or_404(
                Subscription, user=request.user, author=author
            )
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_404_NOT_FOUND)


class IngredientViewSet(ListRetrieveViewSet):
    """ Вьюсет для просмотра ингредиентов """

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filterset_class = IngredientSearchFilter
    search_fields = '^name'


class TagViewSet(ListRetrieveViewSet):
    """ Вьюсет для просмотра тэгов """

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """ Вьюсет для работы с рецептами """

    queryset = Recipe.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = FoodGramPagination
    filterset_class = RecipeFilter
    filterset_fields = ('tags', 'author',
                        'is_favorite', 'is_in_shopping_cart',)
    search_fields = ('$name', )
    http_method_names = ('get', 'post', 'patch', 'delete',)

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method in SAFE_METHODS:
            return RecipeSerializer
        return CreateRecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def favorite_adding(self, request, recipe):
        data = {'user': request.user.id, 'recipe': recipe}
        serializer = FavoriteSerializer(
            data=data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data,
                        status=status.HTTP_201_CREATED)

    def delete_from_favorite(self, request, recipe):
        favorite = Favorite.objects.filter(user=request.user,
                                           recipe=recipe)
        if favorite.exists():
            favorite.delete()
            return Response(
                'Рецепт удален из избранного.',
                status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'error': 'В избранном такого рецепта нет.'},
            status=status.HTTP_404_NOT_FOUND
        )

    @action(
        methods=('post', 'delete',),
        detail=True,
        permission_classes=(IsAuthenticated,)
    )
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            return self.favorite_adding(request, recipe.id)
        return self.delete_from_favorit(request, recipe.id)

    @action(methods=('GET',),
            detail=False,
            serializer_class=ShoppingCartSerializer,
            permission_classes=(IsAuthorOnly,))
    def download_shopping_cart(self, request):
        return download_ingredients_txt(request)

    def add_to_shopping_cart(self, request, recipe):
        data = {'user': request.user.id, 'recipe': recipe}
        serializer = ShoppingCartSerializer(
            data=data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data,
                        status=status.HTTP_201_CREATED)

    def delete_from_shopping_cart(self, request, recipe):
        cart = ShoppingCart.objects.filter(user=request.user,
                                           recipe=recipe)
        if cart.exists():
            cart.delete()
            return Response(
                'Рецепт удален из корзины.',
                status=status.HTTP_204_NO_CONTENT)
        return Response({'error': 'В корзине нет этого рецепта.'},
                        status=status.HTTP_404_NOT_FOUND)

    @action(
        methods=('post', 'delete',),
        detail=True,
        permission_classes=(IsAuthenticated,)
    )
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            return self.add_to_shopping_cart(request, recipe.id)
        return self.delete_from_shopping_cart(request, recipe.id)
