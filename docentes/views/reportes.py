"""
Vistas simplificadas para reportes
"""
from django.views.generic import TemplateView
from django.db.models import Count, Avg
from django.contrib import messages

# Mixins
from gestioncolegio.mixins import RoleRequiredMixin

# Models básicos
from estudiantes.models import Estudiante, Nota, Matricula
from usuarios.models import Docente
from academico.models import Grado
from matricula.models import PeriodoAcademico
from comportamiento.models import Comportamiento
from gestioncolegio.models import AñoLectivo


class ReportesView(RoleRequiredMixin, TemplateView):
    """Vista principal simplificada de reportes"""
    template_name = 'gestioncolegio/reportes/reportes.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas básicas
        context['total_estudiantes'] = Estudiante.objects.filter(estado=True).count()
        context['total_docentes'] = Docente.objects.filter(estado=True).count()
        
        # Año actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if año_actual:
            context['matriculas_ano_actual'] = Matricula.objects.filter(
                año_lectivo=año_actual, 
                estado='ACT'
            ).count()
        
        return context


class ReporteEstadisticasView(RoleRequiredMixin, TemplateView):
    """Reporte simplificado de estadísticas"""
    template_name = 'gestioncolegio/reportes/estadisticas.html'
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas básicas
        context['total_estudiantes'] = Estudiante.objects.filter(estado=True).count()
        context['total_docentes'] = Docente.objects.filter(estado=True).count()
        
        # Distribución por género
        context['estudiantes_masculino'] = Estudiante.objects.filter(
            estado=True, 
            usuario__sexo='M'
        ).count()
        context['estudiantes_femenino'] = Estudiante.objects.filter(
            estado=True, 
            usuario__sexo='F'
        ).count()
        
        # Promedio general
        notas_stats = Nota.objects.filter(
            calificacion__isnull=False
        ).aggregate(promedio=Avg('calificacion'))
        context['promedio_general'] = round(notas_stats['promedio'] or 0, 2)
        
        return context


class ReporteNotasPorGradoView(RoleRequiredMixin, TemplateView):
    """Reporte simplificado de notas por grado"""
    template_name = 'gestioncolegio/reportes/notas_por_grado.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Opciones de filtro
        context['grados'] = Grado.objects.all().order_by('nombre')
        context['periodos'] = PeriodoAcademico.objects.filter(
            año_lectivo__estado=True
        ).order_by('-fecha_inicio')
        
        # Si hay filtros, mostrar datos
        grado_id = self.request.GET.get('grado_id')
        periodo_id = self.request.GET.get('periodo_id')
        
        if grado_id and periodo_id:
            try:
                # Datos básicos
                estudiantes = Estudiante.objects.filter(
                    grado_actual__grado_id=grado_id,
                    estado=True
                ).select_related('usuario')
                
                datos = []
                for estudiante in estudiantes:
                    notas = Nota.objects.filter(
                        estudiante=estudiante,
                        periodo_academico_id=periodo_id
                    )
                    
                    promedio = 0
                    if notas.exists():
                        suma = sum(float(n.calificacion) for n in notas if n.calificacion)
                        promedio = round(suma / notas.count(), 2)
                    
                    datos.append({
                        'estudiante': estudiante,
                        'nombre': estudiante.usuario.get_full_name(),
                        'promedio': promedio
                    })
                
                context['datos_reporte'] = datos
                
            except Exception as e:
                messages.error(self.request, f"Error: {str(e)}")
        
        return context


class ReporteGraficosView(RoleRequiredMixin, TemplateView):
    """Reportes con gráficos simplificados"""
    template_name = 'gestioncolegio/reportes/graficos.html'
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Datos básicos para gráficos
        context['estudiantes_masculino'] = Estudiante.objects.filter(
            usuario__sexo='M'
        ).count()
        context['estudiantes_femenino'] = Estudiante.objects.filter(
            usuario__sexo='F'
        ).count()
        
        # Estudiantes por grado (top 5)
        grados_data = []
        for grado in Grado.objects.all()[:5]:
            count = Estudiante.objects.filter(
                grado_actual__grado=grado
            ).count()
            if count > 0:
                grados_data.append({
                    'nombre': grado.nombre,
                    'cantidad': count
                })
        
        context['grados_data'] = grados_data
        
        return context