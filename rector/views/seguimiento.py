# rector/views/seguimiento.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.views.generic.edit import FormView
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Count, Avg, Q, Sum, F, DecimalField, Max, Min
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.http import JsonResponse
from django.forms import modelformset_factory
from datetime import date, timedelta
import json

# Mixins y modelos
from gestioncolegio.mixins import RoleRequiredMixin
from comportamiento.models import Comportamiento, Asistencia, Inconsistencia
from estudiantes.models import Nota, Estudiante, Matricula
from usuarios.models import Docente
from gestioncolegio.models import Colegio, Sede, AñoLectivo, ConfiguracionGeneral
from matricula.models import PeriodoAcademico, AsignaturaGradoAñoLectivo, GradoAñoLectivo
from academico.models import Asignatura
from ..forms.formularios_seguimiento import *

# ==================== DASHBOARD DE SEGUIMIENTO ====================

class SeguimientoDashboardView(RoleRequiredMixin, TemplateView):
    """Dashboard principal del módulo de seguimiento"""
    template_name = 'rector/seguimiento/dashboard.html'
    allowed_roles = ['Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Colegio del usuario actual
        usuario = self.request.user
        colegio = Colegio.objects.filter(estado=True).first()
        context['colegio'] = colegio
        
        # Obtener año lectivo actual
        config = ConfiguracionGeneral.objects.filter(colegio=colegio).first()
        año_actual = config.año_lectivo_actual if config else None
        context['año_lectivo_actual'] = año_actual
        
        # Obtener periodo académico actual
        periodo_actual = None
        if año_actual:
            periodo_actual = PeriodoAcademico.objects.filter(
                año_lectivo=año_actual,
                estado=True,
                fecha_inicio__lte=date.today(),
                fecha_fin__gte=date.today()
            ).first()
            
            if not periodo_actual:
                periodo_actual = PeriodoAcademico.objects.filter(
                    año_lectivo=año_actual,
                    estado=True
                ).order_by('-fecha_inicio').first()
        
        context['periodo_actual'] = periodo_actual
        
        # ========== MANEJO DE FILTROS ==========
        filtro_form = SeguimientoFilterForm(self.request.GET)
        periodo_filtro = None
        grado_filtro = None
        
        if filtro_form.is_valid():
            data = filtro_form.cleaned_data
            
            # Obtener periodo del filtro si existe
            if data.get('periodo_academico'):
                periodo_filtro = data['periodo_academico']
            
            # Obtener grado del filtro si existe
            if data.get('grado'):
                grado_filtro = data['grado']
        
        # Usar periodo del filtro o el actual
        periodo_para_estadisticas = periodo_filtro or periodo_actual
        context['periodo_seleccionado'] = periodo_para_estadisticas
        
        # ========== CÁLCULO DE ESTADÍSTICAS ==========
        hoy = date.today()
        inicio_mes = date(hoy.year, hoy.month, 1)
        
        # Construir filtros base
        filtros_base = {}
        filtros_mes = {}
        
        if año_actual:
            filtros_base['periodo_academico__año_lectivo'] = año_actual
            filtros_mes['periodo_academico__año_lectivo'] = año_actual
            filtros_mes['fecha__gte'] = inicio_mes
            filtros_mes['fecha__lte'] = hoy
        
        # Aplicar filtro de periodo si existe
        if periodo_para_estadisticas:
            filtros_base['periodo_academico'] = periodo_para_estadisticas
            filtros_mes['periodo_academico'] = periodo_para_estadisticas
        
        # Aplicar filtro de grado si existe (para estudiantes)
        estudiantes_ids = None
        if grado_filtro:
            # Obtener estudiantes del grado seleccionado
            matriculas = Matricula.objects.filter(
                grado_año_lectivo=grado_filtro,
                estado='ACT'
            ).values_list('estudiante_id', flat=True)
            estudiantes_ids = list(matriculas)
            
            if estudiantes_ids:
                filtros_base['estudiante_id__in'] = estudiantes_ids
                filtros_mes['estudiante_id__in'] = estudiantes_ids
        
        # ========== ESTADÍSTICAS GENERALES ==========
        
        # Total estudiantes (considerando filtro de grado)
        if grado_filtro and estudiantes_ids:
            total_estudiantes = len(estudiantes_ids)
        elif año_actual:
            total_estudiantes = Matricula.objects.filter(
                año_lectivo=año_actual,
                estado='ACT'
            ).count()
        else:
            total_estudiantes = 0
        
        context['total_estudiantes'] = total_estudiantes
        
        # Asistencias del mes
        asistencias_mes = Asistencia.objects.filter(**filtros_mes).count()
        context['asistencias_mes'] = asistencias_mes
        
        # Promedio de asistencia
        if total_estudiantes > 0:
            dias_lectivos = (hoy - inicio_mes).days + 1
            asistencias_esperadas = total_estudiantes * dias_lectivos
            if asistencias_esperadas > 0:
                promedio_asistencia = (asistencias_mes / asistencias_esperadas) * 100
            else:
                promedio_asistencia = 0
        else:
            promedio_asistencia = 0
        
        context['promedio_asistencia'] = promedio_asistencia
        
        # Comportamientos del mes
        comportamientos_mes = Comportamiento.objects.filter(**filtros_mes).count()
        context['comportamientos_mes'] = comportamientos_mes
        
        # Distribución de comportamientos
        comportamientos_tipo = Comportamiento.objects.filter(**filtros_mes).values(
            'tipo'
        ).annotate(total=Count('id')).order_by('tipo')
        
        positivos = 0
        negativos = 0
        
        for item in comportamientos_tipo:
            if item['tipo'] == 'Positivo':
                positivos = item['total']
            elif item['tipo'] == 'Negativo':
                negativos = item['total']
        
        context['comportamientos_positivos'] = positivos
        context['comportamientos_negativos'] = negativos
        
        # Calcular porcentajes
        total_comportamientos = positivos + negativos
        context['porcentaje_positivos'] = (positivos / total_comportamientos * 100) if total_comportamientos > 0 else 0
        context['porcentaje_negativos'] = (negativos / total_comportamientos * 100) if total_comportamientos > 0 else 0
        
        # Inconsistencias activas
        fecha_limite = hoy - timedelta(days=30)
        filtros_inconsistencias = {'fecha__gte': fecha_limite}
        
        if estudiantes_ids:
            filtros_inconsistencias['estudiante_id__in'] = estudiantes_ids
        
        inconsistencias_activas = Inconsistencia.objects.filter(**filtros_inconsistencias).count()
        context['inconsistencias_activas'] = inconsistencias_activas
        
        # Calificaciones del periodo
        if periodo_para_estadisticas:
            filtros_calificaciones = {'periodo_academico': periodo_para_estadisticas}
            
            if estudiantes_ids:
                filtros_calificaciones['estudiante_id__in'] = estudiantes_ids
            
            calificaciones_periodo = Nota.objects.filter(**filtros_calificaciones).count()
            context['calificaciones_periodo'] = calificaciones_periodo
            
            # Promedio general de calificaciones
            promedio_result = Nota.objects.filter(**filtros_calificaciones).aggregate(
                promedio=Avg('calificacion')
            )
            context['promedio_calificaciones'] = promedio_result['promedio'] or 0
        else:
            context['calificaciones_periodo'] = 0
            context['promedio_calificaciones'] = 0
        
        # ========== DATOS PARA GRÁFICOS ==========
        
        # Top estudiantes con mejor comportamiento
        if periodo_para_estadisticas:
            filtros_top = {
                'periodo_academico': periodo_para_estadisticas,
                'tipo': 'Positivo'
            }
            
            if estudiantes_ids:
                filtros_top['estudiante_id__in'] = estudiantes_ids
            
            top_comportamiento = Comportamiento.objects.filter(**filtros_top).values(
                'estudiante__usuario__nombres',
                'estudiante__usuario__apellidos'
            ).annotate(
                total=Count('id')
            ).order_by('-total')[:5]
            context['top_comportamiento'] = top_comportamiento
        
        # Asignaturas con mejor desempeño
        if periodo_para_estadisticas:
            filtros_asignaturas = {'periodo_academico': periodo_para_estadisticas}
            
            if estudiantes_ids:
                filtros_asignaturas['estudiante_id__in'] = estudiantes_ids
            
            top_asignaturas = Nota.objects.filter(**filtros_asignaturas).values(
                'asignatura_grado_año_lectivo__asignatura__nombre'
            ).annotate(
                promedio=Avg('calificacion')
            ).order_by('-promedio')[:5]
            
            # Calcular porcentajes
            for item in top_asignaturas:
                promedio = item['promedio'] or 0
                # Escala de 0 a 5 a porcentaje (0-100%)
                item['porcentaje'] = min(promedio * 20, 100)
                item['promedio_formateado'] = f"{promedio:.1f}"
            
            context['top_asignaturas'] = top_asignaturas
        
        # ========== ALERTAS DEL SISTEMA ==========
        alertas = []
        
        if not periodo_actual:
            alertas.append({
                'tipo': 'warning',
                'mensaje': 'No hay un periodo académico activo actualmente.',
                'accion': reverse('rector:periodo_list')
            })
        
        if promedio_asistencia < 85:
            alertas.append({
                'tipo': 'danger',
                'mensaje': f'El promedio de asistencia es bajo: {promedio_asistencia:.1f}%.',
                'accion': reverse('rector:asistencia_list')
            })
        
        if inconsistencias_activas > 5:
            alertas.append({
                'tipo': 'warning',
                'mensaje': f'Hay {inconsistencias_activas} inconsistencias activas que requieren atención.',
                'accion': reverse('rector:inconsistencia_list')
            })
        
        # Verificar si hay comportamientos negativos significativos
        if negativos > positivos * 1.5:  # 50% más negativos que positivos
            alertas.append({
                'tipo': 'warning',
                'mensaje': f'Hay más comportamientos negativos ({negativos}) que positivos ({positivos}).',
                'accion': reverse('rector:comportamiento_list')
            })
        
        context['alertas'] = alertas
        
        # ========== FORMULARIO DE FILTRO ==========
        # Pasar el formulario con datos actuales
        context['filtro_form'] = filtro_form
        
        # Pasar valores de filtro actuales para mostrar en la interfaz
        context['filtro_periodo_id'] = periodo_filtro.id if periodo_filtro else None
        context['filtro_grado_id'] = grado_filtro.id if grado_filtro else None
        
        # Obtener nombre del periodo y grado seleccionados
        if periodo_filtro:
            context['periodo_nombre'] = f"{periodo_filtro.periodo.nombre} - {periodo_filtro.año_lectivo.anho}"
        elif periodo_actual:
            context['periodo_nombre'] = f"{periodo_actual.periodo.nombre} - {periodo_actual.año_lectivo.anho}"
        
        if grado_filtro:
            context['grado_nombre'] = f"{grado_filtro.grado.nombre} - {grado_filtro.año_lectivo.anho}"
        
        return context

# ==================== COMPORTAMIENTO ====================

class ComportamientoListView(RoleRequiredMixin, ListView):
    """Lista de comportamientos con filtros"""
    template_name = 'rector/seguimiento/comportamiento/comportamiento_list.html'
    allowed_roles = ['Rector']
    model = Comportamiento
    context_object_name = 'comportamientos'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Comportamiento.objects.select_related(
            'estudiante__usuario',
            'periodo_academico__año_lectivo',
            'periodo_academico__periodo',
            'docente__usuario'
        ).order_by('-fecha', '-created_at')
        
        # Aplicar filtros
        filtro_form = ComportamientoFilterForm(self.request.GET)
        if filtro_form.is_valid():
            data = filtro_form.cleaned_data
            
            # Filtro por estudiante (búsqueda por nombre o documento)
            if data.get('estudiante'):
                queryset = queryset.filter(
                    Q(estudiante__usuario__nombres__icontains=data['estudiante']) |
                    Q(estudiante__usuario__apellidos__icontains=data['estudiante']) |
                    Q(estudiante__usuario__numero_documento__icontains=data['estudiante'])
                )
            
            # Filtro por periodo académico
            if data.get('periodo_academico'):
                queryset = queryset.filter(periodo_academico=data['periodo_academico'])
            
            # Filtro por tipo
            if data.get('tipo'):
                queryset = queryset.filter(tipo=data['tipo'])
            
            # Filtro por categoría
            if data.get('categoria'):
                queryset = queryset.filter(categoria=data['categoria'])
            
            # Filtro por fecha
            if data.get('fecha_inicio'):
                queryset = queryset.filter(fecha__gte=data['fecha_inicio'])
            if data.get('fecha_fin'):
                queryset = queryset.filter(fecha__lte=data['fecha_fin'])
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtro_form'] = ComportamientoFilterForm(self.request.GET)
        
        # Estadísticas
        queryset = self.get_queryset()
        context['total_registros'] = queryset.count()
        context['total_positivos'] = queryset.filter(tipo='Positivo').count()
        context['total_negativos'] = queryset.filter(tipo='Negativo').count()
        
        # Distribución por categoría
        categorias = queryset.values('categoria').annotate(
            total=Count('id'),
            positivos=Count('id', filter=Q(tipo='Positivo')),
            negativos=Count('id', filter=Q(tipo='Negativo'))
        ).order_by('categoria')
        context['distribucion_categorias'] = categorias
        
        return context

class ComportamientoCreateView(RoleRequiredMixin, CreateView):
    """Crear nuevo registro de comportamiento"""
    template_name = 'rector/seguimiento/comportamiento/comportamiento_form.html'
    allowed_roles = ['Rector']
    model = Comportamiento
    form_class = ComportamientoForm
    success_url = reverse_lazy('rector:comportamiento_list')
    
    def form_valid(self, form):
        # Asignar automáticamente el docente si está logueado
        if self.request.user.tipo_usuario.nombre == 'Docente':
            try:
                docente = Docente.objects.get(usuario=self.request.user)
                form.instance.docente = docente
            except Docente.DoesNotExist:
                pass
        
        response = super().form_valid(form)
        messages.success(self.request, 'Comportamiento registrado exitosamente.')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Registrar Comportamiento'
        return context

class ComportamientoUpdateView(RoleRequiredMixin, UpdateView):
    """Editar registro de comportamiento"""
    template_name = 'rector/seguimiento/comportamiento/comportamiento_form.html'
    allowed_roles = ['Rector']
    model = Comportamiento
    form_class = ComportamientoForm
    success_url = reverse_lazy('rector:comportamiento_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Comportamiento actualizado exitosamente.')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Comportamiento'
        return context

class ComportamientoDetailView(RoleRequiredMixin, DetailView):
    """Detalle de comportamiento"""
    template_name = 'rector/seguimiento/comportamiento/comportamiento_detail.html'
    allowed_roles = ['Rector']
    model = Comportamiento
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener historial de comportamiento del estudiante
        estudiante = self.object.estudiante
        historial = Comportamiento.objects.filter(
            estudiante=estudiante
        ).exclude(id=self.object.id).select_related(
            'periodo_academico__año_lectivo',
            'docente__usuario'
        ).order_by('-fecha')[:10]
        
        context['historial_comportamiento'] = historial
        
        # Estadísticas del estudiante
        context['total_comportamientos'] = Comportamiento.objects.filter(
            estudiante=estudiante
        ).count()
        
        context['total_positivos'] = Comportamiento.objects.filter(
            estudiante=estudiante,
            tipo='Positivo'
        ).count()
        
        context['total_negativos'] = Comportamiento.objects.filter(
            estudiante=estudiante,
            tipo='Negativo'
        ).count()
        
        return context

class ComportamientoDeleteView(RoleRequiredMixin, DeleteView):
    """Eliminar registro de comportamiento"""
    template_name = 'rector/seguimiento/comportamiento/comportamiento_confirm_delete.html'
    allowed_roles = ['Rector']
    model = Comportamiento
    success_url = reverse_lazy('rector:comportamiento_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Comportamiento eliminado exitosamente.')
        return super().delete(request, *args, **kwargs)

# ==================== ASISTENCIA ====================

class AsistenciaListView(RoleRequiredMixin, ListView):
    """Lista de asistencias con filtros"""
    template_name = 'rector/seguimiento/asistencia/asistencia_list.html'
    allowed_roles = ['Rector']
    model = Asistencia
    context_object_name = 'asistencias'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Asistencia.objects.select_related(
            'estudiante__usuario',
            'periodo_academico__año_lectivo',
            'periodo_academico__periodo'
        ).order_by('-fecha', 'estudiante__usuario__nombres')
        
        # Aplicar filtros
        filtro_form = AsistenciaFilterForm(self.request.GET)
        if filtro_form.is_valid():
            data = filtro_form.cleaned_data
            
            # Filtro por estudiante
            if data.get('estudiante'):
                queryset = queryset.filter(
                    Q(estudiante__usuario__nombres__icontains=data['estudiante']) |
                    Q(estudiante__usuario__apellidos__icontains=data['estudiante']) |
                    Q(estudiante__usuario__numero_documento__icontains=data['estudiante'])
                )
            
            # Filtro por periodo académico
            if data.get('periodo_academico'):
                queryset = queryset.filter(periodo_academico=data['periodo_academico'])
            
            # Filtro por grado
            if data.get('grado'):
                # Obtener estudiantes del grado
                matriculas = Matricula.objects.filter(
                    grado_año_lectivo=data['grado'],
                    estado='ACT'
                ).values_list('estudiante_id', flat=True)
                queryset = queryset.filter(estudiante_id__in=matriculas)
            
            # Filtro por estado
            if data.get('estado'):
                queryset = queryset.filter(estado=data['estado'])
            
            # Filtro por fecha
            if data.get('fecha_inicio'):
                queryset = queryset.filter(fecha__gte=data['fecha_inicio'])
            if data.get('fecha_fin'):
                queryset = queryset.filter(fecha__lte=data['fecha_fin'])
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtro_form'] = AsistenciaFilterForm(self.request.GET)
        
        # Estadísticas
        queryset = self.get_queryset()
        context['total_registros'] = queryset.count()
        
        # Distribución por estado
        estados = queryset.values('estado').annotate(
            total=Count('id')
        ).order_by('estado')
        context['distribucion_estados'] = estados
        
        # Porcentajes
        if queryset.count() > 0:
            context['porcentaje_asistencia'] = (queryset.filter(estado='A').count() / queryset.count()) * 100
            context['porcentaje_faltas'] = (queryset.filter(estado='F').count() / queryset.count()) * 100
            context['porcentaje_justificadas'] = (queryset.filter(estado='J').count() / queryset.count()) * 100
        
        return context

class AsistenciaCreateView(RoleRequiredMixin, CreateView):
    """Crear nuevo registro de asistencia"""
    template_name = 'rector/seguimiento/asistencia/asistencia_form.html'
    allowed_roles = ['Rector']
    model = Asistencia
    form_class = AsistenciaForm
    success_url = reverse_lazy('rector:asistencia_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Asistencia registrada exitosamente.')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Registrar Asistencia'
        return context

class AsistenciaDetailView(RoleRequiredMixin, DetailView):
    """Detalle de asistencia"""
    template_name = 'rector/seguimiento/asistencia/asistencia_detail.html'
    allowed_roles = ['Rector']
    model = Asistencia
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asistencia = self.object
        
        # Obtener historial de asistencias del estudiante
        historial = Asistencia.objects.filter(
            estudiante=asistencia.estudiante
        ).exclude(id=asistencia.id).select_related(
            'periodo_academico__año_lectivo',
            'periodo_academico__periodo'
        ).order_by('-fecha')[:10]
        
        context['historial_asistencias'] = historial
        
        # Calcular estadísticas del estudiante para el periodo actual
        periodo = asistencia.periodo_academico
        if periodo:
            # Asistencias en este periodo
            asistencias_periodo = Asistencia.objects.filter(
                estudiante=asistencia.estudiante,
                periodo_academico=periodo
            )
            
            total_asistencias = asistencias_periodo.count()
            if total_asistencias > 0:
                asistio_count = asistencias_periodo.filter(estado='A').count()
                falto_count = asistencias_periodo.filter(estado='F').count()
                justificada_count = asistencias_periodo.filter(estado='J').count()
                
                context['estadisticas_periodo'] = {
                    'total': total_asistencias,
                    'asistio': asistio_count,
                    'falto': falto_count,
                    'justificada': justificada_count,
                    'porcentaje_asistencia': (asistio_count / total_asistencias) * 100
                }
            
            # Obtener días del mes actual para estadísticas
            hoy = date.today()
            inicio_mes = date(hoy.year, hoy.month, 1)
            
            asistencias_mes = Asistencia.objects.filter(
                estudiante=asistencia.estudiante,
                fecha__gte=inicio_mes,
                fecha__lte=hoy
            )
            
            total_mes = asistencias_mes.count()
            if total_mes > 0:
                asistio_mes = asistencias_mes.filter(estado='A').count()
                context['porcentaje_asistencia_mes'] = (asistio_mes / total_mes) * 100
                context['total_asistencias_mes'] = total_mes
        
        # Obtener información de matrícula actual
        matricula_actual = asistencia.estudiante.matricula_actual
        if matricula_actual:
            context['matricula_actual'] = matricula_actual
            context['grado_actual'] = matricula_actual.grado_año_lectivo.grado
        
        return context


class AsistenciaUpdateView(RoleRequiredMixin, UpdateView):
    """Editar registro de asistencia"""
    template_name = 'rector/seguimiento/asistencia/asistencia_form.html'
    allowed_roles = ['Rector']
    model = Asistencia
    form_class = AsistenciaForm
    success_url = reverse_lazy('rector:asistencia_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Asistencia actualizada exitosamente.')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Asistencia'
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Establecer el estudiante como inicial si viene de la lista
        if 'estudiante' in self.request.GET:
            estudiante_id = self.request.GET.get('estudiante')
            if estudiante_id:
                kwargs['initial'] = {'estudiante': estudiante_id}
        return kwargs

class AsistenciaBulkView(RoleRequiredMixin, FormView):
    """Registro masivo de asistencia por grado"""
    template_name = 'rector/seguimiento/asistencia/asistencia_bulk.html'
    allowed_roles = ['Rector']
    form_class = AsistenciaBulkForm
    
    def get_success_url(self):
        return reverse('rector:asistencia_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Verificar si hay parámetros para cargar estudiantes
        periodo_id = self.request.GET.get('periodo')
        grado_id = self.request.GET.get('grado')
        fecha = self.request.GET.get('fecha')
        
        if periodo_id and grado_id and fecha:
            try:
                periodo = PeriodoAcademico.objects.get(id=periodo_id)
                grado = GradoAñoLectivo.objects.get(id=grado_id)
                fecha_obj = date.fromisoformat(fecha)
                
                # Obtener estudiantes del grado
                matriculas = Matricula.objects.filter(
                    grado_año_lectivo=grado,
                    estado='ACT'
                ).select_related('estudiante__usuario')
                
                # Obtener asistencias existentes para esa fecha
                asistencias_existentes = Asistencia.objects.filter(
                    estudiante__in=[m.estudiante for m in matriculas],
                    fecha=fecha_obj,
                    periodo_academico=periodo
                ).values('estudiante_id', 'estado', 'justificacion')
                
                # Crear diccionario de asistencias existentes
                asistencias_dict = {
                    a['estudiante_id']: {
                        'estado': a['estado'],
                        'justificacion': a['justificacion']
                    } for a in asistencias_existentes
                }
                
                # Preparar datos para el formulario
                estudiantes_data = []
                for matricula in matriculas:
                    estudiante = matricula.estudiante
                    asistencia_existente = asistencias_dict.get(estudiante.id)
                    
                    estudiantes_data.append({
                        'id': estudiante.id,
                        'nombre': estudiante.usuario.get_full_name(),
                        'documento': estudiante.usuario.numero_documento,
                        'estado_actual': asistencia_existente['estado'] if asistencia_existente else 'A',
                        'justificacion_actual': asistencia_existente['justificacion'] if asistencia_existente else ''
                    })
                
                context['estudiantes'] = estudiantes_data
                context['periodo'] = periodo
                context['grado'] = grado
                context['fecha'] = fecha_obj
                
            except (ValueError, PeriodoAcademico.DoesNotExist, GradoAñoLectivo.DoesNotExist):
                messages.error(self.request, 'Parámetros inválidos.')
        
        return context
    
    def post(self, request, *args, **kwargs):
        form = self.get_form()
        
        if form.is_valid():
            # Procesar el formulario de selección de grado/fecha
            periodo = form.cleaned_data['periodo_academico']
            grado = form.cleaned_data['grado_año_lectivo']
            fecha = form.cleaned_data['fecha']
            
            # Redirigir a la misma vista con parámetros
            return redirect(reverse('rector:asistencia_bulk') + 
                          f'?periodo={periodo.id}&grado={grado.id}&fecha={fecha}')
        
        return self.form_invalid(form)

class AsistenciaProcesarBulkView(RoleRequiredMixin, View):
    """Procesar el registro masivo de asistencia"""
    allowed_roles = ['Rector']
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            periodo_id = data.get('periodo_id')
            grado_id = data.get('grado_id')
            fecha_str = data.get('fecha')
            asistencias = data.get('asistencias', [])
            
            periodo = PeriodoAcademico.objects.get(id=periodo_id)
            fecha = date.fromisoformat(fecha_str)
            
            # Procesar cada asistencia
            for asistencia_data in asistencias:
                estudiante_id = asistencia_data.get('estudiante_id')
                estado = asistencia_data.get('estado')
                justificacion = asistencia_data.get('justificacion', '')
                
                # Buscar o crear asistencia
                asistencia, created = Asistencia.objects.update_or_create(
                    estudiante_id=estudiante_id,
                    periodo_academico=periodo,
                    fecha=fecha,
                    defaults={
                        'estado': estado,
                        'justificacion': justificacion
                    }
                )
            
            return JsonResponse({
                'success': True,
                'message': f'{len(asistencias)} asistencias registradas exitosamente.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class AsistenciaPorGradoView(RoleRequiredMixin, TemplateView):
    """Vista de asistencia por grado específico"""
    template_name = 'rector/seguimiento/asistencia/asistencia_grado.html'
    allowed_roles = ['Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        grado_id = self.kwargs.get('grado_id')
        periodo_id = self.request.GET.get('periodo')
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        
        try:
            grado = GradoAñoLectivo.objects.get(id=grado_id)
            context['grado'] = grado
            
            # Obtener estudiantes del grado
            matriculas = Matricula.objects.filter(
                grado_año_lectivo=grado,
                estado='ACT'
            ).select_related('estudiante__usuario')
            context['estudiantes'] = [m.estudiante for m in matriculas]
            
            # Determinar rango de fechas
            hoy = date.today()
            if not fecha_inicio:
                # Primer día del mes actual
                fecha_inicio = date(hoy.year, hoy.month, 1)
            else:
                fecha_inicio = date.fromisoformat(fecha_inicio)
            
            if not fecha_fin:
                fecha_fin = hoy
            else:
                fecha_fin = date.fromisoformat(fecha_fin)
            
            context['fecha_inicio'] = fecha_inicio
            context['fecha_fin'] = fecha_fin
            
            # Generar lista de días lectivos
            dias_lectivos = []
            current_date = fecha_inicio
            while current_date <= fecha_fin:
                # Excluir fines de semana
                if current_date.weekday() < 5:  # 0-4 = Lunes a Viernes
                    dias_lectivos.append(current_date)
                current_date += timedelta(days=1)
            
            context['dias_lectivos'] = dias_lectivos
            
            # Obtener asistencias para cada estudiante
            asistencias_data = {}
            for estudiante in context['estudiantes']:
                asistencias = Asistencia.objects.filter(
                    estudiante=estudiante,
                    fecha__gte=fecha_inicio,
                    fecha__lte=fecha_fin
                ).values('fecha', 'estado', 'justificacion')
                
                # Crear diccionario por fecha
                asistencias_dict = {}
                for a in asistencias:
                    asistencias_dict[a['fecha'].isoformat()] = {
                        'estado': a['estado'],
                        'justificacion': a['justificacion']
                    }
                
                # Calcular estadísticas
                total_dias = len(dias_lectivos)
                asistencias_count = sum(1 for d in dias_lectivos 
                                      if asistencias_dict.get(d.isoformat(), {}).get('estado') == 'A')
                faltas_count = sum(1 for d in dias_lectivos 
                                 if asistencias_dict.get(d.isoformat(), {}).get('estado') == 'F')
                justificadas_count = sum(1 for d in dias_lectivos 
                                       if asistencias_dict.get(d.isoformat(), {}).get('estado') == 'J')
                
                asistencias_data[estudiante.id] = {
                    'asistencias': asistencias_dict,
                    'estadisticas': {
                        'total_dias': total_dias,
                        'asistencias': asistencias_count,
                        'faltas': faltas_count,
                        'justificadas': justificadas_count,
                        'porcentaje_asistencia': (asistencias_count / total_dias * 100) if total_dias > 0 else 0
                    }
                }
            
            context['asistencias_data'] = asistencias_data
            
        except GradoAñoLectivo.DoesNotExist:
            messages.error(self.request, 'Grado no encontrado.')
        
        return context

# ==================== INCONSISTENCIAS ====================

class InconsistenciaListView(RoleRequiredMixin, ListView):
    """Lista de inconsistencias"""
    template_name = 'rector/seguimiento/inconsistencia/inconsistencia_list.html'
    allowed_roles = ['Rector']
    model = Inconsistencia
    context_object_name = 'inconsistencias'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Inconsistencia.objects.select_related(
            'estudiante__usuario'
        ).order_by('-fecha', '-created_at')
        
        # Aplicar filtros
        filtro_form = InconsistenciaFilterForm(self.request.GET)
        if filtro_form.is_valid():
            data = filtro_form.cleaned_data
            
            if data.get('estudiante'):
                queryset = queryset.filter(
                    Q(estudiante__usuario__nombres__icontains=data['estudiante']) |
                    Q(estudiante__usuario__apellidos__icontains=data['estudiante']) |
                    Q(estudiante__usuario__numero_documento__icontains=data['estudiante'])
                )
            
            if data.get('tipo'):
                queryset = queryset.filter(tipo__icontains=data['tipo'])
            
            if data.get('fecha_inicio'):
                queryset = queryset.filter(fecha__gte=data['fecha_inicio'])
            if data.get('fecha_fin'):
                queryset = queryset.filter(fecha__lte=data['fecha_fin'])
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtro_form'] = InconsistenciaFilterForm(self.request.GET)
        
        # Estadísticas
        queryset = self.get_queryset()
        context['total_registros'] = queryset.count()
        
        # Tipos más comunes
        tipos_comunes = queryset.values('tipo').annotate(
            total=Count('id')
        ).order_by('-total')[:10]
        context['tipos_comunes'] = tipos_comunes
        
        # Estudiantes con más inconsistencias
        estudiantes_top = queryset.values(
            'estudiante__usuario__nombres',
            'estudiante__usuario__apellidos'
        ).annotate(
            total=Count('id')
        ).order_by('-total')[:10]
        context['estudiantes_top'] = estudiantes_top
        
        return context

class InconsistenciaCreateView(RoleRequiredMixin, CreateView):
    """Crear nueva inconsistencia"""
    template_name = 'rector/seguimiento/inconsistencia/inconsistencia_form.html'
    allowed_roles = ['Rector']
    model = Inconsistencia
    form_class = InconsistenciaForm
    success_url = reverse_lazy('rector:inconsistencia_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Inconsistencia registrada exitosamente.')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Registrar Inconsistencia'
        return context

class InconsistenciaUpdateView(RoleRequiredMixin, UpdateView):
    """Editar inconsistencia"""
    template_name = 'rector/seguimiento/inconsistencia/inconsistencia_form.html'
    allowed_roles = ['Rector']
    model = Inconsistencia
    form_class = InconsistenciaForm
    success_url = reverse_lazy('rector:inconsistencia_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Inconsistencia actualizada exitosamente.')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Inconsistencia'
        return context

class InconsistenciaDetailView(RoleRequiredMixin, DetailView):
    """Detalle de inconsistencia"""
    template_name = 'rector/seguimiento/inconsistencia/inconsistencia_detail.html'
    allowed_roles = ['Rector']
    model = Inconsistencia

class InconsistenciaDeleteView(RoleRequiredMixin, DeleteView):
    """Eliminar inconsistencia"""
    template_name = 'rector/seguimiento/inconsistencia/inconsistencia_confirm_delete.html'
    allowed_roles = ['Rector']
    model = Inconsistencia
    success_url = reverse_lazy('rector:inconsistencia_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Inconsistencia eliminada exitosamente.')
        return super().delete(request, *args, **kwargs)

# ==================== CALIFICACIONES ====================

class CalificacionListView(RoleRequiredMixin, ListView):
    """Lista de calificaciones"""
    template_name = 'rector/seguimiento/calificacion/calificacion_list.html'
    allowed_roles = ['Rector']
    model = Nota
    context_object_name = 'calificaciones'
    paginate_by = 30
    
    def get_queryset(self):
        queryset = Nota.objects.select_related(
            'estudiante__usuario',
            'asignatura_grado_año_lectivo__asignatura',
            'asignatura_grado_año_lectivo__grado_año_lectivo__grado',
            'periodo_academico__año_lectivo',
            'periodo_academico__periodo'
        ).order_by('-periodo_academico__fecha_inicio', 'asignatura_grado_año_lectivo__asignatura__nombre')
        
        # Aplicar filtros
        filtro_form = NotaFilterForm(self.request.GET)
        if filtro_form.is_valid():
            data = filtro_form.cleaned_data
            
            if data.get('estudiante'):
                queryset = queryset.filter(
                    Q(estudiante__usuario__nombres__icontains=data['estudiante']) |
                    Q(estudiante__usuario__apellidos__icontains=data['estudiante']) |
                    Q(estudiante__usuario__numero_documento__icontains=data['estudiante'])
                )
            
            if data.get('periodo_academico'):
                queryset = queryset.filter(periodo_academico=data['periodo_academico'])
            
            if data.get('asignatura'):
                queryset = queryset.filter(
                    asignatura_grado_año_lectivo__asignatura=data['asignatura']
                )
            
            if data.get('grado'):
                queryset = queryset.filter(
                    asignatura_grado_año_lectivo__grado_año_lectivo=data['grado']
                )
            
            if data.get('calificacion_min') is not None:
                queryset = queryset.filter(calificacion__gte=data['calificacion_min'])
            
            if data.get('calificacion_max') is not None:
                queryset = queryset.filter(calificacion__lte=data['calificacion_max'])
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtro_form'] = NotaFilterForm(self.request.GET)
        
        # Estadísticas
        queryset = self.get_queryset()
        context['total_registros'] = queryset.count()
        
        if queryset.count() > 0:
            context['promedio_general'] = queryset.aggregate(
                promedio=Avg('calificacion')
            )['promedio']
            
            context['maxima_calificacion'] = queryset.aggregate(
                maximo=Max('calificacion')
            )['maximo']
            
            context['minima_calificacion'] = queryset.aggregate(
                minimo=Min('calificacion')
            )['minimo']
            
            # Mejores calificaciones
            context['mejores_calificaciones'] = queryset.order_by('-calificacion')[:10]
            
            # Distribución por rangos
            rangos = [
                {'min': 0, 'max': 2.9, 'label': 'Bajo'},
                {'min': 3, 'max': 3.9, 'label': 'Básico'},
                {'min': 4, 'max': 4.5, 'label': 'Alto'},
                {'min': 4.6, 'max': 5, 'label': 'Superior'},
            ]
            
            distribucion = []
            for rango in rangos:
                count = queryset.filter(
                    calificacion__gte=rango['min'],
                    calificacion__lte=rango['max']
                ).count()
                porcentaje = (count / queryset.count() * 100) if queryset.count() > 0 else 0
                
                distribucion.append({
                    'label': rango['label'],
                    'count': count,
                    'porcentaje': round(porcentaje, 1)
                })
            
            context['distribucion_rangos'] = distribucion
        
        return context

class CalificacionCreateView(RoleRequiredMixin, CreateView):
    """Crear nueva calificación"""
    template_name = 'rector/seguimiento/calificacion/calificacion_form.html'
    allowed_roles = ['Rector']
    model = Nota
    form_class = NotaForm
    success_url = reverse_lazy('rector:calificacion_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Calificación registrada exitosamente.')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Registrar Calificación'
        
        # Si viene un estudiante específico en la URL
        estudiante_id = self.request.GET.get('estudiante')
        if estudiante_id:
            try:
                estudiante = Estudiante.objects.get(id=estudiante_id)
                context['estudiante_seleccionado'] = estudiante
            except Estudiante.DoesNotExist:
                pass
        
        return context

class CalificacionBulkView(RoleRequiredMixin, FormView):
    """Registro masivo de calificaciones por asignatura"""
    template_name = 'rector/seguimiento/calificacion/calificacion_bulk.html'
    allowed_roles = ['Rector']
    form_class = NotaBulkForm
    
    def get_success_url(self):
        return reverse('rector:calificacion_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Verificar si hay parámetros para cargar estudiantes
        periodo_id = self.request.GET.get('periodo')
        asignatura_id = self.request.GET.get('asignatura')
        
        if periodo_id and asignatura_id:
            try:
                periodo = PeriodoAcademico.objects.get(id=periodo_id)
                asignatura_grado = AsignaturaGradoAñoLectivo.objects.get(id=asignatura_id)
                
                # Obtener estudiantes del grado de la asignatura
                grado = asignatura_grado.grado_año_lectivo
                matriculas = Matricula.objects.filter(
                    grado_año_lectivo=grado,
                    estado='ACT'
                ).select_related('estudiante__usuario')
                
                # Obtener calificaciones existentes
                calificaciones_existentes = Nota.objects.filter(
                    estudiante__in=[m.estudiante for m in matriculas],
                    periodo_academico=periodo,
                    asignatura_grado_año_lectivo=asignatura_grado
                ).values('estudiante_id', 'calificacion', 'observaciones')
                
                # Crear diccionario de calificaciones existentes
                calificaciones_dict = {
                    c['estudiante_id']: {
                        'calificacion': c['calificacion'],
                        'observaciones': c['observaciones']
                    } for c in calificaciones_existentes
                }
                
                # Preparar datos para el formulario
                estudiantes_data = []
                for matricula in matriculas:
                    estudiante = matricula.estudiante
                    calificacion_existente = calificaciones_dict.get(estudiante.id)
                    
                    estudiantes_data.append({
                        'id': estudiante.id,
                        'nombre': estudiante.usuario.get_full_name(),
                        'documento': estudiante.usuario.numero_documento,
                        'calificacion_actual': calificacion_existente['calificacion'] if calificacion_existente else None,
                        'observaciones_actual': calificacion_existente['observaciones'] if calificacion_existente else ''
                    })
                
                context['estudiantes'] = estudiantes_data
                context['periodo'] = periodo
                context['asignatura'] = asignatura_grado
                
            except (ValueError, PeriodoAcademico.DoesNotExist, 
                    AsignaturaGradoAñoLectivo.DoesNotExist):
                messages.error(self.request, 'Parámetros inválidos.')
        
        return context
    
    def post(self, request, *args, **kwargs):
        form = self.get_form()
        
        if form.is_valid():
            # Procesar el formulario de selección
            periodo = form.cleaned_data['periodo_academico']
            asignatura = form.cleaned_data['asignatura_grado_año_lectivo']
            
            # Redirigir a la misma vista con parámetros
            return redirect(reverse('rector:calificacion_bulk') + 
                          f'?periodo={periodo.id}&asignatura={asignatura.id}')
        
        return self.form_invalid(form)

class CalificacionDetailView(RoleRequiredMixin, DetailView):
    """Detalle de calificación individual"""
    template_name = 'rector/seguimiento/calificacion/calificacion_detail.html'
    allowed_roles = ['Rector']
    model = Nota
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        nota = self.object
        
        # Obtener historial de calificaciones del estudiante en esta asignatura
        historial = Nota.objects.filter(
            estudiante=nota.estudiante,
            asignatura_grado_año_lectivo__asignatura=nota.asignatura_grado_año_lectivo.asignatura
        ).exclude(id=nota.id).select_related(
            'periodo_academico__año_lectivo',
            'periodo_academico__periodo'
        ).order_by('-periodo_academico__fecha_inicio')
        
        context['historial_calificaciones'] = historial
        
        # Calcular promedio del estudiante en esta asignatura
        if historial.exists():
            promedio_asignatura = historial.aggregate(promedio=Avg('calificacion'))
            context['promedio_asignatura'] = promedio_asignatura['promedio'] or 0
        
        # Obtener información de matrícula actual
        matricula_actual = nota.estudiante.matricula_actual
        if matricula_actual:
            context['matricula_actual'] = matricula_actual
        
        return context

class CalificacionUpdateView(RoleRequiredMixin, UpdateView):
    """Editar calificación individual"""
    template_name = 'rector/seguimiento/calificacion/calificacion_form.html'
    allowed_roles = ['Rector']
    model = Nota
    form_class = NotaForm
    success_url = reverse_lazy('rector:calificacion_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Calificación actualizada exitosamente.')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Calificación'
        return context

class CalificacionDeleteView(RoleRequiredMixin, DeleteView):
    """Eliminar calificación individual"""
    template_name = 'rector/seguimiento/calificacion/calificacion_confirm_delete.html'
    allowed_roles = ['Rector']
    model = Nota
    success_url = reverse_lazy('rector:calificacion_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Calificación eliminada exitosamente.')
        return super().delete(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estudiante'] = self.object.estudiante
        context['matricula_actual'] = self.object.estudiante.matricula_actual
        return context

class CalificacionProcesarBulkView(RoleRequiredMixin, View):
    """Procesar el registro masivo de calificaciones"""
    allowed_roles = ['Rector']
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            periodo_id = data.get('periodo_id')
            asignatura_id = data.get('asignatura_id')
            calificaciones = data.get('calificaciones', [])
            
            periodo = PeriodoAcademico.objects.get(id=periodo_id)
            asignatura_grado = AsignaturaGradoAñoLectivo.objects.get(id=asignatura_id)
            
            # Procesar cada calificación
            for calificacion_data in calificaciones:
                estudiante_id = calificacion_data.get('estudiante_id')
                calificacion = calificacion_data.get('calificacion')
                observaciones = calificacion_data.get('observaciones', '')
                
                # Validar calificación
                if calificacion is None or calificacion == '':
                    continue
                
                # Buscar o crear calificación
                nota, created = Nota.objects.update_or_create(
                    estudiante_id=estudiante_id,
                    periodo_academico=periodo,
                    asignatura_grado_año_lectivo=asignatura_grado,
                    defaults={
                        'calificacion': calificacion,
                        'observaciones': observaciones
                    }
                )
            
            return JsonResponse({
                'success': True,
                'message': f'{len(calificaciones)} calificaciones registradas exitosamente.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class CalificacionEstudianteReporteView(RoleRequiredMixin, DetailView):
    """Reporte de calificaciones por estudiante"""
    template_name = 'rector/seguimiento/calificacion/calificacion_estudiante_reporte.html'
    allowed_roles = ['Rector']
    model = Estudiante
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante = self.object
        
        # Obtener todas las calificaciones del estudiante
        calificaciones = Nota.objects.filter(
            estudiante=estudiante
        ).select_related(
            'asignatura_grado_año_lectivo__asignatura',
            'periodo_academico__año_lectivo',
            'periodo_academico__periodo'
        ).order_by(
            '-periodo_academico__año_lectivo__anho',
            'periodo_academico__periodo__nombre'
        )
        
        # Organizar por año y periodo
        calificaciones_organizadas = {}
        periodos_por_año = {}  # Para almacenar información de periodos
        
        for calificacion in calificaciones:
            año = calificacion.periodo_academico.año_lectivo.anho
            periodo = calificacion.periodo_academico.periodo.nombre
            
            if año not in calificaciones_organizadas:
                calificaciones_organizadas[año] = {}
                periodos_por_año[año] = []
            
            if periodo not in calificaciones_organizadas[año]:
                calificaciones_organizadas[año][periodo] = {
                    'items': [],
                    'total': 0,
                    'suma': 0.0,
                    'promedio': 0.0
                }
                if periodo not in periodos_por_año[año]:
                    periodos_por_año[año].append(periodo)
            
            # Añadir calificación a la lista
            calif_data = {
                'id': calificacion.id,
                'asignatura': calificacion.asignatura_grado_año_lectivo.asignatura.nombre,
                'calificacion': float(calificacion.calificacion),
                'observaciones': calificacion.observaciones or '',
                'periodo_id': calificacion.periodo_academico.id,
                'asignatura_id': calificacion.asignatura_grado_año_lectivo.asignatura.id,
                'nivel': self.get_nivel_desempenho(float(calificacion.calificacion))
            }
            
            calificaciones_organizadas[año][periodo]['items'].append(calif_data)
        
        # Calcular estadísticas para cada periodo
        for año in calificaciones_organizadas:
            for periodo in calificaciones_organizadas[año]:
                lista = calificaciones_organizadas[año][periodo]['items']
                total = len(lista)
                
                if total > 0:
                    suma = sum(item['calificacion'] for item in lista)
                    promedio = round(suma / total, 1)
                    
                    calificaciones_organizadas[año][periodo]['total'] = total
                    calificaciones_organizadas[año][periodo]['suma'] = round(suma, 1)
                    calificaciones_organizadas[año][periodo]['promedio'] = promedio
        
        context['calificaciones_organizadas'] = calificaciones_organizadas
        
        # Calcular promedios generales
        if calificaciones.exists():
            # Promedio general
            promedio_general = calificaciones.aggregate(
                promedio=Avg('calificacion')
            )['promedio']
            context['promedio_general'] = round(promedio_general, 2) if promedio_general else 0
            
            # Promedio por año
            promedios_año = {}
            for año in calificaciones_organizadas:
                total_año = 0
                suma_año = 0.0
                
                for periodo in calificaciones_organizadas[año]:
                    total_año += calificaciones_organizadas[año][periodo]['total']
                    # Sumar todas las calificaciones del periodo
                    for item in calificaciones_organizadas[año][periodo]['items']:
                        suma_año += item['calificacion']
                
                promedio_año = round(suma_año / total_año, 2) if total_año > 0 else 0
                promedios_año[año] = {
                    'promedio': promedio_año,
                    'total': total_año,
                    'periodos': len(calificaciones_organizadas[año])
                }
            
            context['promedios_año'] = promedios_año
            
            # Promedio por asignatura
            promedios_asignatura = {}
            # Obtener asignaturas únicas del estudiante
            asignaturas_ids = calificaciones.values_list(
                'asignatura_grado_año_lectivo__asignatura__id',
                'asignatura_grado_año_lectivo__asignatura__nombre'
            ).distinct()
            
            for asignatura_id, asignatura_nombre in asignaturas_ids:
                calificaciones_asignatura = calificaciones.filter(
                    asignatura_grado_año_lectivo__asignatura__id=asignatura_id
                )
                promedio = calificaciones_asignatura.aggregate(
                    promedio=Avg('calificacion')
                )['promedio']
                
                if promedio:
                    promedios_asignatura[asignatura_nombre] = {
                        'promedio': round(promedio, 2),
                        'total': calificaciones_asignatura.count()
                    }
            
            context['promedios_asignatura'] = promedios_asignatura
            
            # Contar por niveles de desempeño
            niveles = {
                'superior': calificaciones.filter(calificacion__gte=4.6).count(),
                'alto': calificaciones.filter(calificacion__gte=4.0, calificacion__lt=4.6).count(),
                'basico': calificaciones.filter(calificacion__gte=3.0, calificacion__lt=4.0).count(),
                'bajo': calificaciones.filter(calificacion__lt=3.0).count()
            }
            context['niveles_desempeno'] = niveles
        
        # Obtener información de matrícula actual
        matricula_actual = estudiante.matricula_actual
        if matricula_actual:
            context['matricula_actual'] = matricula_actual
            context['grado_actual'] = matricula_actual.grado_año_lectivo.grado
        
        # Historial de matrículas
        context['matriculas_anteriores'] = estudiante.matriculas_anteriores()
        
        # Total de años con calificaciones
        context['total_años'] = len(calificaciones_organizadas)
        
        return context
    
    def get_nivel_desempenho(self, calificacion):
        """Determinar nivel de desempeño según la calificación"""
        if calificacion >= 4.6:
            return {'label': 'Superior', 'color': 'success', 'icon': 'bi-star-fill'}
        elif calificacion >= 4.0:
            return {'label': 'Alto', 'color': 'info', 'icon': 'bi-star-half'}
        elif calificacion >= 3.0:
            return {'label': 'Básico', 'color': 'warning', 'icon': 'bi-check-circle'}
        else:
            return {'label': 'Bajo', 'color': 'danger', 'icon': 'bi-exclamation-triangle'}

class CalificacionDeleteView(RoleRequiredMixin, DeleteView):
    """Eliminar calificación"""
    template_name = 'rector/seguimiento/calificacion/calificacion_confirm_delete.html'
    allowed_roles = ['Rector']
    model = Nota
    success_url = reverse_lazy('rector:calificacion_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Calificación eliminada exitosamente.')
        return super().delete(request, *args, **kwargs)