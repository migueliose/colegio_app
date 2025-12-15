"""
Vistas para docentes 
"""
from django.shortcuts import get_object_or_404, redirect
from django.views.generic.edit import FormView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView, CreateView, TemplateView, DetailView, UpdateView, DeleteView
from django.contrib import messages, humanize
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
import logging
logger = logging.getLogger(__name__)

# Mixins
from gestioncolegio.mixins import DocenteAccessMixin

# Forms & Models
from docentes.forms import LogroForm, ComportamientoForm, NotaForm
from estudiantes.models import Estudiante, Nota
from usuarios.models import Docente
from comportamiento.models import Comportamiento
from matricula.models import AsignaturaGradoAñoLectivo, PeriodoAcademico
from academico.models import Logro, Asignatura, Grado

def obtener_asignaturas_por_grado(request):
    """Vista AJAX para obtener asignaturas por grado"""
    from django.http import JsonResponse
    
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'No autenticado'}, status=401)
    
    grado_id = request.GET.get('grado_id')
    if not grado_id:
        return JsonResponse({'error': 'ID de grado no proporcionado'}, status=400)
    
    try:
        # Verificar que el usuario sea docente
        docente = Docente.objects.get(usuario=request.user)
        
        # Obtener asignaturas del docente para ese grado
        asignaturas = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__grado_id=grado_id
        ).select_related('asignatura').distinct()
        
        # Preparar datos para respuesta JSON
        asignaturas_data = [
            {
                'id': agal.asignatura.id,
                'nombre': agal.asignatura.nombre,
                'codigo': agal.asignatura.codigo or ''
            }
            for agal in asignaturas
        ]
        
        return JsonResponse({
            'success': True,
            'asignaturas': asignaturas_data
        })
        
    except Docente.DoesNotExist:
        return JsonResponse({'error': 'Usuario no es docente'}, status=403)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

class ListaNotasDocenteView(LoginRequiredMixin, DocenteAccessMixin, ListView):
    """Lista de notas registradas por el docente"""
    template_name = 'docentes/notas/lista_notas_docente.html'
    context_object_name = 'notas'
    paginate_by = 20
    
    def get_queryset(self):
        try:
            docente = Docente.objects.get(usuario=self.request.user)
            
            queryset = Nota.objects.filter(
                asignatura_grado_año_lectivo__docente=docente
            ).select_related(
                'estudiante__usuario',
                'asignatura_grado_año_lectivo__asignatura',
                'asignatura_grado_año_lectivo__grado_año_lectivo__grado',
                'periodo_academico__periodo',
                'periodo_academico__año_lectivo'
            ).order_by('-created_at')
            
            # Aplicar filtros
            grado_id = self.request.GET.get('grado_id')
            asignatura_id = self.request.GET.get('asignatura_id')
            periodo_id = self.request.GET.get('periodo_id')
            
            if grado_id:
                queryset = queryset.filter(
                    asignatura_grado_año_lectivo__grado_año_lectivo__grado_id=grado_id
                )
            
            if asignatura_id:
                queryset = queryset.filter(
                    asignatura_grado_año_lectivo__asignatura_id=asignatura_id
                )
            
            if periodo_id:
                queryset = queryset.filter(periodo_academico_id=periodo_id)
            
            return queryset
            
        except Docente.DoesNotExist:
            return Nota.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            docente = Docente.objects.get(usuario=self.request.user)
            
            # Obtener opciones para filtros
            # Grados que enseña el docente
            grados_ids = AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente
            ).values_list('grado_año_lectivo__grado_id', flat=True).distinct()
            
            context['grados'] = Grado.objects.filter(id__in=grados_ids)
            
            # Asignaturas que enseña
            asignaturas_ids = AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente
            ).values_list('asignatura_id', flat=True).distinct()
            
            context['asignaturas'] = Asignatura.objects.filter(id__in=asignaturas_ids)
            
            # Períodos disponibles
            context['periodos'] = PeriodoAcademico.objects.filter(
                año_lectivo__estado=True
            ).select_related('periodo', 'año_lectivo').order_by('-fecha_inicio')
            
        except Docente.DoesNotExist:
            context['grados'] = []
            context['asignaturas'] = []
            context['periodos'] = []
        
        return context

class EditarNotaView(LoginRequiredMixin, DocenteAccessMixin, UpdateView):
    """Editar una nota específica"""
    model = Nota
    form_class = NotaForm
    template_name = 'docentes/notas/editar_nota.html'
    success_url = reverse_lazy('docentes:lista_notas_docente')

class ReporteNotasAsignaturaView(LoginRequiredMixin, DocenteAccessMixin, TemplateView):
    """Reporte de notas por asignatura"""
    template_name = 'docentes/reportes/notas_asignatura.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Lógica para estadísticas de notas por asignatura
        return context

class ReporteEstadisticasComportamientoView(LoginRequiredMixin, DocenteAccessMixin, TemplateView):
    """Estadísticas de comportamiento"""
    template_name = 'docentes/reportes/estadisticas_comportamiento.html'


