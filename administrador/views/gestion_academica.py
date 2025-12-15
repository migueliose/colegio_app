#views/gestion_academica.py
from django.shortcuts import render
from django.views.generic import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from academico.models import Grado, NivelEscolar, Area, Asignatura, Periodo
from matricula.models import PeriodoAcademico
from estudiantes.models import Matricula
from gestioncolegio.models import AñoLectivo, AuditoriaSistema
from gestioncolegio.mixins import RoleRequiredMixin
from ..forms.formularios import *
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import JsonResponse, HttpResponseForbidden
# ========================
# GESTIÓN DE GRADOS
# ========================

class GradoListView(RoleRequiredMixin, ListView):
    model = Grado
    template_name = 'administrador/grados/grado_list.html'
    context_object_name = 'grados'
    allowed_roles = ['Administrador', 'Rector']

    def get_queryset(self):
        qs = Grado.objects.select_related('nivel_escolar').order_by('nivel_escolar__nombre', 'nombre')

        # Aplicar filtro por nivel si viene en la querystring
        nivel_id = self.request.GET.get('nivel')
        if nivel_id:
            try:
                nivel_id_int = int(nivel_id)
                qs = qs.filter(nivel_escolar_id=nivel_id_int)
            except (ValueError, TypeError):
                # Si no es un id válido, ignorar el filtro
                pass

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['niveles_escolares'] = NivelEscolar.objects.all()

        # Pasar el nivel seleccionado como int (o None)
        nivel_id = self.request.GET.get('nivel')
        try:
            context['selected_nivel'] = int(nivel_id) if nivel_id else None
        except (ValueError, TypeError):
            context['selected_nivel'] = None

        return context

class GradoCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    model = Grado
    form_class = GradoForm
    template_name = 'administrador/grados/grado_form.html'
    success_url = reverse_lazy('administrador:grado_list')
    success_message = "Grado creado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Nuevo Grado'
        context['submit_text'] = 'Crear Grado'
        return context

class GradoUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Grado
    form_class = GradoForm
    template_name = 'administrador/grados/grado_form.html'
    success_url = reverse_lazy('administrador:grado_list')
    success_message = "Grado actualizado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Grado'
        context['submit_text'] = 'Actualizar Grado'
        return context

