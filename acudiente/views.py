# acudiente/views.py
from django.views.generic import TemplateView, DetailView
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from estudiantes.models import Estudiante, Nota, Acudiente
from comportamiento.models import Comportamiento, Asistencia
from academico.models import HorarioClase
from matricula.models import AsignaturaGradoAñoLectivo, PeriodoAcademico
from gestioncolegio.models import AñoLectivo
from gestioncolegio.views import RoleRequiredMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import date, datetime

class SeleccionarAñoDocumentosView(RoleRequiredMixin, TemplateView):
    """Vista para seleccionar año lectivo para documentos históricos"""
    template_name = 'acudiente/seleccionar_año.html'
    allowed_roles = ['Acudiente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante_id = self.kwargs.get('estudiante_id')
        
        # Verificar permisos
        if not Acudiente.objects.filter(
            acudiente=self.request.user,
            estudiante_id=estudiante_id
        ).exists():
            raise PermissionDenied("No tiene permiso para ver este estudiante")
        
        estudiante = get_object_or_404(Estudiante, id=estudiante_id)
        context['estudiante'] = estudiante
        
        # Obtener años disponibles
        años_matriculados = estudiante.años_matriculados
        años_lectivos = AñoLectivo.objects.filter(
            anho__in=años_matriculados
        ).order_by('-anho')
        
        context['años_lectivos'] = años_lectivos
        
        # Tipo de documento solicitado (si viene como parámetro)
        tipo_documento = self.request.GET.get('tipo', 'boletin')
        context['tipo_documento'] = tipo_documento
        
        return context
    
    
class DetalleEstudianteView(RoleRequiredMixin, DetailView):
    """Vista detallada de un estudiante específico"""
    template_name = 'acudiente/detalle_estudiante.html'
    allowed_roles = ['Acudiente']
    model = Estudiante
    context_object_name = 'estudiante'
    
    def get_queryset(self):
        # Solo permitir ver estudiantes donde el usuario es acudiente
        user_acudientes = Acudiente.objects.filter(acudiente=self.request.user)
        estudiantes_ids = user_acudientes.values_list('estudiante_id', flat=True)
        return Estudiante.objects.filter(id__in=estudiantes_ids)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante = self.object
        
        # Obtener relación del acudiente
        acudiente_rel = Acudiente.objects.filter(
            acudiente=self.request.user,
            estudiante=estudiante
        ).first()
        context['acudiente_rel'] = acudiente_rel
        
        # Obtener matrícula actual
        context['matricula_actual'] = estudiante.matricula_actual
        
        # Obtener todos los años matriculados con información completa
        context['historial_matriculas'] = estudiante.matriculas_anteriores()
        
        # Obtener año lectivo actual
        context['año_lectivo_actual'] = AñoLectivo.objects.filter(estado=True).first()
        
        return context
    
class NotasEstudianteView(RoleRequiredMixin, TemplateView):
    """Vista de notas por año y periodo"""
    template_name = 'acudiente/notas_estudiante.html'
    allowed_roles = ['Acudiente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante_id = self.kwargs.get('estudiante_id')
        
        # Verificar que el acudiente tenga permiso para ver este estudiante
        if not Acudiente.objects.filter(
            acudiente=self.request.user,
            estudiante_id=estudiante_id
        ).exists():
            raise PermissionDenied("No tiene permiso para ver este estudiante")
        
        estudiante = get_object_or_404(Estudiante, id=estudiante_id)
        context['estudiante'] = estudiante
        
        # Obtener parámetros de filtro
        año_lectivo_id = self.request.GET.get('año_lectivo')
        periodo_id = self.request.GET.get('periodo')
        
        # Obtener años disponibles
        años_matriculados = estudiante.años_matriculados
        context['años_disponibles'] = AñoLectivo.objects.filter(
            anho__in=años_matriculados
        ).order_by('-anho')
        
        # Obtener notas filtradas
        notas_query = Nota.objects.filter(estudiante=estudiante)
        
        if año_lectivo_id:
            año_lectivo = get_object_or_404(AñoLectivo, id=año_lectivo_id)
            notas_query = notas_query.filter(
                periodo_academico__año_lectivo=año_lectivo
            )
            context['año_seleccionado'] = año_lectivo
            
            # Obtener periodos disponibles para este año
            periodos_disponibles = PeriodoAcademico.objects.filter(
                año_lectivo=año_lectivo
            ).order_by('periodo__nombre')
            context['periodos_disponibles'] = periodos_disponibles
            
            if periodo_id:
                periodo = get_object_or_404(PeriodoAcademico, id=periodo_id)
                notas_query = notas_query.filter(periodo_academico=periodo)
                context['periodo_seleccionado'] = periodo
        
        # Agrupar notas por asignatura y periodo
        notas_agrupadas = {}
        for nota in notas_query.select_related(
            'asignatura_grado_año_lectivo__asignatura',
            'periodo_academico__periodo'
        ).order_by('periodo_academico__periodo__nombre'):
            
            asignatura = nota.asignatura_grado_año_lectivo.asignatura
            periodo = nota.periodo_academico.periodo
            
            if asignatura.id not in notas_agrupadas:
                notas_agrupadas[asignatura.id] = {
                    'asignatura': asignatura,
                    'notas_por_periodo': {}
                }
            
            notas_agrupadas[asignatura.id]['notas_por_periodo'][periodo.nombre] = nota.calificacion
        
        context['notas_agrupadas'] = notas_agrupadas
        
        # Calcular promedios
        context['promedios'] = self.calcular_promedios(notas_query)
        
        return context
    
    def calcular_promedios(self, notas_query):
        """Calcula promedios por periodo y general"""
        promedios = {
            'por_periodo': {},
            'general': 0.0
        }
        
        notas_por_periodo = {}
        for nota in notas_query:
            periodo_nombre = nota.periodo_academico.periodo.nombre
            if periodo_nombre not in notas_por_periodo:
                notas_por_periodo[periodo_nombre] = []
            notas_por_periodo[periodo_nombre].append(float(nota.calificacion))
        
        # Promedios por periodo
        total_general = 0
        count_general = 0
        for periodo, notas in notas_por_periodo.items():
            if notas:
                promedio = sum(notas) / len(notas)
                promedios['por_periodo'][periodo] = round(promedio, 2)
                total_general += sum(notas)
                count_general += len(notas)
        
        # Promedio general
        if count_general > 0:
            promedios['general'] = round(total_general / count_general, 2)
        
        return promedios
    
class AsistenciaEstudianteView(RoleRequiredMixin, TemplateView):
    """Vista de registro de asistencia"""
    template_name = 'acudiente/asistencia_estudiante.html'
    allowed_roles = ['Acudiente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante_id = self.kwargs.get('estudiante_id')
        
        # Verificar permisos
        if not Acudiente.objects.filter(
            acudiente=self.request.user,
            estudiante_id=estudiante_id
        ).exists():
            raise PermissionDenied("No tiene permiso para ver este estudiante")
        
        estudiante = get_object_or_404(Estudiante, id=estudiante_id)
        context['estudiante'] = estudiante
        
        # Filtros
        mes = self.request.GET.get('mes')
        año = self.request.GET.get('año')
        
        # Obtener año lectivo actual
        año_lectivo_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_lectivo_actual
        
        # Obtener asistencia
        asistencias_query = Asistencia.objects.filter(
            estudiante=estudiante
        ).select_related('periodo_academico__periodo')
        
        if año_lectivo_actual:
            asistencias_query = asistencias_query.filter(
                periodo_academico__año_lectivo=año_lectivo_actual
            )
        
        # Filtrar por mes y año si se especifican
        if mes and año:
            try:
                fecha_inicio = date(int(año), int(mes), 1)
                if int(mes) == 12:
                    fecha_fin = date(int(año) + 1, 1, 1)
                else:
                    fecha_fin = date(int(año), int(mes) + 1, 1)
                
                asistencias_query = asistencias_query.filter(
                    fecha__gte=fecha_inicio,
                    fecha__lt=fecha_fin
                )
                context['mes_seleccionado'] = int(mes)
                context['año_seleccionado'] = int(año)
            except (ValueError, TypeError):
                pass
        
        # Ordenar por fecha
        asistencias_query = asistencias_query.order_by('-fecha')
        
        # Estadísticas
        total_asistencias = asistencias_query.count()
        faltas = asistencias_query.filter(estado='F').count()
        faltas_justificadas = asistencias_query.filter(estado='J').count()
        asistencias = total_asistencias - faltas - faltas_justificadas
        
        context['asistencias'] = asistencias_query
        context['estadisticas'] = {
            'total': total_asistencias,
            'asistencias': asistencias,
            'faltas': faltas,
            'faltas_justificadas': faltas_justificadas,
            'porcentaje_asistencia': round((asistencias / total_asistencias * 100), 2) if total_asistencias > 0 else 0
        }
        
        # Meses disponibles para filtro
        context['meses'] = [
            (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
            (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
            (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
        ]
        
        return context
    
class ComportamientoEstudianteView(RoleRequiredMixin, TemplateView):
    """Vista de registros de comportamiento"""
    template_name = 'acudiente/comportamiento_estudiante.html'
    allowed_roles = ['Acudiente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante_id = self.kwargs.get('estudiante_id')
        
        # Verificar permisos
        if not Acudiente.objects.filter(
            acudiente=self.request.user,
            estudiante_id=estudiante_id
        ).exists():
            raise PermissionDenied("No tiene permiso para ver este estudiante")
        
        estudiante = get_object_or_404(Estudiante, id=estudiante_id)
        context['estudiante'] = estudiante
        
        # Filtros
        tipo_comportamiento = self.request.GET.get('tipo')
        categoria = self.request.GET.get('categoria')
        desde = self.request.GET.get('desde')
        hasta = self.request.GET.get('hasta')
        
        # Obtener comportamientos
        comportamientos_query = Comportamiento.objects.filter(
            estudiante=estudiante
        ).select_related(
            'docente__usuario',
            'periodo_academico__periodo'
        ).order_by('-fecha')
        
        # Aplicar filtros
        if tipo_comportamiento:
            comportamientos_query = comportamientos_query.filter(tipo=tipo_comportamiento)
            context['tipo_seleccionado'] = tipo_comportamiento
        
        if categoria:
            comportamientos_query = comportamientos_query.filter(categoria=categoria)
            context['categoria_seleccionada'] = categoria
        
        if desde:
            try:
                fecha_desde = datetime.strptime(desde, '%Y-%m-%d').date()
                comportamientos_query = comportamientos_query.filter(fecha__gte=fecha_desde)
                context['desde'] = desde
            except ValueError:
                pass
        
        if hasta:
            try:
                fecha_hasta = datetime.strptime(hasta, '%Y-%m-%d').date()
                comportamientos_query = comportamientos_query.filter(fecha__lte=fecha_hasta)
                context['hasta'] = hasta
            except ValueError:
                pass
        
        # Estadísticas
        total_comportamientos = comportamientos_query.count()
        positivos = comportamientos_query.filter(tipo='Positivo').count()
        negativos = comportamientos_query.filter(tipo='Negativo').count()
        
        # Agrupar por categoría para gráfico
        categorias_data = {}
        for cat in Comportamiento.CATEGORIAS:
            count = comportamientos_query.filter(categoria=cat[0]).count()
            if count > 0:
                categorias_data[cat[1]] = count
        
        context['comportamientos'] = comportamientos_query
        context['estadisticas'] = {
            'total': total_comportamientos,
            'positivos': positivos,
            'negativos': negativos,
            'porcentaje_positivos': round((positivos / total_comportamientos * 100), 2) if total_comportamientos > 0 else 0,
            'categorias_data': categorias_data
        }
        
        return context
    
class HistorialAcademicoView(RoleRequiredMixin, TemplateView):
    """Vista de historial académico completo del estudiante"""
    template_name = 'acudiente/historial_academico.html'
    allowed_roles = ['Acudiente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante_id = self.kwargs.get('estudiante_id')
        
        # Verificar permisos
        if not Acudiente.objects.filter(
            acudiente=self.request.user,
            estudiante_id=estudiante_id
        ).exists():
            raise PermissionDenied("No tiene permiso para ver este estudiante")
        
        estudiante = get_object_or_404(Estudiante, id=estudiante_id)
        context['estudiante'] = estudiante
        
        # Obtener TODAS las notas del estudiante (historial completo)
        notas = Nota.objects.filter(
            estudiante=estudiante
        ).select_related(
            'asignatura_grado_año_lectivo__asignatura',
            'asignatura_grado_año_lectivo__grado_año_lectivo__año_lectivo',
            'periodo_academico__periodo'
        ).order_by(
            '-asignatura_grado_año_lectivo__grado_año_lectivo__año_lectivo__anho',
            'periodo_academico__periodo__nombre',
            'asignatura_grado_año_lectivo__asignatura__nombre'
        )
        
        # Organizar por año lectivo y periodo
        historial_organizado = {}
        
        for nota in notas:
            año_lectivo = nota.asignatura_grado_año_lectivo.grado_año_lectivo.año_lectivo
            año = año_lectivo.anho
            año_id = año_lectivo.id
            periodo = nota.periodo_academico.periodo.nombre if nota.periodo_academico else 'General'
            asignatura = nota.asignatura_grado_año_lectivo.asignatura
            
            # Inicializar estructura para este año si no existe
            if año not in historial_organizado:
                historial_organizado[año] = {
                    'periodos': {},
                    'info': {
                        'id': año_id,
                        'año_obj': año_lectivo
                    }
                }
            
            # Inicializar lista para este periodo si no existe
            if periodo not in historial_organizado[año]['periodos']:
                historial_organizado[año]['periodos'][periodo] = []
            
            # Crear objeto similar a HistorialAcademicoEstudiante
            registro = {
                'asignatura': asignatura,
                'promedio_periodo': nota.calificacion,
                'faltas': 0,  # Necesitarías obtener faltas de otro modelo
                'logros': nota.observaciones or '',
                'nota_obj': nota  # Mantener referencia a la nota original
            }
            
            historial_organizado[año]['periodos'][periodo].append(registro)
        
        context['historial_organizado'] = historial_organizado
        
        # Calcular estadísticas generales
        context['estadisticas'] = self.calcular_estadisticas_historial(notas)
        
        return context
    
    def calcular_estadisticas_historial(self, notas):
        """Calcula estadísticas del historial académico basado en notas"""
        estadisticas = {
            'total_registros': notas.count(),
            'promedio_general': 0.0,
            'mejor_promedio': 0.0,
            'peor_promedio': 5.0,
            'años_estudiados': set()
        }
        
        if not notas:
            return estadisticas
        
        total_promedio = 0
        count_promedio = 0
        
        for nota in notas:
            # Agregar año estudiado
            año = nota.asignatura_grado_año_lectivo.grado_año_lectivo.año_lectivo.anho
            estadisticas['años_estudiados'].add(año)
            
            # Calcular promedios
            if nota.calificacion:
                try:
                    promedio = float(nota.calificacion)
                    total_promedio += promedio
                    count_promedio += 1
                    
                    if promedio > estadisticas['mejor_promedio']:
                        estadisticas['mejor_promedio'] = promedio
                    
                    if promedio < estadisticas['peor_promedio']:
                        estadisticas['peor_promedio'] = promedio
                except (ValueError, TypeError):
                    continue
        
        if count_promedio > 0:
            estadisticas['promedio_general'] = round(total_promedio / count_promedio, 2)
            estadisticas['mejor_promedio'] = round(estadisticas['mejor_promedio'], 2)
            estadisticas['peor_promedio'] = round(estadisticas['peor_promedio'], 2)
        
        estadisticas['años_estudiados'] = len(estadisticas['años_estudiados'])
        
        return estadisticas
        
class HorarioEstudianteView(RoleRequiredMixin, TemplateView):
    """Vista del horario del estudiante"""
    template_name = 'acudiente/horario_estudiante.html'
    allowed_roles = ['Acudiente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante_id = self.kwargs.get('estudiante_id')
        
        # Verificar permisos
        if not Acudiente.objects.filter(
            acudiente=self.request.user,
            estudiante_id=estudiante_id
        ).exists():
            raise PermissionDenied("No tiene permiso para ver este estudiante")
        
        estudiante = get_object_or_404(Estudiante, id=estudiante_id)
        context['estudiante'] = estudiante
        
        # Obtener matrícula actual
        matricula_actual = estudiante.matricula_actual
        if not matricula_actual:
            context['horario'] = None
            return context
        
        context['matricula'] = matricula_actual
        
        # Obtener horario del estudiante
        # Necesitas obtener las asignaturas del grado del estudiante
        grado_año_lectivo = matricula_actual.grado_año_lectivo
        
        # Obtener asignaturas del grado
        asignaturas_grado = AsignaturaGradoAñoLectivo.objects.filter(
            grado_año_lectivo=grado_año_lectivo,
            sede=matricula_actual.sede
        ).select_related('asignatura', 'docente__usuario')
        
        context['asignaturas'] = asignaturas_grado
        
        # Obtener horarios por asignatura
        horarios = {}
        dias_semana = ['LUN', 'MAR', 'MIE', 'JUE', 'VIE']
        
        for asignatura in asignaturas_grado:
            horarios_asignatura = HorarioClase.objects.filter(
                asignatura_grado=asignatura
            ).order_by('dia_semana', 'hora_inicio')
            
            if horarios_asignatura.exists():
                for horario in horarios_asignatura:
                    dia = horario.dia_semana
                    hora_inicio = horario.hora_inicio.strftime('%H:%M')
                    
                    if dia not in horarios:
                        horarios[dia] = {}
                    
                    horarios[dia][hora_inicio] = {
                        'asignatura': asignatura.asignatura.nombre,
                        'docente': asignatura.docente.usuario.get_full_name() if asignatura.docente else 'Por asignar',
                        'hora_inicio': horario.hora_inicio,
                        'hora_fin': horario.hora_fin,
                        'salon': horario.salon,
                        'color': self.get_color_for_asignatura(asignatura.asignatura.id)
                    }
        
        # Organizar por horas
        horas_ordenadas = sorted(set(
            hora for dia_horas in horarios.values() for hora in dia_horas.keys()
        ))
        
        context['dias_semana'] = [
            ('LUN', 'Lunes'), ('MAR', 'Martes'), ('MIE', 'Miércoles'),
            ('JUE', 'Jueves'), ('VIE', 'Viernes')
        ]
        context['horarios'] = horarios
        context['horas_ordenadas'] = horas_ordenadas
        
        return context
    
    def get_color_for_asignatura(self, asignatura_id):
        """Genera un color único para cada asignatura"""
        colores = [
            '#e3f2fd', '#f3e5f5', '#e8f5e8', '#fff3e0',
            '#fce4ec', '#e0f2f1', '#f3e5f5', '#fff8e1'
        ]
        return colores[asignatura_id % len(colores)]
    
class DocumentosEstudianteView(RoleRequiredMixin, TemplateView):
    """Vista para acceder a documentos PDF del estudiante"""
    template_name = 'acudiente/documentos_estudiante.html'
    allowed_roles = ['Acudiente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante_id = self.kwargs.get('estudiante_id')
        
        # Verificar permisos
        if not Acudiente.objects.filter(
            acudiente=self.request.user,
            estudiante_id=estudiante_id
        ).exists():
            raise PermissionDenied("No tiene permiso para ver este estudiante")
        
        estudiante = get_object_or_404(Estudiante, id=estudiante_id)
        context['estudiante'] = estudiante
        
        # Obtener años disponibles (solo donde el estudiante ha estado matriculado)
        años_matriculados = estudiante.años_matriculados
        años_lectivos = AñoLectivo.objects.filter(
            anho__in=años_matriculados
        ).order_by('-anho')
        context['años_lectivos'] = años_lectivos
        
        # Obtener matrícula actual del estudiante (si existe)
        matricula_actual = estudiante.matricula_actual
        context['matricula_actual'] = matricula_actual
        
        return context
    
class InconsistenciasEstudianteView(LoginRequiredMixin, TemplateView):
    """Vista de inconsistencias académicas del estudiante"""
    template_name = 'acudiente/inconsistencias_estudiante.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante_id = self.kwargs.get('estudiante_id')
        
        # Verificar permisos
        if not Acudiente.objects.filter(
            acudiente=self.request.user,
            estudiante_id=estudiante_id
        ).exists():
            raise PermissionDenied("No tiene permiso para ver este estudiante")
        
        estudiante = get_object_or_404(Estudiante, id=estudiante_id)
        context['estudiante'] = estudiante
        
        # Obtener inconsistencias
        from comportamiento.models import Inconsistencia
        inconsistencias = Inconsistencia.objects.filter(
            estudiante=estudiante
        ).order_by('-fecha')
        
        context['inconsistencias'] = inconsistencias
        
        return context

class ComunicacionEstudianteView(LoginRequiredMixin, TemplateView):
    """Vista de comunicación con docentes"""
    template_name = 'acudiente/comunicacion_estudiante.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante_id = self.kwargs.get('estudiante_id')
        
        # Verificar permisos
        if not Acudiente.objects.filter(
            acudiente=self.request.user,
            estudiante_id=estudiante_id
        ).exists():
            raise PermissionDenied("No tiene permiso para ver este estudiante")
        
        estudiante = get_object_or_404(Estudiante, id=estudiante_id)
        context['estudiante'] = estudiante
        
        # Obtener docentes del estudiante (del año actual)
        matricula_actual = estudiante.matricula_actual
        if matricula_actual:
            # Aquí puedes agregar lógica para obtener docentes
            # Por ahora, es un placeholder
            context['docentes'] = []
        
        return context

class EventosEstudianteView(LoginRequiredMixin, TemplateView):
    """Vista de eventos y calendario"""
    template_name = 'acudiente/eventos_estudiante.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante_id = self.kwargs.get('estudiante_id')
        
        # Verificar permisos
        if not Acudiente.objects.filter(
            acudiente=self.request.user,
            estudiante_id=estudiante_id
        ).exists():
            raise PermissionDenied("No tiene permiso para ver este estudiante")
        
        estudiante = get_object_or_404(Estudiante, id=estudiante_id)
        context['estudiante'] = estudiante
        
        # Aquí puedes agregar lógica para obtener eventos del colegio
        # Por ahora, es un placeholder
        context['eventos'] = []
        context['calendario'] = {}
        
        return context