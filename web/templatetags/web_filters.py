from django import template

register = template.Library()

@register.filter
def strip(value):
    """Elimina espacios al inicio y final de una cadena."""
    if isinstance(value, str):
        return value.strip()
    return value
