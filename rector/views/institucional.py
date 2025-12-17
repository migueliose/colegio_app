# rector/views.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.views.generic.edit import FormView
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone
from datetime import timedelta, datetime
import json
from datetime import date

# Mixins y modelos
from gestioncolegio.mixins import RoleRequiredMixin
from estudiantes.models import Matricula
from usuarios.models import Docente
from gestioncolegio.models import Colegio, Sede, AñoLectivo, ConfiguracionGeneral
from matricula.models import PeriodoAcademico, AsignaturaGradoAñoLectivo, GradoAñoLectivo
from ..forms.formularios_academicco import *
from ..forms.formularios_institucional import *

# ==================== DASHBOARD INSTITUCIONAL ====================

class InstitucionalDashboardView(RoleRequiredMixin, TemplateView):
    """Dashboard principal del módulo institucional"""
    template_name = 'rector/institucional/dashboard.html'
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
        
        # Estadísticas generales
        if año_actual:
            # Total estudiantes matriculados
            total_estudiantes = Matricula.objects.filter(
                año_lectivo=año_actual,
                estado='ACT'
            ).count()
            context['total_estudiantes'] = total_estudiantes
            
            # Total docentes activos
            total_docentes = Docente.objects.filter(estado=True).count()
            context['total_docentes'] = total_docentes
            
            # Sedes activas
            sedes_activas = Sede.objects.filter(estado=True).count()
            context['sedes_activas'] = sedes_activas
            
            # Grados activos en el año actual
            grados_activos = GradoAñoLectivo.objects.filter(
                año_lectivo=año_actual,
                estado=True
            ).count()
            context['grados_activos'] = grados_activos
            
            # Periodos académicos configurados
            periodos_configurados = PeriodoAcademico.objects.filter(
                año_lectivo=año_actual
            ).count()
            context['periodos_configurados'] = periodos_configurados
        
        # Lista de años lectivos
        años_lectivos = AñoLectivo.objects.all().order_by('-anho')
        context['años_lectivos'] = años_lectivos
        
        # Próximos eventos (matrículas, inicio de periodos, etc.)
        hoy = date.today()
        if año_actual:
            periodos_proximos = PeriodoAcademico.objects.filter(
                año_lectivo=año_actual,
                fecha_inicio__gte=hoy
            ).order_by('fecha_inicio')[:5]
            context['periodos_proximos'] = periodos_proximos
        
        # Sedes con información básica
        sedes = Sede.objects.filter(estado=True).select_related('colegio', 'director')
        context['sedes'] = sedes
        
        # Alertas del sistema
        alertas = []
        
        # Verificar si hay año lectivo configurado
        if not año_actual:
            alertas.append({
                'tipo': 'warning',
                'mensaje': 'No hay año lectivo configurado como actual. Configúrelo en Configuración General.'
            })
        
        # Verificar si hay periodos académicos configurados para el año actual
        if año_actual and PeriodoAcademico.objects.filter(año_lectivo=año_actual).count() == 0:
            alertas.append({
                'tipo': 'warning',
                'mensaje': f'No hay periodos académicos configurados para el año {año_actual.anho}.'
            })
        
        context['alertas'] = alertas
        
        return context

# ==================== GESTIÓN DE AÑOS LECTIVOS ====================

class AñoLectivoListView(RoleRequiredMixin, ListView):
    """Lista de años lectivos con filtros y estadísticas"""
    template_name = 'rector/institucional/año_lectivo/año_lectivo_list.html'
    allowed_roles = ['Rector']
    model = AñoLectivo
    context_object_name = 'años_lectivos'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = AñoLectivo.objects.select_related('colegio', 'sede')
        
        # Filtros
        sede_id = self.request.GET.get('sede')
        estado_filter = self.request.GET.get('estado')
        search = self.request.GET.get('search')
        
        # Filtrar por sede
        if sede_id and sede_id.isdigit():
            queryset = queryset.filter(sede_id=int(sede_id))
        
        # Filtrar por estado
        if estado_filter:
            if estado_filter == '1':
                queryset = queryset.filter(estado=True)
            elif estado_filter == '0':
                queryset = queryset.filter(estado=False)
        
        # Búsqueda por año
        if search:
            queryset = queryset.filter(anho__icontains=search)
        
        # Ordenamiento por defecto: años más recientes primero
        return queryset.order_by('-anho')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener configuraciones para saber el año actual
        config = ConfiguracionGeneral.objects.first()
        context['año_lectivo_actual'] = config.año_lectivo_actual if config else None
        
        # Obtener todas las sedes para el filtro
        context['sedes'] = Sede.objects.filter(estado=True).order_by('nombre')
        
        # Estadísticas generales
        context['total_años'] = AñoLectivo.objects.count()
        context['años_activos'] = AñoLectivo.objects.filter(estado=True).count()
        
        # Total de estudiantes en todos los años (solo matrículas activas)
        total_estudiantes = 0
        for año in context['años_lectivos']:
            total_estudiantes += Matricula.objects.filter(
                año_lectivo=año,
                estado='ACT'
            ).count()
        context['total_estudiantes_general'] = total_estudiantes
        
        # Estadísticas detalladas por año lectivo
        for año in context['años_lectivos']:
            # Estudiantes matriculados (activos)
            año.total_estudiantes = Matricula.objects.filter(
                año_lectivo=año,
                estado='ACT'
            ).count()
            
            # Estudiantes por estado de matrícula
            año.estudiantes_pre = Matricula.objects.filter(
                año_lectivo=año,
                estado='PRE'
            ).count()
            año.estudiantes_pen = Matricula.objects.filter(
                año_lectivo=año,
                estado='PEN'
            ).count()
            año.estudiantes_act = Matricula.objects.filter(
                año_lectivo=año,
                estado='ACT'
            ).count()
            año.estudiantes_ina = Matricula.objects.filter(
                año_lectivo=año,
                estado='INA'
            ).count()
            año.estudiantes_ret = Matricula.objects.filter(
                año_lectivo=año,
                estado='RET'
            ).count()
            
            # Docentes asignados
            año.total_docentes = DocenteSede.objects.filter(
                año_lectivo=año,
                estado=True
            ).values('docente').distinct().count()
            
            # Grados activos
            año.total_grados = GradoAñoLectivo.objects.filter(
                año_lectivo=año,
                estado=True
            ).count()
            
            # Periodos configurados
            año.periodos_configurados = PeriodoAcademico.objects.filter(
                año_lectivo=año
            ).count()
            
            # Periodos activos
            año.periodos_activos = PeriodoAcademico.objects.filter(
                año_lectivo=año,
                estado=True
            ).count()
            
            # Asignaturas configuradas
            año.asignaturas_configuradas = AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo__año_lectivo=año
            ).count()
            
            # Asignaturas con docente
            año.asignaturas_con_docente = AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo__año_lectivo=año,
                docente__isnull=False
            ).count()
            
            # Calcular porcentaje de asignación docente
            if año.asignaturas_configuradas > 0:
                año.porcentaje_asignacion = (año.asignaturas_con_docente / año.asignaturas_configuradas) * 100
            else:
                año.porcentaje_asignacion = 0
            
            # Indicador de completitud
            año.completitud = 0
            if año.fecha_inicio and año.fecha_fin:
                año.completitud += 25
            if año.total_grados > 0:
                año.completitud += 25
            if año.periodos_configurados > 0:
                año.completitud += 25
            if año.porcentaje_asignacion > 50:
                año.completitud += 25
        
        # Año más reciente por sede
        años_recientes = []
        for sede in context['sedes']:
            año_reciente = AñoLectivo.objects.filter(
                sede=sede
            ).order_by('-anho').first()
            if año_reciente:
                años_recientes.append({
                    'sede': sede.nombre,
                    'año': año_reciente.anho,
                    'estado': año_reciente.estado
                })
        context['años_recientes'] = años_recientes
        
        # Parámetros de filtro para mantener en la paginación
        context['filtro_sede'] = self.request.GET.get('sede', '')
        context['filtro_estado'] = self.request.GET.get('estado', '')
        context['filtro_search'] = self.request.GET.get('search', '')
        
        return context
    
