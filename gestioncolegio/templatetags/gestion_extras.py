# gestioncolegio/templatetags/gestion_extras.py
from django import template

register = template.Library()

@register.filter(name='tiene_tipo_usuario')
def tiene_tipo_usuario(user):
    """Verifica si el usuario tiene tipo_usuario asignado"""
    if not user or not user.is_authenticated:
        return False
    return hasattr(user, 'tipo_usuario') and user.tipo_usuario is not None

@register.filter(name='get_tipo_usuario')
def get_tipo_usuario(user):
    """Obtiene el tipo de usuario del perfil - VERSIÓN SEGURA"""
    if not user or not user.is_authenticated:
        return "No autenticado"
    
    if user.is_superuser:
        return "Super Administrador"
    
    if not tiene_tipo_usuario(user):
        return "Usuario Básico"
    
    # Verificar que tipo_usuario tenga el atributo nombre
    if not hasattr(user.tipo_usuario, 'nombre'):
        return "Usuario Básico"
    
    return user.tipo_usuario.nombre

@register.filter(name='pertenece_a_grupo')
def pertenece_a_grupo(user, group_name):
    """Verifica si el usuario pertenece a un grupo específico"""
    if not user or not user.is_authenticated:
        return False
    
    # Usar get_tipo_usuario para obtener el nombre del tipo
    tipo = get_tipo_usuario(user)
    return tipo == group_name

@register.filter(name='tiene_perfil_extendido')
def tiene_perfil_extendido(user):
    """Verifica si el usuario tiene perfil extendido o es superusuario"""
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    # Tipos que tienen perfiles extendidos
    tipos_con_perfil = ['Administrador', 'Docente', 'Estudiante', 'Acudiente', 'Rector']
    tipo = get_tipo_usuario(user)
    
    return tipo in tipos_con_perfil

@register.filter(name='es_administrador')
def es_administrador(user):
    """Verifica si el usuario es administrador o superusuario"""
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    tipo = get_tipo_usuario(user)
    return tipo == 'Administrador'

@register.filter(name='es_docente')
def es_docente(user):
    """Verifica si el usuario es docente"""
    if not user or not user.is_authenticated:
        return False
    
    tipo = get_tipo_usuario(user)
    return tipo == 'Docente'

@register.filter(name='es_estudiante')
def es_estudiante(user):
    """Verifica si el usuario es estudiante"""
    if not user or not user.is_authenticated:
        return False
    
    tipo = get_tipo_usuario(user)
    return tipo == 'Estudiante'

@register.filter(name='es_acudiente')
def es_acudiente(user):
    """Verifica si el usuario es acudiente"""
    if not user or not user.is_authenticated:
        return False
    
    tipo = get_tipo_usuario(user)
    return tipo == 'Acudiente'

@register.filter(name='es_rector')
def es_rector(user):
    """Verifica si el usuario es rector"""
    if not user or not user.is_authenticated:
        return False
    
    tipo = get_tipo_usuario(user)
    return tipo == 'Rector'

# Filtro para mostrar badge
@register.filter(name='obtener_badge_usuario')
def obtener_badge_usuario(user, safe=False):
    """Devuelve el badge HTML según el tipo de usuario"""
    if not user or not user.is_authenticated:
        return ""
    
    tipo = get_tipo_usuario(user)
    
    badge_classes = {
        'Super Administrador': 'bg-danger',
        'Administrador': 'bg-danger',
        'Docente': 'bg-warning',
        'Estudiante': 'bg-success',
        'Acudiente': 'bg-info',
        'Rector': 'bg-primary',
    }
    
    badge_text = {
        'Super Administrador': 'Super Admin',
        'Administrador': 'Admin',
        'Docente': 'Docente',
        'Estudiante': 'Estudiante',
        'Acudiente': 'Acudiente',
        'Rector': 'Rector',
    }
    
    if tipo in badge_classes:
        badge_html = f'<span class="badge {badge_classes[tipo]} ms-1">{badge_text[tipo]}</span>'
        if safe:
            from django.utils.safestring import mark_safe
            return mark_safe(badge_html)
        return badge_html
    
    return ""

# Filtros de utilidad
@register.filter
def split(value, arg):
    """Divide un string por un separador"""
    if not value:
        return []
    return value.split(arg)

@register.filter
def get_item(dictionary, key):
    """Obtiene un item de un diccionario"""
    if not dictionary:
        return None
    return dictionary.get(key, None)

@register.filter
def multiply(value, arg):
    """Multiplica dos valores"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Divide dos valores"""
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def default_if_none(value, default):
    """Devuelve un valor por defecto si es None"""
    return value if value is not None else default