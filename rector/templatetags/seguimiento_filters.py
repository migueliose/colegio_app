# rector/templatetags/seguimiento_filters.py
from django import template

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    """Multiplica el valor por el argumento"""
    try:
        # Para números flotantes
        return float(value) * float(arg)
    except (ValueError, TypeError):
        try:
            # Para enteros
            return int(value) * int(arg)
        except (ValueError, TypeError):
            return 0

# Elimina o renombra el filtro 'mul' si existe duplicado
# @register.filter(name='mul')
# def mul(value, arg):
#     """Multiplica el valor por el argumento"""
#     try:
#         return float(value) * float(arg)
#     except (ValueError, TypeError):
#         return 0

# Mantén los otros filtros...
@register.filter(name='divisibleby')
def divisibleby(value, arg):
    """Divide el valor por el argumento"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter(name='percentage')
def percentage(value, total=100):
    """Calcula el porcentaje"""
    try:
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def abs(value):
    try:
        return abs(value)
    except:
        return value