# rector/templatetags/asignatura_filters.py
from django import template
from django.db.models import Count

register = template.Library()

@register.filter
def unique_count(queryset, field_name):
    """Cuenta valores únicos de un campo en un queryset"""
    if hasattr(queryset, 'values_list'):
        # Usamos set para obtener valores únicos
        unique_values = set(queryset.values_list(field_name, flat=True))
        # Filtramos None values
        unique_values = {v for v in unique_values if v is not None}
        return len(unique_values)
    return 0

@register.filter
def unique_items(queryset, field_name):
    """Retorna valores únicos de un campo"""
    if hasattr(queryset, 'values_list'):
        unique_values = set(queryset.values_list(field_name, flat=True))
        return [v for v in unique_values if v is not None]
    return []