class AñoLectivoCreateView(RoleRequiredMixin, CreateView):
    """Crear nuevo año lectivo"""
    template_name = 'rector/institucional/año_lectivo/año_lectivo_form.html'
    allowed_roles = ['Rector']
    model = AñoLectivo
    fields = ['colegio', 'sede', 'anho', 'fecha_inicio', 'fecha_fin', 'estado']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear Nuevo Año Lectivo'
        context['colegios'] = Colegio.objects.filter(estado=True)
        context['sedes'] = Sede.objects.filter(estado=True)
        return context
    
    def form_valid(self, form):
        # Verificar que no exista año lectivo duplicado
        if AñoLectivo.objects.filter(
            colegio=form.cleaned_data['colegio'],
            sede=form.cleaned_data['sede'],
            anho=form.cleaned_data['anho']
        ).exists():
            messages.error(self.request, 'Ya existe un año lectivo con estos datos')
            return self.render_to_response(self.get_context_data(form=form))
        
        response = super().form_valid(form)
        messages.success(self.request, 'Año lectivo creado exitosamente')
        return response
    
    def get_success_url(self):
        return reverse('rector:año_lectivo_list')

class AñoLectivoUpdateView(RoleRequiredMixin, UpdateView):
    """Editar año lectivo"""
    template_name = 'rector/institucional/año_lectivo/año_lectivo_form.html'
    allowed_roles = ['Rector']
    model = AñoLectivo
    fields = ['colegio', 'sede', 'anho', 'fecha_inicio', 'fecha_fin', 'estado']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Año Lectivo'
        context['colegios'] = Colegio.objects.filter(estado=True)
        context['sedes'] = Sede.objects.filter(estado=True)
        return context
    
    def form_valid(self, form):
        # Verificar que no exista año lectivo duplicado (excluyendo el actual)
        if AñoLectivo.objects.filter(
            colegio=form.cleaned_data['colegio'],
            sede=form.cleaned_data['sede'],
            anho=form.cleaned_data['anho']
        ).exclude(pk=self.object.pk).exists():
            messages.error(self.request, 'Ya existe otro año lectivo con estos datos')
            return self.render_to_response(self.get_context_data(form=form))
        
        response = super().form_valid(form)
        messages.success(self.request, 'Año lectivo actualizado exitosamente')
        return response
    
    def get_success_url(self):
        return reverse('rector:año_lectivo_list')