def verificar_permiso_logro(docente, logro):
    """
    Verifica si un docente tiene permiso para acceder a un logro
    según la estructura del proyecto colegio_app
    """
    try:
        from gestioncolegio.models import AñoLectivo
        
        # Obtener año lectivo del logro
        año_lectivo_logro = logro.periodo_academico.año_lectivo
        
        # Verificar si el docente está asignado a esa asignatura y grado
        # en el año lectivo del logro
        tiene_permiso = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            asignatura=logro.asignatura,
            grado_año_lectivo__grado=logro.grado,
            grado_año_lectivo__año_lectivo=año_lectivo_logro
        ).exists()
        
        # Si no tiene permiso para ese año, verificar si tiene asignación actual
        if not tiene_permiso:
            año_lectivo_actual = AñoLectivo.objects.filter(estado=True).first()
            if año_lectivo_actual:
                # Verificar si el docente enseña esa asignatura actualmente
                tiene_permiso = AsignaturaGradoAñoLectivo.objects.filter(
                    docente=docente,
                    asignatura=logro.asignatura,
                    grado_año_lectivo__grado=logro.grado,
                    grado_año_lectivo__año_lectivo=año_lectivo_actual
                ).exists()
        
        return tiene_permiso
        
    except Exception as e:
        logger.error(f"Error en verificar_permiso_logro: {str(e)}")
        return False

def obtener_docente_actual(request):
    """Obtiene el docente actual basado en el usuario"""
    try:
        from usuarios.models import Docente
        return Docente.objects.get(usuario=request.user)
    except Docente.DoesNotExist:
        logger.error(f"Docente no encontrado para usuario {request.user.username}")
        return None

def tiene_permiso_logro(docente, logro):
    """
    Verifica si un docente tiene permiso para acceder/modificar un logro
    """
    try:
        # Verificar si el docente enseña la asignatura y grado del logro
        from matricula.models import AsignaturaGradoAñoLectivo
        from gestioncolegio.models import AñoLectivo
        
        # Obtener año lectivo del logro
        año_lectivo_logro = logro.periodo_academico.año_lectivo
        
        # Verificar asignación directa en el año del logro
        asignacion = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            asignatura=logro.asignatura,
            grado_año_lectivo__grado=logro.grado,
            grado_año_lectivo__año_lectivo=año_lectivo_logro
        ).first()
        
        if asignacion:
            logger.info(f"Permiso CONCEDIDO para docente {docente.id} en logro {logro.id}")
            return True
        
        # Si no hay asignación en ese año, verificar en el año actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if año_actual:
            asignacion_actual = AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente,
                asignatura=logro.asignatura,
                grado_año_lectivo__grado=logro.grado,
                grado_año_lectivo__año_lectivo=año_actual
            ).first()
            
            if asignacion_actual:
                logger.info(f"Permiso CONCEDIDO (año actual) para docente {docente.id} en logro {logro.id}")
                return True
        
        logger.warning(f"Permiso DENEGADO para docente {docente.id} en logro {logro.id}")
        logger.warning(f"  Logro: {logro.asignatura.nombre} - {logro.grado.nombre} - {año_lectivo_logro.anho}")
        
        return False
        
    except Exception as e:
        logger.error(f"Error en verificación de permisos: {str(e)}")
        return False
    
class ListaNotasView(LoginRequiredMixin, DocenteAccessMixin, ListView):
    """Lista de notas por estudiante"""
    model = Nota
    template_name = 'docentes/notas/lista_notas.html'
    context_object_name = 'notas'
    paginate_by = 20
    
    def get_queryset(self):
        try:
            docente = Docente.objects.get(usuario=self.request.user)
            return Nota.objects.filter(
                asignatura_grado_año_lectivo__docente=docente
            ).select_related(
                'estudiante__usuario',
                'asignatura_grado_año_lectivo__asignatura'
            ).order_by('-created_at')
        except Docente.DoesNotExist:
            return Nota.objects.none()

class EliminarNotaView(LoginRequiredMixin, DocenteAccessMixin, DeleteView):
    """Eliminar nota específica"""
    model = Nota
    template_name = 'docentes/notas/eliminar_nota.html'
    success_url = reverse_lazy('docentes:lista_notas_docente')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Nota eliminada exitosamente.")
        return super().delete(request, *args, **kwargs)
    
class CalificarNotasView(LoginRequiredMixin, DocenteAccessMixin, TemplateView):
    """Vista principal para calificar notas"""
    template_name = 'docentes/notas/calificar_notas.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            docente = Docente.objects.get(usuario=self.request.user)
            
            # Grados que enseña el docente
            grados_ids = AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente,
                grado_año_lectivo__año_lectivo__estado=True
            ).values_list('grado_año_lectivo__grado_id', flat=True).distinct()
            
            context['grados'] = Grado.objects.filter(
                id__in=grados_ids
            ).select_related('nivel_escolar').order_by('nombre')
            
        except Docente.DoesNotExist:
            context['grados'] = []
        
        return context