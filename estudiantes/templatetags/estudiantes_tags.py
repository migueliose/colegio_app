from django import template
from estudiantes.models import Estudiante
from matricula.models import PeriodoAcademico

register = template.Library()

@register.filter
def get_periodo_actual(estudiante):
    """Obtiene el período actual del estudiante"""
    try:
        if estudiante.grado_actual:
            año_lectivo = estudiante.grado_actual.año_lectivo
            # Buscar el período actual
            from django.utils import timezone
            hoy = timezone.now().date()
            
            periodo = PeriodoAcademico.objects.filter(
                año_lectivo=año_lectivo,
                fecha_inicio__lte=hoy,
                fecha_fin__gte=hoy,
                estado=True
            ).first()
            
            if periodo:
                return periodo
    except:
        pass
    return None