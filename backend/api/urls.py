from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from api.views import (IngredientViewSet, RecipeViewSet,
                       SubscribeView, SubscriptionViewSet, TagViewSet)

router = DefaultRouter()
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
        SubscriptionViewSet.as_view(),
        name='subscriptions'
    ),
    path('', include(router.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
