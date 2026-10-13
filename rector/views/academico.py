# rector/views/academico.py
from django.db.models import Exists, OuterRef
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.views.generic.edit import FormView
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
import json
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Count, Avg, Q, Sum, Max, Min
from django.utils import timezone
from datetime import timedelta
from datetime import date, datetime

# Mixins y modelos
from gestioncolegio.mixins import RoleRequiredMixin
from estudiantes.models import Estudiante, Matricula, Nota, Acudiente
from usuarios.models import Docente, Usuario
from gestioncolegio.models import AñoLectivo, Sede
from matricula.models import PeriodoAcademico, AsignaturaGradoAñoLectivo, GradoAñoLectivo, Periodo
from comportamiento.models import Comportamiento, Asistencia, Inconsistencia
from academico.models import Grado, Asignatura, Area, NivelEscolar, Logro, HorarioClase
from ..forms.formularios_academicco import *

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

class AcademicoDashboardView(RoleRequiredMixin, TemplateView):
    """Dashboard principal del módulo académico"""
    template_name = 'rector/academico/academico_dashboard.html'
    allowed_roles = ['Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas generales
        context['total_estudiantes'] = Estudiante.objects.filter(estado=True).count()
        context['total_docentes'] = Docente.objects.filter(estado=True).count()
        context['total_grados'] = Grado.objects.count()
        
        # Año lectivo actual para estadísticas
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if año_actual:
            context['grados_activos'] = GradoAñoLectivo.objects.filter(
                año_lectivo=año_actual,
                estado=True
            ).count()
            
            # Estudiantes nuevos en el año actual
            context['estudiantes_nuevos'] = Matricula.objects.filter(
                año_lectivo=año_actual,
                estado='ACT'
            ).count()
        
        # Docentes activos
        context['docentes_activos'] = Docente.objects.filter(estado=True).count()
        
        # Niveles escolares
        context['niveles_count'] = NivelEscolar.objects.count()
        
        # Promedio general (simulado - ajustar según necesidades)
        context['promedio_general'] = 3.8
        
        # Actividad reciente (simulada)
        context['actividades_recientes'] = [
            {
                'titulo': 'Nueva matrícula registrada',
                'descripcion': 'Estudiante Juan Pérez matriculado en Primero',
                'usuario': 'Sistema',
                'fecha': timezone.now() - timedelta(minutes=5)
            },
            {
                'titulo': 'Notas actualizadas',
                'descripcion': 'Calificaciones del primer período ingresadas',
                'usuario': 'Docente García',
                'fecha': timezone.now() - timedelta(hours=1)
            },
            {
                'titulo': 'Asignatura creada',
                'descripcion': 'Nueva asignatura "Robótica" agregada',
                'usuario': 'Administrador',
                'fecha': timezone.now() - timedelta(hours=2)
            }
        ]
        
        # Estadísticas por nivel escolar
        estadisticas_niveles = []
        for nivel in NivelEscolar.objects.all():
            total_estudiantes = Matricula.objects.filter(
                grado_año_lectivo__grado__nivel_escolar=nivel,
                estado='ACT'
            ).count()
            
            estadisticas_niveles.append({
                'nivel': nivel,
                'total_grados': nivel.grados.count(),
                'total_estudiantes': total_estudiantes,
                'promedio': 3.5,  # Simulado
                'total_docentes': 5,  # Simulado
                'activo': True
            })
        
        context['estadisticas_niveles'] = estadisticas_niveles
        
        return context
# ================== ESTUDIANTES ==================
class EstudianteListView(RoleRequiredMixin, ListView):
    """Lista completa de estudiantes con filtros avanzados"""
    template_name = 'rector/academico/estudiante/estudiante_list.html'
    allowed_roles = ['Rector']
    model = Estudiante
    context_object_name = 'estudiantes'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = Estudiante.objects.all()  # Incluye todos, activos e inactivos
        
        # Filtros principales
        año_filter = self.request.GET.get('año')
        grado_filter = self.request.GET.get('grado')
        sede_filter = self.request.GET.get('sede')
        estado_filter = self.request.GET.get('estado')
        search = self.request.GET.get('search')
        nivel_filter = self.request.GET.get('nivel')
        
        # Filtro por año lectivo
        if año_filter and año_filter != 'todos':
            año_lectivo = AñoLectivo.objects.filter(id=año_filter).first()
            if año_lectivo:
                estudiante_ids = Matricula.objects.filter(
                    año_lectivo=año_lectivo
                ).values_list('estudiante_id', flat=True)
                queryset = queryset.filter(id__in=estudiante_ids)
        
        # Filtro por grado
        if grado_filter and grado_filter != 'todos':
            queryset = queryset.filter(
                matriculas__grado_año_lectivo__grado__id=grado_filter
            )
        
        # Filtro por sede
        if sede_filter and sede_filter != 'todos':
            queryset = queryset.filter(matriculas__sede__id=sede_filter)
        
        # Filtro por estado del estudiante
        if estado_filter:
            if estado_filter == 'activo':
                queryset = queryset.filter(estado=True)
            elif estado_filter == 'inactivo':
                queryset = queryset.filter(estado=False)
        
        # Filtro por nivel escolar
        if nivel_filter and nivel_filter != 'todos':
            queryset = queryset.filter(
                matriculas__grado_año_lectivo__grado__nivel_escolar__id=nivel_filter
            )
        
        # Búsqueda
        if search:
            queryset = queryset.filter(
                Q(usuario__nombres__icontains=search) |
                Q(usuario__apellidos__icontains=search) |
                Q(usuario__numero_documento__icontains=search) |
                Q(usuario__email__icontains=search)
            )
        
        return queryset.distinct().select_related('usuario').order_by('usuario__apellidos', 'usuario__nombres')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Opciones de filtro
        context['años_lectivos'] = AñoLectivo.objects.all().order_by('-anho')
        context['grados'] = Grado.objects.all().order_by('nombre')
        context['sedes'] = Sede.objects.filter(estado=True)
        context['niveles'] = NivelEscolar.objects.all()
        
        # Estado del estudiante (no de matrícula)
        context['estados_estudiante'] = [
            ('activo', 'Activo'),
            ('inactivo', 'Inactivo'),
            ('todos', 'Todos')
        ]
        
        # Aplicar filtros al contexto
        for key in ['año', 'grado', 'sede', 'estado', 'search', 'nivel']:
            value = self.request.GET.get(key)
            if value:
                context[f'filter_{key}'] = value
        
        # Estadísticas
        context['total_estudiantes'] = Estudiante.objects.count()
        context['estudiantes_activos'] = Estudiante.objects.filter(estado=True).count()
        context['estudiantes_inactivos'] = Estudiante.objects.filter(estado=False).count()
        
        return context

class EstudianteDetailView(RoleRequiredMixin, DetailView):
    """Detalle completo de un estudiante"""
    template_name = 'rector/academico/estudiante/estudiante_detail.html'
    allowed_roles = ['Rector']
    model = Estudiante
    context_object_name = 'estudiante'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante = self.object
        
        # Información básica
        context['usuario'] = estudiante.usuario
        
        # Matrículas (todas, no solo la actual)
        context['matriculas'] = estudiante.matriculas.select_related(
            'grado_año_lectivo__grado',
            'sede',
            'año_lectivo'
        ).order_by('-año_lectivo__anho')
        
        # Año lectivo actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_actual
        
        # Si hay año actual, mostrar información específica
        if año_actual:
            matricula_actual = estudiante.matriculas.filter(
                año_lectivo=año_actual
            ).first()
            context['matricula_actual'] = matricula_actual
            
            # Notas del año actual
            context['notas_actual'] = Nota.objects.filter(
                estudiante=estudiante,
                periodo_academico__año_lectivo=año_actual
            ).select_related(
                'asignatura_grado_año_lectivo__asignatura',
                'periodo_academico__periodo'
            ).order_by('periodo_academico__periodo__nombre')
            
            # Asistencias del año actual
            context['asistencias'] = Asistencia.objects.filter(
                estudiante=estudiante,
                periodo_academico__año_lectivo=año_actual
            ).select_related('periodo_academico__periodo').order_by('-fecha')[:30]
            
            # Comportamientos del año actual
            context['comportamientos'] = Comportamiento.objects.filter(
                estudiante=estudiante,
                periodo_academico__año_lectivo=año_actual
            ).select_related(
                'docente__usuario',
                'periodo_academico__periodo'
            ).order_by('-fecha')
        
        # Historial completo de notas
        context['historial_notas'] = estudiante.get_notas_completas()

        # === DOCUMENTOS Y ARCHIVOS ===
        context['documentos_estudiante'] = self.obtener_documentos(estudiante)
        
        # Acudientes
        context['acudientes'] = estudiante.acudientes.all().select_related('acudiente')
        
        # Inconsistencias
        context['inconsistencias'] = Inconsistencia.objects.filter(
            estudiante=estudiante
        ).order_by('-fecha')
        
        return context
    
    
    def obtener_documentos(self, estudiante):
        """Obtener documentos relacionados con el estudiante"""
        from django.urls import reverse
        documentos = []
        
        # Constancias de años matriculados
        for año_str in estudiante.años_matriculados:
            # Buscar el año lectivo por su año (string)
            año_lectivo = AñoLectivo.objects.filter(anho=año_str).first()
            if año_lectivo:
                documentos.append({
                    'tipo': 'Constancia',
                    'nombre': f'Constancia de Estudio {año_str}',
                    'año': año_str,
                    'url': reverse('rector:constancia_individual_pdf', 
                                kwargs={
                                    'estudiante_id': estudiante.id,
                                    'año_lectivo_id': año_lectivo.id
                                }),
                    'icono': 'fa-file-certificate',
                    'color': 'primary'
                })

                documentos.append({
                'tipo': 'Boletín',
                'nombre': 'Boletín de Calificaciones',
                'año': año_lectivo.anho,
                'url': reverse('rector:boletin_individual_pdf',
                            kwargs={
                                'estudiante_id': estudiante.id,
                                'año_lectivo_id': año_lectivo.id
                            }),
                'icono': 'fa-chart-bar',
                'color': 'success'
                }),

                documentos.append({
                'tipo': 'Observador',
                'nombre': f'Observador {año_lectivo.anho}',
                'año': año_lectivo.anho,
                'url': reverse('rector:observador_individual_pdf',
                            kwargs={
                                'estudiante_id': estudiante.id,
                                'año_lectivo_id': año_lectivo.id
                            }),
                'icono': 'fa-clipboard-list',
                'color': 'warning'
                })
        
        # Observador del año actual
        if estudiante.matricula_actual:
            año_actual = estudiante.matricula_actual.año_lectivo
            documentos.append({
                'tipo': 'Observador',
                'nombre': f'Observador {año_actual.anho}',
                'año': año_actual.anho,
                'url': reverse('rector:observador_individual_pdf',
                            kwargs={
                                'estudiante_id': estudiante.id,
                                'año_lectivo_id': año_actual.id
                            }),
                'icono': 'fa-clipboard-list',
                'color': 'warning'
            })
        
        # Boletín de notas (año actual)
        if estudiante.matricula_actual:
            año_actual = estudiante.matricula_actual.año_lectivo
            documentos.append({
                'tipo': 'Boletín',
                'nombre': 'Boletín de Calificaciones',
                'año': año_actual.anho,
                'url': reverse('rector:boletin_individual_pdf',
                            kwargs={
                                'estudiante_id': estudiante.id,
                                'año_lectivo_id': año_actual.id
                            }),
                'icono': 'fa-chart-bar',
                'color': 'success'
            })
        
        return documentos

class EstudianteUpdateView(RoleRequiredMixin, UpdateView):
    template_name = 'rector/academico/estudiante/estudiante_form.html'
    allowed_roles = ['Rector']
    model = Estudiante
    fields = ['estado', 'foto']
    success_url = reverse_lazy('rector:estudiante_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accion'] = 'Editar'
        context['titulo'] = f'Editar Estudiante: {self.object.usuario.get_full_name()}'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Estudiante actualizado correctamente')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Error al actualizar el estudiante. Revise los datos.')
        return super().form_invalid(form)

