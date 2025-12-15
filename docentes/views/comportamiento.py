# docentes/views/comportamiento.py
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone

from comportamiento.models import Comportamiento, Asistencia
from estudiantes.models import Estudiante, Matricula
from gestioncolegio.models import AñoLectivo
from matricula.models import AsignaturaGradoAñoLectivo, PeriodoAcademico
from usuarios.models import Docente
from docentes.mixins import DocenteRequiredMixin

def get_docente_usuario(user):
    """Función helper para obtener docente desde usuario"""
    try:
        return Docente.objects.filter(usuario=user).first()
    except:
        return None

# =============================================
# VISTAS DE COMPORTAMIENTO
# =============================================

class ListaComportamientosView(LoginRequiredMixin, DocenteRequiredMixin, ListView):
    """Vista para listar los comportamientos registrados por el docente"""
    model = Comportamiento
    template_name = 'docentes/comportamiento/comportamiento_list.html'
    context_object_name = 'comportamientos'
    paginate_by = 20

    def get_docente(self):
        return get_docente_usuario(self.request.user)

    def get_queryset(self):
        docente = self.get_docente()
        if not docente:
            return Comportamiento.objects.none()
        
        # Obtener estudiantes de los grados del docente
        estudiantes_docente = self._get_estudiantes_docente(docente)
        if not estudiantes_docente:
            return Comportamiento.objects.none()
        
        # Filtrar comportamientos de esos estudiantes
        queryset = Comportamiento.objects.filter(
            estudiante__in=estudiantes_docente
        ).select_related(
            'estudiante__usuario',
            'periodo_academico__periodo',
            'docente__usuario'
        ).order_by('-fecha', '-created_at')
        
        # Aplicar filtros
        periodo_id = self.request.GET.get('periodo')
        estudiante_id = self.request.GET.get('estudiante')
        tipo = self.request.GET.get('tipo')
        categoria = self.request.GET.get('categoria')
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        
        if periodo_id:
            queryset = queryset.filter(periodo_academico_id=periodo_id)
        
        if estudiante_id:
            queryset = queryset.filter(estudiante_id=estudiante_id)
        
        if tipo and tipo != 'todos':
            queryset = queryset.filter(tipo=tipo)
        
        if categoria and categoria != 'todas':
            queryset = queryset.filter(categoria=categoria)
        
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
        
        return queryset
    
    def _get_estudiantes_docente(self, docente):
        """Obtener estudiantes de los grados asignados al docente"""
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if not año_actual:
            return Estudiante.objects.none()
        
        # Obtener grados asignados al docente
        grados_docente = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__año_lectivo=año_actual
        ).values_list('grado_año_lectivo__grado_id', flat=True).distinct()
        
        if not grados_docente:
            return Estudiante.objects.none()
        
        # Obtener estudiantes matriculados en esos grados
        estudiantes = Estudiante.objects.filter(
            matriculas__grado_año_lectivo__grado_id__in=grados_docente,
            matriculas__año_lectivo=año_actual,
            matriculas__estado__in=['ACT', 'PEN']
        ).distinct()
        
        return estudiantes

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        docente = self.get_docente()
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        if not docente or not año_actual:
            context['periodos'] = PeriodoAcademico.objects.none()
            context['estudiantes'] = []
            return context
        
        # Obtener periodos académicos
        context['periodos'] = PeriodoAcademico.objects.filter(
            año_lectivo=año_actual,
            estado=True
        ).select_related('periodo').order_by('fecha_inicio')
        
        # Obtener estudiantes del docente
        estudiantes = self._get_estudiantes_docente(docente)
        context['estudiantes'] = estudiantes.select_related('usuario')
        
        # Tipos y categorías
        context['tipos'] = [
            ('Positivo', 'Positivo'),
            ('Negativo', 'Negativo'),
        ]
        
        context['categorias'] = [
            ('Respeto', 'Respeto'),
            ('Responsabilidad', 'Responsabilidad'),
            ('Disciplina', 'Disciplina'),
            ('Solidaridad', 'Solidaridad'),
            ('Academico', 'Académico'),
        ]
        
        # Mantener filtros actuales
        context['filtro_periodo'] = self.request.GET.get('periodo', '')
        context['filtro_estudiante'] = self.request.GET.get('estudiante', '')
        context['filtro_tipo'] = self.request.GET.get('tipo', '')
        context['filtro_categoria'] = self.request.GET.get('categoria', '')
        context['filtro_fecha_inicio'] = self.request.GET.get('fecha_inicio', '')
        context['filtro_fecha_fin'] = self.request.GET.get('fecha_fin', '')
        
        # Estadísticas
        queryset = self.get_queryset()
        context['total_positivos'] = queryset.filter(tipo='Positivo').count()
        context['total_negativos'] = queryset.filter(tipo='Negativo').count()
        context['total_registros'] = queryset.count()
        
        return context

