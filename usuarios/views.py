from django.shortcuts import redirect
from django.contrib import messages
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.db.models import Q
from django.views.generic import DeleteView
from estudiantes.models import Estudiante
from usuarios.models import Usuario, Docente
from matricula.models import AsignaturaGradoAñoLectivo
from docentes.forms import *
from gestioncolegio.views import RoleRequiredMixin

# Vistas simplificadas para empezar
class GestionUsuariosView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """Vista principal de gestión de usuarios"""
    template_name = 'usuarios/gestion_usuarios.html'
    allowed_roles = ['Administrador', 'Rector']

class EstudiantesListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """Lista de estudiantes"""
    template_name = 'usuarios/estudiantes_list.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    paginate_by = 20
    
    def get_queryset(self):
        from estudiantes.models import Estudiante
        queryset = Estudiante.objects.filter(estado=True).select_related('usuario')
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(usuario__nombres__icontains=search) |
                Q(usuario__apellidos__icontains=search) |
                Q(usuario__numero_documento__icontains=search)
            )
        
        return queryset.order_by('usuario__apellidos', 'usuario__nombres')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estudiantes'] = self.get_queryset()
        return context

class DocentesListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """Lista de docentes"""
    template_name = 'usuarios/docentes_list.html'
    allowed_roles = ['Administrador', 'Rector']
    model = Docente  
    context_object_name = 'docentes'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Docente.objects.filter(estado=True).select_related('usuario')
        
        # Búsqueda
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(usuario__nombres__icontains=search) |
                Q(usuario__apellidos__icontains=search) |
                Q(usuario__numero_documento__icontains=search)
            )
        
        return queryset.order_by('usuario__apellidos', 'usuario__nombres')

# =============================================
# VISTAS CRUD PARA ESTUDIANTES
# =============================================

class EstudianteCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    """Crear nuevo estudiante"""
    template_name = 'usuarios/estudiante_form.html'
    allowed_roles = ['Administrador', 'Rector']
    model = Estudiante # usar el modelo directamente, no string
    fields = ['usuario', 'foto', 'estado']
    success_url = reverse_lazy('usuarios:estudiantes_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filtrar usuarios que no sean estudiantes
        form.fields['usuario'].queryset = Usuario.objects.filter(
            estado=True,
            tipo_usuario__nombre='Estudiante'
        )
        return form
    
    def form_valid(self, form):
        messages.success(self.request, 'Estudiante creado exitosamente.')
        return super().form_valid(form)

class EstudianteUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    """Editar estudiante"""
    template_name = 'usuarios/estudiante_form.html'
    allowed_roles = ['Administrador', 'Rector']
    model = Estudiante  
    fields = ['foto', 'estado']
    success_url = reverse_lazy('usuarios:estudiantes_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Estudiante actualizado exitosamente.')
        return super().form_valid(form)

class EstudianteDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    """Eliminar estudiante (eliminación lógica)"""
    template_name = 'usuarios/estudiante_confirm_delete.html'
    allowed_roles = ['Administrador', 'Rector']
    model = Estudiante  
    success_url = reverse_lazy('usuarios:estudiantes_list')
    
    def form_valid(self, form):
        success_message = f"Estudiante {self.object.usuario.get_full_name()} desactivado exitosamente."
        self.object.estado = False
        self.object.save()
        messages.success(self.request, success_message)
        return redirect(self.success_url)

# Vistas adicionales útiles
class EstudianteDetailView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    """Detalle de estudiante"""
    template_name = 'usuarios/estudiante_detail.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    model = Estudiante  
    context_object_name = 'estudiante'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante = self.object
        
        # Agregar información adicional al contexto
        try:
            context['matricula'] = estudiante.matricula.select_related(
                'año_lectivo', 'grado_año_lectivo__grado', 'sede'
            ).order_by('-año_lectivo__anho')
            
            context['notas'] = estudiante.notas.select_related(
                'asignatura_grado_año_lectivo__asignatura',
                'periodo_academico'
            ).order_by('-periodo_academico__fecha_inicio')[:10]
            
            context['acudientes'] = estudiante.acudientes.select_related('acudiente')
            
        except Exception as e:
            print(f"Error cargando datos del estudiante: {e}")
        
        return context

# =============================================
# VISTAS CRUD PARA DOCENTES
# =============================================
class DocenteDetailView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    """Detalle de docente"""
    template_name = 'usuarios/docente_detail.html'
    allowed_roles = ['Administrador', 'Rector']
    model = Docente  
    context_object_name = 'docente'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        docente = self.object
        
        try:
            context['asignaturas_actuales'] = AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente,
                grado_año_lectivo__año_lectivo__estado=True
            ).select_related('asignatura', 'grado_año_lectivo__grado', 'sede')
            
            context['contactos'] = docente.contactos.all()
            
        except Exception as e:
            print(f"Error cargando datos del docente: {e}")
        
        return context
    
class DocenteCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    """Crear nuevo docente"""
    template_name = 'usuarios/docente_form.html'
    allowed_roles = ['Administrador', 'Rector']
    model = Docente  
    fields = ['usuario', 'foto', 'hdv', 'estado']
    success_url = reverse_lazy('usuarios:docentes_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filtrar usuarios que sean docentes
        form.fields['usuario'].queryset = Usuario.objects.filter(
            estado=True,
            tipo_usuario__nombre='Docente'
        )
        return form
    
    def form_valid(self, form):
        messages.success(self.request, 'Docente creado exitosamente.')
        return super().form_valid(form)

class DocenteUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    """Editar docente"""
    template_name = 'usuarios/docente_form.html'
    allowed_roles = ['Administrador', 'Rector']
    model = Docente  
    fields = ['foto', 'hdv', 'estado']
    success_url = reverse_lazy('usuarios:docentes_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Docente actualizado exitosamente.')
        return super().form_valid(form)

class DocenteDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    """Eliminar docente (eliminación lógica)"""
    template_name = 'usuarios/docente_confirm_delete.html'
    allowed_roles = ['Administrador', 'Rector']
    model = Docente  
    success_url = reverse_lazy('usuarios:docentes_list')
    
    def form_valid(self, form):
        success_message = f"Docente {self.object.usuario.get_full_name()} desactivado exitosamente."
        self.object.estado = False
        self.object.save()
        messages.success(self.request, success_message)
        return redirect(self.success_url)

class AdministradoresListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """Lista de administradores"""
    template_name = 'usuarios/administradores_list.html'
    allowed_roles = ['Administrador', 'Rector']
    context_object_name = 'administradores'
    paginate_by = 20
    
    def get_queryset(self):
        from usuarios.models import Usuario
        from usuarios.models import TipoUsuario
        
        try:
            # Obtener el tipo de usuario "Administrador"
            tipo_administrador = TipoUsuario.objects.filter(nombre='Administrador').first()
            if tipo_administrador:
                queryset = Usuario.objects.filter(
                    tipo_usuario=tipo_administrador,
                    estado=True
                )
            else:
                queryset = Usuario.objects.none()
        except:
            queryset = Usuario.objects.none()
        
        # Búsqueda
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nombres__icontains=search) |
                Q(apellidos__icontains=search) |
                Q(numero_documento__icontains=search) |
                Q(email__icontains=search)
            )
        
        return queryset.order_by('apellidos', 'nombres')