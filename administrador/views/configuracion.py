from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.db.models import Q
from django.views.generic import View


from gestioncolegio.mixins import RoleRequiredMixin
from gestioncolegio.models import (
    Colegio, 
    Sede, 
    RecursosColegio, 
    AñoLectivo,
    ConfiguracionGeneral,
    ParametroSistema,
)

from ..forms.formularios import AñoLectivoForm
from ..forms.config import *

# ===================== DATOS INSTITUCIONALES =====================

class ColegioListView(RoleRequiredMixin, ListView):
    model = Colegio
    template_name = 'administrador/configuracion/colegio_list.html'
    context_object_name = 'colegios'
    allowed_roles = ['Administrador', 'Rector']

    def get_queryset(self):
        return Colegio.objects.filter(estado=True).order_by('nombre')

class ColegioCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    model = Colegio
    form_class = ColegioForm
    template_name = 'administrador/configuracion/colegio_form.html'
    success_url = reverse_lazy('administrador:colegio_list')
    success_message = "Colegio creado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Nuevo Colegio'
        context['submit_text'] = 'Crear Colegio'
        return context

class ColegioUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Colegio
    form_class = ColegioForm
    template_name = 'administrador/configuracion/colegio_form.html'
    success_url = reverse_lazy('administrador:colegio_list')
    success_message = "Colegio actualizado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Colegio'
        context['submit_text'] = 'Actualizar Colegio'
        return context

class ColegioDetailView(RoleRequiredMixin, DetailView):
    model = Colegio
    template_name = 'administrador/configuracion/colegio_detail.html'
    context_object_name = 'colegio'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sedes'] = self.object.sedes_gestion.filter(estado=True)
        context['años_lectivos'] = self.object.años_lectivos.filter(estado=True)
        try:
            context['recursos'] = self.object.recursos
        except RecursosColegio.DoesNotExist:
            context['recursos'] = None
        return context

# ===================== SEDES =====================

class SedeListView(RoleRequiredMixin, ListView):
    model = Sede
    template_name = 'administrador/configuracion/sede_list.html'
    context_object_name = 'sedes'
    allowed_roles = ['Administrador', 'Rector']
    paginate_by = 20

    def get_queryset(self):
        qs = Sede.objects.select_related(
            'colegio', 
            'director',  # Asegurar que traemos el director
            'director__tipo_usuario'  # Y su tipo de usuario
        ).order_by('colegio__nombre', 'nombre')

        # Filtro por estado (activo por defecto)
        estado = self.request.GET.get('estado', 'activas')
        if estado == 'activas':
            qs = qs.filter(estado=True)
        elif estado == 'inactivas':
            qs = qs.filter(estado=False)
        elif estado == 'todas':
            pass  # Mostrar todas

        # Filtro por colegio
        colegio_id = self.request.GET.get('colegio')
        if colegio_id and colegio_id != 'todos':
            try:
                colegio_id_int = int(colegio_id)
                qs = qs.filter(colegio_id=colegio_id_int)
            except (ValueError, TypeError):
                pass

        # Filtro por texto (búsqueda)
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(
                Q(nombre__icontains=search) |
                Q(direccion__icontains=search) |
                Q(email__icontains=search) |
                Q(telefono__icontains=search) |
                Q(colegio__nombre__icontains=search)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas
        total_sedes = Sede.objects.count()
        sedes_activas = Sede.objects.filter(estado=True).count()
        sedes_inactivas = total_sedes - sedes_activas
        
        # Colegios para el filtro
        colegios = Colegio.objects.filter(estado=True).order_by('nombre')
        
        context.update({
            'colegios': colegios,
            'selected_colegio': self.request.GET.get('colegio', 'todos'),
            'selected_estado': self.request.GET.get('estado', 'activas'),
            'search_query': self.request.GET.get('search', ''),
            'total_sedes': total_sedes,
            'sedes_activas': sedes_activas,
            'sedes_inactivas': sedes_inactivas,
            'title': 'Gestión de Sedes',
        })
        
        return context

class SedeCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    model = Sede
    form_class = SedeForm
    template_name = 'administrador/configuracion/sede_form.html'
    success_url = reverse_lazy('administrador:sede_list')
    success_message = "✅ Sede creada exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': 'Crear Nueva Sede',
            'submit_text': 'Crear Sede',
            'action': 'create',
        })
        return context
    
    def form_valid(self, form):
        # Asignar el usuario actual si es un rector y no se seleccionó director
        if self.request.user.tipo_usuario and 'Rector' in self.request.user.tipo_usuario.nombre:
            if not form.cleaned_data.get('director'):
                form.instance.director = self.request.user.usuario
        return super().form_valid(form)

class SedeUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Sede
    form_class = SedeForm
    template_name = 'administrador/configuracion/sede_form.html'
    success_url = reverse_lazy('administrador:sede_list')
    success_message = "✅ Sede actualizada exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': f'Editar Sede: {self.object.nombre}',
            'submit_text': 'Actualizar Sede',
            'action': 'update',
        })
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pasar la instancia actual para que el formulario pueda excluirla de las validaciones
        kwargs['instance'] = self.object
        return kwargs