class AñoLectivoDeleteView(RoleRequiredMixin, DeleteView):
    """Eliminar año lectivo con validaciones exhaustivas"""
    template_name = 'rector/institucional/año_lectivo/año_lectivo_confirm_delete.html'
    allowed_roles = ['Rector']
    model = AñoLectivo
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        año = self.object
        
        # Obtener todas las dependencias con detalles
        dependencias = self._obtener_dependencias_detalladas(año)
        context.update(dependencias)
        
        # Determinar si se puede eliminar
        context['puede_eliminar'] = self._puede_eliminar_año(año)
        
        # Información del año lectivo para mostrar
        context['año_info'] = {
            'nombre_completo': f"{año.anho} - {año.sede.nombre}",
            'sede': año.sede.nombre,
            'colegio': año.colegio.nombre,
            'fecha_inicio': año.fecha_inicio.strftime('%d/%m/%Y') if año.fecha_inicio else 'No definida',
            'fecha_fin': año.fecha_fin.strftime('%d/%m/%Y') if año.fecha_fin else 'No definida',
            'estado': 'Activo' if año.estado else 'Inactivo',
            'es_actual': self._es_año_lectivo_actual(año)
        }
        
        return context
    
    def _obtener_dependencias_detalladas(self, año):
        """Obtener todas las dependencias del año lectivo con detalles"""
        dependencias = {
            # Matrículas
            'tiene_matriculas': False,
            'matriculas_count': 0,
            'matriculas_info': [],
            
            # Periodos académicos
            'tiene_periodos': False,
            'periodos_count': 0,
            'periodos_info': [],
            
            # Grados
            'tiene_grados': False,
            'grados_count': 0,
            'grados_info': [],
            
            # Notas (dependencia indirecta a través de periodos)
            'tiene_notas': False,
            'notas_count': 0,
            
            # Logros (dependencia indirecta)
            'tiene_logros': False,
            'logros_count': 0,
            
            # Comportamientos
            'tiene_comportamientos': False,
            'comportamientos_count': 0,
            
            # Asistencia
            'tiene_asistencias': False,
            'asistencias_count': 0,
            
            # Docentes asignados
            'tiene_docentes_asignados': False,
            'docentes_count': 0,
            
            # Asignaturas asignadas
            'tiene_asignaturas': False,
            'asignaturas_count': 0,
            
            # Todas las dependencias en una lista para mostrar
            'dependencias_lista': []
        }
        
        # 1. Matrículas
        matriculas = Matricula.objects.filter(año_lectivo=año)
        if matriculas.exists():
            dependencias['tiene_matriculas'] = True
            dependencias['matriculas_count'] = matriculas.count()
            
            # Tipos de matrículas
            estados_matriculas = matriculas.values('estado').annotate(
                total=Count('id')
            )
            estados_info = []
            for estado in estados_matriculas:
                estado_display = dict(Matricula.ESTADOS_MATRICULA).get(estado['estado'], estado['estado'])
                estados_info.append(f"{estado_display}: {estado['total']}")
            
            dependencias['matriculas_info'] = estados_info
            dependencias['dependencias_lista'].append(
                f"Matrículas: {dependencias['matriculas_count']} ({', '.join(estados_info)})"
            )
        
        # 2. Periodos académicos
        periodos = PeriodoAcademico.objects.filter(año_lectivo=año)
        if periodos.exists():
            dependencias['tiene_periodos'] = True
            dependencias['periodos_count'] = periodos.count()
            
            # Información de periodos
            periodos_data = []
            for periodo in periodos.order_by('periodo__nombre')[:5]:  # Limitar a 5
                periodos_data.append(f"{periodo.periodo.nombre} ({periodo.fecha_inicio} a {periodo.fecha_fin})")
            
            dependencias['periodos_info'] = periodos_data
            dependencias['dependencias_lista'].append(
                f"Periodos académicos: {dependencias['periodos_count']}"
            )
        
        # 3. Grados asociados
        grados = GradoAñoLectivo.objects.filter(año_lectivo=año)
        if grados.exists():
            dependencias['tiene_grados'] = True
            dependencias['grados_count'] = grados.count()
            
            # Nombres de grados
            grados_nombres = grados.values_list('grado__nombre', flat=True).distinct()
            dependencias['grados_info'] = list(grados_nombres)
            dependencias['dependencias_lista'].append(
                f"Grados: {dependencias['grados_count']} ({', '.join(grados_nombres[:3])}{'...' if grados_nombres.count() > 3 else ''})"
            )
        
        # 4. Notas (a través de periodos académicos)
        if periodos.exists():
            from estudiantes.models import Nota
            notas = Nota.objects.filter(periodo_academico__in=periodos)
            if notas.exists():
                dependencias['tiene_notas'] = True
                dependencias['notas_count'] = notas.count()
                dependencias['dependencias_lista'].append(
                    f"Notas registradas: {dependencias['notas_count']}"
                )
        
        # 5. Logros (a través de periodos académicos)
        if periodos.exists():
            from academico.models import Logro
            logros = Logro.objects.filter(periodo_academico__in=periodos)
            if logros.exists():
                dependencias['tiene_logros'] = True
                dependencias['logros_count'] = logros.count()
                dependencias['dependencias_lista'].append(
                    f"Logros académicos: {dependencias['logros_count']}"
                )
        
        # 6. Comportamientos (a través de periodos académicos)
        if periodos.exists():
            from comportamiento.models import Comportamiento
            comportamientos = Comportamiento.objects.filter(periodo_academico__in=periodos)
            if comportamientos.exists():
                dependencias['tiene_comportamientos'] = True
                dependencias['comportamientos_count'] = comportamientos.count()
                dependencias['dependencias_lista'].append(
                    f"Registros de comportamiento: {dependencias['comportamientos_count']}"
                )
        
        # 7. Asistencia (a través de periodos académicos)
        if periodos.exists():
            from comportamiento.models import Asistencia
            asistencias = Asistencia.objects.filter(periodo_academico__in=periodos)
            if asistencias.exists():
                dependencias['tiene_asistencias'] = True
                dependencias['asistencias_count'] = asistencias.count()
                dependencias['dependencias_lista'].append(
                    f"Registros de asistencia: {dependencias['asistencias_count']}"
                )
        
        # 8. Docentes asignados a sedes
        docentes_asignados = DocenteSede.objects.filter(año_lectivo=año)
        if docentes_asignados.exists():
            dependencias['tiene_docentes_asignados'] = True
            dependencias['docentes_count'] = docentes_asignados.count()
            dependencias['dependencias_lista'].append(
                f"Docentes asignados: {dependencias['docentes_count']}"
            )
        
        # 9. Asignaturas asignadas
        asignaturas = AsignaturaGradoAñoLectivo.objects.filter(
            grado_año_lectivo__año_lectivo=año
        )
        if asignaturas.exists():
            dependencias['tiene_asignaturas'] = True
            dependencias['asignaturas_count'] = asignaturas.count()
            dependencias['dependencias_lista'].append(
                f"Asignaturas configuradas: {dependencias['asignaturas_count']}"
            )
        
        return dependencias
    
    def _puede_eliminar_año(self, año):
        """Determinar si un año lectivo puede ser eliminado"""
        # CRITERIOS PARA NO PERMITIR ELIMINACIÓN:
        # 1. Tiene matrículas
        if Matricula.objects.filter(año_lectivo=año).exists():
            return False
        
        # 2. Tiene periodos académicos
        if PeriodoAcademico.objects.filter(año_lectivo=año).exists():
            return False
        
        # 3. Tiene grados asociados
        if GradoAñoLectivo.objects.filter(año_lectivo=año).exists():
            return False
        
        # 4. Tiene docentes asignados
        if DocenteSede.objects.filter(año_lectivo=año).exists():
            return False
        
        # 5. Es el año lectivo actual
        if self._es_año_lectivo_actual(año):
            return False
        
        return True
    
    def _es_año_lectivo_actual(self, año):
        """Verificar si es el año lectivo actual configurado"""
        config = ConfiguracionGeneral.objects.first()
        if config and config.año_lectivo_actual:
            return config.año_lectivo_actual.id == año.id
        return False
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        año = self.object
        
        # VALIDACIONES EXHAUSTIVAS ANTES DE ELIMINAR
        # 1. Verificar si es el año lectivo actual
        if self._es_año_lectivo_actual(año):
            messages.error(
                request, 
                f'No se puede eliminar el año lectivo {año.anho} porque está configurado como año lectivo actual. '
                f'Configure otro año como actual antes de eliminar este.'
            )
            return redirect('rector:año_lectivo_detail', pk=año.pk)
        
        # 2. Verificar matrículas
        if Matricula.objects.filter(año_lectivo=año).exists():
            total_matriculas = Matricula.objects.filter(año_lectivo=año).count()
            messages.error(
                request,
                f'No se puede eliminar el año lectivo porque tiene {total_matriculas} matrículas asociadas.'
            )
            return redirect('rector:año_lectivo_detail', pk=año.pk)
        
        # 3. Verificar periodos académicos
        if PeriodoAcademico.objects.filter(año_lectivo=año).exists():
            total_periodos = PeriodoAcademico.objects.filter(año_lectivo=año).count()
            messages.error(
                request,
                f'No se puede eliminar el año lectivo porque tiene {total_periodos} periodos académicos configurados.'
            )
            return redirect('rector:año_lectivo_detail', pk=año.pk)
        
        # 4. Verificar grados asociados
        if GradoAñoLectivo.objects.filter(año_lectivo=año).exists():
            total_grados = GradoAñoLectivo.objects.filter(año_lectivo=año).count()
            messages.error(
                request,
                f'No se puede eliminar el año lectivo porque tiene {total_grados} grados asociados.'
            )
            return redirect('rector:año_lectivo_detail', pk=año.pk)
        
        # 5. Verificar docentes asignados
        if DocenteSede.objects.filter(año_lectivo=año).exists():
            total_docentes = DocenteSede.objects.filter(año_lectivo=año).count()
            messages.error(
                request,
                f'No se puede eliminar el año lectivo porque tiene {total_docentes} docentes asignados.'
            )
            return redirect('rector:año_lectivo_detail', pk=año.pk)
        
        # 6. Verificar asignaturas configuradas
        if AsignaturaGradoAñoLectivo.objects.filter(grado_año_lectivo__año_lectivo=año).exists():
            total_asignaturas = AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo__año_lectivo=año
            ).count()
            messages.error(
                request,
                f'No se puede eliminar el año lectivo porque tiene {total_asignaturas} asignaturas configuradas.'
            )
            return redirect('rector:año_lectivo_detail', pk=año.pk)
        
        # Si pasa todas las validaciones, proceder con la eliminación
        nombre_año = f"{año.anho} - {año.sede.nombre}"
        
        try:
            # Eliminar el año lectivo
            año.delete()
            
            messages.success(
                request, 
                f'Año lectivo "{nombre_año}" eliminado exitosamente.'
            )
            
            return redirect('rector:año_lectivo_list')
            
        except Exception as e:
            messages.error(
                request, 
                f'Error al eliminar el año lectivo: {str(e)}'
            )
            return redirect('rector:año_lectivo_detail', pk=año.pk)
    
    def get_success_url(self):
        return reverse('rector:año_lectivo_list')

class AñoLectivoSetCurrentView(RoleRequiredMixin, View):
    """Establecer año lectivo como actual"""
    allowed_roles = ['Rector']
    
    def post(self, request, pk):
        año_lectivo = get_object_or_404(AñoLectivo, pk=pk)
        
        # Obtener o crear configuración general
        config, created = ConfiguracionGeneral.objects.get_or_create(
            colegio=año_lectivo.colegio,
            defaults={'año_lectivo_actual': año_lectivo}
        )
        
        # Si ya existe, actualizar
        if not created:
            config.año_lectivo_actual = año_lectivo
            config.save()
        
        messages.success(
            request, 
            f'Año lectivo {año_lectivo.anho} establecido como actual para {año_lectivo.sede.nombre}'
        )
        
        return redirect('rector:año_lectivo_list')

# ==================== GESTIÓN DE PERIODOS ACADÉMICOS ====================

