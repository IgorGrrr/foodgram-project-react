from django.db.models.expressions import Exists, OuterRef
from django.shortcuts import get_object_or_404
from recipes.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from requests import Response
from rest_framework import generics, status, viewsets, views
from rest_framework.decorators import action
from rest_framework.permissions import (SAFE_METHODS,
                                        IsAuthenticated,
                                        AllowAny)
from rest_framework.views import APIView
from users.models import Subscription, User

from .filters import IngredientSearchFilter, RecipeFilter
from .mixins import ListRetrieveViewSet
from .pagination import FoodGramPagination
from .permissions import IsAdminOrAuthorOrReadOnly
from .serializers import (CreateRecipeSerializer, FavAndShoppingCartSerializer,
                          IngredientSerializer, RecipeSerializer,
                          SubscriptionSerializer, TagSerializer)
from .utils import download_ingredients_txt


class SubscriptionViewSet(generics.ListAPIView):
    """ Вьюсет для отображения подписок """

    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = FoodGramPagination
    http_method_names = ('get', )

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user.id)


class SubscribeView(APIView):
    """ Операция подписки/отписки. """

    permission_classes = [IsAuthenticated, ]

    def post(self, request, id):
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

    def delete(self, request, id):
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
    permission_classes = (AllowAny,)
    pagination_class = None
    filterset_class = IngredientSearchFilter
    search_fields = '^name'


class TagViewSet(ListRetrieveViewSet):
    """ Вьюсет для просмотра тэгов """

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """ Вьюсет для работы с рецептами """

    queryset = Recipe.objects.all()
    permission_classes = (IsAdminOrAuthorOrReadOnly,)
    pagination_class = FoodGramPagination
    filterset_class = RecipeFilter
    filterset_fields = ('tags', 'author',
                        'is_favorite', 'is_in_shopping_cart',)
    search_fields = ('$name', )
    http_method_names = ('get', 'post', 'patch', 'delete',)

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return Recipe.objects.annotate(
                is_favorited=Exists(Favorite.objects.filter(
                    user=user, recipe=OuterRef('id'))
                ),
                is_in_shopping_cart=Exists(ShoppingCart.objects.filter(
                    user=user, recipe=OuterRef('id'))
                )
            ).select_related('author', )
        return Recipe.objects.all()

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method in SAFE_METHODS:
            return RecipeSerializer
        return CreateRecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def __make_fav_shop_cart_action(self, request, use_model, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = self.request.user
        if user.is_anonymous:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        checked_queryset = use_model.objects.filter(
            user=user, recipe=recipe)
        if request.method == 'POST':
            if not checked_queryset:
                created = use_model.objects.create(user=user, recipe=recipe)
                serializer = FavAndShoppingCartSerializer(created.recipe)
                return Response(
                    status=status.HTTP_201_CREATED, data=serializer.data)
            else:
                if use_model == Favorite:
                    data = {'errors': 'Этот рецепт уже в избранном.'}
                elif use_model == ShoppingCart:
                    data = {'errors': 'Этот рецепт уже в корзине.'}
                return Response(status=status.HTTP_400_BAD_REQUEST, data=data)
        elif request.method == 'DELETE':
            if not checked_queryset:
                if use_model == Favorite:
                    data = {
                        'errors': 'Этот рецепт не находится в избранном.'}
                elif use_model == ShoppingCart:
                    data = {
                        'errors': 'Этот рецепт не находится в корзине.'}
                return Response(status=status.HTTP_400_BAD_REQUEST, data=data)
            else:
                checked_queryset.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['post', 'delete'], detail=True,
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        return self.__make_fav_shop_cart_action(
            request, use_model=Favorite, pk=pk)

    @action(
        methods=['post', 'delete'], detail=True,
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        return self.__make_fav_shop_cart_action(
            request, use_model=ShoppingCart, pk=pk)

    @action(
        methods=['get'], detail=False,
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        return download_ingredients_txt(request)
