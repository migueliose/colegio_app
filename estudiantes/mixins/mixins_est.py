from matricula.models import AsignaturaGradoAñoLectivo, PeriodoAcademico
from django.utils import timezone

class PeriodoActualMixin:
    """Mixin para obtener el período actual de forma inteligente"""
    
    def obtener_periodo_actual_inteligente(self, año_lectivo, hoy=None):
        """Obtiene el período académico actual o más reciente"""
        if hoy is None:
            hoy = timezone.now().date()
            
        if not año_lectivo:
            return None
        
        try:
            # 1. Buscar período activo que contenga la fecha actual
            periodo = PeriodoAcademico.objects.filter(
                año_lectivo=año_lectivo,
                fecha_inicio__lte=hoy,
                fecha_fin__gte=hoy
            ).first()
            
            if periodo:
                return periodo
            
            # 2. Buscar último período que terminó
            periodo = PeriodoAcademico.objects.filter(
                año_lectivo=año_lectivo,
                fecha_fin__lt=hoy
            ).order_by('-fecha_fin').first()
            
            if periodo:
                return periodo
            
            # 3. Buscar próximo período
            periodo = PeriodoAcademico.objects.filter(
                año_lectivo=año_lectivo,
                fecha_inicio__gt=hoy
            ).order_by('fecha_inicio').first()
            
            if periodo:
                return periodo
            
            # 4. Usar cualquier período del año
            return PeriodoAcademico.objects.filter(
                año_lectivo=año_lectivo
            ).first()
            
        except Exception as e:
            print(f"Error obteniendo período: {e}")
            return None