class EstudianteToggleEstadoView(RoleRequiredMixin, View):
    allowed_roles = ['Rector']
    
    def post(self, request, pk):
        estudiante = get_object_or_404(Estudiante, pk=pk)
        estudiante.estado = not estudiante.estado
        estudiante.save()
        
        estado = "activado" if estudiante.estado else "desactivado"
        messages.success(request, f'Estudiante {estado} correctamente')
        
        return redirect('rector:estudiante_detail', pk=pk)

# ================== DOCENTES ==================
class DocenteListView(RoleRequiredMixin, ListView):
    """Lista completa de docentes con filtros avanzados"""
    template_name = 'rector/academico/docente/docente_list.html'
    allowed_roles = ['Rector']
    model = Docente
    context_object_name = 'docentes'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Docente.objects.select_related('usuario').all()
        
        # Filtros
        sede_filter = self.request.GET.get('sede')
        año_filter = self.request.GET.get('año')
        estado_filter = self.request.GET.get('estado')
        search = self.request.GET.get('search')
        
        # Filtro por sede
        if sede_filter and sede_filter != 'todos':
            queryset = queryset.filter(
                sedes_asignadas__sede__id=sede_filter,
                sedes_asignadas__estado=True
            ).distinct()
        
        # Filtro por año lectivo
        if año_filter and año_filter != 'todos':
            queryset = queryset.filter(
                sedes_asignadas__año_lectivo__id=año_filter,
                sedes_asignadas__estado=True
            ).distinct()
        
        # Filtro por estado
        if estado_filter:
            if estado_filter == 'activo':
                queryset = queryset.filter(estado=True)
            elif estado_filter == 'inactivo':
                queryset = queryset.filter(estado=False)
        
        # Búsqueda
        if search:
            queryset = queryset.filter(
                Q(usuario__nombres__icontains=search) |
                Q(usuario__apellidos__icontains=search) |
                Q(usuario__numero_documento__icontains=search) |
                Q(usuario__email__icontains=search) |
                Q(usuario__telefono__icontains=search)
            )
        
        return queryset.order_by('usuario__apellidos', 'usuario__nombres')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener año actual para estadísticas
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_actual
        
        # Opciones de filtro
        context['sedes'] = Sede.objects.filter(estado=True)
        context['años_lectivos'] = AñoLectivo.objects.all().order_by('-anho')
        
        # Estado del docente
        context['estados_docente'] = [
            ('activo', 'Activo'),
            ('inactivo', 'Inactivo'),
            ('todos', 'Todos')
        ]
        
        # Aplicar filtros al contexto
        for key in ['sede', 'año', 'estado', 'search']:
            value = self.request.GET.get(key)
            if value:
                context[f'filter_{key}'] = value
        
        # Estadísticas
        context['total_docentes'] = Docente.objects.count()
        context['docentes_activos'] = Docente.objects.filter(estado=True).count()
        context['docentes_inactivos'] = Docente.objects.filter(estado=False).count()
        
        # Docentes sin asignaturas en año actual
        if año_actual:
            docentes_con_asignaturas = AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo__año_lectivo=año_actual,
                docente__isnull=False
            ).values_list('docente_id', flat=True).distinct()
            
            context['docentes_sin_asignaturas'] = Docente.objects.filter(
                estado=True
            ).exclude(
                id__in=docentes_con_asignaturas
            ).count()
        else:
            context['docentes_sin_asignaturas'] = 0
        
        return context

class DocenteCreateView(RoleRequiredMixin, CreateView):
    """Crear un nuevo docente completo"""
    template_name = 'rector/academico/docente/docente_create.html'
    allowed_roles = ['Rector']
    form_class = DocenteCreateForm
    success_url = reverse_lazy('rector:docente_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Docente'
        context['accion'] = 'Crear'
        
        # Obtener año lectivo actual para mostrar
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_actual
        
        # Sedes disponibles
        context['sedes_disponibles'] = Sede.objects.filter(estado=True)
        
        return context
    
    def form_valid(self, form):
        # Intentar crear el docente
        try:
            docente = form.save()
            sede_asignada = form.cleaned_data.get('sede_inicial')
            año_lectivo = form.cleaned_data.get('año_lectivo_sede')
            
            # Construir mensaje de éxito
            mensaje = f'Docente {docente.usuario.get_full_name()} creado exitosamente. '
            mensaje += f'Usuario: {docente.usuario.username} - Contraseña temporal: {docente.usuario.numero_documento}'
            
            if sede_asignada and año_lectivo:
                # Verificar si se creó la asignación de sede
                asignacion_existe = DocenteSede.objects.filter(
                    docente=docente,
                    sede=sede_asignada,
                    año_lectivo=año_lectivo,
                    estado=True
                ).exists()
                
                if asignacion_existe:
                    mensaje += f' | Asignado a sede: {sede_asignada.nombre} ({año_lectivo.anho})'
                else:
                    mensaje += f' | <span class="text-warning">Nota: No se pudo asignar a la sede {sede_asignada.nombre}. Puede asignarla manualmente después.</span>'
            
            messages.success(self.request, mensaje)
            
            return redirect('rector:docente_detail', pk=docente.pk)
            
        except Exception as e:
            # Log del error para depuración
            import traceback
            print(f"Error al crear docente: {e}")
            print(traceback.format_exc())
            
            messages.error(
                self.request, 
                f'Error al crear el docente: {str(e)}. Por favor, verifique los datos e intente nuevamente.'
            )
            return self.render_to_response(self.get_context_data(form=form))
        
class DocenteDetailView(RoleRequiredMixin, DetailView):
    """Detalle completo de un docente"""
    template_name = 'rector/academico/docente/docente_detail.html'
    allowed_roles = ['Rector']
    model = Docente
    context_object_name = 'docente'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        docente = self.object
        
        # Información básica
        context['usuario'] = docente.usuario
        
        # Año lectivo actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_actual
        
        # Asignaturas que dicta en el año actual
        if año_actual:
            context['asignaturas_actuales'] = AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente,
                grado_año_lectivo__año_lectivo=año_actual
            ).select_related(
                'asignatura',
                'grado_año_lectivo__grado',
                'sede'
            ).order_by('asignatura__nombre')
        else:
            context['asignaturas_actuales'] = AsignaturaGradoAñoLectivo.objects.none()
        
        # Historial completo de asignaturas
        context['historial_asignaturas'] = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente
        ).select_related(
            'asignatura',
            'grado_año_lectivo__grado',
            'sede',
            'grado_año_lectivo__año_lectivo'
        ).order_by('-grado_año_lectivo__año_lectivo__anho')
        
        # Sedes asignadas (historial completo)
        context['sedes_asignadas'] = docente.sedes_asignadas.filter().select_related('sede', 'año_lectivo').order_by('-año_lectivo__anho')
        
        # Contactos de emergencia
        context['contactos'] = docente.contactos.all()
        
        # Comportamientos registrados (últimos 50)
        context['comportamientos_registrados'] = Comportamiento.objects.filter(
            docente=docente
        ).select_related(
            'estudiante__usuario',
            'periodo_academico__periodo',
            'periodo_academico__año_lectivo'
        ).order_by('-fecha')[:50]
        
        # Estadísticas de comportamientos
        if context['comportamientos_registrados']:
            total = len(context['comportamientos_registrados'])
            positivos = sum(1 for c in context['comportamientos_registrados'] if c.tipo == 'Positivo')
            context['estadisticas_comportamientos'] = {
                'total': total,
                'positivos': positivos,
                'negativos': total - positivos,
                'porcentaje_positivo': round((positivos / total) * 100, 1) if total > 0 else 0
            }
        
        # Formularios para acciones rápidas
        context['form_asignatura'] = AsignaturaDocenteForm(
            initial={'docente': docente.id}
        )
        context['form_sede'] = DocenteSedeForm(
            initial={'docente': docente.id}
        )
        
        return context