class PeriodoAcademicoListView(RoleRequiredMixin, ListView):
    """Lista de periodos académicos"""
    template_name = 'rector/institucional/periodo/periodo_list.html'
    allowed_roles = ['Rector']
    model = PeriodoAcademico
    context_object_name = 'periodos'
    
    def get_queryset(self):
        # Filtrar por año lectivo si se especifica
        año_lectivo_id = self.request.GET.get('año_lectivo')
        queryset = PeriodoAcademico.objects.select_related(
            'año_lectivo', 'periodo'
        ).order_by('año_lectivo__anho', 'periodo__nombre')
        
        if año_lectivo_id:
            queryset = queryset.filter(año_lectivo_id=año_lectivo_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener todos los años lectivos para el filtro
        context['años_lectivos'] = AñoLectivo.objects.all().order_by('-anho')
        
        # Año lectivo seleccionado (si hay)
        año_lectivo_id = self.request.GET.get('año_lectivo')
        if año_lectivo_id:
            context['año_lectivo_seleccionado'] = get_object_or_404(AñoLectivo, pk=año_lectivo_id)
        
        # Verificar estado de los periodos (si están activos o vencidos)
        hoy = date.today()
        for periodo in context['periodos']:
            if periodo.fecha_fin < hoy:
                periodo.estado_periodo = 'finalizado'
            elif periodo.fecha_inicio <= hoy <= periodo.fecha_fin:
                periodo.estado_periodo = 'en_curso'
            else:
                periodo.estado_periodo = 'pendiente'
        
        return context

class PeriodoAcademicoCreateView(RoleRequiredMixin, CreateView):
    """Crear nuevo periodo académico"""
    template_name = 'rector/institucional/periodo/periodo_form.html'
    allowed_roles = ['Rector']
    model = PeriodoAcademico
    fields = ['año_lectivo', 'periodo', 'fecha_inicio', 'fecha_fin', 'estado']
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filtrar años lectivos activos
        form.fields['año_lectivo'].queryset = AñoLectivo.objects.filter(estado=True)
        return form
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear Nuevo Periodo Académico'
        
        # Obtener periodos disponibles del modelo academico
        from academico.models import Periodo
        periodos_disponibles = Periodo.objects.all()
        context['periodos_disponibles'] = periodos_disponibles
        
        return context
    
    def form_valid(self, form):
        # Verificar que no exista periodo duplicado para el mismo año
        if PeriodoAcademico.objects.filter(
            año_lectivo=form.cleaned_data['año_lectivo'],
            periodo=form.cleaned_data['periodo']
        ).exists():
            messages.error(self.request, 'Ya existe este periodo académico para el año lectivo seleccionado')
            return self.render_to_response(self.get_context_data(form=form))
        
        # Verificar fechas
        if form.cleaned_data['fecha_inicio'] >= form.cleaned_data['fecha_fin']:
            messages.error(self.request, 'La fecha de inicio debe ser anterior a la fecha de fin')
            return self.render_to_response(self.get_context_data(form=form))
        
        response = super().form_valid(form)
        messages.success(self.request, 'Periodo académico creado exitosamente')
        return response
    
    def get_success_url(self):
        return reverse('rector:periodo_list')

class PeriodoAcademicoUpdateView(RoleRequiredMixin, UpdateView):
    """Editar periodo académico"""
    template_name = 'rector/institucional/periodo/periodo_form.html'
    allowed_roles = ['Rector']
    model = PeriodoAcademico
    fields = ['año_lectivo', 'periodo', 'fecha_inicio', 'fecha_fin', 'estado']
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filtrar años lectivos activos
        form.fields['año_lectivo'].queryset = AñoLectivo.objects.filter(estado=True)
        return form
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Periodo Académico'
        
        # Obtener periodos disponibles del modelo academico
        from academico.models import Periodo
        periodos_disponibles = Periodo.objects.all()
        context['periodos_disponibles'] = periodos_disponibles
        
        return context
    
    def form_valid(self, form):
        # Verificar que no exista periodo duplicado (excluyendo el actual)
        if PeriodoAcademico.objects.filter(
            año_lectivo=form.cleaned_data['año_lectivo'],
            periodo=form.cleaned_data['periodo']
        ).exclude(pk=self.object.pk).exists():
            messages.error(self.request, 'Ya existe este periodo académico para el año lectivo seleccionado')
            return self.render_to_response(self.get_context_data(form=form))
        
        # Verificar fechas
        if form.cleaned_data['fecha_inicio'] >= form.cleaned_data['fecha_fin']:
            messages.error(self.request, 'La fecha de inicio debe ser anterior a la fecha de fin')
            return self.render_to_response(self.get_context_data(form=form))
        
        response = super().form_valid(form)
        messages.success(self.request, 'Periodo académico actualizado exitosamente')
        return response
    
    def get_success_url(self):
        return reverse('rector:periodo_list')

class PeriodoAcademicoDeleteView(RoleRequiredMixin, DeleteView):
    """Eliminar periodo académico"""
    template_name = 'rector/institucional/periodo/periodo_confirm_delete.html'
    allowed_roles = ['Rector']
    model = PeriodoAcademico
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Verificar si tiene dependencias (logros, notas, etc.)
        periodo = self.object
        
        # Verificar logros (del modelo academico)
        from academico.models import Logro
        tiene_logros = Logro.objects.filter(periodo_academico=periodo).exists()
        context['tiene_logros'] = tiene_logros
        
        # Verificar notas
        from estudiantes.models import Nota
        tiene_notas = Nota.objects.filter(periodo_academico=periodo).exists()
        context['tiene_notas'] = tiene_notas
        
        # Verificar comportamientos
        from comportamiento.models import Comportamiento
        tiene_comportamientos = Comportamiento.objects.filter(periodo_academico=periodo).exists()
        context['tiene_comportamientos'] = tiene_comportamientos
        
        puede_eliminar = not (tiene_logros or tiene_notas or tiene_comportamientos)
        context['puede_eliminar'] = puede_eliminar
        
        return context
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # Verificar dependencias antes de eliminar
        from academico.models import Logro
        from estudiantes.models import Nota
        from comportamiento.models import Comportamiento
        
        if Logro.objects.filter(periodo_academico=self.object).exists():
            messages.error(request, 'No se puede eliminar el periodo porque tiene logros asociados')
            return redirect('rector:periodo_list')
        
        if Nota.objects.filter(periodo_academico=self.object).exists():
            messages.error(request, 'No se puede eliminar el periodo porque tiene notas asociadas')
            return redirect('rector:periodo_list')
        
        if Comportamiento.objects.filter(periodo_academico=self.object).exists():
            messages.error(request, 'No se puede eliminar el periodo porque tiene registros de comportamiento asociados')
            return redirect('rector:periodo_list')
        
        messages.success(request, 'Periodo académico eliminado exitosamente')
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('rector:periodo_list')
    
# ==================== GESTIÓN DE ASIGNACIÓN DOCENTE (COMPLETAR) ====================

class AsignacionDocenteDashboardView(RoleRequiredMixin, TemplateView):
    """Dashboard de asignación docente"""
    template_name = 'rector/institucional/asignacion_docente/asignacion_dashboard.html'
    allowed_roles = ['Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener año lectivo actual
        config = ConfiguracionGeneral.objects.first()
        año_actual = config.año_lectivo_actual if config else None
        context['año_lectivo_actual'] = año_actual
        
        if año_actual:
            # Docentes sin asignaturas asignadas
            docentes_sin_asignaturas = Docente.objects.filter(
                estado=True
            ).exclude(
                asignaturas_dictadas__grado_año_lectivo__año_lectivo=año_actual
            ).distinct()
            context['docentes_sin_asignaturas'] = docentes_sin_asignaturas
            
            # Asignaturas sin docente asignado
            asignaturas_sin_docente = AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo__año_lectivo=año_actual,
                docente__isnull=True
            ).select_related('asignatura', 'grado_año_lectivo__grado', 'sede')
            context['asignaturas_sin_docente'] = asignaturas_sin_docente
            
            # Docentes sin sede asignada en el año actual
            docentes_sin_sede = Docente.objects.filter(
                estado=True
            ).exclude(
                sedes_asignadas__año_lectivo=año_actual
            ).distinct()
            context['docentes_sin_sede'] = docentes_sin_sede
        
        # Estadísticas generales de asignación
        total_docentes = Docente.objects.filter(estado=True).count()
        context['total_docentes'] = total_docentes
        
        if año_actual:
            docentes_con_asignaturas = Docente.objects.filter(
                asignaturas_dictadas__grado_año_lectivo__año_lectivo=año_actual
            ).distinct().count()
            context['docentes_con_asignaturas'] = docentes_con_asignaturas
            
            docentes_con_sede = Docente.objects.filter(
                sedes_asignadas__año_lectivo=año_actual,
                sedes_asignadas__estado=True
            ).distinct().count()
            context['docentes_con_sede'] = docentes_con_sede
        
        return context

class AsignacionPorSedeView(RoleRequiredMixin, ListView):
    """Ver asignaciones por sede"""
    template_name = 'rector/institucional/asignacion_docente/asignacion_por_sede.html'
    allowed_roles = ['Rector']
    context_object_name = 'sedes'
    
    def get_queryset(self):
        # Filtrar por año lectivo si se especifica
        año_lectivo_id = self.request.GET.get('año_lectivo')
        queryset = Sede.objects.filter(estado=True).select_related('colegio')
        
        if año_lectivo_id:
            self.año_lectivo = get_object_or_404(AñoLectivo, pk=año_lectivo_id)
        else:
            # Usar año actual por defecto
            config = ConfiguracionGeneral.objects.first()
            self.año_lectivo = config.año_lectivo_actual if config else None
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Años lectivos para filtro
        context['años_lectivos'] = AñoLectivo.objects.all().order_by('-anho')
        context['año_lectivo_seleccionado'] = getattr(self, 'año_lectivo', None)
        
        # Información por sede
        año_lectivo = getattr(self, 'año_lectivo', None)
        if año_lectivo:
            for sede in context['sedes']:

                sede.docentes_asignados_qs = DocenteSede.objects.filter(
                    sede=sede,
                    año_lectivo=año_lectivo,
                    estado=True
                ).select_related('docente__usuario')

                sede.asignaturas_qs = AsignaturaGradoAñoLectivo.objects.filter(
                    sede=sede,
                    grado_año_lectivo__año_lectivo=año_lectivo
                ).select_related(
                    'asignatura',
                    'grado_año_lectivo__grado',
                    'docente__usuario'
                )

                sede.total_docentes = sede.docentes_asignados_qs.count()
                sede.total_asignaturas = sede.asignaturas_qs.count()
                sede.asignaturas_sin_docente = sede.asignaturas_qs.filter(
                    docente__isnull=True
                ).count()
        
        return context

# ==================== GESTIÓN DE SEDES ====================
class SedesRectorView(RoleRequiredMixin, ListView):
    """Gestión de sedes para el rector"""
    template_name = 'rector/institucional/sede/sedes.html'
    allowed_roles = ['Rector']
    model = Sede
    context_object_name = 'sedes'
    paginate_by = 10
    
    def get_queryset(self):
        # Filtrar por estado si se especifica
        estado_filter = self.request.GET.get('estado', 'activas')
        
        if estado_filter == 'activas':
            queryset = Sede.objects.filter(estado=True)
        elif estado_filter == 'inactivas':
            queryset = Sede.objects.filter(estado=False)
        else:
            queryset = Sede.objects.all()
        
        queryset = queryset.select_related('colegio', 'director')
        
        # Filtros de búsqueda
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(direccion__icontains=search) |
                Q(colegio__nombre__icontains=search) |
                Q(director__nombres__icontains=search) |
                Q(director__apellidos__icontains=search)
            )
        
        # Ordenamiento
        sort_by = self.request.GET.get('sort_by', 'nombre')
        if sort_by in ['nombre', 'colegio__nombre', 'estado']:
            if sort_by == 'estado':
                # Ordenar por estado (activas primero)
                queryset = queryset.order_by('-estado', 'nombre')
            else:
                queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener año lectivo actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        # Pre-cargar estadísticas para cada sede
        sedes_con_estadisticas = []
        for sede in context['sedes']:
            sede_data = {
                'id': sede.id,
                'nombre': sede.nombre,
                'direccion': sede.direccion,
                'colegio': sede.colegio,
                'director': sede.director,
                'estado': sede.estado,
                'telefono': sede.telefono,
                'email': sede.email,
                'total_estudiantes': 0,
                'total_docentes': 0,
                'total_grados': 0,
            }
            
            # Solo calcular estadísticas si la sede está activa y hay año actual
            if sede.estado and año_actual:
                # Estudiantes matriculados
                sede_data['total_estudiantes'] = Matricula.objects.filter(
                    sede=sede,
                    año_lectivo=año_actual,
                    estado='ACT'
                ).count()
                
                # Docentes asignados
                sede_data['total_docentes'] = DocenteSede.objects.filter(
                    sede=sede,
                    año_lectivo=año_actual,
                    estado=True
                ).values('docente').distinct().count()
                
                # Grados activos
                sede_data['total_grados'] = GradoAñoLectivo.objects.filter(
                    año_lectivo=año_actual,
                    estado=True
                ).filter(
                    Q(matriculas__sede=sede) |
                    Q(asignaturas_grado__sede=sede)
                ).distinct().count()
            
            # Años lectivos (últimos 3 años)
            años_lectivos = AñoLectivo.objects.filter(
                sede=sede
            ).order_by('-anho')[:3]
            
            # Historial completo para el dropdown (máximo 10)
            años_lectivos_historial = AñoLectivo.objects.filter(
                sede=sede
            ).order_by('-anho')[:10]
            
            # Agregar las listas al diccionario
            sede_data['años_lectivos'] = list(años_lectivos)
            sede_data['años_lectivos_historial'] = list(años_lectivos_historial)
            
            sedes_con_estadisticas.append(sede_data)
        
        context['sedes'] = sedes_con_estadisticas
        
        # Estadísticas generales del sistema
        context['total_sedes'] = Sede.objects.filter(estado=True).count()
        context['sedes_inactivas'] = Sede.objects.filter(estado=False).count()
        
        if año_actual:
            # Total estudiantes en el sistema (año actual)
            context['total_estudiantes_sistema'] = Matricula.objects.filter(
                año_lectivo=año_actual,
                estado='ACT'
            ).count()
            
            # Total docentes asignados en el sistema (año actual)
            context['total_docentes_sistema'] = DocenteSede.objects.filter(
                año_lectivo=año_actual,
                estado=True
            ).values('docente').distinct().count()
        else:
            context['total_estudiantes_sistema'] = 0
            context['total_docentes_sistema'] = 0
        
        # Parámetros de filtro
        context['search_query'] = self.request.GET.get('search', '')
        context['sort_by'] = self.request.GET.get('sort_by', 'nombre')
        context['estado_filter'] = self.request.GET.get('estado', 'activas')
        
        return context