class GradoDeleteView(RoleRequiredMixin, DeleteView):
    model = Grado
    template_name = 'administrador/grados/grado_confirm_delete.html'
    success_url = reverse_lazy('administrador:grado_list')
    allowed_roles = ['Administrador', 'Rector']
    
    def post(self, request, *args, **kwargs):
        # Capturar el motivo si se envió
        motivo = request.POST.get('motivo', '')
        if motivo:
            # Aquí podrías guardar el motivo en un log o tabla de auditoría
            print(f"Grado eliminado. Motivo: {motivo}")
        
        messages.success(request, "Grado eliminado exitosamente")
        return self.delete(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar información adicional si es necesario
        context['title'] = 'Eliminar Grado'
        return context

class AreaListView(RoleRequiredMixin, ListView):
    model = Area
    template_name = 'administrador/areas/area_list.html'
    context_object_name = 'areas'
    allowed_roles = ['Administrador', 'Rector']
    paginate_by = 15  # Opcional

    def get_queryset(self):
        queryset = Area.objects.select_related('nivel_escolar').order_by('nivel_escolar__nombre', 'nombre')

        nivel_id = self.request.GET.get('nivel')
        search = self.request.GET.get('search')

        if nivel_id:
            queryset = queryset.filter(nivel_escolar_id=nivel_id)

        if search:
            queryset = queryset.filter(nombre__icontains=search)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['niveles_escolares'] = NivelEscolar.objects.all()

        # Estadísticas corregidas
        context['areas_preescolar'] = Area.objects.filter(nivel_escolar__nombre="Preescolar").count()
        context['areas_primaria'] = Area.objects.filter(nivel_escolar__nombre="Primaria").count()
        context['areas_with_subjects'] = Area.objects.annotate(
            num_asig=Count('asignaturas')
        ).filter(num_asig__gt=0).count()

        return context

class AreaCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    model = Area
    form_class = AreaForm
    template_name = 'administrador/areas/area_form.html'
    success_url = reverse_lazy('administrador:area_list')
    success_message = "Área creada exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Nueva Área'
        context['submit_text'] = 'Crear Área'
        return context

class AreaUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Area
    form_class = AreaForm
    template_name = 'administrador/areas/area_form.html'
    success_url = reverse_lazy('administrador:area_list')
    success_message = "Área actualizada exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Área'
        context['submit_text'] = 'Actualizar Área'
        return context

class AreaDeleteView(RoleRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Area
    template_name = 'administrador/areas/area_confirm_delete.html'
    success_url = reverse_lazy('administrador:area_list')
    success_message = "Área eliminada exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

class AsignaturaListView(RoleRequiredMixin, ListView):
    model = Asignatura
    template_name = 'administrador/asignaturas/asignatura_list.html'
    context_object_name = 'asignaturas'
    allowed_roles = ['Administrador', 'Rector']
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Asignatura.objects.select_related(
            'area',
            'area__nivel_escolar'
        ).order_by(
            'area__nivel_escolar__nombre',
            'area__nombre',
            'nombre'
        )
        
        # Aplicar filtros
        area_id = self.request.GET.get('area')
        nivel_id = self.request.GET.get('nivel')
        search = self.request.GET.get('search')
        
        if area_id:
            queryset = queryset.filter(area_id=area_id)
        
        if nivel_id:
            queryset = queryset.filter(area__nivel_escolar_id=nivel_id)
        
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(area__nombre__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['areas'] = Area.objects.select_related('nivel_escolar').all()
        context['niveles_escolares'] = NivelEscolar.objects.all()
        
        # Estadísticas
        queryset = self.get_queryset()
        context['preescolar_count'] = queryset.filter(
            area__nivel_escolar__nombre='Preescolar'
        ).count()
        
        context['primaria_count'] = queryset.filter(
            area__nivel_escolar__nombre='Primaria'
        ).count()
        
        context['con_ih_count'] = queryset.filter(
            ih__isnull=False
        ).exclude(ih='').count()
        
        return context

class AsignaturaCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    model = Asignatura
    form_class = AsignaturaForm
    template_name = 'administrador/asignaturas/asignatura_form.html'
    success_url = reverse_lazy('administrador:asignatura_list')
    success_message = "Asignatura creada exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Nueva Asignatura'
        context['submit_text'] = 'Crear Asignatura'
        return context

class AsignaturaUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Asignatura
    form_class = AsignaturaForm
    template_name = 'administrador/asignaturas/asignatura_form.html'
    success_url = reverse_lazy('administrador:asignatura_list')
    success_message = "Asignatura actualizada exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Asignatura'
        context['submit_text'] = 'Actualizar Asignatura'
        return context

class AsignaturaDeleteView(RoleRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Asignatura
    template_name = 'administrador/asignaturas/asignatura_confirm_delete.html'
    success_url = reverse_lazy('administrador:asignatura_list')
    success_message = "Asignatura eliminada exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

class AñoLectivoListView_Academica(RoleRequiredMixin, ListView):
    model = AñoLectivo
    template_name = 'administrador/añolectivo/añolectivo_list.html'
    context_object_name = 'años_lectivos'
    allowed_roles = ['Administrador', 'Rector']
    
    def get_queryset(self):
        return AñoLectivo.objects.select_related('colegio', 'sede').order_by('-anho', 'colegio__nombre')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['año_lectivo_actual'] = AñoLectivo.objects.filter(estado=True).first()
        
        # Obtener estadísticas
        años_lectivos = self.get_queryset()
        context['años_lectivos_count'] = años_lectivos.filter(estado=True).count()
        # Años con periodos académicos
        años_con_periodos = 0
        for año in años_lectivos:
            if año.periodos_academicos.exists():
                años_con_periodos += 1
        context['años_con_periodos'] = años_con_periodos
        
        # Años con matrículas
        años_con_matriculas = 0
        for año in años_lectivos:
            if Matricula.objects.filter(año_lectivo=año).exists():
                años_con_matriculas += 1
        context['años_con_matriculas'] = años_con_matriculas
        
        return context

class AñoLectivoCreateView_Academica(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    model = AñoLectivo
    form_class = AñoLectivoForm
    template_name = 'administrador/añolectivo/añolectivo_form.html'
    success_url = reverse_lazy('administrador:añolectivo_list')
    success_message = "Año lectivo creado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Nuevo Año Lectivo'
        context['submit_text'] = 'Crear Año Lectivo'
        return context

class AñoLectivoUpdateView_Academica(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    model = AñoLectivo
    form_class = AñoLectivoForm
    template_name = 'administrador/añolectivo/añolectivo_form.html'
    success_url = reverse_lazy('administrador:añolectivo_list')
    success_message = "Año lectivo actualizado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Año Lectivo'
        context['submit_text'] = 'Actualizar Año Lectivo'
        return context

class AñoLectivoDeleteView(RoleRequiredMixin, SuccessMessageMixin, DeleteView):
    model = AñoLectivo
    template_name = 'administrador/añolectivo/añolectivo_confirm_delete.html'
    success_url = reverse_lazy('administrador:añolectivo_list')
    success_message = "Año lectivo eliminado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

class AñoLectivoActivarDesactivarView(RoleRequiredMixin, View):
    allowed_roles = ['Administrador', 'Rector']
    
    def post(self, request, pk):
        año_lectivo = get_object_or_404(AñoLectivo, pk=pk)
        
        if año_lectivo.estado:
            # Si está activo, desactivarlo
            año_lectivo.estado = False
            año_lectivo.save()
            messages.success(request, f"Año lectivo {año_lectivo.anho} desactivado exitosamente")
        else:
            # Si está inactivo, activarlo (desactivando otros)
            AñoLectivo.objects.filter(estado=True).update(estado=False)
            año_lectivo.estado = True
            año_lectivo.save()
            messages.success(request, f"Año lectivo {año_lectivo.anho} activado exitosamente")
        
        return redirect('administrador:añolectivo_list')
    
    def get(self, request, pk):
        # Si alguien accede por GET, redirigir a la lista
        return redirect('administrador:añolectivo_list')
    
class AñoLectivoPeriodosView(View):
    template_name = 'administrador/añolectivo/añolectivo_periodos.html'
    
    def get(self, request, pk):
        # Obtener el año lectivo
        año_lectivo = get_object_or_404(AñoLectivo, pk=pk)
        
        # Obtener periodos académicos con select_related
        periodos = PeriodoAcademico.objects.filter(
            año_lectivo=año_lectivo
        ).select_related('periodo').order_by('periodo__nombre')
        
        # Obtener todos los periodos disponibles
        periodos_disponibles = Periodo.objects.all()
        
        # Identificar periodos faltantes
        periodos_asignados_ids = periodos.values_list('periodo_id', flat=True)
        periodos_faltantes = periodos_disponibles.exclude(id__in=periodos_asignados_ids)
        
        # Calcular estadísticas
        total_periodos = periodos.count()
        total_activos = periodos.filter(estado=True).count()
        total_inactivos = periodos.filter(estado=False).count()
        
        # Calcular días totales
        dias_totales = 0
        for periodo in periodos:
            if periodo.fecha_inicio and periodo.fecha_fin:
                duracion = (periodo.fecha_fin - periodo.fecha_inicio).days
                if duracion > 0:
                    dias_totales += duracion
        
        # Porcentaje de completitud
        if periodos_disponibles.count() > 0:
            porcentaje_completitud = round((total_periodos / periodos_disponibles.count()) * 100, 1)
        else:
            porcentaje_completitud = 0
        
        # Verificar periodo actual
        hoy = timezone.now().date()
        periodo_actual = None
        for periodo in periodos:
            if periodo.fecha_inicio and periodo.fecha_fin:
                if periodo.fecha_inicio <= hoy <= periodo.fecha_fin:
                    periodo_actual = periodo
                    break
        
        # Contexto completo
        context = {
            'año_lectivo': año_lectivo,
            'periodos': periodos,
            'total_periodos': total_periodos,
            'total_activos': total_activos,
            'total_inactivos': total_inactivos,
            'dias_totales': dias_totales,
            'semanas_totales': round(dias_totales / 7, 1) if dias_totales > 0 else 0,
            'periodos_disponibles': periodos_disponibles,
            'periodos_faltantes': periodos_faltantes,
            'total_faltantes': periodos_faltantes.count(),
            'porcentaje_completitud': porcentaje_completitud,
            'periodo_actual': periodo_actual,
            'tiene_periodos': periodos.exists(),
            'tiene_todos_periodos': total_periodos == periodos_disponibles.count(),
            'fechas_completas': all(p.fecha_inicio and p.fecha_fin for p in periodos) if periodos.exists() else False,
        }
        
        return render(request, self.template_name, context)

class PeriodoAcademicoCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    model = PeriodoAcademico
    form_class = PeriodoAcademicoForm
    template_name = 'administrador/añolectivo/periodo_form.html'
    success_message = "Periodo académico creado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['año_lectivo'] = self.año_lectivo
        return kwargs
    
    def dispatch(self, request, *args, **kwargs):
        # Obtener el año lectivo desde la URL
        self.año_lectivo = get_object_or_404(AñoLectivo, pk=self.kwargs['año_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.año_lectivo = self.año_lectivo
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['año_lectivo'] = self.año_lectivo
        context['title'] = 'Crear Nuevo Periodo Académico'
        context['submit_text'] = 'Crear Periodo'
        return context
    
    def get_success_url(self):
        return reverse_lazy('administrador:añolectivo_periodos', kwargs={'pk': self.año_lectivo.pk})

class PeriodoAcademicoUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    model = PeriodoAcademico
    form_class = PeriodoAcademicoForm
    template_name = 'administrador/añolectivo/periodo_form.html'
    success_message = "Periodo académico actualizado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['año_lectivo'] = self.object.año_lectivo
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['año_lectivo'] = self.object.año_lectivo
        context['title'] = 'Editar Periodo Académico'
        context['submit_text'] = 'Actualizar Periodo'
        return context
    
    def get_success_url(self):
        return reverse_lazy('administrador:añolectivo_periodos', kwargs={'pk': self.object.año_lectivo.pk})

class PeriodoAcademicoDeleteView(RoleRequiredMixin, SuccessMessageMixin, DeleteView):
    model = PeriodoAcademico
    template_name = 'administrador/añolectivo/periodo_confirm_delete.html'
    success_message = "Periodo académico eliminado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['año_lectivo'] = self.object.año_lectivo
        return context
    
    def get_success_url(self):
        año_lectivo_id = self.object.año_lectivo.pk
        messages.success(self.request, self.success_message)
        return reverse_lazy('administrador:añolectivo_periodos', kwargs={'pk': año_lectivo_id})

class AgregarMultiplesPeriodosView(RoleRequiredMixin, View):
    allowed_roles = ['Administrador', 'Rector']
    
    def post(self, request, pk):
        año_lectivo = get_object_or_404(AñoLectivo, pk=pk)
        
        # Verificar si el año lectivo tiene fechas definidas
        if not año_lectivo.fecha_inicio or not año_lectivo.fecha_fin:
            messages.error(request, "El año lectivo debe tener fecha de inicio y fin definidas")
            return redirect('administrador:añolectivo_periodos', pk=año_lectivo.pk)
        
        # Obtener periodos ya asignados
        periodos_asignados = PeriodoAcademico.objects.filter(
            año_lectivo=año_lectivo
        ).values_list('periodo_id', flat=True)
        
        # Obtener periodos faltantes
        periodos_faltantes = Periodo.objects.exclude(id__in=periodos_asignados)
        
        # Calcular fechas para los periodos faltantes
        periodo_creados = []
        
        # Dividir el año lectivo en periodos iguales
        fecha_inicio_año = año_lectivo.fecha_inicio
        fecha_fin_año = año_lectivo.fecha_fin
        duracion_año = (fecha_fin_año - fecha_inicio_año).days
        num_periodos_faltantes = periodos_faltantes.count()
        
        if num_periodos_faltantes > 0:
            duracion_periodo = duracion_año // num_periodos_faltantes
            
            for i, periodo in enumerate(periodos_faltantes):
                # Calcular fechas para este periodo
                periodo_inicio = fecha_inicio_año + timedelta(days=i * duracion_periodo)
                periodo_fin = fecha_inicio_año + timedelta(days=(i + 1) * duracion_periodo - 1)
                
                # Ajustar el último periodo para terminar en la fecha fin del año
                if i == num_periodos_faltantes - 1:
                    periodo_fin = fecha_fin_año
                
                # Crear el periodo académico
                periodo_academico = PeriodoAcademico.objects.create(
                    año_lectivo=año_lectivo,
                    periodo=periodo,
                    fecha_inicio=periodo_inicio,
                    fecha_fin=periodo_fin,
                    estado=False  # Por defecto inactivo
                )
                periodo_creados.append(periodo_academico)
        
        if periodo_creados:
            messages.success(request, f"Se crearon {len(periodo_creados)} periodos académicos")
        else:
            messages.info(request, "No hay periodos faltantes para agregar")
        
        return redirect('administrador:añolectivo_periodos', pk=año_lectivo.pk)
    
# ========================
# GESTIÓN DE GRADOS POR AÑO LECTIVO
# ========================

class GradoAñoLectivoListView(RoleRequiredMixin, ListView):
    model = GradoAñoLectivo
    template_name = 'administrador/gestion_academica/grado_anho_list.html'
    context_object_name = 'grados_anho'
    allowed_roles = ['Administrador', 'Rector']
    paginate_by = 20
    
    def get_queryset(self):
        # Queryset base con filtros
        qs = GradoAñoLectivo.objects.select_related(
            'grado__nivel_escolar',
            'año_lectivo__sede'
        ).order_by('-año_lectivo__anho', 'grado__nombre')
        
        # Aplicar filtros desde GET parameters
        año_lectivo = self.request.GET.get('año_lectivo')
        sede = self.request.GET.get('sede')
        nivel_escolar = self.request.GET.get('nivel_escolar')
        estado = self.request.GET.get('estado')
        
        if año_lectivo:
            qs = qs.filter(año_lectivo_id=año_lectivo)
        
        if sede:
            qs = qs.filter(año_lectivo__sede_id=sede)
        
        if nivel_escolar:
            qs = qs.filter(grado__nivel_escolar__nombre=nivel_escolar)
        
        if estado:
            qs = qs.filter(estado=bool(int(estado)))
        
        # Guardar queryset completo para estadísticas
        self.qs_completo = qs
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener queryset completo (antes de paginación)
        qs = self.qs_completo
        
        # Estadísticas
        context['total_grados'] = qs.count()
        context['total_activos'] = qs.filter(estado=True).count()
        context['total_inactivos'] = qs.filter(estado=False).count()
        context['total_preescolar'] = qs.filter(
            grado__nivel_escolar__nombre='Preescolar'
        ).count()
        context['total_primaria'] = qs.filter(
            grado__nivel_escolar__nombre='Primaria'
        ).count()
        
        # Datos para filtros
        from gestioncolegio.models import AñoLectivo, Sede
        context['años_lectivos'] = AñoLectivo.objects.filter(estado=True).order_by('-anho')
        context['sedes'] = Sede.objects.filter(estado=True).order_by('nombre')
        
        return context

class GradoAñoLectivoCreateView(RoleRequiredMixin, CreateView):
    """Crear nueva relación grado-año lectivo"""
    model = GradoAñoLectivo
    form_class = GradoAñoLectivoForm
    template_name = 'administrador/gestion_academica/grado_anho_form.html'
    success_url = reverse_lazy('administrador:grado_anho_list')
    allowed_roles = ['Administrador', 'Rector']
    
    def get_success_url(self):
        messages.success(self.request, 'Relación grado-año lectivo creada exitosamente')
        return super().get_success_url()

class GradoAñoLectivoUpdateView(RoleRequiredMixin, UpdateView):
    """Editar relación grado-año lectivo"""
    model = GradoAñoLectivo
    form_class = GradoAñoLectivoForm
    template_name = 'administrador/gestion_academica/grado_anho_form.html'
    success_url = reverse_lazy('administrador:grado_anho_list')
    allowed_roles = ['Administrador', 'Rector']
    
    def get_success_url(self):
        messages.success(self.request, 'Relación grado-año lectivo actualizada exitosamente')
        return super().get_success_url()

class GradoAñoLectivoDeleteView(RoleRequiredMixin, DeleteView):
    """Eliminar relación grado-año lectivo"""
    model = GradoAñoLectivo
    template_name = 'administrador/gestion_academica/grado_anho_confirm_delete.html'
    success_url = reverse_lazy('administrador:grado_anho_list')
    allowed_roles = ['Administrador', 'Rector']
    
    def get_success_url(self):
        messages.success(self.request, 'Relación grado-año lectivo eliminada exitosamente')
        return super().get_success_url()

# ========================
# GESTIÓN DE ASIGNATURAS POR GRADO Y AÑO
# ========================

class AsignaturaGradoAñoLectivoListView(RoleRequiredMixin, ListView):
    """Lista de asignaturas por grado y año lectivo"""
    model = AsignaturaGradoAñoLectivo
    template_name = 'administrador/gestion_academica/asignatura_grado_list.html'
    context_object_name = 'asignaturas_grado'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    paginate_by = 30
    
    def get_queryset(self):
        queryset = AsignaturaGradoAñoLectivo.objects.select_related(
            'asignatura__area__nivel_escolar',
            'grado_año_lectivo__grado',
            'grado_año_lectivo__año_lectivo__sede',
            'docente__usuario'
        ).order_by(
            'grado_año_lectivo__año_lectivo__anho',
            'grado_año_lectivo__grado__nombre',
            'asignatura__nombre'
        )
        
        # Filtros
        año_lectivo = self.request.GET.get('año_lectivo')
        grado = self.request.GET.get('grado')
        sede = self.request.GET.get('sede')
        docente = self.request.GET.get('docente')
        
        if año_lectivo:
            queryset = queryset.filter(grado_año_lectivo__año_lectivo_id=año_lectivo)
        
        if grado:
            queryset = queryset.filter(grado_año_lectivo__grado_id=grado)
        
        if sede:
            queryset = queryset.filter(grado_año_lectivo__año_lectivo__sede_id=sede)
        
        if docente:
            queryset = queryset.filter(docente_id=docente)

        # 👉 Guardamos la versión SIN paginación
        self.queryset_original = queryset

        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        qs = self.queryset_original  # ← QuerySet real SIN paginar

        # Estadísticas
        context["total_con_docente"] = qs.filter(docente__isnull=False).count()
        context["total_sin_docente"] = qs.filter(docente__isnull=True).count()
        context["total_grados"] = qs.values(
            "grado_año_lectivo__grado"
        ).distinct().count()

        # Filtros
        context['años_lectivos'] = AñoLectivo.objects.filter(estado=True).order_by('-anho')
        context['grados'] = Grado.objects.all().order_by('nombre')
        context['sedes'] = Sede.objects.filter(estado=True).order_by('nombre')
        context['docentes'] = Docente.objects.filter(estado=True).select_related('usuario')

        return context

class AsignaturaGradoAñoLectivoCreateView(RoleRequiredMixin, CreateView):
    """Crear nueva asignatura por grado y año"""
    model = AsignaturaGradoAñoLectivo
    form_class = AsignaturaGradoAñoLectivoForm
    template_name = 'administrador/gestion_academica/asignatura_grado_form.html'
    success_url = reverse_lazy('administrador:asignatura_grado_list')
    allowed_roles = ['Administrador', 'Rector']
    
    def get_success_url(self):
        messages.success(self.request, 'Asignatura por grado creada exitosamente')
        return super().get_success_url()

class AsignaturaGradoAñoLectivoUpdateView(RoleRequiredMixin, UpdateView):
    """Editar asignatura por grado y año"""
    model = AsignaturaGradoAñoLectivo
    form_class = AsignaturaGradoAñoLectivoForm
    template_name = 'administrador/gestion_academica/asignatura_grado_form.html'
    success_url = reverse_lazy('administrador:asignatura_grado_list')
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get_success_url(self):
        messages.success(self.request, 'Asignatura por grado actualizada exitosamente')
        return super().get_success_url()

class AsignaturaGradoAñoLectivoDeleteView(RoleRequiredMixin, SuccessMessageMixin, DeleteView):
    """Eliminar asignatura por grado y año"""
    model = AsignaturaGradoAñoLectivo
    template_name = 'administrador/gestion_academica/asignatura_grado_confirm_delete.html'
    success_url = reverse_lazy('administrador:asignatura_grado_list')
    success_message = "Asignatura por grado eliminada exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar estadísticas relacionadas
        object = self.get_object()
        context['horarios_count'] = object.horarios.count() if hasattr(object, 'horarios') else 0
        context['notas_count'] = object.notas.count() if hasattr(object, 'notas') else 0
        context['logros_count'] = object.logros.count() if hasattr(object, 'logros') else 0
        return context

# Vistas adicionales para gestión masiva

class AsignaturaGradoAñoLectivoBulkCreateView(RoleRequiredMixin, View):
    """Crear asignaturas por grado de forma masiva"""
    template_name = 'administrador/gestion_academica/asignatura_grado_bulk.html'
    allowed_roles = ['Administrador', 'Rector']
    
    def get(self, request):
        form = AsignaturaGradoBulkForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = AsignaturaGradoBulkForm(request.POST)
        
        if form.is_valid():
            # Lógica para crear múltiples asignaturas
            pass
        
        return render(request, self.template_name, {'form': form})

class AsignaturaGradoAñoLectivoCopyView(RoleRequiredMixin, View):
    """Copiar asignaturas de un año/grado a otro"""
    template_name = 'administrador/gestion_academica/asignatura_grado_copy.html'
    allowed_roles = ['Administrador', 'Rector']
    
    def get(self, request):
        form = AsignaturaGradoCopyForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = AsignaturaGradoCopyForm(request.POST)
        
        if form.is_valid():
            try:
                # Obtener datos del formulario
                año_origen = form.cleaned_data['año_origen']
                año_destino = form.cleaned_data['año_destino']
                grados_origen = form.cleaned_data['grados_origen']
                grados_destino = form.cleaned_data['grados_destino']
                sedes = form.cleaned_data['sedes']
                incluir_docentes = form.cleaned_data['incluir_docentes']
                sobrescribir_existentes = form.cleaned_data['sobrescribir_existentes']
                
                # Verificar que el número de grados sea igual
                if len(grados_origen) != len(grados_destino):
                    messages.error(request, 'El número de grados en origen y destino debe ser igual.')
                    return render(request, self.template_name, {'form': form})
                
                # Crear mapeo de grados
                mapeo_grados = dict(zip(grados_origen, grados_destino))
                
                # Contadores
                asignaturas_copiadas = 0
                asignaturas_sobrescritas = 0
                errores = []
                
                # Para cada grado en el origen
                for grado_origen, grado_destino in mapeo_grados.items():
                    # Para cada sede
                    for sede in sedes:
                        try:
                            # Obtener las asignaturas origen para este grado y sede
                            asignaturas_origen = AsignaturaGradoAñoLectivo.objects.filter(
                                grado_año_lectivo__grado=grado_origen,
                                grado_año_lectivo__año_lectivo=año_origen,
                                sede=sede
                            ).select_related('asignatura', 'docente')
                            
                            # Obtener el GradoAñoLectivo destino
                            grado_año_destino = GradoAñoLectivo.objects.get(
                                grado=grado_destino,
                                año_lectivo=año_destino
                            )
                            
                            # Si se debe sobrescribir, eliminar existentes
                            if sobrescribir_existentes:
                                asignaturas_existentes = AsignaturaGradoAñoLectivo.objects.filter(
                                    grado_año_lectivo=grado_año_destino,
                                    sede=sede
                                )
                                asignaturas_sobrescritas += asignaturas_existentes.count()
                                asignaturas_existentes.delete()
                            
                            # Copiar cada asignatura
                            for asignatura_origen in asignaturas_origen:
                                try:
                                    # Verificar si ya existe en destino
                                    existe = AsignaturaGradoAñoLectivo.objects.filter(
                                        asignatura=asignatura_origen.asignatura,
                                        grado_año_lectivo=grado_año_destino,
                                        sede=sede
                                    ).exists()
                                    
                                    if not existe:
                                        # Crear nueva asignatura en destino
                                        nueva_asignatura = AsignaturaGradoAñoLectivo(
                                            asignatura=asignatura_origen.asignatura,
                                            grado_año_lectivo=grado_año_destino,
                                            sede=sede,
                                            docente=asignatura_origen.docente if incluir_docentes else None
                                        )
                                        nueva_asignatura.save()
                                        asignaturas_copiadas += 1
                                    
                                except Exception as e:
                                    errores.append(
                                        f"Error copiando {asignatura_origen.asignatura.nombre} "
                                        f"a {grado_destino.nombre}: {str(e)}"
                                    )
                            
                        except GradoAñoLectivo.DoesNotExist:
                            errores.append(
                                f"Grado-año destino no encontrado: {grado_destino.nombre} en {año_destino.anho}"
                            )
                        except Exception as e:
                            errores.append(
                                f"Error procesando {grado_origen.nombre} a {grado_destino.nombre}: {str(e)}"
                            )
                
                # Preparar mensaje de resultado
                if asignaturas_copiadas > 0:
                    messages.success(
                        request,
                        f"¡Copia completada exitosamente!<br>"
                        f"<strong>{asignaturas_copiadas}</strong> asignaturas copiadas<br>"
                        f"De: {año_origen.anho} → A: {año_destino.anho}<br>"
                        f"{'Incluyendo docentes' if incluir_docentes else 'Sin asignación de docentes'}<br>"
                        f"{f'{asignaturas_sobrescritas} sobrescritas' if sobrescribir_existentes else 'Sin sobrescribir'}"
                    )
                    
                    if errores:
                        messages.warning(
                            request,
                            f"Se encontraron {len(errores)} errores durante la copia. "
                            f"La mayoría de las asignaturas se copiaron correctamente."
                        )
                
                elif errores:
                    messages.error(
                        request,
                        "No se pudieron copiar las asignaturas debido a errores."
                    )
                else:
                    messages.info(
                        request,
                        "No se encontraron asignaturas para copiar con los criterios seleccionados."
                    )
                
                # Registrar la acción
                AuditoriaSistema.objects.create(
                    usuario=request.user.usuario if hasattr(request.user, 'usuario') else None,
                    accion='creacion_masiva',
                    modelo_afectado='AsignaturaGradoAñoLectivo',
                    descripcion=f"Copia masiva de asignaturas de {año_origen.anho} a {año_destino.anho}",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return redirect('administrador:asignatura_grado_list')
                
            except Exception as e:
                messages.error(
                    request,
                    f"Error inesperado durante la copia: {str(e)}"
                )
                return render(request, self.template_name, {'form': form})
        
        # Si el formulario no es válido
        return render(request, self.template_name, {'form': form})

class GestionAcademicaAjaxView(RoleRequiredMixin, View):
    """Vistas AJAX para gestión académica"""
    allowed_roles = ['Administrador', 'Rector']
    
    def get(self, request):
        tipo = request.GET.get('tipo')
        
        if tipo == 'asignatura_grado_ajax_stats':
            # Estadísticas de asignaturas por año - Para vista de copia
            año_lectivo_id = request.GET.get('año_lectivo_id')
            
            if not año_lectivo_id:
                return JsonResponse({'error': 'ID de año lectivo requerido'}, status=400)
            
            try:
                año_lectivo = AñoLectivo.objects.get(id=año_lectivo_id)
                
                # Total de asignaturas en el año
                total_asignaturas = AsignaturaGradoAñoLectivo.objects.filter(
                    grado_año_lectivo__año_lectivo=año_lectivo
                ).count()
                
                # Grados con asignaturas
                grados_con_asignaturas = AsignaturaGradoAñoLectivo.objects.filter(
                    grado_año_lectivo__año_lectivo=año_lectivo
                ).values('grado_año_lectivo__grado').distinct().count()
                
                # Asignaturas con docente
                con_docente = AsignaturaGradoAñoLectivo.objects.filter(
                    grado_año_lectivo__año_lectivo=año_lectivo,
                    docente__isnull=False
                ).count()
                
                # Asignaturas sin docente
                sin_docente = AsignaturaGradoAñoLectivo.objects.filter(
                    grado_año_lectivo__año_lectivo=año_lectivo,
                    docente__isnull=True
                ).count()
                
                # Promedio de asignaturas por grado
                promedio = 0
                if grados_con_asignaturas > 0:
                    promedio = round(total_asignaturas / grados_con_asignaturas, 1)
                
                # Sedes con asignaturas
                sedes_con_asignaturas = AsignaturaGradoAñoLectivo.objects.filter(
                    grado_año_lectivo__año_lectivo=año_lectivo
                ).values('sede').distinct().count()
                
                data = {
                    'success': True,
                    'anho': año_lectivo.anho,
                    'total_asignaturas': total_asignaturas,
                    'grados_con_asignaturas': grados_con_asignaturas,
                    'asignaturas_con_docente': con_docente,
                    'asignaturas_sin_docente': sin_docente,
                    'promedio_asignaturas_por_grado': promedio,
                    'sedes_con_asignaturas': sedes_con_asignaturas,
                    'porcentaje_con_docente': round((con_docente / total_asignaturas * 100), 1) if total_asignaturas > 0 else 0,
                }
                return JsonResponse(data)
            except AñoLectivo.DoesNotExist:
                return JsonResponse({'error': 'Año lectivo no encontrado'}, status=404)
        
        # ... (mantener otros tipos de consulta)
        
        return JsonResponse({'error': 'Tipo de consulta no válido'}, status=400)