class CrearComportamientoView(LoginRequiredMixin, DocenteRequiredMixin, CreateView):
    """Vista para crear un nuevo registro de comportamiento"""
    model = Comportamiento
    template_name = 'docentes/comportamiento/comportamiento_form.html'
    fields = [
        'estudiante', 'periodo_academico', 'tipo', 'categoria', 
        'descripcion', 'fecha'
    ]
    success_url = reverse_lazy('docentes:lista_comportamientos')
    
    def get_docente(self):
        return get_docente_usuario(self.request.user)
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        docente = self.get_docente()
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        if not año_actual or not docente:
            messages.error(self.request, 'No hay un año lectivo activo o no tiene perfil de docente.')
            return form
        
        # Filtrar estudiantes del docente
        estudiantes = self._get_estudiantes_docente(docente, año_actual)
        form.fields['estudiante'].queryset = estudiantes.select_related('usuario')
        
        # Filtrar periodos académicos
        form.fields['periodo_academico'].queryset = PeriodoAcademico.objects.filter(
            año_lectivo=año_actual,
            estado=True
        )
        
        # Establecer fecha por defecto
        form.fields['fecha'].initial = timezone.now().date()
        
        return form
    
    def _get_estudiantes_docente(self, docente, año_actual):
        """Obtener estudiantes de los grados asignados al docente"""
        # Obtener grados asignados al docente
        grados_docente = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__año_lectivo=año_actual
        ).values_list('grado_año_lectivo__grado_id', flat=True).distinct()
        
        if not grados_docente:
            return Estudiante.objects.none()
        
        # Obtener estudiantes matriculados en esos grados
        estudiantes = Estudiante.objects.filter(
            matriculas__grado_año_lectivo__grado_id__in=grados_docente,
            matriculas__año_lectivo=año_actual,
            matriculas__estado__in=['ACT', 'PEN']
        ).distinct()
        
        return estudiantes
    
    def form_valid(self, form):
        # Asignar automáticamente al docente actual
        docente = self.get_docente()
        if docente:
            form.instance.docente = docente
        messages.success(self.request, 'Registro de comportamiento creado exitosamente.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Por favor corrija los errores en el formulario.')
        return super().form_invalid(form)

class DetalleComportamientoView(LoginRequiredMixin, DocenteRequiredMixin, DetailView):
    """Vista para ver detalles de un registro de comportamiento"""
    model = Comportamiento
    template_name = 'docentes/comportamiento/comportamiento_detail.html'
    context_object_name = 'comportamiento'
    
    def get_docente(self):
        return get_docente_usuario(self.request.user)
    
    def get_queryset(self):
        docente = self.get_docente()
        if not docente:
            return Comportamiento.objects.none()
        
        # Obtener estudiantes del docente
        estudiantes = self._get_estudiantes_docente(docente)
        if not estudiantes:
            return Comportamiento.objects.none()
        
        # Solo mostrar comportamientos de estudiantes del docente
        return Comportamiento.objects.filter(
            estudiante__in=estudiantes
        ).select_related(
            'estudiante__usuario',
            'periodo_academico__periodo',
            'docente__usuario'
        )
    
    def _get_estudiantes_docente(self, docente):
        """Obtener estudiantes de los grados asignados al docente"""
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if not año_actual:
            return Estudiante.objects.none()
        
        # Obtener grados asignados al docente
        grados_docente = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__año_lectivo=año_actual
        ).values_list('grado_año_lectivo__grado_id', flat=True).distinct()
        
        if not grados_docente:
            return Estudiante.objects.none()
        
        # Obtener estudiantes matriculados en esos grados
        estudiantes = Estudiante.objects.filter(
            matriculas__grado_año_lectivo__grado_id__in=grados_docente,
            matriculas__año_lectivo=año_actual,
            matriculas__estado__in=['ACT', 'PEN']
        ).distinct()
        
        return estudiantes