class SedeDetailView(RoleRequiredMixin, DetailView):
    """Detalle completo de una sede"""
    template_name = 'rector/institucional/sede/sede_detail.html'
    allowed_roles = ['Rector']
    model = Sede
    context_object_name = 'sede'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sede = self.object
        
        # Obtener año lectivo actual para estadísticas
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_actual'] = año_actual
        
        # Inicializar variables
        total_estudiantes = 0
        total_docentes = 0
        total_grados = 0
        total_asignaturas = 0
        asignaturas_sin_docente = 0
        asignaturas_con_docente = 0
        porcentaje_asignadas = 0
        
        if año_actual:
            # Estudiantes matriculados
            total_estudiantes = Matricula.objects.filter(
                sede=sede,
                año_lectivo=año_actual,
                estado='ACT'
            ).count()
            
            # Docentes asignados
            total_docentes = DocenteSede.objects.filter(
                sede=sede,
                año_lectivo=año_actual,
                estado=True
            ).values('docente').distinct().count()
            
            # Grados activos en esta sede
            total_grados = GradoAñoLectivo.objects.filter(
                año_lectivo=año_actual,
                estado=True
            ).filter(
                Q(matriculas__sede=sede) |
                Q(asignaturas_grado__sede=sede)
            ).distinct().count()
            
            # Asignaturas en esta sede
            total_asignaturas = AsignaturaGradoAñoLectivo.objects.filter(
                sede=sede,
                grado_año_lectivo__año_lectivo=año_actual
            ).count()
            
            # Asignaturas sin docente
            asignaturas_sin_docente = AsignaturaGradoAñoLectivo.objects.filter(
                sede=sede,
                grado_año_lectivo__año_lectivo=año_actual,
                docente__isnull=True
            ).count()
            
            # Calcular asignaturas con docente
            asignaturas_con_docente = total_asignaturas - asignaturas_sin_docente
            
            # Calcular porcentaje
            if total_asignaturas > 0:
                porcentaje_asignadas = (asignaturas_con_docente / total_asignaturas) * 100

            context['dependencias_info'] = {
                'años_lectivos_activos': AñoLectivo.objects.filter(sede=sede, estado=True).count(),
                'matriculas_activas': Matricula.objects.filter(
                    sede=sede,
                    año_lectivo=año_actual,
                    estado='ACT'
                ).count(),
                'docentes_asignados': DocenteSede.objects.filter(
                    sede=sede,
                    año_lectivo=año_actual,
                    estado=True
                ).values('docente').distinct().count(),
                'asignaturas_activas': AsignaturaGradoAñoLectivo.objects.filter(
                    sede=sede,
                    grado_año_lectivo__año_lectivo=año_actual
                ).count(),
            }
        
        # Pasar variables al contexto
        context['total_estudiantes'] = total_estudiantes
        context['total_docentes'] = total_docentes
        context['total_grados'] = total_grados
        context['total_asignaturas'] = total_asignaturas
        context['asignaturas_sin_docente'] = asignaturas_sin_docente
        context['asignaturas_con_docente'] = asignaturas_con_docente
        context['porcentaje_asignadas'] = porcentaje_asignadas
        
        context['puede_desactivar'] = not (
            AñoLectivo.objects.filter(sede=sede, estado=True).exists() or
            (año_actual and Matricula.objects.filter(
                sede=sede,
                año_lectivo=año_actual,
                estado='ACT'
            ).exists())
        )
        # Historial de años lectivos (resumen)
        context['años_lectivos_resumen'] = AñoLectivo.objects.filter(
            sede=sede
        ).order_by('-anho')[:5]
        
        # Docentes asignados (detalle)
        if año_actual:
            context['docentes_asignados'] = DocenteSede.objects.filter(
                sede=sede,
                año_lectivo=año_actual,
                estado=True
            ).select_related('docente__usuario')[:10]
        
        # Grados por nivel
        if año_actual:
            # Obtener grados únicos que están en esta sede
            grados_ids = GradoAñoLectivo.objects.filter(
                año_lectivo=año_actual,
                estado=True
            ).filter(
                Q(matriculas__sede=sede) |
                Q(asignaturas_grado__sede=sede)
            ).values_list('grado_id', flat=True).distinct()
            
            # Obtener los objetos Grado con sus niveles
            grados = Grado.objects.filter(
                id__in=grados_ids
            ).select_related('nivel_escolar')
            
            # Agrupar por nivel
            grados_por_nivel = {}
            for grado in grados:
                nivel = grado.nivel_escolar.nombre
                if nivel not in grados_por_nivel:
                    grados_por_nivel[nivel] = []
                grados_por_nivel[nivel].append(grado)
            
            context['grados_por_nivel'] = grados_por_nivel
        
        # Directores disponibles para cambiar
        from usuarios.models import TipoUsuario
        try:
            tipo_rector = TipoUsuario.objects.get(nombre='Rector')
            tipo_admin = TipoUsuario.objects.get(nombre='Administrador')
            
            context['directores_disponibles'] = Usuario.objects.filter(
                tipo_usuario__in=[tipo_rector, tipo_admin],
                estado=True
            ).order_by('nombres', 'apellidos')
        except TipoUsuario.DoesNotExist:
            context['directores_disponibles'] = Usuario.objects.none()
        
        return context
    