class DocenteUpdateView(RoleRequiredMixin, UpdateView):
    """Actualizar información del perfil docente"""
    template_name = 'rector/academico/docente/docente_form.html'
    allowed_roles = ['Rector']
    model = Docente
    form_class = DocenteUpdateForm
    success_url = reverse_lazy('rector:docente_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accion'] = 'Editar Perfil'
        context['titulo'] = f'Editar Docente: {self.object.usuario.get_full_name()}'
        return context
    
    def get_success_url(self):
        messages.success(self.request, 'Perfil docente actualizado correctamente')
        return reverse('rector:docente_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        return response

class DocenteInformacionPersonalView(RoleRequiredMixin, UpdateView):
    """Editar información personal del docente (datos del usuario)"""
    template_name = 'rector/academico/docente/docente_informacion_personal_form.html'
    allowed_roles = ['Rector']
    form_class = DocenteInformacionPersonalForm
    
    def get_object(self):
        # Obtener el usuario del docente
        docente = get_object_or_404(Docente, pk=self.kwargs['pk'])
        return docente.usuario
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        docente = get_object_or_404(Docente, pk=self.kwargs['pk'])
        context['docente'] = docente
        context['titulo'] = f'Editar Información Personal: {docente.usuario.get_full_name()}'
        return context
    
    def get_success_url(self):
        docente_pk = self.kwargs['pk']
        messages.success(self.request, 'Información personal actualizada correctamente')
        return reverse('rector:docente_detail', kwargs={'pk': docente_pk})

class DocenteToggleEstadoView(RoleRequiredMixin, View):
    """Cambiar el estado activo/inactivo de un docente"""
    allowed_roles = ['Rector']
    
    def post(self, request, pk):
        docente = get_object_or_404(Docente, pk=pk)
        docente.estado = not docente.estado
        docente.save()
        
        estado = "activado" if docente.estado else "desactivado"
        messages.success(request, f'Docente {estado} correctamente')
        
        return redirect('rector:docente_detail', pk=pk)
    
# ================== VISTAS ADICIONALES ACADÉMICAS ==================

class GradoListView(RoleRequiredMixin, ListView):
    """Lista de grados con estadísticas por año lectivo"""
    template_name = 'rector/academico/grado/grado_list.html'
    allowed_roles = ['Rector']
    model = Grado
    context_object_name = 'grados'
    
    def get_queryset(self):
        queryset = Grado.objects.select_related('nivel_escolar').order_by('nivel_escolar__nombre', 'nombre')
        
        # Filtros
        nivel_filter = self.request.GET.get('nivel')
        año_filter = self.request.GET.get('año')
        sede_filter = self.request.GET.get('sede')
        
        if nivel_filter and nivel_filter != 'todos':
            queryset = queryset.filter(nivel_escolar__id=nivel_filter)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener año actual y filtros
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        año_selected = self.request.GET.get('año')
        sede_selected = self.request.GET.get('sede')
        
        # Si se seleccionó un año específico, usarlo
        if año_selected and año_selected != 'todos':
            año_lectivo = AñoLectivo.objects.filter(id=año_selected).first()
        else:
            año_lectivo = año_actual
        
        # Opciones de filtro
        context['años_lectivos'] = AñoLectivo.objects.all().order_by('-anho')
        context['niveles'] = NivelEscolar.objects.all()
        context['sedes'] = Sede.objects.filter(estado=True)
        
        # Aplicar filtros al contexto
        context['filter_año'] = año_selected or ''
        context['filter_sede'] = sede_selected or ''
        context['filter_nivel'] = self.request.GET.get('nivel', '')
        
        # Estadísticas para cada grado
        if año_lectivo:
            context['año_lectivo_actual'] = año_lectivo
            
            # Agregar estadísticas a cada grado
            for grado in context['grados']:
                # Total de estudiantes en el grado (filtrado por sede si se especifica)
                filters = {
                    'grado_año_lectivo__grado': grado,
                    'año_lectivo': año_lectivo,
                    'estado': 'ACT'
                }
                
                if sede_selected and sede_selected != 'todos':
                    filters['sede__id'] = sede_selected
                
                grado.total_estudiantes = Matricula.objects.filter(**filters).count()
                
                # Grados asignados a año lectivo
                grado.asignado_a_año = GradoAñoLectivo.objects.filter(
                    grado=grado,
                    año_lectivo=año_lectivo,
                    estado=True
                ).exists()
                
                # ID del grado año lectivo si está asignado
                if grado.asignado_a_año:
                    grado_año = GradoAñoLectivo.objects.filter(
                        grado=grado,
                        año_lectivo=año_lectivo
                    ).first()
                    grado.grado_año_lectivo_id = grado_año.id if grado_año else None
                
                # Docentes asignados a asignaturas de este grado
                docente_filters = {
                    'grado_año_lectivo__grado': grado,
                    'grado_año_lectivo__año_lectivo': año_lectivo,
                    'docente__isnull': False
                }
                
                if sede_selected and sede_selected != 'todos':
                    docente_filters['sede__id'] = sede_selected
                
                grado.total_docentes = AsignaturaGradoAñoLectivo.objects.filter(
                    **docente_filters
                ).values('docente').distinct().count()
                
                # Promedio académico del grado
                nota_filters = {
                    'estudiante__matriculas__grado_año_lectivo__grado': grado,
                    'periodo_academico__año_lectivo': año_lectivo
                }
                
                if sede_selected and sede_selected != 'todos':
                    nota_filters['estudiante__matriculas__sede__id'] = sede_selected
                
                notas = Nota.objects.filter(**nota_filters).aggregate(
                    promedio=Avg('calificacion'),
                    total=Count('id')
                )
                
                grado.promedio = round(notas['promedio'] or 0, 1)
                grado.total_notas = notas['total'] or 0
        else:
            context['año_lectivo_actual'] = None
        
        # Estadísticas generales
        context['total_grados'] = Grado.objects.count()
        if año_lectivo:
            context['grados_asignados'] = GradoAñoLectivo.objects.filter(
                año_lectivo=año_lectivo
            ).count()
            context['estudiantes_totales'] = Matricula.objects.filter(
                año_lectivo=año_lectivo,
                estado='ACT'
            ).count()
        
        return context

class GradoDetailView(RoleRequiredMixin, DetailView):
    """Detalle de un grado con todas sus asignaturas"""
    template_name = 'rector/academico/grado/grado_detail.html'
    allowed_roles = ['Rector']
    model = Grado
    context_object_name = 'grado'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        grado = self.object
        
        # Obtener año lectivo actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_actual
        
        # Asignaturas por año lectivo
        años_lectivos = AñoLectivo.objects.filter(
            grados_año_lectivo__grado=grado
        ).distinct().order_by('-anho')
        
        asignaturas_por_año = []
        for año in años_lectivos:
            asignaturas = AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo__grado=grado,
                grado_año_lectivo__año_lectivo=año
            ).select_related(
                'asignatura',
                'sede',
                'docente__usuario'
            )
            
            asignaturas_por_año.append({
                'año': año,
                'asignaturas': asignaturas,
                'total': asignaturas.count()
            })
        
        context['asignaturas_por_año'] = asignaturas_por_año
        
        # Estadísticas
        if año_actual:
            context['matriculas_actual'] = Matricula.objects.filter(
                grado_año_lectivo__grado=grado,
                año_lectivo=año_actual,
                estado='ACT'
            ).count()
            
            context['docentes_actual'] = AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo__grado=grado,
                grado_año_lectivo__año_lectivo=año_actual,
                docente__isnull=False
            ).values('docente').distinct().count()
        
        # Logros del grado
        context['logros'] = Logro.objects.filter(
            grado=grado
        ).select_related(
            'asignatura',
            'periodo_academico__periodo',
            'periodo_academico__año_lectivo'
        ).order_by('-periodo_academico__año_lectivo__anho')[:10]
        
        return context

class GradoAñoLectivoCreateView(RoleRequiredMixin, CreateView):
    """Asignar un grado a un año lectivo"""
    template_name = 'rector/academico/grado/gradoañoelectivo_form.html'
    allowed_roles = ['Rector']
    form_class = GradoAñoLectivoForm
    success_url = reverse_lazy('rector:grado_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accion'] = 'Asignar'
        context['titulo'] = 'Asignar Grado a Año Lectivo'
        
        # Obtener año lectivo de la URL si está presente
        año_id = self.request.GET.get('año')
        if año_id:
            try:
                context['año_lectivo'] = AñoLectivo.objects.get(id=año_id)
                # Pre-seleccionar el año lectivo en el formulario
                self.initial['año_lectivo'] = context['año_lectivo']
            except AñoLectivo.DoesNotExist:
                pass
        
        # Filtrar grados que no estén ya asignados a este año
        if 'año_lectivo' in context:
            grados_asignados = GradoAñoLectivo.objects.filter(
                año_lectivo=context['año_lectivo']
            ).values_list('grado_id', flat=True)
            
            # Actualizar el queryset del campo grado
            context['form'].fields['grado'].queryset = Grado.objects.exclude(
                id__in=grados_asignados
            ).order_by('nombre')
            
            # Grados disponibles para mostrar en tabla informativa
            context['grados_disponibles'] = Grado.objects.exclude(
                id__in=grados_asignados
            ).select_related('nivel_escolar').order_by('nombre')
        
        return context
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Asegurar que los campos tengan las clases correctas
        for field_name in form.fields:
            if field_name not in ['estado']:  # Excluir checkbox
                form.fields[field_name].widget.attrs.update({'class': 'form-control select2'})
        return form
    
    def form_valid(self, form):
        # Verificar que el grado no esté ya asignado a este año
        if GradoAñoLectivo.objects.filter(
            grado=form.cleaned_data['grado'],
            año_lectivo=form.cleaned_data['año_lectivo']
        ).exists():
            messages.error(self.request, 'Este grado ya está asignado a este año lectivo.')
            return self.form_invalid(form)
        
        messages.success(self.request, 'Grado asignado al año lectivo exitosamente')
        return super().form_valid(form)

class GradoAñoLectivoUpdateView(RoleRequiredMixin, UpdateView):
    """Modificar asignación de grado a año lectivo"""
    template_name = 'rector/academico/grado/gradoañoelectivo_form.html'
    allowed_roles = ['Rector']
    model = GradoAñoLectivo
    form_class = GradoAñoLectivoUpdateForm
    success_url = reverse_lazy('rector:grado_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accion'] = 'Modificar'
        context['titulo'] = f'Modificar Asignación: {self.object.grado.nombre}'
        context['grado_actual'] = self.object.grado
        context['año_lectivo_actual'] = self.object.año_lectivo
        return context
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Asegurar que el checkbox tenga la clase correcta
        form.fields['estado'].widget.attrs.update({'class': 'form-check-input'})
        return form
    
    def form_valid(self, form):
        messages.success(self.request, 'Asignación de grado actualizada exitosamente')
        return super().form_valid(form)

class GradoAñoLectivoDeleteView(RoleRequiredMixin, DeleteView):
    """Eliminar asignación de grado a año lectivo"""
    template_name = 'rector/academico/grado/gradoañoelectivo_confirm_delete.html'
    allowed_roles = ['Rector']
    model = GradoAñoLectivo
    success_url = reverse_lazy('rector:grado_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Grado removido del año lectivo exitosamente')
        return super().delete(request, *args, **kwargs)
    