class EditarComportamientoView(LoginRequiredMixin, DocenteRequiredMixin, UpdateView):
    """Vista para editar un registro de comportamiento"""
    model = Comportamiento
    template_name = 'docentes/comportamiento/comportamiento_form.html'
    fields = [
        'estudiante', 'periodo_academico', 'tipo', 'categoria', 
        'descripcion', 'fecha'
    ]
    success_url = reverse_lazy('docentes:lista_comportamientos')
    
    def get_docente(self):
        return get_docente_usuario(self.request.user)
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        docente = self.get_docente()
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        if not año_actual or not docente:
            messages.error(self.request, 'No hay un año lectivo activo o no tiene perfil de docente.')
            return form
        
        # Filtrar estudiantes del docente
        estudiantes = self._get_estudiantes_docente(docente, año_actual)
        form.fields['estudiante'].queryset = estudiantes.select_related('usuario')
        
        # Filtrar periodos académicos del año actual
        form.fields['periodo_academico'].queryset = PeriodoAcademico.objects.filter(
            año_lectivo=año_actual,
            estado=True
        )
        
        # Si estamos editando, establecer el año del periodo del comportamiento
        if self.object and self.object.periodo_academico:
            año_comportamiento = self.object.periodo_academico.año_lectivo
            if año_comportamiento != año_actual:
                # Si el comportamiento es de otro año, mostrar periodos de ese año
                form.fields['periodo_academico'].queryset = PeriodoAcademico.objects.filter(
                    año_lectivo=año_comportamiento,
                    estado=True
                )
        
        return form
    
    def _get_estudiantes_docente(self, docente, año_actual):
        """Obtener estudiantes de los grados asignados al docente"""
        # Obtener grados asignados al docente
        grados_docente = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__año_lectivo=año_actual
        ).values_list('grado_año_lectivo__grado_id', flat=True).distinct()
        
        if not grados_docente:
            return Estudiante.objects.none()
        
        # Obtener estudiantes matriculados en esos grados
        estudiantes = Estudiante.objects.filter(
            matriculas__grado_año_lectivo__grado_id__in=grados_docente,
            matriculas__año_lectivo=año_actual,
            matriculas__estado__in=['ACT', 'PEN']
        ).distinct()
        
        return estudiantes
    
    def get_queryset(self):
        docente = self.get_docente()
        if not docente:
            return Comportamiento.objects.none()
        
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if not año_actual:
            return Comportamiento.objects.none()
        
        # Obtener estudiantes del docente (para el año actual)
        estudiantes = self._get_estudiantes_docente(docente, año_actual)
        if not estudiantes:
            return Comportamiento.objects.none()
        
        # PERMITIR editar comportamientos de estudiantes del docente, 
        # independientemente de quién los creó
        return Comportamiento.objects.filter(
            estudiante__in=estudiantes
            # Quitamos la restricción: docente=docente
            # Esto permite editar comportamientos creados por otros docentes
            # Si quieres restringir solo a los creados por este docente, descomenta:
            # Q(docente=docente) | Q(docente__isnull=True)
        )
    
    def form_valid(self, form):
        # Si el comportamiento no tenía docente, asignar al docente actual
        if not form.instance.docente:
            form.instance.docente = self.get_docente()
        
        messages.success(self.request, 'Registro de comportamiento actualizado exitosamente.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Por favor corrija los errores en el formulario.')
        return super().form_invalid(form)

class EliminarComportamientoView(LoginRequiredMixin, DocenteRequiredMixin, DeleteView):
    """Vista para eliminar un registro de comportamiento"""
    model = Comportamiento
    template_name = 'docentes/comportamiento/comportamiento_confirm_delete.html'
    success_url = reverse_lazy('docentes:lista_comportamientos')
    
    def get_docente(self):
        return get_docente_usuario(self.request.user)
    
    def get_queryset(self):
        docente = self.get_docente()
        if not docente:
            return Comportamiento.objects.none()
        
        # Solo permitir eliminar comportamientos creados por este docente
        return Comportamiento.objects.filter(docente=docente)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Registro de comportamiento eliminado exitosamente.')
        return super().delete(request, *args, **kwargs)