class SedeCreateView(RoleRequiredMixin, CreateView):
    """Crear nueva sede"""
    template_name = 'rector/institucional/sede/sede_form.html'
    allowed_roles = ['Rector']
    model = Sede
    fields = ['colegio', 'nombre', 'direccion', 'telefono', 'email', 'director', 'estado']
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filtrar usuarios que sean rectores o directores
        form.fields['director'].queryset = Usuario.objects.filter(
            tipo_usuario__nombre__in=['Rector', 'Administrador']
        )
        return form
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear Nueva Sede'
        context['colegios'] = Colegio.objects.filter(estado=True)
        return context
    
    def form_valid(self, form):
        # Verificar que no exista sede con el mismo nombre en el mismo colegio
        if Sede.objects.filter(
            colegio=form.cleaned_data['colegio'],
            nombre=form.cleaned_data['nombre']
        ).exists():
            messages.error(self.request, 'Ya existe una sede con este nombre en el colegio seleccionado')
            return self.render_to_response(self.get_context_data(form=form))
        
        response = super().form_valid(form)
        messages.success(self.request, 'Sede creada exitosamente')
        return response
    
    def get_success_url(self):
        return reverse('rector:sedes')

class SedeUpdateView(RoleRequiredMixin, UpdateView):
    """Editar sede existente"""
    template_name = 'rector/institucional/sede/sede_form.html'
    allowed_roles = ['Rector']
    model = Sede
    fields = ['colegio', 'nombre', 'direccion', 'telefono', 'email', 'director', 'estado']
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filtrar usuarios que sean rectores o directores
        form.fields['director'].queryset = Usuario.objects.filter(
            tipo_usuario__nombre__in=['Rector', 'Administrador']
        )
        return form
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Sede'
        context['colegios'] = Colegio.objects.filter(estado=True)
        return context
    
    def form_valid(self, form):
        # Verificar que no exista otra sede con el mismo nombre en el mismo colegio
        if Sede.objects.filter(
            colegio=form.cleaned_data['colegio'],
            nombre=form.cleaned_data['nombre']
        ).exclude(pk=self.object.pk).exists():
            messages.error(self.request, 'Ya existe otra sede con este nombre en el colegio seleccionado')
            return self.render_to_response(self.get_context_data(form=form))
        
        response = super().form_valid(form)
        messages.success(self.request, 'Sede actualizada exitosamente')
        return response
    
    def get_success_url(self):
        return reverse('rector:sedes')

