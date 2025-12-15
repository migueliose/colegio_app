# En gestioncolegio/templatetags/logro_tags.py
from django import template
from usuarios.models import Docente
from matricula.models import AsignaturaGradoAñoLectivo
from gestioncolegio.models import AñoLectivo
import logging

register = template.Library()
logger = logging.getLogger(__name__)

@register.filter(name='has_permiso_logro')
def has_permiso_logro(user, logro):
    """
    Template filter para verificar si un usuario tiene permiso sobre un logro
    """
    try:
        # Obtener docente
        docente = Docente.objects.get(usuario=user)
        
        # Verificar asignación directa
        tiene_permiso = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            asignatura=logro.asignatura,
            grado_año_lectivo__grado=logro.grado
        ).exists()
        
        # Si no tiene permiso directo, verificar por año lectivo
        if not tiene_permiso and hasattr(logro, 'periodo_academico'):
            año_lectivo = logro.periodo_academico.año_lectivo
            tiene_permiso = AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente,
                asignatura=logro.asignatura,
                grado_año_lectivo__grado=logro.grado,
                grado_año_lectivo__año_lectivo=año_lectivo
            ).exists()
        
        return tiene_permiso
        
    except Docente.DoesNotExist:
        logger.error(f"Docente no encontrado para usuario {user.username}")
        return False
    except Exception as e:
        logger.error(f"Error en has_permiso_logro: {str(e)}")
        return False