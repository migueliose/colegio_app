from django import template
from web.models import Pagina, RedSocial, About

register = template.Library()

@register.simple_tag
def get_legal_pages():
    """Obtiene páginas legales"""
    return Pagina.objects.filter(is_published=True)

@register.simple_tag
def get_about_pages():
    """Obtiene páginas de información institucional"""
    return About.objects.filter(is_active=True)

@register.simple_tag
def get_admision_pages():
    """Obtiene información de admisiones"""
    from web.models import Admision
    return Admision.objects.filter(is_active=True)

@register.simple_tag
def get_social_links():
    """Obtiene redes sociales activas"""
    return RedSocial.objects.filter(is_active=True)

@register.simple_tag
def get_about_by_type(tipo):
    """Obtiene información about por tipo"""
    return About.objects.filter(tipo=tipo, is_active=True).first()