class SedeDeleteView(RoleRequiredMixin, DeleteView):
    """Eliminar (desactivar) sede"""
    template_name = 'rector/institucional/sede/sede_confirm_delete.html'
    allowed_roles = ['Rector']
    model = Sede
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sede = self.object
        
        # Obtener información de dependencias
        context.update(self._obtener_dependencias_sede(sede))
        
        # Determinar si se puede desactivar
        context['puede_desactivar'] = self._puede_desactivar_sede(sede)
        
        return context
    
    def _obtener_dependencias_sede(self, sede):
        """Obtener todas las dependencias de la sede"""
        dependencias = {
            'tiene_años_lectivos_activos': False,
            'tiene_matriculas_activas': False,
            'tiene_periodos_activos': False,
            'tiene_docentes_activos': False,
            'tiene_asignaturas_activas': False,
            'dependencias_lista': [],
            'años_lectivos_activos_list': [],
            'matriculas_activas_count': 0,
            'periodos_activos_count': 0,
            'docentes_activos_count': 0,
            'asignaturas_activas_count': 0
        }
        
        # 1. Años lectivos ACTIVOS
        años_lectivos_activos = AñoLectivo.objects.filter(
            sede=sede,
            estado=True
        )
        if años_lectivos_activos.exists():
            dependencias['tiene_años_lectivos_activos'] = True
            dependencias['años_lectivos_activos_list'] = list(años_lectivos_activos.values_list('anho', flat=True))
            dependencias['dependencias_lista'].append(
                f"Años lectivos activos: {', '.join(dependencias['años_lectivos_activos_list'])}"
            )
        
        # 2. Matrículas ACTIVAS (en cualquier año)
        matriculas_activas = Matricula.objects.filter(
            sede=sede,
            estado='ACT'
        )
        if matriculas_activas.exists():
            dependencias['tiene_matriculas_activas'] = True
            dependencias['matriculas_activas_count'] = matriculas_activas.count()
            dependencias['dependencias_lista'].append(
                f"Matrículas activas: {dependencias['matriculas_activas_count']}"
            )
        
        # 3. Periodos académicos ACTIVOS
        periodos_activos = PeriodoAcademico.objects.filter(
            año_lectivo__sede=sede,
            estado=True
        )
        if periodos_activos.exists():
            dependencias['tiene_periodos_activos'] = True
            dependencias['periodos_activos_count'] = periodos_activos.count()
            dependencias['dependencias_lista'].append(
                f"Periodos académicos activos: {dependencias['periodos_activos_count']}"
            )
        
        # 4. Docentes asignados ACTIVOS
        docentes_activos = DocenteSede.objects.filter(
            sede=sede,
            estado=True
        )
        if docentes_activos.exists():
            dependencias['tiene_docentes_activos'] = True
            dependencias['docentes_activos_count'] = docentes_activos.count()
            dependencias['dependencias_lista'].append(
                f"Docentes asignados activos: {dependencias['docentes_activos_count']}"
            )
        
        # 5. Asignaturas activas
        asignaturas_activas = AsignaturaGradoAñoLectivo.objects.filter(
            sede=sede
        )
        if asignaturas_activas.exists():
            dependencias['tiene_asignaturas_activas'] = True
            dependencias['asignaturas_activas_count'] = asignaturas_activas.count()
            dependencias['dependencias_lista'].append(
                f"Asignaturas configuradas: {dependencias['asignaturas_activas_count']}"
            )
        
        return dependencias
    
    def _puede_desactivar_sede(self, sede):
        """Determinar si una sede puede ser desactivada"""
        # CRITERIOS PARA NO PERMITIR DESACTIVACIÓN:
        # 1. Tiene años lectivos activos
        if AñoLectivo.objects.filter(sede=sede, estado=True).exists():
            return False
        
        # 2. Tiene matrículas activas
        if Matricula.objects.filter(sede=sede, estado='ACT').exists():
            return False
        
        # 3. Tiene periodos académicos activos
        if PeriodoAcademico.objects.filter(año_lectivo__sede=sede, estado=True).exists():
            return False
        
        # 4. La sede ya está inactiva
        if not sede.estado:
            return False
        
        return True
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        sede = self.object
        
        # VALIDAR ANTES DE DESACTIVAR
        if not self._puede_desactivar_sede(sede):
            # Obtener dependencias específicas para mostrar mensajes precisos
            dependencias = self._obtener_dependencias_sede(sede)
            
            mensajes_error = []
            
            if dependencias['tiene_años_lectivos_activos']:
                años_list = ", ".join(dependencias['años_lectivos_activos_list'])
                mensajes_error.append(
                    f"Tiene {len(dependencias['años_lectivos_activos_list'])} "
                    f"año(s) lectivo(s) activo(s): {años_list}"
                )
            
            if dependencias['tiene_matriculas_activas']:
                mensajes_error.append(
                    f"Tiene {dependencias['matriculas_activas_count']} "
                    f"matrícula(s) activa(s)"
                )
            
            if dependencias['tiene_periodos_activos']:
                mensajes_error.append(
                    f"Tiene {dependencias['periodos_activos_count']} "
                    f"periodo(s) académico(s) activo(s)"
                )
            
            # Construir mensaje final
            if mensajes_error:
                mensaje_final = (
                    f"No se puede desactivar la sede '{sede.nombre}' porque:\n"
                    f"• " + "\n• ".join(mensajes_error)
                )
            else:
                mensaje_final = f"La sede '{sede.nombre}' no puede ser desactivada en este momento."
            
            messages.error(request, mensaje_final)
            return redirect('rector:sede_detail', pk=sede.pk)
        
        # Proceder con la desactivación si pasa todas las validaciones
        try:
            # Desactivar la sede
            sede.estado = False
            sede.save()
            
            # También desactivar todos los años lectivos asociados (si los hay)
            AñoLectivo.objects.filter(sede=sede, estado=True).update(estado=False)
            
            messages.success(
                request, 
                f'Sede "{sede.nombre}" desactivada exitosamente. '
                f'También se han desactivado los años lectivos asociados.'
            )
            
            return redirect('rector:sedes')
            
        except Exception as e:
            messages.error(
                request, 
                f'Error al desactivar la sede: {str(e)}'
            )
            return redirect('rector:sede_detail', pk=sede.pk)
    
    def get_success_url(self):
        return reverse('rector:sedes')

class SedeReactivateView(RoleRequiredMixin, View):
    """Reactivar sede inactiva"""
    allowed_roles = ['Rector']
    
    def post(self, request, pk):
        sede = get_object_or_404(Sede, pk=pk)
        
        if sede.estado:
            messages.warning(request, 'La sede ya está activa')
            return redirect('rector:sedes')
        
        sede.estado = True
        sede.save()
        
        messages.success(request, f'Sede "{sede.nombre}" reactivada exitosamente')
        return redirect('rector:sedes')

class SedeChangeDirectorView(RoleRequiredMixin, View):
    """Cambiar director de una sede"""
    allowed_roles = ['Rector']
    
    def post(self, request, pk):
        sede = get_object_or_404(Sede, pk=pk)
        director_id = request.POST.get('director_id')
        
        if not director_id:
            messages.error(request, 'Debe seleccionar un director')
            return redirect('rector:sede_detail', pk=pk)
        
        try:
            nuevo_director = Usuario.objects.get(pk=director_id)
            sede.director = nuevo_director
            sede.save()
            
            messages.success(request, f'Director actualizado a {nuevo_director.get_full_name()}')
        except Usuario.DoesNotExist:
            messages.error(request, 'El usuario seleccionado no existe')
        
        return redirect('rector:sede_detail', pk=pk)
    
