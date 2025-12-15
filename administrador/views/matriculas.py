# administrador/views/matriculas.py (o agregar a views.py)
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q, Count
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied

from matricula.models import PeriodoAcademico, AsignaturaGradoAñoLectivo, GradoAñoLectivo
from estudiantes.models import Matricula, Estudiante
from gestioncolegio.models import AñoLectivo, Sede
from gestioncolegio.mixins import RoleRequiredMixin
from administrador.forms import MatriculaForm, MatriculaFilterForm, MatriculaBulkForm

# ========================
# GESTIÓN DE MATRÍCULAS
# ========================

class MatriculaListView(RoleRequiredMixin, ListView):
    """Lista de matrículas con filtros"""
    model = Matricula
    template_name = 'administrador/matriculas/matricula_list.html'
    context_object_name = 'matriculas'
    allowed_roles = ['Administrador', 'Rector']
    paginate_by = 30
    
    def get_queryset(self):
        # Por defecto, mostrar solo el año lectivo actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        queryset = Matricula.objects.select_related(
            'estudiante__usuario',
            'estudiante__usuario__tipo_documento',
            'año_lectivo',
            'sede',
            'grado_año_lectivo__grado'
        ).order_by('-fecha_matricula', 'estudiante__usuario__apellidos')
        
        # Aplicar filtros
        search = self.request.GET.get('search')
        estado = self.request.GET.get('estado')
        grado = self.request.GET.get('grado')
        año_lectivo = self.request.GET.get('año_lectivo')
        sede = self.request.GET.get('sede')
        
        # Si no se especifica año lectivo, mostrar solo el actual
        if not año_lectivo and año_actual:
            queryset = queryset.filter(año_lectivo=año_actual)
            self.año_filtrado = año_actual.id
        elif año_lectivo:
            self.año_filtrado = año_lectivo
        else:
            self.año_filtrado = None
        
        if search:
            queryset = queryset.filter(
                Q(estudiante__usuario__nombres__icontains=search) |
                Q(estudiante__usuario__apellidos__icontains=search) |
                Q(estudiante__usuario__numero_documento__icontains=search) |
                Q(codigo_matricula__icontains=search)
            )
        
        if estado:
            queryset = queryset.filter(estado=estado)
        
        if grado:
            if grado == 'preescolar':
                queryset = queryset.filter(grado_año_lectivo__grado__nivel_escolar__nombre='Preescolar')
            elif grado == 'primaria':
                queryset = queryset.filter(grado_año_lectivo__grado__nivel_escolar__nombre='Primaria')
        
        if año_lectivo:
            queryset = queryset.filter(año_lectivo_id=año_lectivo)
        
        if sede:
            queryset = queryset.filter(sede_id=sede)
        
        self.queryset_filtrado = queryset  # Guardar para estadísticas
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Formulario de filtros con datos actuales
        context['filter_form'] = MatriculaFilterForm(self.request.GET or None)
        
        # Obtener año lectivo activo
        año_lectivo_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_lectivo_actual
        
        # Obtener años lectivos para filtro
        context['años_lectivos'] = AñoLectivo.objects.all().order_by('-anho')
        
        # Obtener sedes para filtro
        context['sedes'] = Sede.objects.all().order_by('nombre')
        
        # Estudiantes sin matrícula en año actual
        if año_lectivo_actual:
            estudiantes_sin_matricula = Estudiante.objects.filter(estado=True).exclude(
                matriculas__año_lectivo=año_lectivo_actual
            ).select_related('usuario')
            
            context['estudiantes_sin_matricula_list'] = estudiantes_sin_matricula[:10]
            context['total_sin_matricula'] = estudiantes_sin_matricula.count()
            context['estudiantes_sin_matricula'] = estudiantes_sin_matricula.count()
        
        # Total de matrículas filtradas
        total_matriculas = self.queryset_filtrado.count()
        context['total_matriculas'] = total_matriculas
        
        # Estadísticas de nivel escolar
        context['preescolar_count'] = self.queryset_filtrado.filter(
            grado_año_lectivo__grado__nivel_escolar__nombre='Preescolar'
        ).count()
        
        context['primaria_count'] = self.queryset_filtrado.filter(
            grado_año_lectivo__grado__nivel_escolar__nombre='Primaria'
        ).count()
        
        # Estadísticas por estado
        estados = dict(Matricula.ESTADOS_MATRICULA)
        estadisticas_estado = {}
        for codigo, nombre in estados.items():
            estadisticas_estado[codigo] = self.queryset_filtrado.filter(estado=codigo).count()
        
        context['estadisticas_estado'] = estadisticas_estado
        
        return context

class MatriculaCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    """Crear nueva matrícula con opción de crear estudiante"""
    model = Matricula
    form_class = MatriculaForm
    template_name = 'administrador/matriculas/matricula_form.html'
    success_message = "Matrícula creada exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        
        # Pasar estudiante_id si viene de estudiante_detail
        estudiante_id = self.request.GET.get('estudiante_id')
        if estudiante_id:
            kwargs['estudiante_id'] = estudiante_id
        
        # Pasar año_lectivo_id si viene con parámetro específico
        año_lectivo_id = self.request.GET.get('año_lectivo_id')
        if año_lectivo_id:
            kwargs['año_lectivo_id'] = año_lectivo_id
        else:
            # Si no viene por parámetro, usar año actual
            año_actual = AñoLectivo.objects.filter(estado=True).first()
            if año_actual:
                kwargs['año_lectivo_id'] = año_actual.id
        
        return kwargs
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Establecer año lectivo actual por defecto si no viene por parámetro
        año_lectivo_id = self.request.GET.get('año_lectivo_id')
        if not año_lectivo_id:
            año_actual = AñoLectivo.objects.filter(estado=True).first()
            if año_actual:
                initial['año_lectivo'] = año_actual.id
        
        # Si viene de estudiante_detail, establecer tipo como existente
        estudiante_id = self.request.GET.get('estudiante_id')
        if estudiante_id:
            initial['tipo_estudiante'] = 'existente'
        
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Nueva Matrícula'
        context['submit_text'] = 'Crear Matrícula'
        
        # Pasar información del estudiante si viene de estudiante_detail
        estudiante_id = self.request.GET.get('estudiante_id')
        if estudiante_id:
            try:
                estudiante = Estudiante.objects.select_related('usuario').get(id=estudiante_id)
                context['estudiante_info'] = estudiante
                context['matriculas_anteriores'] = estudiante.matriculas_anteriores()
                
                # Verificar si ya tiene matrícula en año actual
                año_actual = AñoLectivo.objects.filter(estado=True).first()
                if año_actual:
                    tiene_matricula = Matricula.objects.filter(
                        estudiante=estudiante,
                        año_lectivo=año_actual
                    ).exists()
                    context['tiene_matricula_actual'] = tiene_matricula
                    context['año_actual'] = año_actual
            except Estudiante.DoesNotExist:
                pass
        
        return context
    
    def get_success_url(self):
        # Redirigir a la lista de matrículas o al detalle del estudiante
        redirect_to = self.request.GET.get('redirect_to')
        if redirect_to == 'estudiante_detail' and self.object.estudiante:
            return reverse_lazy('administrador:estudiante_detail', kwargs={'pk': self.object.estudiante.pk})
        return reverse_lazy('administrador:matricula_list')
    
class MatriculaUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar matrícula existente"""
    model = Matricula
    form_class = MatriculaForm
    template_name = 'administrador/matriculas/matricula_form.html'
    success_message = "Matrícula actualizada exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Matrícula'
        context['submit_text'] = 'Actualizar Matrícula'
        context['estudiante_info'] = self.object.estudiante
        context['matriculas_anteriores'] = self.object.estudiante.matriculas_anteriores()
        return context
    
    def get_success_url(self):
        # Redirigir a la lista de matrículas o al detalle del estudiante
        redirect_to = self.request.GET.get('redirect_to')
        if redirect_to == 'estudiante_detail':
            return reverse_lazy('administrador:estudiante_detail', kwargs={'pk': self.object.estudiante.pk})
        return reverse_lazy('administrador:matricula_list')

class MatriculaDetailView(RoleRequiredMixin, DetailView):
    """Ver detalle de matrícula - Versión corregida"""
    model = Matricula
    template_name = 'administrador/matriculas/matricula_detail.html'
    context_object_name = 'matricula'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get_object(self):
        return get_object_or_404(
            Matricula.objects.select_related(
                'estudiante__usuario',
                'estudiante__usuario__tipo_documento',
                'año_lectivo',
                'sede',
                'grado_año_lectivo__grado'
            ),
            pk=self.kwargs['pk']
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener información adicional
        matricula = self.object

        # Obtener acudientes del estudiante
        context['acudientes'] = matricula.estudiante.acudientes.all().select_related('acudiente')
        
        # Obtener historial académico del año actual
        # Obtener notas del estudiante para el año lectivo de la matrícula

        from estudiantes.models import Nota
        
        notas = Nota.objects.filter(
            estudiante=matricula.estudiante,
            asignatura_grado_año_lectivo__grado_año_lectivo__año_lectivo=matricula.año_lectivo
        ).select_related(
            'asignatura_grado_año_lectivo__asignatura',
            'periodo_academico__periodo'
        ).order_by('periodo_academico__periodo__nombre', 'asignatura_grado_año_lectivo__asignatura__nombre')
        
        context['notas'] = notas
        
        # Organizar notas por periodo para mejor visualización
        notas_por_periodo = {}
        for nota in notas:
            periodo_nombre = nota.periodo_academico.periodo.nombre
            if periodo_nombre not in notas_por_periodo:
                notas_por_periodo[periodo_nombre] = []
            notas_por_periodo[periodo_nombre].append(nota)
        
        context['notas_por_periodo'] = notas_por_periodo
        
        # Calcular promedio por periodo si es necesario
        promedios_por_periodo = {}
        for periodo, notas_list in notas_por_periodo.items():
            if notas_list:
                total = sum(nota.calificacion for nota in notas_list)
                promedios_por_periodo[periodo] = total / len(notas_list)
        
        context['promedios_por_periodo'] = promedios_por_periodo
        
        # Obtener comportamientos del año actual
        from comportamiento.models import Comportamiento
        comportamientos = Comportamiento.objects.filter(
            estudiante=matricula.estudiante,
            periodo_academico__año_lectivo=matricula.año_lectivo
        ).select_related('periodo_academico', 'docente').order_by('-fecha')
        context['comportamientos'] = comportamientos[:10]
        
        # Separar comportamientos positivos y negativos
        context['comportamientos_positivos'] = comportamientos.filter(tipo='Positivo')[:5]
        context['comportamientos_negativos'] = comportamientos.filter(tipo='Negativo')[:5]
        
        # Obtener asistencias del año actual
        from comportamiento.models import Asistencia
        asistencias = Asistencia.objects.filter(
            estudiante=matricula.estudiante,
            periodo_academico__año_lectivo=matricula.año_lectivo
        ).order_by('-fecha')
        context['asistencias'] = asistencias[:10]
        
        # Calcular estadísticas de asistencia
        total_asistencias = asistencias.count()
        if total_asistencias > 0:
            asistencias_contadas = asistencias.filter(estado='A').count()
            faltas = asistencias.filter(estado='F').count()
            justificadas = asistencias.filter(estado='J').count()
            
            context['porcentaje_asistencia'] = round((asistencias_contadas / total_asistencias) * 100, 1)
            context['total_faltas'] = faltas
            context['total_justificadas'] = justificadas
            context['total_asistencias_registradas'] = total_asistencias
        else:
            context['porcentaje_asistencia'] = 0
            context['total_faltas'] = 0
            context['total_justificadas'] = 0
            context['total_asistencias_registradas'] = 0
        
        # Información adicional del estudiante
        context['matriculas_anteriores'] = matricula.estudiante.matriculas_anteriores()
        
        return context
    
class MatriculaDeleteView(RoleRequiredMixin, SuccessMessageMixin, DeleteView):
    """Eliminar matrícula"""
    model = Matricula
    template_name = 'administrador/matriculas/matricula_confirm_delete.html'
    success_message = "Matrícula eliminada exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_success_url(self):
        # Redirigir a la lista de matrículas o al detalle del estudiante
        redirect_to = self.request.GET.get('redirect_to')
        if redirect_to == 'estudiante_detail':
            return reverse_lazy('administrador:estudiante_detail', kwargs={'pk': self.object.estudiante.pk})
        return reverse_lazy('administrador:matricula_list')

class MatriculaChangeStatusView(RoleRequiredMixin, View):
    """Cambiar estado de matrícula"""
    allowed_roles = ['Administrador', 'Rector']
    
    def post(self, request, pk):
        matricula = get_object_or_404(Matricula, pk=pk)
        nuevo_estado = request.POST.get('nuevo_estado')
        
        if nuevo_estado in dict(Matricula.ESTADOS_MATRICULA).keys():
            estado_anterior = matricula.estado
            matricula.estado = nuevo_estado
            matricula.save()
            
            messages.success(
                request, 
                f'Matrícula {matricula.codigo_matricula} actualizada: '
                f'{dict(Matricula.ESTADOS_MATRICULA).get(estado_anterior)} → '
                f'{dict(Matricula.ESTADOS_MATRICULA).get(nuevo_estado)}'
            )
        else:
            messages.error(request, 'Estado no válido.')
        
        return redirect('administrador:matricula_detail', pk=matricula.pk)

class MatriculaBulkCreateView(RoleRequiredMixin, SuccessMessageMixin, View):
    """Crear matrículas masivas"""
    template_name = 'administrador/matriculas/matricula_bulk.html'
    allowed_roles = ['Administrador', 'Rector']
    
    def get(self, request):
        form = MatriculaBulkForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = MatriculaBulkForm(request.POST)
        
        if form.is_valid():
            grado_año_lectivo = form.cleaned_data['grado_año_lectivo']
            sede = form.cleaned_data['sede']
            año_lectivo = form.cleaned_data['año_lectivo']
            estado = form.cleaned_data['estado']
            estudiantes = form.cleaned_data['estudiantes']
            
            matriculas_creadas = 0
            errores = []
            
            for estudiante in estudiantes:
                try:
                    # Verificar que no tenga ya matrícula en ese año
                    if Matricula.objects.filter(
                        estudiante=estudiante,
                        año_lectivo=año_lectivo
                    ).exists():
                        errores.append(
                            f"{estudiante.usuario.get_full_name()} ya tiene matrícula en {año_lectivo.anho}"
                        )
                        continue
                    
                    # Crear matrícula
                    Matricula.objects.create(
                        estudiante=estudiante,
                        año_lectivo=año_lectivo,
                        sede=sede,
                        grado_año_lectivo=grado_año_lectivo,
                        estado=estado
                    )
                    matriculas_creadas += 1
                    
                except Exception as e:
                    errores.append(f"Error con {estudiante.usuario.get_full_name()}: {str(e)}")
            
            if matriculas_creadas > 0:
                messages.success(request, f'Se crearon {matriculas_creadas} matrículas exitosamente.')
            
            if errores:
                for error in errores:
                    messages.warning(request, error)
            
            return redirect('administrador:matricula_list')
        
        return render(request, self.template_name, {'form': form})

class MatriculaReportView(RoleRequiredMixin, View):
    """Generar reportes de matrículas"""
    template_name = 'administrador/matriculas/matricula_reports.html'
    allowed_roles = ['Administrador', 'Rector']
    
    def get(self, request):
        # Obtener años lectivos para filtros
        años_lectivos = AñoLectivo.objects.all().order_by('-anho')
        
        # Obtener estadísticas generales
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        context = {
            'años_lectivos': años_lectivos,
            'año_actual': año_actual,
        }
        
        return render(request, self.template_name, context)

class MatriculaAjaxView(RoleRequiredMixin, View):
    """Vistas AJAX para matrículas"""
    allowed_roles = ['Administrador', 'Rector']
    
    def get(self, request):
        tipo = request.GET.get('tipo')
        
        if tipo == 'estudiantes_sin_matricula':
            # Obtener estudiantes sin matrícula en año actual
            año_actual = AñoLectivo.objects.filter(estado=True).first()
            
            if not año_actual:
                return JsonResponse({'error': 'No hay año lectivo activo'}, status=400)
            
            estudiantes_sin_matricula = Estudiante.objects.filter(
                estado=True
            ).exclude(
                matriculas__año_lectivo=año_actual
            ).select_related('usuario').order_by('usuario__apellidos', 'usuario__nombres')
            
            data = []
            for estudiante in estudiantes_sin_matricula:
                data.append({
                    'id': estudiante.id,
                    'nombre_completo': estudiante.usuario.get_full_name(),
                    'documento': estudiante.usuario.numero_documento,
                    'edad': estudiante.usuario.edad,
                    'sexo': estudiante.usuario.get_sexo_display() if estudiante.usuario.sexo else 'No especificado',
                })
            
            return JsonResponse({'estudiantes': data})
        
        elif tipo == 'grados_por_año':
            # Obtener grados disponibles para un año lectivo
            año_lectivo_id = request.GET.get('año_lectivo_id')
            
            if not año_lectivo_id:
                return JsonResponse({'error': 'ID de año lectivo requerido'}, status=400)
            
            grados = GradoAñoLectivo.objects.filter(
                año_lectivo_id=año_lectivo_id
            ).select_related('grado').order_by('grado__nombre')
            
            data = []
            for grado in grados:
                data.append({
                    'id': grado.id,
                    'nombre': grado.grado.nombre,
                    'nivel_escolar': grado.grado.nivel_escolar.nombre,
                })
            
            return JsonResponse({'grados': data})
        
        elif tipo == 'sedes_por_año':
            # Obtener sedes disponibles para un año lectivo
            año_lectivo_id = request.GET.get('año_lectivo_id')
            
            if not año_lectivo_id:
                return JsonResponse({'error': 'ID de año lectivo requerido'}, status=400)
            
            sedes = Sede.objects.filter(
                años_lectivos__id=año_lectivo_id
            ).distinct().order_by('nombre')
            
            data = []
            for sede in sedes:
                data.append({
                    'id': sede.id,
                    'nombre': sede.nombre,
                })
            
            return JsonResponse({'sedes': data})
        
        return JsonResponse({'error': 'Tipo de consulta no válido'}, status=400)

class MatriculaExportView(RoleRequiredMixin, View):
    """Exportar matrículas a Excel/PDF"""
    allowed_roles = ['Administrador', 'Rector']
    
    def get(self, request, formato):
        año_lectivo_id = request.GET.get('año_lectivo')
        sede_id = request.GET.get('sede')
        estado = request.GET.get('estado')
        
        # Filtrar matrículas
        matriculas = Matricula.objects.select_related(
            'estudiante__usuario',
            'año_lectivo',
            'sede',
            'grado_año_lectivo__grado'
        )
        
        if año_lectivo_id:
            matriculas = matriculas.filter(año_lectivo_id=año_lectivo_id)
        
        if sede_id:
            matriculas = matriculas.filter(sede_id=sede_id)
        
        if estado:
            matriculas = matriculas.filter(estado=estado)
        
        matriculas = matriculas.order_by('grado_año_lectivo__grado__nombre', 'estudiante__usuario__apellidos')
        
        if formato == 'excel':
            # Implementar exportación a Excel
            # Necesitarías instalar openpyxl o xlwt
            messages.info(request, 'Funcionalidad de exportación a Excel en desarrollo.')
            return redirect('administrador:matricula_list')
        
        elif formato == 'pdf':
            # Implementar exportación a PDF
            # Necesitarías instalar reportlab o weasyprint
            messages.info(request, 'Funcionalidad de exportación a PDF en desarrollo.')
            return redirect('administrador:matricula_list')
        
        messages.error(request, 'Formato no soportado.')
        return redirect('administrador:matricula_list')

class MatriculaFromEstudianteListView(RoleRequiredMixin, View):
    """Crear matrícula desde la lista de estudiantes"""
    allowed_roles = ['Administrador', 'Rector']
    
    def get(self, request, estudiante_id):
        estudiante = get_object_or_404(Estudiante, pk=estudiante_id)
        
        # Verificar si ya tiene matrícula en año actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        if año_actual:
            matricula_existente = Matricula.objects.filter(
                estudiante=estudiante,
                año_lectivo=año_actual
            ).first()
            
            if matricula_existente:
                messages.info(
                    request, 
                    f'El estudiante ya tiene matrícula en {año_actual.anho}. '
                    f'Puede editarla desde el detalle.'
                )
                return redirect('administrador:matricula_update', pk=matricula_existente.pk)
        
        # Redirigir al formulario de creación
        return redirect(
            f"{reverse_lazy('administrador:matricula_create')}"
            f"?estudiante_id={estudiante_id}&redirect_to=estudiante_list"
        )

class EstudianteMatriculasView(RoleRequiredMixin, DetailView):
    """Ver todas las matrículas de un estudiante"""
    model = Estudiante
    template_name = 'administrador/matriculas/estudiante_matriculas.html'
    context_object_name = 'estudiante'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante = self.object
        
        # Obtener todas las matrículas ordenadas por año
        context['matriculas'] = estudiante.matriculas.select_related(
            'año_lectivo',
            'sede',
            'grado_año_lectivo__grado'
        ).order_by('-año_lectivo__anho')
        
        # Obtener años disponibles para nueva matrícula
        años_matriculados = estudiante.matriculas.values_list('año_lectivo_id', flat=True)
        context['años_disponibles'] = AñoLectivo.objects.exclude(
            id__in=años_matriculados
        ).order_by('-anho')
        
        return context
    
class MatriculaCreateConAñoView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    """Crear matrícula para un estudiante en un año específico"""
    model = Matricula
    form_class = MatriculaForm
    template_name = 'administrador/matriculas/matricula_form.html'
    success_message = "Matrícula creada exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def dispatch(self, request, *args, **kwargs):
        self.estudiante_id = kwargs.get('estudiante_id')
        self.año_lectivo_id = kwargs.get('año_lectivo_id')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['estudiante_id'] = self.estudiante_id
        kwargs['año_lectivo_id'] = self.año_lectivo_id
        return kwargs
    
    def get_initial(self):
        initial = super().get_initial()
        initial['estudiante'] = self.estudiante_id
        initial['año_lectivo'] = self.año_lectivo_id
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Nueva Matrícula'
        context['submit_text'] = 'Crear Matrícula'
        
        # Pasar información del estudiante
        try:
            estudiante = Estudiante.objects.select_related('usuario').get(id=self.estudiante_id)
            context['estudiante_info'] = estudiante
            context['matriculas_anteriores'] = estudiante.matriculas_anteriores()
        except Estudiante.DoesNotExist:
            pass
        
        # Pasar información del año lectivo
        try:
            año_lectivo = AñoLectivo.objects.get(id=self.año_lectivo_id)
            context['año_lectivo_info'] = año_lectivo
        except AñoLectivo.DoesNotExist:
            pass
        
        return context
    
class EstudianteHistorialAcademicoView(RoleRequiredMixin, DetailView):
    """Historial académico completo del estudiante - Nueva versión"""
    model = Estudiante
    template_name = 'administrador/estudiantes/historial_academico.html'
    context_object_name = 'estudiante'
    allowed_roles = ['Administrador', 'Rector', 'Docente', 'Acudiente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante = self.object
        
        # Obtener todas las matrículas del estudiante
        matriculas = estudiante.matriculas.select_related(
            'año_lectivo',
            'grado_año_lectivo__grado'
        ).order_by('-año_lectivo__anho')
        
        historial_completo = []
        
        # Para cada matrícula (año lectivo), obtener las notas
        from estudiantes.models import Nota
        
        for matricula in matriculas:
            año_info = {
                'año_lectivo': matricula.año_lectivo,
                'grado': matricula.grado_año_lectivo.grado,
                'sede': matricula.sede,
                'estado_matricula': matricula.get_estado_display(),
                'notas': {}
            }
            
            # Obtener notas para este año lectivo
            notas = Nota.objects.filter(
                estudiante=estudiante,
                asignatura_grado_año_lectivo__grado_año_lectivo__año_lectivo=matricula.año_lectivo
            ).select_related(
                'asignatura_grado_año_lectivo__asignatura',
                'periodo_academico__periodo'
            ).order_by('periodo_academico__periodo__nombre')
            
            # Organizar notas por periodo
            for nota in notas:
                periodo_nombre = nota.periodo_academico.periodo.nombre
                asignatura_nombre = nota.asignatura_grado_año_lectivo.asignatura.nombre
                
                if periodo_nombre not in año_info['notas']:
                    año_info['notas'][periodo_nombre] = {}
                
                año_info['notas'][periodo_nombre][asignatura_nombre] = {
                    'calificacion': nota.calificacion,
                    'observaciones': nota.observaciones
                }
            
            historial_completo.append(año_info)
        
        context['historial_completo'] = historial_completo
        
        # Calcular promedios generales si es necesario
        promedios_generales = {}
        for año in historial_completo:
            año_key = f"{año['año_lectivo'].anho} - {año['grado'].nombre}"
            promedios_generales[año_key] = {}
            
            for periodo, asignaturas in año['notas'].items():
                if asignaturas:
                    total = sum(data['calificacion'] for data in asignaturas.values())
                    promedios_generales[año_key][periodo] = round(total / len(asignaturas), 2)
        
        context['promedios_generales'] = promedios_generales
        
        return context