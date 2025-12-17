from django import template

register = template.Library()

@register.filter
def filter_by_nivel(areas, nivel_nombre):
    """Filtrar áreas por nombre de nivel"""
    return [area for area in areas if area.nivel_escolar.nombre == nivel_nombre]

@register.filter
def filter_by_dictadas(asignaturas, año_lectivo):
    """Filtrar asignaturas dictadas en un año específico"""
    if not año_lectivo:
        return []
    
    dictadas = []
    for asignatura in asignaturas:
        if hasattr(asignatura, 'dictada_actual') and asignatura.dictada_actual:
            dictadas.append(asignatura)
    
    return dictadas

@register.simple_tag
def get_start_index(page_obj, forloop_counter):
    """Calcular el índice de inicio para la paginación"""
    if page_obj and page_obj.number > 1:
        return (page_obj.number - 1) * page_obj.paginator.per_page + forloop_counter
    return forloop_counter