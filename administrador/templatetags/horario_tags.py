# administrador/templatetags/horario_tags.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Obtener un elemento de un diccionario"""
    return dictionary.get(key)

@register.filter
def dict_values(dictionary):
    """Obtener todos los valores de un diccionario"""
    return dictionary.values()

@register.filter
def flatten(list_of_lists):
    """Aplanar una lista de listas"""
    result = []
    for sublist in list_of_lists:
        if isinstance(sublist, list):
            result.extend(sublist)
        else:
            result.append(sublist)
    return result

@register.filter
def unique(sequence):
    """Eliminar duplicados manteniendo el orden"""
    seen = set()
    result = []
    for item in sequence:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

@register.filter
def map(sequence, attribute):
    """Mapear un atributo de una secuencia de objetos"""
    result = []
    for item in sequence:
        try:
            # Manejar acceso a atributos anidados (ej: "asignatura_grado.docente")
            attrs = attribute.split('.')
            value = item
            for attr in attrs:
                value = getattr(value, attr, None)
                if value is None:
                    break
            if value:
                result.append(value)
        except:
            continue
    return result

@register.simple_tag
def generar_horas():
    """Generar rangos de horas de 7:00 a 18:00 en intervalos de 1 hora"""
    from datetime import time
    
    horas = []
    for h in range(7, 18):
        horas.append((time(h, 0), time(h + 1, 0)))
    return horas

@register.filter
def subtract(value, arg):
    """Resta arg de value"""
    try:
        # Manejar diferentes tipos de entrada
        if hasattr(value, '__len__'):
            value_len = len(value)
            return value_len - int(arg)
        else:
            return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0