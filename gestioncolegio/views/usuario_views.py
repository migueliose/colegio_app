"""
Vistas simplificadas para gestión de usuarios
"""
import logging
from django.views.generic import ListView, UpdateView, DeleteView, CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Q

# Mixins
from gestioncolegio.mixins import RoleRequiredMixin

# Models
from usuarios.models import Usuario, TipoUsuario, Docente
from estudiantes.models import Estudiante, Acudiente

logger = logging.getLogger(__name__)


class UsuarioListView(RoleRequiredMixin, ListView):
    """Lista simplificada de usuarios"""
    template_name = 'gestioncolegio/usuarios/usuarios_list.html'
    allowed_roles = ['Administrador']
    context_object_name = 'usuarios'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = Usuario.objects.select_related(
            'tipo_usuario'
        ).order_by('apellidos', 'nombres')
        
        # Filtro por tipo de usuario
        tipo_id = self.request.GET.get('tipo_usuario')
        if tipo_id:
            queryset = queryset.filter(tipo_usuario_id=tipo_id)
        
        # Filtro por búsqueda
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(nombres__icontains=search_query) |
                Q(apellidos__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Tipos de usuario para filtros
        context['tipos_usuario'] = TipoUsuario.objects.all()
        
        return context


class UsuarioUpdateView(RoleRequiredMixin, UpdateView):
    """Actualizar usuario - Versión simplificada"""
    template_name = 'gestioncolegio/usuarios/usuario_form.html'
    allowed_roles = ['Administrador']
    model = Usuario
    fields = [
        'tipo_usuario',
        'nombres',
        'apellidos',
        'email',
        'telefono',
        'estado'
    ]
    success_url = reverse_lazy('gestioncolegio:usuario_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Usuario actualizado correctamente.")
        return super().form_valid(form)


class UsuarioDeleteView(RoleRequiredMixin, DeleteView):
    """Desactivar usuario - Versión simplificada"""
    template_name = 'gestioncolegio/usuarios/usuario_confirm_delete.html'
    allowed_roles = ['Administrador']
    model = Usuario
    success_url = reverse_lazy('gestioncolegio:usuario_list')
    
    def form_valid(self, form):
        usuario = self.get_object()
        usuario.estado = False
        usuario.is_active = False
        usuario.save()
        
        messages.success(self.request, f"Usuario {usuario.get_full_name()} desactivado.")
        return redirect(self.success_url)


class UsuarioCreateView(RoleRequiredMixin, CreateView):
    """Crear nuevo usuario - Versión simplificada"""
    template_name = 'gestioncolegio/usuarios/usuario_form.html'
    allowed_roles = ['Administrador']
    model = Usuario
    fields = [
        'username',
        'tipo_usuario',
        'nombres',
        'apellidos',
        'email',
        'password'
    ]
    success_url = reverse_lazy('gestioncolegio:usuario_list')
    
    def form_valid(self, form):
        usuario = form.save(commit=False)
        usuario.set_password(form.cleaned_data['password'])
        usuario.estado = True
        usuario.save()
        
        # Crear perfil según tipo
        tipo = usuario.tipo_usuario.nombre if usuario.tipo_usuario else None
        
        if tipo == 'Docente':
            Docente.objects.get_or_create(usuario=usuario)
        elif tipo == 'Estudiante':
            Estudiante.objects.get_or_create(usuario=usuario)
        
        messages.success(self.request, "Usuario creado correctamente.")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['es_creacion'] = True
        return context


class DocenteListView(RoleRequiredMixin, ListView):
    """Lista simplificada de docentes"""
    template_name = 'gestioncolegio/usuarios/docentes_list.html'
    allowed_roles = ['Administrador', 'Rector']
    context_object_name = 'docentes'
    
    def get_queryset(self):
        return Docente.objects.filter(
            usuario__estado=True
        ).select_related('usuario').order_by('usuario__apellidos', 'usuario__nombres')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_docentes'] = self.get_queryset().count()
        return context


class EstudianteListView(RoleRequiredMixin, ListView):
    """Lista simplificada de estudiantes"""
    template_name = 'gestioncolegio/usuarios/estudiantes_list.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    context_object_name = 'estudiantes'
    
    def get_queryset(self):
        queryset = Estudiante.objects.filter(
            usuario__estado=True
        ).select_related(
            'usuario',
            'grado_actual__grado'
        ).order_by('usuario__apellidos', 'usuario__nombres')
        
        # Si es docente, filtrar sus estudiantes
        if self.request.user.tipo_usuario.nombre == 'Docente':
            try:
                docente = Docente.objects.get(usuario=self.request.user)
                from matricula.models import AsignaturaGradoAñoLectivo
                grados_ids = AsignaturaGradoAñoLectivo.objects.filter(
                    docente=docente
                ).values_list('grado_año_lectivo__grado_id', flat=True).distinct()
                
                queryset = queryset.filter(grado_actual__grado_id__in=grados_ids)
            except Docente.DoesNotExist:
                pass
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_estudiantes'] = self.get_queryset().count()
        return context