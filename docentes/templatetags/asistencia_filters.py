# En algún lugar de tu proyecto (ej: templatetags/asistencia_filters.py)
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Obtener item de un diccionario por clave"""
    return dictionary.get(key)

@register.filter
def get_item_by_day(lista, day_index):
    """Obtener día por índice (0=Lunes, 4=Viernes)"""
    for item in lista:
        # Convertir fecha a día de la semana (0=Domingo, 1=Lunes, etc.)
        fecha_obj = item.get('fecha')
        if isinstance(fecha_obj, str):
            from datetime import datetime
            fecha_obj = datetime.strptime(fecha_obj, '%Y-%m-%d').date()
        
        # Ajustar: Lunes=1, Martes=2, etc.
        dia_semana = fecha_obj.weekday()  # 0=Lunes, 1=Martes, etc.
        
        if dia_semana == (day_index - 1):  # day_index viene como string "1", "2", etc.
            return item
    return None