class SedeDeleteView(RoleRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Sede
    template_name = 'administrador/configuracion/sede_confirm_delete.html'
    success_url = reverse_lazy('administrador:sede_list')
    success_message = "🗑️ Sede eliminada exitosamente"
    allowed_roles = ['Administrador']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminar Sede'
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

class SedeActivateView(RoleRequiredMixin, View):
    """Activar/Desactivar sede"""
    allowed_roles = ['Administrador', 'Rector']
    
    def post(self, request, pk):
        try:
            sede = Sede.objects.get(pk=pk)
            sede.estado = not sede.estado
            sede.save()
            
            action = "activada" if sede.estado else "desactivada"
            messages.success(request, f"Sede {action} exitosamente")
            
        except Sede.DoesNotExist:
            messages.error(request, "Sede no encontrada")
        
        return redirect('administrador:sede_list')

# ===================== RECURSOS DEL COLEGIO =====================

class RecursosColegioUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    model = RecursosColegio
    form_class = RecursosColegioForm
    template_name = 'administrador/configuracion/recursos_form.html'
    success_message = "Recursos actualizados exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_object(self):
        colegio_id = self.kwargs.get('colegio_id')
        colegio = get_object_or_404(Colegio, id=colegio_id)
        try:
            recursos = colegio.recursos
        except RecursosColegio.DoesNotExist:
            recursos = RecursosColegio.objects.create(colegio=colegio)
        return recursos
    
    def get_success_url(self):
        return reverse_lazy('administrador:colegio_detail', kwargs={'pk': self.object.colegio.id})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Configurar Recursos del Colegio'
        context['submit_text'] = 'Guardar Recursos'
        context['colegio'] = self.object.colegio
        return context

# ===================== AÑOS LECTIVOS =====================

class AñoLectivoListView(RoleRequiredMixin, ListView):
    model = AñoLectivo
    template_name = 'administrador/configuracion/año_lectivo_list.html'
    context_object_name = 'años_lectivos'
    allowed_roles = ['Administrador', 'Rector']

    def get_queryset(self):
        qs = AñoLectivo.objects.select_related('colegio', 'sede').filter(estado=True).order_by('-anho', 'colegio__nombre')

        # Filtros
        colegio_id = self.request.GET.get('colegio')
        sede_id = self.request.GET.get('sede')
        
        if colegio_id:
            try:
                qs = qs.filter(colegio_id=int(colegio_id))
            except (ValueError, TypeError):
                pass
        
        if sede_id:
            try:
                qs = qs.filter(sede_id=int(sede_id))
            except (ValueError, TypeError):
                pass

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['colegios'] = Colegio.objects.filter(estado=True)
        context['sedes'] = Sede.objects.filter(estado=True)
        context['selected_colegio'] = self.request.GET.get('colegio')
        context['selected_sede'] = self.request.GET.get('sede')
        return context

class AñoLectivoCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    model = AñoLectivo
    form_class = AñoLectivoForm
    template_name = 'administrador/configuracion/año_lectivo_form.html'
    success_url = reverse_lazy('administrador:año_lectivo_list')
    success_message = "Año lectivo creado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Nuevo Año Lectivo'
        context['submit_text'] = 'Crear Año Lectivo'
        return context

class AñoLectivoUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    model = AñoLectivo
    form_class = AñoLectivoForm
    template_name = 'administrador/configuracion/año_lectivo_form.html'
    success_url = reverse_lazy('administrador:año_lectivo_list')
    success_message = "Año lectivo actualizado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Año Lectivo'
        context['submit_text'] = 'Actualizar Año Lectivo'
        return context

# ===================== CONFIGURACIÓN GENERAL =====================

class ConfiguracionGeneralUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    model = ConfiguracionGeneral
    form_class = ConfiguracionGeneralForm
    template_name = 'administrador/configuracion/configuracion_form.html'
    success_message = "Configuración actualizada exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_object(self):
        # Obtener o crear configuración para el colegio principal
        colegio = Colegio.objects.filter(estado=True).first()
        if not colegio:
            messages.error(self.request, "No existe un colegio configurado")
            return None
        
        try:
            config = colegio.configuracion
        except ConfiguracionGeneral.DoesNotExist:
            config = ConfiguracionGeneral.objects.create(colegio=colegio)
        return config
    
    def get_success_url(self):
        return reverse_lazy('gestioncolegio:dashboard_administrador')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Configuración General del Sistema'
        context['submit_text'] = 'Guardar Configuración'
        return context

# ===================== PARÁMETROS DEL SISTEMA =====================

class ParametroSistemaListView(RoleRequiredMixin, ListView):
    model = ParametroSistema
    template_name = 'administrador/configuracion/parametro_list.html'
    context_object_name = 'parametros'
    allowed_roles = ['Administrador', 'Rector']

    def get_queryset(self):
        qs = ParametroSistema.objects.all().order_by('clave')
        
        # Filtro por tipo
        tipo = self.request.GET.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)
            
        # Filtro por búsqueda
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(
                Q(clave__icontains=search) |
                Q(descripcion__icontains=search) |
                Q(valor__icontains=search)
            )
        
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tipos_parametros'] = [
            ('texto', 'Texto'),
            ('numero', 'Número'),
            ('booleano', 'Booleano'),
            ('fecha', 'Fecha'),
        ]
        context['selected_tipo'] = self.request.GET.get('tipo')
        context['search_query'] = self.request.GET.get('search', '')
        return context

class ParametroSistemaCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    model = ParametroSistema
    form_class = ParametroSistemaForm
    template_name = 'administrador/configuracion/parametro_form.html'
    success_url = reverse_lazy('administrador:parametro_list')
    success_message = "Parámetro creado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Nuevo Parámetro'
        context['submit_text'] = 'Crear Parámetro'
        return context

class ParametroSistemaUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    model = ParametroSistema
    form_class = ParametroSistemaForm
    template_name = 'administrador/configuracion/parametro_form.html'
    success_url = reverse_lazy('administrador:parametro_list')
    success_message = "Parámetro actualizado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Parámetro'
        context['submit_text'] = 'Actualizar Parámetro'
        return context
