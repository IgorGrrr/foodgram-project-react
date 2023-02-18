from django_filters.rest_framework import FilterSet, filters
from recipes.models import Ingredient, Recipe


class IngredientSearchFilter(FilterSet):
    name = filters.CharFilter(lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilter(FilterSet):
    tags = filters.AllValuesMultipleFilter(field_name='tags__slug')
    is_favorite = filters.BooleanFilter(method='filter_is_favorite')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = ('tags', 'author', 'is_favorite', 'is_in_shopping_cart')

    def filter_is_favorite(self, queryset, name, value):
        if value:
            return queryset.filter(favorites__user=self.request.user)
        return queryset