class NivelEscolarListView(RoleRequiredMixin, ListView):
    """Lista de niveles escolares con estadísticas"""
    template_name = 'rector/academico/grado/nivel_list.html'
    allowed_roles = ['Rector']
    model = NivelEscolar
    context_object_name = 'niveles'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener año actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        # Agregar estadísticas a cada nivel
        for nivel in context['niveles']:
            # Total de grados en este nivel
            nivel.total_grados = nivel.grados.count()
            
            # Total de estudiantes en este nivel (año actual)
            if año_actual:
                nivel.total_estudiantes = Matricula.objects.filter(
                    grado_año_lectivo__grado__nivel_escolar=nivel,
                    año_lectivo=año_actual,
                    estado='ACT'
                ).count()
            else:
                nivel.total_estudiantes = 0
            
            # Áreas del conocimiento
            nivel.total_areas = nivel.areas.count()
            
            # Asignaturas totales
            nivel.total_asignaturas = Asignatura.objects.filter(
                area__nivel_escolar=nivel
            ).count()
        
        return context

class NivelEscolarDetailView(RoleRequiredMixin, DetailView):
    """Detalle de un nivel escolar"""
    template_name = 'rector/academico/grado/nivel_detail.html'
    allowed_roles = ['Rector']
    model = NivelEscolar
    context_object_name = 'nivel'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        nivel = self.object
        
        # Grados pertenecientes a este nivel
        context['grados'] = nivel.grados.all().order_by('nombre')
        
        # Áreas del conocimiento
        context['areas'] = nivel.areas.all().order_by('nombre')
        
        # Estadísticas por año lectivo
        años_lectivos = AñoLectivo.objects.all().order_by('-anho')[:5]
        context['estadisticas_por_año'] = []
        
        for año in años_lectivos:
            estudiantes = Matricula.objects.filter(
                grado_año_lectivo__grado__nivel_escolar=nivel,
                año_lectivo=año,
                estado='ACT'
            ).count()
            
            context['estadisticas_por_año'].append({
                'año': año,
                'estudiantes': estudiantes,
                'grados_asignados': GradoAñoLectivo.objects.filter(
                    grado__nivel_escolar=nivel,
                    año_lectivo=año
                ).count()
            })
        
        # Año lectivo actual para referencia
        año_lectivo_actual = AñoLectivo.objects.filter(estado=True).first()

        context['grados'] = nivel.grados.annotate(
            asignado=Exists(
                GradoAñoLectivo.objects.filter(
                    grado=OuterRef('pk'),
                    año_lectivo=año_lectivo_actual
                )
            )
        ).order_by('nombre')

        context['año_lectivo_actual'] = año_lectivo_actual
        
        return context

# ================== ÁREAS DEL CONOCIMIENTO ==================

