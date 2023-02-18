from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from api.views import (CustomUserViewSet, IngredientViewSet, TagViewSet,
                       RecipeViewSet, SubscriptionViewSet, SubscribeView)

router = DefaultRouter()
router.register('users', CustomUserViewSet, basename='users_list')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('tags', TagViewSet, basename='tags')
router.register('recipes', RecipeViewSet, basename='recipes')

app_name = 'api'

urlpatterns = [
    path(
        'docs/',
        TemplateView.as_view(template_name='redoc.html'),
        name='docs'
    ),
    path(
        'users/<int:id>/subscribe/',
        SubscribeView.as_view(),
        name='subscribe'),
    path(
        'users/subscriptions/',
        SubscriptionViewSet.as_view({'get': 'list'}),
        name='subscriptions'
    ),
    path('', include(router.urls)),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]