# ================== VISTAS PARA ASIGNAR ASIGNATURAS Y SEDES ==================

class DocenteAsignarAsignaturaView(RoleRequiredMixin, CreateView):
    """Asignar una asignatura a un docente con filtros en cascada"""
    template_name = 'rector/institucional/docente/docente_asignar_asignatura.html'
    allowed_roles = ['Rector']
    form_class = AsignaturaDocenteForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['docente_id'] = self.kwargs.get('pk')
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        docente = get_object_or_404(Docente, pk=self.kwargs['pk'])
        context['docente'] = docente
        context['titulo'] = f'Asignar Asignatura a {docente.usuario.get_full_name()}'
        
        # Obtener año lectivo actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_actual
        
        # Información del docente
        context['docente_info'] = {
            'nombre': docente.usuario.get_full_name(),
            'documento': docente.usuario.numero_documento,
            'email': docente.usuario.email,
            'estado': docente.estado,
        }
        
        # Sedes disponibles del docente en el año actual
        if año_actual:
            sedes_docente = docente.sedes_asignadas.filter(
                año_lectivo=año_actual,
                estado=True
            ).select_related('sede')
            
            context['sedes_docente'] = sedes_docente
            
            # Grados disponibles en las sedes del docente
            if sedes_docente:
                sede_ids = sedes_docente.values_list('sede_id', flat=True)
                grados_disponibles = GradoAñoLectivo.objects.filter(
                    año_lectivo=año_actual,
                    estado=True
                ).filter(
                    Q(asignaturas_grado__sede__id__in=sede_ids) |
                    Q(matriculas__sede__id__in=sede_ids)
                ).distinct().select_related('grado')
                
                context['grados_disponibles'] = grados_disponibles
        
        return context
    
    def form_valid(self, form):
        docente = get_object_or_404(Docente, pk=self.kwargs['pk'])
        
        try:
            # Guardar la asignación
            instance = form.save()
            
            messages.success(
                self.request,
                f'Asignatura "{instance.asignatura.nombre}" asignada exitosamente al docente '
                f'para el grado {instance.grado_año_lectivo.grado.nombre} en {instance.sede.nombre}.'
            )
            
            return redirect('rector:docente_detail', pk=docente.pk)
            
        except Exception as e:
            messages.error(
                self.request,
                f'Error al asignar la asignatura: {str(e)}'
            )
            return self.render_to_response(self.get_context_data(form=form))
    
    def get_success_url(self):
        docente_pk = self.kwargs['pk']
        return reverse('rector:docente_detail', kwargs={'pk': docente_pk})

class AsignaturaQuitarConfirmView(RoleRequiredMixin, TemplateView):
    """Confirmación para quitar asignatura de docente"""
    template_name = 'rector/institucional/docente/asignatura_quitar_confirm.html'
    allowed_roles = ['Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asignatura = get_object_or_404(AsignaturaGradoAñoLectivo, pk=self.kwargs['pk'])
        context['asignatura'] = asignatura
        context['docente'] = asignatura.docente
        return context

class SedeQuitarConfirmView(RoleRequiredMixin, TemplateView):
    """Confirmación para quitar sede de docente"""
    template_name = 'rector/institucional/sede/sede_quitar_confirm.html'
    allowed_roles = ['Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sede_asignada = get_object_or_404(DocenteSede, pk=self.kwargs['pk'])
        context['sede_asignada'] = sede_asignada
        context['docente'] = sede_asignada.docente
        return context

class DocenteAsignarSedeView(RoleRequiredMixin, CreateView):
    """Asignar una sede a un docente (página completa)"""
    template_name = 'rector/institucional/docente/docente_asignar_sede.html'
    allowed_roles = ['Rector']
    form_class = DocenteSedeForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['docente_id'] = self.kwargs.get('pk')
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        docente = get_object_or_404(Docente, pk=self.kwargs['pk'])
        context['docente'] = docente
        context['titulo'] = f'Asignar Sede a {docente.usuario.get_full_name()}'
        
        # Sedes ya asignadas al docente
        context['sedes_asignadas'] = docente.sedes_asignadas.select_related(
            'sede', 'año_lectivo'
        ).order_by('-año_lectivo__anho')
        
        return context
    
    def form_valid(self, form):
        docente = get_object_or_404(Docente, pk=self.kwargs['pk'])
        form.instance.docente = docente
        
        # Verificar si ya existe asignación para ese año
        if DocenteSede.objects.filter(
            docente=docente,
            sede=form.cleaned_data['sede'],
            año_lectivo=form.cleaned_data['año_lectivo']
        ).exists():
            messages.error(self.request, 'El docente ya está asignado a esta sede para el año seleccionado')
            return self.render_to_response(self.get_context_data(form=form))
        
        messages.success(self.request, 'Sede asignada al docente exitosamente')
        return super().form_valid(form)
    
    def get_success_url(self):
        docente_pk = self.kwargs['pk']
        return reverse('rector:docente_detail', kwargs={'pk': docente_pk})

class AsignaturaDocenteDeleteView(RoleRequiredMixin, View):
    """Eliminar asignación de asignatura a docente (POST tradicional)"""
    allowed_roles = ['Rector']
    
    def post(self, request, pk):
        asignatura = get_object_or_404(AsignaturaGradoAñoLectivo, pk=pk)
        docente = asignatura.docente
        asignatura_nombre = asignatura.asignatura.nombre
        
        # Verificar que tenga docente asignado
        if not docente:
            messages.error(request, 'Esta asignatura no tiene docente asignado')
            return redirect('rector:docente_detail', pk=docente.pk)
        
        # Quitar asignación
        asignatura.docente = None
        asignatura.save()
        
        messages.success(
            request, 
            f'Asignatura "{asignatura_nombre}" quitada del docente "{docente.usuario.get_full_name()}"'
        )
        
        return redirect('rector:docente_detail', pk=docente.pk)

class DocenteSedeDeleteView(RoleRequiredMixin, View):
    """Eliminar asignación de sede a docente (POST tradicional)"""
    allowed_roles = ['Rector']
    
    def post(self, request, pk):
        sede_asignada = get_object_or_404(DocenteSede, pk=pk)
        docente = sede_asignada.docente
        sede_nombre = sede_asignada.sede.nombre
        
        # Desactivar la asignación
        sede_asignada.estado = False
        sede_asignada.save()
        
        messages.success(
            request, 
            f'Sede "{sede_nombre}" quitada del docente "{docente.usuario.get_full_name()}"'
        )
        
        return redirect('rector:docente_detail', pk=docente.pk)

class DocenteSedeReactivarView(RoleRequiredMixin, View):
    """Reactivar asignación de sede a docente"""
    allowed_roles = ['Rector']
    
    def post(self, request, pk):
        sede_asignada = get_object_or_404(DocenteSede, pk=pk)
        docente = sede_asignada.docente
        
        # Verificar que la sede esté inactiva antes de reactivarla
        if sede_asignada.estado:
            messages.warning(request, 'Esta sede ya está activa')
            return redirect('rector:docente_detail', pk=docente.pk)
        
        sede_nombre = sede_asignada.sede.nombre
        
        # Reactivar la asignación
        sede_asignada.estado = True
        sede_asignada.save()
        
        messages.success(
            request, 
            f'Sede "{sede_nombre}" reactivada para el docente "{docente.usuario.get_full_name()}"'
        )
        
        return redirect('rector:docente_detail', pk=docente.pk)