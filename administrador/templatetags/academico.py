from django import template
register = template.Library()

@register.filter
def activos(queryset):
    """Filtra solo los objetos activos"""
    return queryset.filter(estado=True)

@register.filter(name='activos')
def filtrar_activos(queryset):
    """Filtra solo los objetos activos (estado=True)"""
    try:
        return queryset.filter(estado=True)
    except:
        return queryset.none()
    
@register.filter
def preescolar(queryset):
    """Filtra solo grados de preescolar"""
    return queryset.filter(grado__nivel_escolar__nombre='Preescolar')

@register.filter(name='preescolar')
def filtrar_preescolar(queryset):
    """Filtra grados de preescolar"""
    try:
        return queryset.filter(grado__nivel_escolar__nombre='Preescolar')
    except:
        return queryset.none()
    
@register.filter
def primaria(queryset):
    """Filtra solo grados de primaria"""
    return queryset.filter(grado__nivel_escolar__nombre='Primaria')

@register.filter
def con_docente(queryset):
    """Retorna solo las asignaturas que sí tienen docente asignado."""
    return queryset.filter(docente__isnull=False)

@register.filter(name='primaria')
def filtrar_primaria(queryset):
    """Filtra grados de primaria"""
    try:
        return queryset.filter(grado__nivel_escolar__nombre='Primaria')
    except:
        return queryset.none()

@register.filter
def get_item(dictionary, key):
    """Obtener un valor de un diccionario usando una clave"""
    return dictionary.get(key)

@register.filter
def subtract(value, arg):
    """Restar un valor de otro"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def div(value, arg):
    """Dividir un valor por otro"""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def multiply(value, arg):
    """Multiplicar un valor por otro"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value
    
@register.simple_tag
def contar_activos(queryset):
    """Cuenta objetos activos"""
    return queryset.filter(estado=True).count()

@register.simple_tag
def contar_preescolar(queryset):
    """Cuenta grados preescolar"""
    return queryset.filter(grado__nivel_escolar__nombre='Preescolar').count()

@register.simple_tag
def contar_primaria(queryset):
    """Cuenta grados primaria"""
    return queryset.filter(grado__nivel_escolar__nombre='Primaria').count()