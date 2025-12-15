from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DeleteView
from estudiantes.models import Estudiante, Nota
from academico.models import Grado, Asignatura, HorarioClase
from matricula.models import AsignaturaGradoAñoLectivo, PeriodoAcademico
from estudiantes.models import Estudiante, Nota
from matricula.models import PeriodoAcademico, AsignaturaGradoAñoLectivo
from gestioncolegio.views import RoleRequiredMixin

class GradosListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """Lista de grados académicos"""
    template_name = 'academico/grados_list.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    model = Grado  
    context_object_name = 'grados'
    
    def get_queryset(self):
        return Grado.objects.select_related('nivel_escolar').order_by('nivel_escolar', 'nombre')

class GradoCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    """Crear nuevo grado"""
    template_name = 'academico/grado_form.html'
    allowed_roles = ['Administrador', 'Rector']
    model = Grado  
    fields = ['nombre', 'nivel_escolar']
    success_url = reverse_lazy('academico:grados_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Grado "{form.instance.nombre}" creado exitosamente.')
        return super().form_valid(form)

class GradoUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    """Editar grado"""
    template_name = 'academico/grado_form.html'
    allowed_roles = ['Administrador', 'Rector']
    model = Grado  
    fields = ['nombre', 'nivel_escolar']
    success_url = reverse_lazy('academico:grados_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Grado "{form.instance.nombre}" actualizado exitosamente.')
        return super().form_valid(form)

class GradoDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    """Eliminar grado"""
    template_name = 'academico/grado_confirm_delete.html'
    allowed_roles = ['Administrador', 'Rector']
    model = Grado  
    success_url = reverse_lazy('academico:grados_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Grado "{self.object.nombre}" eliminado exitosamente.')
        return super().form_valid(form)

    
class AsignaturasListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """Lista de asignaturas"""
    template_name = 'academico/asignaturas_list.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    model = Asignatura  
    context_object_name = 'asignaturas'
    
    def get_queryset(self):
        return Asignatura.objects.select_related('area', 'area__nivel_escolar').order_by('area__nivel_escolar', 'area', 'nombre')

class HorariosListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """Lista de horarios"""
    template_name = 'academico/horarios_list.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    model = HorarioClase  
    context_object_name = 'horarios'
    
    def get_queryset(self):
        return HorarioClase.objects.select_related(
            'asignatura_grado__asignatura',
            'asignatura_grado__grado_año_lectivo__grado',
            'asignatura_grado__sede'
        ).order_by('dia_semana', 'hora_inicio')

# =============================================
# SISTEMA DE NOTAS
# =============================================
class NotasListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """Lista de notas"""
    template_name = 'academico/notas_list.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    model = Nota  
    context_object_name = 'notas'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Nota.objects.select_related(
            'estudiante__usuario',
            'asignatura_grado_año_lectivo__asignatura',
            'periodo_academico'
        )
        
        # Filtros
        estudiante_id = self.request.GET.get('estudiante')
        asignatura_id = self.request.GET.get('asignatura')
        periodo_id = self.request.GET.get('periodo')
        
        if estudiante_id:
            queryset = queryset.filter(estudiante_id=estudiante_id)
        if asignatura_id:
            queryset = queryset.filter(asignatura_grado_año_lectivo_id=asignatura_id)
        if periodo_id:
            queryset = queryset.filter(periodo_academico_id=periodo_id)
        
        return queryset.order_by('-periodo_academico__fecha_inicio', 'estudiante__usuario__apellidos')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar opciones para los filtros
        context['estudiantes'] = Estudiante.objects.filter(estado=True).select_related('usuario')
        context['asignaturas'] = AsignaturaGradoAñoLectivo.objects.filter(
            grado_año_lectivo__año_lectivo__estado=True
        ).select_related('asignatura')
        context['periodos'] = PeriodoAcademico.objects.filter(
            año_lectivo__estado=True
        ).select_related('periodo', 'año_lectivo')
        return context

class NotaCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    """Crear nueva nota"""
    template_name = 'academico/nota_form.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    model = Nota  
    fields = ['estudiante', 'asignatura_grado_año_lectivo', 'periodo_academico', 'calificacion', 'observaciones']
    success_url = reverse_lazy('academico:notas_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filtrar querysets
        form.fields['estudiante'].queryset = Estudiante.objects.filter(estado=True)
        form.fields['asignatura_grado_año_lectivo'].queryset = AsignaturaGradoAñoLectivo.objects.filter(
            grado_año_lectivo__año_lectivo__estado=True
        )
        form.fields['periodo_academico'].queryset = PeriodoAcademico.objects.filter(
            año_lectivo__estado=True
        )
        
        return form
    
    def form_valid(self, form):
        messages.success(self.request, 'Nota registrada exitosamente.')
        return super().form_valid(form)

class NotaUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    """Editar nota"""
    template_name = 'academico/nota_form.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    model = Nota  
    fields = ['calificacion', 'observaciones']
    success_url = reverse_lazy('academico:notas_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Nota actualizada exitosamente.')
        return super().form_valid(form)

class NotaDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    """Eliminar nota"""
    template_name = 'academico/nota_confirm_delete.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    model = Nota  
    success_url = reverse_lazy('academico:notas_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Nota eliminada exitosamente.')
        return super().form_valid(form)