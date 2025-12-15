from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Obtener un valor de un diccionario usando una clave"""
    return dictionary.get(key)

@register.simple_tag
def increment(value):
    """Incrementar un valor (para contadores)"""
    try:
        return int(value) + 1
    except (ValueError, TypeError):
        return value

@register.filter
def div(value, arg):
    """Dividir un valor por otro"""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0