class AreaListView(RoleRequiredMixin, ListView):
    """Lista de áreas del conocimiento"""
    template_name = 'rector/academico/area/area_list.html'
    allowed_roles = ['Rector']
    model = Area
    context_object_name = 'areas'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Area.objects.select_related('nivel_escolar').order_by('nivel_escolar__nombre', 'nombre')
        
        # Filtros
        nivel_filter = self.request.GET.get('nivel')
        search = self.request.GET.get('search')
        
        if nivel_filter and nivel_filter != 'todos':
            queryset = queryset.filter(nivel_escolar__id=nivel_filter)
        
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(nivel_escolar__nombre__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener año actual para estadísticas
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_actual
        
        # Opciones de filtro
        context['niveles'] = NivelEscolar.objects.all()
        
        # Aplicar filtros al contexto
        for key in ['nivel', 'search']:
            value = self.request.GET.get(key)
            if value:
                context[f'filter_{key}'] = value
        
        # Estadísticas
        context['total_areas'] = Area.objects.count()
        
        # Contar asignaturas por área
        for area in context['areas']:
            area.total_asignaturas = area.asignaturas.count()
            # Grados del nivel
            area.total_grados = area.nivel_escolar.grados.count()
        
        return context

class AreaDetailView(RoleRequiredMixin, DetailView):
    """Detalle de un área del conocimiento"""
    template_name = 'rector/academico/area/area_detail.html'
    allowed_roles = ['Rector']
    model = Area
    context_object_name = 'area'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        area = self.object
        
        # Asignaturas de esta área
        context['asignaturas'] = area.asignaturas.all().order_by('nombre')
        
        # Grados del nivel escolar
        context['grados'] = area.nivel_escolar.grados.all().order_by('nombre')
        
        # Estadísticas
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if año_actual:
            # Asignaturas dictadas este año
            context['asignaturas_dictadas'] = AsignaturaGradoAñoLectivo.objects.filter(
                asignatura__area=area,
                grado_año_lectivo__año_lectivo=año_actual
            ).select_related(
                'asignatura',
                'grado_año_lectivo__grado',
                'sede',
                'docente__usuario'
            )
            
            # Total de grados que tienen asignaturas de esta área
            context['total_grados_dictados'] = context['asignaturas_dictadas'].values(
                'grado_año_lectivo__grado'
            ).distinct().count()
        
        return context

class AreaCreateView(RoleRequiredMixin, CreateView):
    """Crear nueva área del conocimiento"""
    template_name = 'rector/academico/area/area_form.html'
    allowed_roles = ['Rector']
    model = Area
    form_class = AreaForm
    success_url = reverse_lazy('rector:area_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accion'] = 'Crear'
        context['titulo'] = 'Nueva Área del Conocimiento'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Área creada exitosamente')
        return super().form_valid(form)

class AreaUpdateView(RoleRequiredMixin, UpdateView):
    """Actualizar área del conocimiento"""
    template_name = 'rector/academico/area/area_form.html'
    allowed_roles = ['Rector']
    model = Area
    form_class = AreaForm
    success_url = reverse_lazy('rector:area_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accion'] = 'Editar'
        context['titulo'] = f'Editar Área: {self.object.nombre}'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Área actualizada exitosamente')
        return super().form_valid(form)

class AreaDeleteView(RoleRequiredMixin, DeleteView):
    """Eliminar área del conocimiento"""
    template_name = 'rector/academico/area/area_confirm_delete.html'
    allowed_roles = ['Rector']
    model = Area
    success_url = reverse_lazy('rector:area_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['asignaturas_count'] = self.object.asignaturas.count()
        return context
    
    def delete(self, request, *args, **kwargs):
        area = self.get_object()
        
        # Verificar si tiene asignaturas
        if area.asignaturas.exists():
            messages.error(
                request, 
                f'No se puede eliminar el área "{area.nombre}" porque tiene {area.asignaturas.count()} asignaturas asociadas.'
            )
            return redirect('rector:area_list')
        
        messages.success(self.request, 'Área eliminada exitosamente')
        return super().delete(request, *args, **kwargs)

# ================== ASIGNATURAS ==================
class AsignaturaListView(RoleRequiredMixin, ListView):
    """Lista de asignaturas con estadísticas"""
    template_name = 'rector/academico/asignatura/asignatura_list.html'
    allowed_roles = ['Rector']
    model = Asignatura
    context_object_name = 'asignaturas'
    paginate_by = 25  # Aumenta a 25
    
    def get_queryset(self):
        queryset = Asignatura.objects.select_related('area', 'area__nivel_escolar').order_by('area__nivel_escolar__nombre', 'area__nombre', 'nombre')
        
        # Filtros
        area_filter = self.request.GET.get('area')
        nivel_filter = self.request.GET.get('nivel')
        search = self.request.GET.get('search')
        
        if area_filter and area_filter != 'todos':
            queryset = queryset.filter(area__id=area_filter)
        
        if nivel_filter and nivel_filter != 'todos':
            queryset = queryset.filter(area__nivel_escolar__id=nivel_filter)
        
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(area__nombre__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener año actual para estadísticas
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_actual
        
        # Opciones de filtro
        context['areas'] = Area.objects.select_related('nivel_escolar').order_by('nivel_escolar__nombre', 'nombre')
        context['niveles'] = NivelEscolar.objects.all()
        
        # Aplicar filtros al contexto
        for key in ['area', 'nivel', 'search']:
            value = self.request.GET.get(key)
            if value:
                context[f'filter_{key}'] = value
        
        # Estadísticas generales
        context['total_asignaturas'] = Asignatura.objects.count()
        
        # Estadísticas por nivel
        niveles_stats = []
        for nivel in NivelEscolar.objects.all():
            asignaturas_nivel = Asignatura.objects.filter(area__nivel_escolar=nivel).count()
            areas_nivel = Area.objects.filter(nivel_escolar=nivel).count()
            
            niveles_stats.append({
                'nivel': nivel,
                'asignaturas': asignaturas_nivel,
                'areas': areas_nivel,
                'promedio': round(asignaturas_nivel / max(areas_nivel, 1), 1) if areas_nivel > 0 else 0
            })
        
        context['niveles_stats'] = niveles_stats
        
        # Agregar estadísticas a cada asignatura
        for asignatura in context['asignaturas']:
            # Total de veces dictada
            asignatura.total_dictada = AsignaturaGradoAñoLectivo.objects.filter(
                asignatura=asignatura
            ).count()
            
            # Dictada actualmente
            if año_actual:
                context['asignaturas_dictadas_actual'] = AsignaturaGradoAñoLectivo.objects.filter(
                    grado_año_lectivo__año_lectivo=año_actual
                ).values('asignatura').distinct().count()
            else:
                context['asignaturas_dictadas_actual'] = 0
        
        return context

class AsignaturaDetailView(RoleRequiredMixin, DetailView):
    """Detalle de una asignatura"""
    template_name = 'rector/academico/asignatura/asignatura_detail.html'
    allowed_roles = ['Rector']
    model = Asignatura
    context_object_name = 'asignatura'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asignatura = self.object

        # Año lectivo actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_actual

        # Obtener datos del historial
        qs_base = AsignaturaGradoAñoLectivo.objects.filter(
            asignatura=asignatura
        ).select_related(
            'grado_año_lectivo__grado',
            'grado_año_lectivo__año_lectivo',
            'sede',
            'docente__usuario'
        )

        # Datos del año actual
        if año_actual:
            context['grados_dictados'] = qs_base.filter(
                grado_año_lectivo__año_lectivo=año_actual
            ).order_by('grado_año_lectivo__grado__nombre')
            
            context['asignaturas_dictadas'] = context['grados_dictados']
            
            # Estadísticas de notas del año actual
            notas_filters = {
                'asignatura_grado_año_lectivo__asignatura': asignatura,
                'periodo_academico__año_lectivo': año_actual
            }
            
            context['estadisticas_notas'] = Nota.objects.filter(
                **notas_filters
            ).aggregate(
                promedio=Avg('calificacion'),
                total=Count('id'),
                maximo=Max('calificacion'),
                minimo=Min('calificacion')
            )

        # Historial completo
        historial = qs_base.order_by(
            '-grado_año_lectivo__año_lectivo__anho',
            'grado_año_lectivo__grado__nombre'
        )
        context['historial_dictado'] = historial

        # Agrupar por año para el template
        historial_por_año = {}
        for dictado in historial:
            año = dictado.grado_año_lectivo.año_lectivo.anho
            if año not in historial_por_año:
                historial_por_año[año] = []
            historial_por_año[año].append(dictado)
        
        context['historial_por_año'] = historial_por_año

        # Estadísticas generales
        context.update({
            'total_años_dictada': historial.values(
                'grado_año_lectivo__año_lectivo'
            ).distinct().count(),
            'total_grados_atendidos': historial.values(
                'grado_año_lectivo__grado'
            ).distinct().count(),
            'total_docentes_diferentes': historial.filter(
                docente__isnull=False
            ).values('docente').distinct().count(),
            'total_sedes_diferentes': historial.values('sede').distinct().count(),
            'total_dictados': historial.count(),
        })

        # Asignaturas relacionadas (misma área)
        context['asignaturas_relacionadas'] = Asignatura.objects.filter(
            area=asignatura.area
        ).exclude(
            id=asignatura.id
        ).order_by('nombre')[:6]

        return context
    
class AsignaturaCreateView(RoleRequiredMixin, CreateView):
    """Crear nueva asignatura"""
    template_name = 'rector/academico/asignatura/asignatura_form.html'
    allowed_roles = ['Rector']
    model = Asignatura
    form_class = AsignaturaForm
    success_url = reverse_lazy('rector:asignatura_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accion'] = 'Crear'
        context['titulo'] = 'Nueva Asignatura'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Asignatura creada exitosamente')
        return super().form_valid(form)

class AsignaturaUpdateView(RoleRequiredMixin, UpdateView):
    """Actualizar asignatura"""
    template_name = 'rector/academico/asignatura/asignatura_form.html'
    allowed_roles = ['Rector']
    model = Asignatura
    form_class = AsignaturaForm
    success_url = reverse_lazy('rector:asignatura_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accion'] = 'Editar'
        context['titulo'] = f'Editar Asignatura: {self.object.nombre}'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Asignatura actualizada exitosamente')
        return super().form_valid(form)

class AsignaturaDeleteView(RoleRequiredMixin, DeleteView):
    """Eliminar asignatura"""
    template_name = 'rector/academico/asignatura/asignatura_confirm_delete.html'
    allowed_roles = ['Rector']
    model = Asignatura
    success_url = reverse_lazy('rector:asignatura_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Verificar uso de la asignatura
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if año_actual:
            context['asignaturas_dictadas'] = AsignaturaGradoAñoLectivo.objects.filter(
                asignatura=self.object,
                grado_año_lectivo__año_lectivo=año_actual
            ).count()
        
        context['total_dictados'] = AsignaturaGradoAñoLectivo.objects.filter(
            asignatura=self.object
        ).count()
        
        return context
    
    def delete(self, request, *args, **kwargs):
        asignatura = self.get_object()
        
        # Verificar si está siendo dictada actualmente
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if año_actual:
            dictada_actual = AsignaturaGradoAñoLectivo.objects.filter(
                asignatura=asignatura,
                grado_año_lectivo__año_lectivo=año_actual
            ).exists()
            
            if dictada_actual:
                messages.error(
                    request, 
                    f'No se puede eliminar la asignatura "{asignatura.nombre}" porque está siendo dictada en el año lectivo actual.'
                )
                return redirect('rector:asignatura_list')
        
        # Verificar si tiene logros asociados
        if asignatura.logros.exists():
            messages.error(
                request, 
                f'No se puede eliminar la asignatura "{asignatura.nombre}" porque tiene logros académicos asociados.'
            )
            return redirect('rector:asignatura_list')
        
        messages.success(self.request, 'Asignatura eliminada exitosamente')
        return super().delete(request, *args, **kwargs)

class AsignaturaBulkCreateView(RoleRequiredMixin, FormView):
    """Crear múltiples asignaturas a la vez"""
    template_name = 'rector/academico/asignatura/asignatura_bulk_form.html'
    allowed_roles = ['Rector']
    form_class = AsignaturaBulkForm
    success_url = reverse_lazy('rector:asignatura_list')
    
    def form_valid(self, form):
        area = form.cleaned_data['area']
        nombres_text = form.cleaned_data['nombres']
        ih = form.cleaned_data['ih']
        
        # Procesar cada línea
        nombres = [nombre.strip() for nombre in nombres_text.split('\n') if nombre.strip()]
        
        creadas = 0
        duplicadas = 0
        errores = []
        
        for nombre in nombres:
            # Verificar si ya existe
            if Asignatura.objects.filter(nombre__iexact=nombre, area=area).exists():
                duplicadas += 1
                continue
            
            try:
                Asignatura.objects.create(
                    nombre=nombre,
                    area=area,
                    ih=ih if ih else None
                )
                creadas += 1
            except Exception as e:
                errores.append(f'{nombre}: {str(e)}')
        
        # Mensaje de resultado
        if creadas > 0:
            messages.success(self.request, f'Se crearon {creadas} asignaturas exitosamente.')
        
        if duplicadas > 0:
            messages.warning(self.request, f'Se omitieron {duplicadas} asignaturas porque ya existían.')
        
        if errores:
            messages.error(self.request, f'Hubo {len(errores)} errores al crear algunas asignaturas.')
            for error in errores[:5]:  # Mostrar solo los primeros 5 errores
                messages.error(self.request, error)
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear Múltiples Asignaturas'
        return context

# ================== ASIGNACIÓN DE ASIGNATURAS A GRADOS ==================

class AsignaturaGradoCreateView(RoleRequiredMixin, CreateView):
    """Asignar una asignatura a un grado"""
    template_name = 'rector/academico/asignatura/asignatura_grado_form.html'
    allowed_roles = ['Rector']
    model = AsignaturaGradoAñoLectivo
    form_class = AsignaturaGradoForm
    success_url = reverse_lazy('rector:asignatura_list')
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Pre-seleccionar valores de la URL
        asignatura_id = self.request.GET.get('asignatura')
        año_id = self.request.GET.get('año')
        grado_id = self.request.GET.get('grado')
        
        if asignatura_id:
            try:
                initial['asignatura'] = Asignatura.objects.get(id=asignatura_id)
            except Asignatura.DoesNotExist:
                pass
        
        if año_id and grado_id:
            try:
                año_lectivo = AñoLectivo.objects.get(id=año_id)
                grado = Grado.objects.get(id=grado_id)
                grado_año = GradoAñoLectivo.objects.get(
                    grado=grado,
                    año_lectivo=año_lectivo
                )
                initial['grado_año_lectivo'] = grado_año
            except (AñoLectivo.DoesNotExist, Grado.DoesNotExist, GradoAñoLectivo.DoesNotExist):
                pass
        
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Asignar Asignatura a Grado'
        context['accion'] = 'Asignar'
        
        # Obtener año lectivo actual para información
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_actual
        
        return context
    
    def form_valid(self, form):
        # Verificar que no exista ya la asignación
        if AsignaturaGradoAñoLectivo.objects.filter(
            asignatura=form.cleaned_data['asignatura'],
            grado_año_lectivo=form.cleaned_data['grado_año_lectivo'],
            sede=form.cleaned_data['sede']
        ).exists():
            messages.error(
                self.request,
                'Esta asignatura ya está asignada a este grado en esta sede.'
            )
            return self.form_invalid(form)
        
        messages.success(
            self.request,
            f'Asignatura asignada exitosamente al grado.'
        )
        return super().form_valid(form)

class AsignaturaGradoUpdateView(RoleRequiredMixin, UpdateView):
    """Actualizar asignación de asignatura a grado"""
    template_name = 'rector/academico/asignatura/asignatura_grado_form.html'
    allowed_roles = ['Rector']
    model = AsignaturaGradoAñoLectivo
    form_class = AsignaturaGradoForm
    success_url = reverse_lazy('rector:asignatura_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Modificar Asignación de Asignatura'
        context['accion'] = 'Modificar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Asignación actualizada exitosamente')
        return super().form_valid(form)

class AsignaturaGradoDeleteView(RoleRequiredMixin, DeleteView):
    """Eliminar asignación de asignatura a grado"""
    template_name = 'rector/academico/asignatura/asignatura_grado_confirm_delete.html'
    allowed_roles = ['Rector']
    model = AsignaturaGradoAñoLectivo
    
    def get_success_url(self):
        # Redirigir a la asignatura o al grado según sea apropiado
        if self.request.GET.get('from_asignatura'):
            return reverse('rector:asignatura_detail', kwargs={'pk': self.object.asignatura.pk})
        elif self.request.GET.get('from_grado'):
            return reverse('rector:grado_detail', kwargs={'pk': self.object.grado_año_lectivo.grado.pk})
        return reverse('rector:asignatura_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Verificar si tiene notas asociadas
        año_lectivo = self.object.grado_año_lectivo.año_lectivo
        tiene_notas = Nota.objects.filter(
            asignatura_grado_año_lectivo=self.object,
            periodo_academico__año_lectivo=año_lectivo
        ).exists()
        
        context['tiene_notas'] = tiene_notas
        context['from_asignatura'] = self.request.GET.get('from_asignatura')
        context['from_grado'] = self.request.GET.get('from_grado')
        
        return context
    
    def delete(self, request, *args, **kwargs):
        asignatura_grado = self.get_object()
        
        # Verificar si tiene notas
        año_lectivo = asignatura_grado.grado_año_lectivo.año_lectivo
        tiene_notas = Nota.objects.filter(
            asignatura_grado_año_lectivo=asignatura_grado,
            periodo_academico__año_lectivo=año_lectivo
        ).exists()
        
        if tiene_notas:
            messages.error(
                request,
                'No se puede eliminar esta asignación porque tiene calificaciones registradas.'
            )
            return redirect(self.get_success_url())
        
        messages.success(request, 'Asignación eliminada exitosamente')
        return super().delete(request, *args, **kwargs)
      
# ================== VISTAS ADICIONALES PARA ESTUDIANTES ==================
class EstudianteEditarInformacionBaseView(RoleRequiredMixin, UpdateView):
    """Editar información base del estudiante (datos del usuario)"""
    template_name = 'rector/academico/estudiante/estudiante_editar_informacion.html'
    allowed_roles = ['Rector']
    model = Usuario
    fields = [
        'nombres', 'apellidos', 'email', 'telefono', 'direccion',
        'fecha_nacimiento', 'sexo', 'tipo_documento', 'numero_documento'
    ]
    
    def get_object(self):
        """Obtener el usuario del estudiante"""
        estudiante = get_object_or_404(Estudiante, pk=self.kwargs['pk'])
        return estudiante.usuario
    
    def get_form(self, form_class=None):
        """Personalizar el formulario"""
        form = super().get_form(form_class)
        
        # Agregar placeholders
        form.fields['nombres'].widget.attrs['placeholder'] = 'Ingrese nombres'
        form.fields['apellidos'].widget.attrs['placeholder'] = 'Ingrese apellidos'
        form.fields['numero_documento'].widget.attrs['placeholder'] = 'Ingrese número de documento'
        form.fields['email'].widget.attrs['placeholder'] = 'ejemplo@email.com'
        form.fields['telefono'].widget.attrs['placeholder'] = 'Ingrese número telefónico'
        form.fields['direccion'].widget.attrs['placeholder'] = 'Ingrese dirección completa'
        form.fields['fecha_nacimiento'].widget.attrs['class'] = 'form-control'
        
        return form
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Registrar cambios
        cambios = []
        if 'nombres' in form.changed_data:
            cambios.append(f"nombres: {form.cleaned_data['nombres']}")
        if 'apellidos' in form.changed_data:
            cambios.append(f"apellidos: {form.cleaned_data['apellidos']}")
        if 'numero_documento' in form.changed_data:
            cambios.append(f"documento: {form.cleaned_data['numero_documento']}")
            # Actualizar username
            self.object.username = form.cleaned_data['numero_documento']
            self.object.save()
        
        if cambios:
            messages.success(
                self.request, 
                f'Información personal actualizada correctamente. '
                f'Cambios: {", ".join(cambios)}'
            )
        else:
            messages.info(self.request, 'No se realizaron cambios en la información personal.')
        
        return response
    
    def form_invalid(self, form):
        """Manejar formulario inválido"""
        messages.error(self.request, 'Error al actualizar la información. Revise los datos.')
        return super().form_invalid(form)
    
    def get_success_url(self):
        """URL de redirección después de éxito"""
        estudiante_pk = self.kwargs['pk']
        return reverse_lazy('rector:estudiante_detail', kwargs={'pk': estudiante_pk})
    
    def get_context_data(self, **kwargs):
        """Agregar contexto adicional"""
        context = super().get_context_data(**kwargs)
        estudiante = get_object_or_404(Estudiante, pk=self.kwargs['pk'])
        
        context.update({
            'estudiante': estudiante,
            'titulo': f'Editar Información Personal: {estudiante.usuario.get_full_name()}',
            'accion': 'editar',
            'edad_actual': estudiante.usuario.edad,
        })
        
        return context

class AcudienteEditarInformacionView(RoleRequiredMixin, UpdateView):
    """Editar información de un acudiente"""
    template_name = 'rector/academico/acudiente/acudiente_editar_informacion.html'
    allowed_roles = ['Rector']
    model = Usuario
    fields = [
        'nombres', 'apellidos', 'email', 'telefono', 'direccion',
        'tipo_documento', 'numero_documento'
    ]
    
    def get_object(self):
        # Obtener el usuario del acudiente
        acudiente_rel = get_object_or_404(Acudiente, pk=self.kwargs['acudiente_pk'])
        return acudiente_rel.acudiente
    
    def get_success_url(self):
        messages.success(self.request, 'Información del acudiente actualizada correctamente')
        estudiante_pk = self.kwargs['estudiante_pk']
        return reverse_lazy('rector:estudiante_detail', kwargs={'pk': estudiante_pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estudiante'] = get_object_or_404(Estudiante, pk=self.kwargs['estudiante_pk'])
        context['acudiente_rel'] = get_object_or_404(Acudiente, pk=self.kwargs['acudiente_pk'])
        context['titulo'] = f'Editar Acudiente: {self.object.get_full_name()}'
        return context

class AcudienteCrearView(RoleRequiredMixin, CreateView):
    """Crear nuevo acudiente para un estudiante"""
    template_name = 'rector/academico/acudiente/acudiente_crear.html'
    allowed_roles = ['Rector']
    form_class = AcudienteForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # No pasamos estudiante aquí, se maneja en form_valid
        return kwargs
    
    def form_valid(self, form):
        estudiante = get_object_or_404(Estudiante, pk=self.kwargs['pk'])
        form.instance.estudiante = estudiante
        messages.success(self.request, 'Acudiente creado exitosamente')
        return super().form_valid(form)
    
    def get_success_url(self):
        estudiante_pk = self.kwargs['pk']
        return reverse_lazy('rector:estudiante_detail', kwargs={'pk': estudiante_pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estudiante'] = get_object_or_404(Estudiante, pk=self.kwargs['pk'])
        context['titulo'] = f'Agregar Acudiente a {context["estudiante"].usuario.get_full_name()}'
        return context

class AcudienteEditarInformacionView(RoleRequiredMixin, UpdateView):
    """Editar información de un acudiente"""
    template_name = 'rector/academico/acudiente/acudiente_editar_informacion.html'
    allowed_roles = ['Rector']
    form_class = AcudienteForm  # Usar el nuevo formulario
    
    def get_object(self):
        # Obtener la relación acudiente-estudiante
        return get_object_or_404(Acudiente, pk=self.kwargs['acudiente_pk'])
    
    def get_success_url(self):
        messages.success(self.request, 'Información del acudiente actualizada correctamente')
        estudiante_pk = self.kwargs['estudiante_pk']
        return reverse_lazy('rector:estudiante_detail', kwargs={'pk': estudiante_pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estudiante'] = get_object_or_404(Estudiante, pk=self.kwargs['estudiante_pk'])
        context['acudiente_rel'] = self.object
        context['titulo'] = f'Editar Acudiente: {self.object.acudiente.get_full_name()}'
        return context
    
class AcudienteDeleteView(RoleRequiredMixin, DeleteView):
    """Eliminar relación acudiente-estudiante"""
    template_name = 'rector/academico/acudiente/acudiente_confirm_delete.html'
    allowed_roles = ['Rector']
    model = Acudiente
    
    def get_object(self):
        return get_object_or_404(Acudiente, pk=self.kwargs['acudiente_pk'])
    
    def get_success_url(self):
        estudiante_pk = self.kwargs['estudiante_pk']
        messages.success(self.request, 'Acudiente eliminado del estudiante')
        return reverse_lazy('rector:estudiante_detail', kwargs={'pk': estudiante_pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estudiante'] = get_object_or_404(Estudiante, pk=self.kwargs['estudiante_pk'])
        context['titulo'] = 'Eliminar Acudiente'
        return context
    
# ================== LOGROS ==================
class LogroListView(RoleRequiredMixin, ListView):
    """Lista de logros académicos"""
    template_name = 'rector/academico/logro/logro_list.html'
    allowed_roles = ['Rector']
    model = Logro
    context_object_name = 'logros'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Logro.objects.select_related(
            'asignatura',
            'periodo_academico__periodo',
            'periodo_academico__año_lectivo',
            'grado'
        ).order_by('-created_at')
        
        # Obtener parámetros de filtro
        asignatura_filter = self.request.GET.get('asignatura')
        grado_filter = self.request.GET.get('grado')
        periodo_filter = self.request.GET.get('periodo')
        año_filter = self.request.GET.get('año')  # Este es el ID del AñoLectivo
        search = self.request.GET.get('search')
        
        # Aplicar filtro por año lectivo
        if año_filter and año_filter != 'todos':
            try:
                queryset = queryset.filter(periodo_academico__año_lectivo__id=año_filter)
            except (ValueError, AñoLectivo.DoesNotExist):
                # Si el ID no es válido, ignorar el filtro
                pass
        
        # Resto de los filtros (mantén tu código actual)
        if asignatura_filter and asignatura_filter != 'todos':
            queryset = queryset.filter(asignatura__id=asignatura_filter)
        
        if grado_filter and grado_filter != 'todos':
            queryset = queryset.filter(grado__id=grado_filter)
        
        if periodo_filter and periodo_filter != 'todos':
            queryset = queryset.filter(periodo_academico__id=periodo_filter)
        
        if search:
            queryset = queryset.filter(
                Q(tema__icontains=search) |
                Q(descripcion_superior__icontains=search) |
                Q(descripcion_alto__icontains=search) |
                Q(descripcion_basico__icontains=search) |
                Q(descripcion_bajo__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Opciones para los filtros
        context['asignaturas'] = Asignatura.objects.all().order_by('nombre')
        context['grados'] = Grado.objects.all().order_by('nombre')
        context['periodos'] = Periodo.objects.all().order_by('nombre')
        context['años_lectivos'] = AñoLectivo.objects.all().order_by('-anho')
        
        # Pasar los valores actuales de los filtros al contexto
        # (Mantén tu código actual para los filtros)
        filter_keys = ['asignatura', 'grado', 'periodo', 'año', 'search']
        for key in filter_keys:
            value = self.request.GET.get(key)
            if value:
                context[f'filter_{key}'] = value
        
        # Estadísticas (mantén tu código actual)
        context['total_logros'] = Logro.objects.count()
        
        # Si hay filtro de año, calcular estadísticas solo para ese año
        año_filter = self.request.GET.get('año')
        if año_filter and año_filter != 'todos':
            try:
                año_lectivo = AñoLectivo.objects.get(id=año_filter)
                logros_filtrados = Logro.objects.filter(
                    periodo_academico__año_lectivo=año_lectivo
                )
                context['logros_por_asignatura'] = logros_filtrados.values(
                    'asignatura__nombre'
                ).annotate(
                    total=Count('id')
                ).order_by('-total')[:5]
            except AñoLectivo.DoesNotExist:
                context['logros_por_asignatura'] = Logro.objects.values(
                    'asignatura__nombre'
                ).annotate(
                    total=Count('id')
                ).order_by('-total')[:5]
        else:
            context['logros_por_asignatura'] = Logro.objects.values(
                'asignatura__nombre'
            ).annotate(
                total=Count('id')
            ).order_by('-total')[:5]
        
        return context

class LogroDetailView(RoleRequiredMixin, DetailView):
    """Detalle de un logro académico"""
    template_name = 'rector/academico//logro/logro_detail.html'
    allowed_roles = ['Rector']
    model = Logro
    context_object_name = 'logro'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        logro = self.object
        
        # Información relacionada
        context['asignatura'] = logro.asignatura
        context['periodo_academico'] = logro.periodo_academico
        context['grado'] = logro.grado
        
        # Estadísticas de notas relacionadas (si existen)
        año_lectivo = logro.periodo_academico.año_lectivo
        
        # Podrías agregar más estadísticas aquí según tus necesidades
        context['año_lectivo'] = año_lectivo
        
        return context

class LogroCreateView(RoleRequiredMixin, CreateView):
    """Crear nuevo logro académico"""
    template_name = 'rector/academico/logro/logro_form.html'
    allowed_roles = ['Rector']
    model = Logro
    form_class = LogroForm
    success_url = reverse_lazy('rector:logro_list')
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Pre-seleccionar valores de la URL
        asignatura_id = self.request.GET.get('asignatura')
        grado_id = self.request.GET.get('grado')
        
        if asignatura_id:
            try:
                initial['asignatura'] = Asignatura.objects.get(id=asignatura_id)
            except Asignatura.DoesNotExist:
                pass
        
        if grado_id:
            try:
                initial['grado'] = Grado.objects.get(id=grado_id)
            except Grado.DoesNotExist:
                pass
        
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accion'] = 'Crear'
        context['titulo'] = 'Nuevo Logro Académico'
        
        # Obtener año lectivo actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_actual
        
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Logro creado exitosamente')
        return super().form_valid(form)

class LogroUpdateView(RoleRequiredMixin, UpdateView):
    """Actualizar logro académico"""
    template_name = 'rector/academico/logro/logro_form.html'
    allowed_roles = ['Rector']
    model = Logro
    form_class = LogroForm
    success_url = reverse_lazy('rector:logro_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accion'] = 'Editar'
        context['titulo'] = f'Editar Logro: {self.object.tema[:50]}...'
        
        # Obtener año lectivo actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_actual
        
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Logro actualizado exitosamente')
        return super().form_valid(form)

class LogroDeleteView(RoleRequiredMixin, DeleteView):
    """Eliminar logro académico"""
    template_name = 'rector/academico/logro/logro_confirm_delete.html'
    allowed_roles = ['Rector']
    model = Logro
    success_url = reverse_lazy('rector:logro_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Logro eliminado exitosamente')
        return super().delete(request, *args, **kwargs)

class LogrosPorAsignaturaView(RoleRequiredMixin, ListView):
    """Logros agrupados por asignatura"""
    template_name = 'rector/academico/logro/logros_por_asignatura.html'
    allowed_roles = ['Rector']
    context_object_name = 'asignaturas'
    
    def get_queryset(self):
        # Obtener año lectivo actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        if año_actual:
            # Obtener asignaturas que tienen logros en el año actual
            asignaturas_con_logros = Asignatura.objects.filter(
                logros__periodo_academico__año_lectivo=año_actual
            ).distinct().prefetch_related(
                'logros__periodo_academico__periodo',
                'logros__grado'
            ).order_by('nombre')
            
            # Agregar conteo de logros a cada asignatura
            for asignatura in asignaturas_con_logros:
                asignatura.total_logros = asignatura.logros.filter(
                    periodo_academico__año_lectivo=año_actual
                ).count()
            
            return asignaturas_con_logros
        
        return Asignatura.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Año lectivo actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_actual
        
        # Periodos académicos del año actual
        if año_actual:
            context['periodos'] = PeriodoAcademico.objects.filter(
                año_lectivo=año_actual
            ).select_related('periodo')
        
        return context

# ================== HORARIOS ==================

class HorarioListView(RoleRequiredMixin, ListView):
    """Lista de horarios de clases"""
    template_name = 'rector/academico/horario/horario_list.html'
    allowed_roles = ['Rector']
    model = HorarioClase
    context_object_name = 'horarios'
    paginate_by = 30
    
    def get_queryset(self):
        queryset = HorarioClase.objects.select_related(
            'asignatura_grado__asignatura',
            'asignatura_grado__grado_año_lectivo__grado',
            'asignatura_grado__grado_año_lectivo__año_lectivo',
            'asignatura_grado__sede'
        ).order_by('dia_semana', 'hora_inicio')
        
        # Filtros
        grado_filter = self.request.GET.get('grado')
        asignatura_filter = self.request.GET.get('asignatura')
        dia_filter = self.request.GET.get('dia')
        sede_filter = self.request.GET.get('sede')
        año_filter = self.request.GET.get('año')
        
        # Filtro por grado
        if grado_filter and grado_filter != 'todos':
            queryset = queryset.filter(
                asignatura_grado__grado_año_lectivo__grado__id=grado_filter
            )
        
        # Filtro por asignatura
        if asignatura_filter and asignatura_filter != 'todos':
            queryset = queryset.filter(asignatura_grado__asignatura__id=asignatura_filter)
        
        # Filtro por día
        if dia_filter and dia_filter != 'todos':
            queryset = queryset.filter(dia_semana=dia_filter)
        
        # Filtro por sede
        if sede_filter and sede_filter != 'todos':
            queryset = queryset.filter(asignatura_grado__sede__id=sede_filter)
        
        # Filtro por año lectivo
        if año_filter and año_filter != 'todos':
            queryset = queryset.filter(
                asignatura_grado__grado_año_lectivo__año_lectivo__id=año_filter
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Opciones de filtro
        context['grados'] = Grado.objects.all().order_by('nombre')
        context['asignaturas'] = Asignatura.objects.all().order_by('nombre')
        context['sedes'] = Sede.objects.filter(estado=True)
        context['años_lectivos'] = AñoLectivo.objects.all().order_by('-anho')
        
        # Días de la semana
        context['dias_semana'] = [
            ('LUN', 'Lunes'),
            ('MAR', 'Martes'),
            ('MIE', 'Miércoles'),
            ('JUE', 'Jueves'),
            ('VIE', 'Viernes')
        ]
        
        # Aplicar filtros al contexto
        for key in ['grado', 'asignatura', 'dia', 'sede', 'año']:
            value = self.request.GET.get(key)
            if value:
                context[f'filter_{key}'] = value
        
        # Estadísticas
        context['total_horarios'] = HorarioClase.objects.count()
        
        # Horarios por día
        horarios_por_dia = HorarioClase.objects.values(
            'dia_semana'
        ).annotate(
            total=Count('id')
        ).order_by('dia_semana')
        
        context['horarios_por_dia'] = horarios_por_dia
        
        return context

class HorarioDetailView(RoleRequiredMixin, DetailView):
    """Detalle de un horario"""
    template_name = 'rector/academico/horario/horario_detail.html'
    allowed_roles = ['Rector']
    model = HorarioClase
    context_object_name = 'horario'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        horario = self.object
        
        # Información relacionada
        context['asignatura_grado'] = horario.asignatura_grado
        context['asignatura'] = horario.asignatura_grado.asignatura
        context['grado'] = horario.asignatura_grado.grado_año_lectivo.grado
        context['sede'] = horario.asignatura_grado.sede
        context['año_lectivo'] = horario.asignatura_grado.grado_año_lectivo.año_lectivo
        
        return context

class HorarioCreateView(RoleRequiredMixin, CreateView):
    """Crear nuevo horario"""
    template_name = 'rector/academico/horario/horario_form.html'
    allowed_roles = ['Rector']
    model = HorarioClase
    fields = [
        'asignatura_grado', 'dia_semana', 'hora_inicio', 
        'hora_fin', 'salon'
    ]
    success_url = reverse_lazy('rector:horario_list')
    
    def get_suggested_times(self, nivel):
        """Obtener horarios sugeridos según el nivel"""
        if nivel == 'Preescolar':
            return [
                ('07:00', '07:45'),
                ('07:45', '08:30'),
                ('08:30', '09:00'),  # Media hora antes del recreo
                ('09:30', '10:15'),
                ('10:15', '11:00'),
                ('11:00', '11:45')
            ]
        else:  # Primaria
            return [
                ('06:25', '07:15'),  # 50 minutos
                ('07:15', '08:00'),
                ('08:00', '08:45'),
                ('08:45', '09:30'),
                ('09:45', '10:30'),
                ('10:30', '11:15'),
                ('11:15', '12:00'),
                ('12:00', '12:45')
            ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accion'] = 'Crear'
        context['titulo'] = 'Nuevo Horario de Clase'
        
        # Obtener información del grado si viene por GET
        grado_id = self.request.GET.get('grado')
        sede_id = self.request.GET.get('sede')
        
        if grado_id:
            try:
                grado = Grado.objects.get(id=grado_id)
                nivel_nombre = grado.nivel_escolar.nombre
                
                context['grado_info'] = {
                    'id': grado.id,
                    'nombre': grado.nombre,
                    'nivel': nivel_nombre
                }
                
                # Obtener horarios sugeridos
                context['suggested_times'] = self.get_suggested_times(nivel_nombre)
                
                # Información sobre la jornada
                if nivel_nombre == 'Preescolar':
                    context['jornada_info'] = {
                        'nombre': 'Preescolar',
                        'horario': '7:00 AM - 12:00 PM',
                        'recreo': '9:00 - 9:30 (30 min)',
                        'clases': '6 clases diarias',
                        'duracion_clases': '45 min (excepto 3ra: 30 min)'
                    }
                else:
                    context['jornada_info'] = {
                        'nombre': 'Primaria',
                        'horario': '6:25 AM - 12:45 PM',
                        'recreo': '9:30 - 9:45 (15 min)',
                        'clases': '8 clases diarias',
                        'duracion_clases': '45 min (excepto 1ra: 50 min)'
                    }
                
            except Grado.DoesNotExist:
                pass
        
        return context
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filtrar asignaturas por año lectivo activo
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if año_actual:
            form.fields['asignatura_grado'].queryset = AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo__año_lectivo=año_actual
            )
        
        # Pre-seleccionar grado si viene por GET
        grado_id = self.request.GET.get('grado')
        sede_id = self.request.GET.get('sede')
        
        if grado_id and sede_id and año_actual:
            # Filtrar asignaturas solo del grado seleccionado
            form.fields['asignatura_grado'].queryset = form.fields['asignatura_grado'].queryset.filter(
                grado_año_lectivo__grado__id=grado_id,
                sede__id=sede_id
            )
        
        return form
    
    def form_valid(self, form):
        messages.success(self.request, 'Horario creado exitosamente')
        return super().form_valid(form)
    
class HorarioUpdateView(RoleRequiredMixin, UpdateView):
    """Actualizar horario"""
    template_name = 'rector/academico/horario/horario_form.html'
    allowed_roles = ['Rector']
    model = HorarioClase
    fields = [
        'asignatura_grado', 'dia_semana', 'hora_inicio', 
        'hora_fin', 'salon'
    ]
    success_url = reverse_lazy('rector:horario_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accion'] = 'Editar'
        context['titulo'] = f'Editar Horario: {self.object.asignatura_grado}'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Horario actualizado exitosamente')
        return super().form_valid(form)

class HorarioDeleteView(RoleRequiredMixin, DeleteView):
    """Eliminar horario"""
    template_name = 'rector/academico/horario/horario_confirm_delete.html'
    allowed_roles = ['Rector']
    model = HorarioClase
    success_url = reverse_lazy('rector:horario_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Horario eliminado exitosamente')
        return super().delete(request, *args, **kwargs)

class HorarioPorGradoView(RoleRequiredMixin, TemplateView):
    """Horario completo por grado"""
    template_name = 'rector/academico/horario/horario_por_grado.html'
    allowed_roles = ['Rector']
    
    def get_horas_por_nivel(self, nivel_nombre):
        """Obtener horas específicas por nivel escolar"""
        if nivel_nombre == 'Preescolar':
            # Preescolar: 7:00 AM - 12:00 PM con recreo de 9:00-9:30
            horas = [
                '07:00', '07:45', '08:30', 
                '09:00',  # Inicio recreo (se mostrará como recreo)
                '09:30', '10:15', '11:00', '11:45'
                # Nota: 12:00 no se incluye como hora de inicio
            ]
            return horas
        else:  # Primaria
            # Primaria: 6:25 AM - 12:45 PM con recreo 9:30-9:45
            horas = [
                '06:25', '07:15', '08:00', '08:45', '09:30',  # Inicio recreo
                '09:45', '10:30', '11:15', '12:00', '12:45'
            ]
            return horas
    
    def get_suggested_times(self, nivel):
        """Obtener horarios sugeridos según el nivel"""
        if nivel == 'Preescolar':
            return [
                ('07:00', '07:45'),
                ('07:45', '08:30'),
                ('08:30', '09:00'),  # Media hora antes del recreo
                ('09:30', '10:15'),
                ('10:15', '11:00'),
                ('11:00', '11:45')
            ]
        else:  # Primaria
            return [
                ('06:25', '07:15'),
                ('07:15', '08:00'),
                ('08:00', '08:45'),
                ('08:45', '09:30'),
                ('09:45', '10:30'),
                ('10:30', '11:15'),
                ('11:15', '12:00'),
                ('12:00', '12:45')
            ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener año lectivo actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_actual
        
        # Grados disponibles
        context['grados'] = Grado.objects.all().order_by('nombre')
        
        # Sedes disponibles
        context['sedes'] = Sede.objects.filter(estado=True)
        
        # Días de la semana
        context['dias_semana'] = [
            ('LUN', 'Lunes'),
            ('MAR', 'Martes'),
            ('MIE', 'Miércoles'),
            ('JUE', 'Jueves'),
            ('VIE', 'Viernes')
        ]
        
        # Si hay filtros, mostrar horarios
        grado_id = self.request.GET.get('grado')
        sede_id = self.request.GET.get('sede')
        
        if grado_id and sede_id and año_actual:
            try:
                grado = Grado.objects.get(id=grado_id)
                sede = Sede.objects.get(id=sede_id)
                
                # Determinar tipo de jornada según el nivel
                nivel_nombre = grado.nivel_escolar.nombre
                context['nivel_seleccionado'] = nivel_nombre
                context['grado_seleccionado'] = grado
                context['sede_seleccionada'] = sede
                
                # Obtener horas según el nivel
                horas = self.get_horas_por_nivel(nivel_nombre)
                context['horas'] = horas
                
                # Obtener sugerencias para creación
                context['suggested_times'] = self.get_suggested_times(nivel_nombre)
                
                # Obtener horarios para ese grado, sede y año
                horarios = HorarioClase.objects.filter(
                    asignatura_grado__grado_año_lectivo__grado__id=grado_id,
                    asignatura_grado__sede__id=sede_id,
                    asignatura_grado__grado_año_lectivo__año_lectivo=año_actual
                ).select_related(
                    'asignatura_grado__asignatura',
                    'asignatura_grado__docente__usuario',
                    'asignatura_grado__grado_año_lectivo__grado__nivel_escolar'
                ).order_by('dia_semana', 'hora_inicio')
                
                # Organizar horarios por día y hora
                horarios_organizados = {}
                for dia_key, dia_name in context['dias_semana']:
                    horarios_organizados[dia_key] = {}
                    for hora in horas:
                        horarios_organizados[dia_key][hora] = None
                
                for horario in horarios:
                    dia = horario.dia_semana
                    hora_inicio = horario.hora_inicio.strftime('%H:%M')
                    
                    # Encontrar la celda correspondiente
                    for hora_celda in horas:
                        if hora_inicio == hora_celda:
                            horarios_organizados[dia][hora_celda] = horario
                            break
                    else:
                        # Si no encuentra hora exacta, buscar la más cercana
                        for i, hora_celda in enumerate(horas):
                            if hora_inicio < hora_celda:
                                # Asignar a la hora más cercana
                                horarios_organizados[dia][hora_celda] = horario
                                break
                
                context['horarios_organizados'] = horarios_organizados
                
                # Calcular estadísticas
                total_clases = sum(
                    1 for dia in horarios_organizados.values() 
                    for h in dia.values() if h
                )
                context['total_clases'] = total_clases
                
                # Calcular horas semanales
                total_horas = 0
                for dia in horarios_organizados.values():
                    for hora_celda, horario in dia.items():
                        if horario:
                            inicio = horario.hora_inicio
                            fin = horario.hora_fin
                            diff = datetime.combine(datetime.today(), fin) - datetime.combine(datetime.today(), inicio)
                            total_horas += diff.total_seconds() / 3600
                context['total_horas'] = round(total_horas, 1)
                
            except (Grado.DoesNotExist, Sede.DoesNotExist):
                pass
        
        return context

#Vista auxiliar

class UsarEstudianteExistenteAjaxView(RoleRequiredMixin, View):
    """Usar un estudiante existente para matricularlo (AJAX)"""
    allowed_roles = ['Rector']
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            usuario_id = data.get('usuario_id')
            matricula_data = data.get('matricula', {})
            
            if not usuario_id:
                return JsonResponse({
                    'success': False,
                    'error': 'ID de usuario requerido'
                }, status=400)
            
            # Obtener usuario
            usuario = Usuario.objects.get(id=usuario_id)
            
            # Verificar si ya es estudiante
            estudiante = Estudiante.objects.filter(usuario=usuario).first()
            
            if not estudiante:
                # Convertir usuario a estudiante
                tipo_estudiante, _ = TipoUsuario.objects.get_or_create(
                    nombre='Estudiante',
                    defaults={'nombre': 'Estudiante'}
                )
                
                usuario.tipo_usuario = tipo_estudiante
                usuario.save()
                
                estudiante = Estudiante.objects.create(
                    usuario=usuario,
                    estado=True
                )
            
            # Verificar que no exista matrícula para el mismo año
            año_lectivo_id = matricula_data.get('año_lectivo')
            año_lectivo = AñoLectivo.objects.get(id=año_lectivo_id)
            
            matricula_existente = Matricula.objects.filter(
                estudiante=estudiante,
                año_lectivo=año_lectivo
            ).exists()
            
            if matricula_existente:
                return JsonResponse({
                    'success': False,
                    'error': 'El estudiante ya tiene matrícula para este año lectivo'
                }, status=400)
            
            # 2. Crear matrícula
            matricula_data = data.get('matricula', {})
            
            # Validar datos de matrícula
            año_lectivo_id = matricula_data.get('año_lectivo')
            sede_id = matricula_data.get('sede')
            grado_año_lectivo_id = matricula_data.get('grado_año_lectivo')
            estado = matricula_data.get('estado', 'PRE')
            
            if not all([año_lectivo_id, sede_id, grado_año_lectivo_id]):
                return JsonResponse({
                    'success': False,
                    'error': 'Faltan datos de matrícula'
                }, status=400)
            
            # Verificar que no exista matrícula para el mismo año
            año_lectivo = AñoLectivo.objects.get(id=año_lectivo_id)
            matricula_existente = Matricula.objects.filter(
                estudiante=estudiante,
                año_lectivo=año_lectivo
            ).exists()
            
            if matricula_existente:
                return JsonResponse({
                    'success': False,
                    'error': 'El estudiante ya tiene matrícula para este año lectivo'
                }, status=400)
            
            # Verificar que el grado pertenezca al año lectivo
            grado_año_lectivo = GradoAñoLectivo.objects.get(id=grado_año_lectivo_id)
            if grado_año_lectivo.año_lectivo != año_lectivo:
                return JsonResponse({
                    'success': False,
                    'error': 'El grado seleccionado no pertenece al año lectivo elegido'
                }, status=400)
            
            # Crear matrícula
            sede = Sede.objects.get(id=sede_id)
            
            matricula = Matricula.objects.create(
                estudiante=estudiante,
                año_lectivo=año_lectivo,
                sede=sede,
                grado_año_lectivo=grado_año_lectivo,
                estado=estado,
                observaciones=matricula_data.get('observaciones', '')
            )
            
            return JsonResponse({
                'success': True,
                'estudiante': {
                    'id': estudiante.id,
                    'nombre': estudiante.usuario.get_full_name(),
                    'documento': estudiante.usuario.numero_documento,
                },
                'mensaje': 'Usuario convertido a estudiante y matriculado exitosamente'
            })
            
        except Usuario.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Usuario no encontrado'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)