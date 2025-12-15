# docentes/logros/logros/views/logros.py
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, TemplateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from itertools import groupby
from django.core.paginator import Paginator

from usuarios.models import Docente
from docentes.mixins import DocenteRequiredMixin, DocenteBaseView
from academico.models import Logro, Asignatura, Grado
from matricula.models import PeriodoAcademico, AsignaturaGradoAñoLectivo
from gestioncolegio.models import AñoLectivo

class DocenteRequiredMixin(UserPassesTestMixin):
    """Mixin para verificar que el usuario es docente - VERSIÓN SIMPLE"""
    
    def test_func(self):
        """Verifica que el usuario sea docente"""
        user = self.request.user
        if not user.is_authenticated:
            return False
        
        # Verificar si es superusuario (tiene acceso a todo)
        if user.is_superuser:
            return True
        
        # Verificar si tiene tipo_usuario
        if hasattr(user, 'tipo_usuario') and user.tipo_usuario:
            # Si es administrador o rector, también puede acceder
            if user.tipo_usuario.nombre in ['Administrador', 'Rector']:
                return True
            
            # Si es docente, verificar que tenga perfil
            if user.tipo_usuario.nombre == 'Docente':
                return Docente.objects.filter(usuario=user).exists()
        
        # Por último, verificar directamente si tiene perfil de docente
        return Docente.objects.filter(usuario=user).exists()
    
    def handle_no_permission(self):
        messages.error(self.request, 'No tiene permisos para acceder a esta sección.')
        return redirect('login')

def get_docente_usuario(user):
    """Función helper para obtener docente desde usuario"""
    try:
        # Método 1: Buscar directamente
        return Docente.objects.filter(usuario=user).first()
    except:
        return None

class ListaLogrosView(LoginRequiredMixin, DocenteRequiredMixin, ListView):
    """Vista para listar los logros del docente"""
    model = Logro
    template_name = 'docentes/logros/logro_list.html'
    context_object_name = 'grupos_logros'
    paginate_by = 10

    def get_docente(self):
        """Obtiene el docente asociado al usuario"""
        return get_docente_usuario(self.request.user)

    def get_queryset(self):
        docente = self.get_docente()
        if not docente:
            return []
        
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if not año_actual:
            return []
    
        # Obtener asignaturas que dicta el docente en el año actual
        asignaturas_grado = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__año_lectivo=año_actual
        ).select_related('grado_año_lectivo__grado', 'asignatura')

        # Si no hay asignaturas, retornar vacío
        if not asignaturas_grado.exists():
            return []

        # Crear conjunto de pares únicos (grado_id, asignatura_id)
        pares = set()
        for ag in asignaturas_grado:
            pares.add((ag.grado_año_lectivo.grado_id, ag.asignatura_id))

        # Aplicar filtros
        periodo_id = self.request.GET.get('periodo')
        grado_id = self.request.GET.get('grado')
        asignatura_id = self.request.GET.get('asignatura')
        search = self.request.GET.get('search', '').strip()

        # Filtrar por periodo si está seleccionado
        periodo = None
        if periodo_id:
            periodo = PeriodoAcademico.objects.filter(id=periodo_id).first()

        # Recolectar logros según filtros
        logros = []
        for (grado_id_filtro, asignatura_id_filtro) in pares:
            # Aplicar filtros de grado y asignatura si están seleccionados
            if grado_id and int(grado_id) != grado_id_filtro:
                continue
            if asignatura_id and int(asignatura_id) != asignatura_id_filtro:
                continue
            
            # Construir filtro base
            filtro = {
                'grado_id': grado_id_filtro,
                'asignatura_id': asignatura_id_filtro,
                'periodo_academico__año_lectivo': año_actual
            }
            
            if periodo:
                filtro['periodo_academico'] = periodo
            
            # Obtener logros
            logros_query = Logro.objects.filter(**filtro).select_related(
                'grado', 'asignatura', 'periodo_academico'
            )
            
            # Filtrar por búsqueda si hay texto
            if search:
                logros_query = logros_query.filter(
                    Q(tema__icontains=search) |
                    Q(descripcion_superior__icontains=search) |
                    Q(descripcion_alto__icontains=search) |
                    Q(descripcion_basico__icontains=search) |
                    Q(descripcion_bajo__icontains=search)
                )
            
            logros.extend(logros_query)

        # Formatear nombre del periodo para cada logro
        for logro in logros:
            periodo_obj = logro.periodo_academico
            if periodo_obj and periodo_obj.fecha_inicio and periodo_obj.fecha_fin:
                try:
                    logro.nombre_periodo = f"{periodo_obj.fecha_inicio.strftime('%b')}-{periodo_obj.fecha_fin.strftime('%b %Y')}"
                except:
                    logro.nombre_periodo = periodo_obj.periodo.nombre if hasattr(periodo_obj, 'periodo') else "Periodo"
            else:
                logro.nombre_periodo = "Sin periodo"

        # Ordenar por grado y asignatura
        logros.sort(key=lambda logro: (logro.grado.nombre, logro.asignatura.nombre))

        # Agrupar por grado y asignatura
        grupos = []
        for (grado, asignatura), group in groupby(
            logros,
            key=lambda logro: (logro.grado, logro.asignatura)
        ):
            grupos.append({
                'grado': grado,
                'asignatura': asignatura,
                'logros': list(group),
            })

        return grupos

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        docente = self.get_docente()
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        if not docente:
            messages.error(self.request, 'No tiene perfil de docente.')
            return context
        
        if not año_actual:
            messages.warning(self.request, 'No hay año lectivo activo.')
            context['periodos'] = PeriodoAcademico.objects.none()
            context['grados'] = []
            context['asignaturas'] = []
            return context
        
        # Obtener periodos académicos del año actual
        context['periodos'] = PeriodoAcademico.objects.filter(
            año_lectivo=año_actual,
            estado=True
        ).select_related('periodo').order_by('fecha_inicio')
        
        # Obtener grados del docente
        asignaturas_grado = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__año_lectivo=año_actual
        ).select_related('grado_año_lectivo__grado')
        
        grados_ids = set(ag.grado_año_lectivo.grado_id for ag in asignaturas_grado)
        context['grados'] = Grado.objects.filter(id__in=grados_ids).order_by('nombre')
        
        # Obtener asignaturas del docente
        asignaturas_ids = set(ag.asignatura_id for ag in asignaturas_grado)
        context['asignaturas'] = Asignatura.objects.filter(id__in=asignaturas_ids).order_by('nombre')
        
        # Mantener filtros actuales
        context['filtro_periodo'] = self.request.GET.get('periodo', '')
        context['filtro_grado'] = self.request.GET.get('grado', '')
        context['filtro_asignatura'] = self.request.GET.get('asignatura', '')
        context['filtro_search'] = self.request.GET.get('search', '')
        
        # Paginación manual para grupos
        grupos = self.get_queryset()
        paginator = Paginator(grupos, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['page_obj'] = page_obj
        context['grupos_logros'] = page_obj.object_list
        context['is_paginated'] = paginator.num_pages > 1
        
        # Información del docente para el contexto
        context['docente'] = docente
        
        return context

class ListaLogrosFiltradosView(LoginRequiredMixin, DocenteRequiredMixin, TemplateView):
    """Vista alternativa con filtros por grado y asignatura - Similar a tu versión"""
    template_name = 'docentes/logros/logros_filtrados.html'

    def get_docente(self):
        """Obtiene el docente asociado al usuario"""
        try:
            if hasattr(self.request.user, 'usuario_profile'):
                return get_object_or_404(
                    Docente,
                    usuario__numero_documento=self.request.user.usuario_profile.numero_documento
                )
            return None
        except:
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        docente = self.get_docente()
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        if not docente or not año_actual:
            return context

        # Obtener cursos (grados) y asignaturas que dicta el docente
        asignaturas_grado = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__año_lectivo=año_actual
        ).select_related('grado_año_lectivo__grado')

        # Obtener grados únicos
        grados_set = {ag.grado_año_lectivo.grado for ag in asignaturas_grado}
        context['grados'] = sorted(grados_set, key=lambda g: g.nombre)

        # Obtener parámetros de filtro
        grado_id = self.request.GET.get('grado')
        asignatura_id = self.request.GET.get('asignatura')

        # Filtrar asignaturas si se seleccionó un grado
        asignaturas = []
        if grado_id:
            asignaturas = Asignatura.objects.filter(
                id__in=asignaturas_grado.filter(
                    grado_año_lectivo__grado_id=grado_id
                ).values_list('asignatura_id', flat=True)
            ).order_by('nombre')
        context['asignaturas_filtradas'] = asignaturas

        # Filtrar logros si se seleccionaron ambos filtros
        logros = []
        if grado_id and asignatura_id:
            logros = Logro.objects.filter(
                grado_id=grado_id,
                asignatura_id=asignatura_id,
                periodo_academico__año_lectivo=año_actual
            ).select_related(
                'periodo_academico__periodo'
            ).order_by('periodo_academico__fecha_inicio')

            # Generar nombre_periodo para cada logro
            for logro in logros:
                periodo = logro.periodo_academico
                logro.nombre_periodo = f"{periodo.fecha_inicio.strftime('%b')}-{periodo.fecha_fin.strftime('%b %Y')}"

        context.update({
            'logros': logros,
            'grado_seleccionado': int(grado_id) if grado_id else None,
            'asignatura_seleccionada': int(asignatura_id) if asignatura_id else None,
        })
        
        return context

class CrearLogroView(LoginRequiredMixin, DocenteRequiredMixin, CreateView):
    """Vista para crear un nuevo logro"""
    model = Logro
    template_name = 'docentes/logros/logro_form.html'
    fields = [
        'grado', 'asignatura', 'periodo_academico', 'tema',
        'descripcion_superior', 'descripcion_alto',
        'descripcion_basico', 'descripcion_bajo'
    ]
    success_url = reverse_lazy('docentes:lista_logros')
    
    def get_docente(self):
        return get_docente_usuario(self.request.user)
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        docente = self.get_docente()
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        if not año_actual or not docente:
            messages.error(self.request, 'No hay un año lectivo activo o no tiene perfil de docente.')
            return form
        
        # Filtrar grados del docente
        grados_docente = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__año_lectivo=año_actual
        ).values_list('grado_año_lectivo__grado__id', flat=True).distinct()
        
        form.fields['grado'].queryset = Grado.objects.filter(id__in=grados_docente)
        
        # Filtrar asignaturas - se cargarán dinámicamente vía AJAX
        form.fields['asignatura'].queryset = Asignatura.objects.none()
        
        # Filtrar periodos académicos del año actual
        form.fields['periodo_academico'].queryset = PeriodoAcademico.objects.filter(
            año_lectivo=año_actual,
            estado=True
        )        
        return form
    
    def form_valid(self, form):
        messages.success(self.request, 'Logro creado exitosamente.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Por favor corrija los errores en el formulario.')
        return super().form_invalid(form)

class DetalleLogroView(LoginRequiredMixin, DocenteRequiredMixin, DocenteBaseView, DetailView):
    """Vista para ver detalles de un logro"""
    model = Logro
    template_name = 'docentes/logros/logro_detail.html'
    context_object_name = 'logro'
    
    def get_queryset(self):
        docente = self.get_docente()
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        if not año_actual or not docente:
            return Logro.objects.none()
        
        # Obtener las asignaturas que dicta el docente
        asignaturas_docente = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__año_lectivo=año_actual
        ).select_related('asignatura')
        
        asignatura_ids = asignaturas_docente.values_list('asignatura__id', flat=True)
        
        if not asignatura_ids:
            return Logro.objects.none()
        
        return Logro.objects.filter(
            asignatura_id__in=asignatura_ids,
            periodo_academico__año_lectivo=año_actual
        ).select_related(
            'asignatura',
            'periodo_academico__periodo',
            'grado'
        )

class EditarLogroView(LoginRequiredMixin, DocenteRequiredMixin, DocenteBaseView, UpdateView):
    """Vista para editar un logro existente"""
    model = Logro
    template_name = 'docentes/logros/logro_form.html'
    fields = [
        'grado', 'asignatura', 'periodo_academico', 'tema',
        'descripcion_superior', 'descripcion_alto',
        'descripcion_basico', 'descripcion_bajo'
    ]
    success_url = reverse_lazy('docentes:lista_logros')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        docente = self.get_docente()
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        if not año_actual or not docente:
            messages.error(self.request, 'No hay un año lectivo activo o no tiene perfil de docente.')
            return form
        
        # Filtrar grados del docente
        grados_docente = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__año_lectivo=año_actual
        ).values_list('grado_año_lectivo__grado__id', flat=True).distinct()
        
        form.fields['grado'].queryset = Grado.objects.filter(id__in=grados_docente)
        
        # Para edición, mostrar las asignaturas del grado actual
        if self.object and self.object.grado:
            asignaturas_docente = AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente,
                grado_año_lectivo__grado=self.object.grado,
                grado_año_lectivo__año_lectivo=año_actual
            ).select_related('asignatura')
            
            asignaturas_ids = asignaturas_docente.values_list('asignatura__id', flat=True)
            form.fields['asignatura'].queryset = Asignatura.objects.filter(id__in=asignaturas_ids)
        else:
            form.fields['asignatura'].queryset = Asignatura.objects.none()
        
        # Filtrar periodos académicos del año actual
        form.fields['periodo_academico'].queryset = PeriodoAcademico.objects.filter(
            año_lectivo=año_actual,
            estado=True
        )
        
        return form
    
    def get_queryset(self):
        docente = self.get_docente()
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        if not año_actual or not docente:
            return Logro.objects.none()
        
        # Obtener las asignaturas que dicta el docente
        asignaturas_docente = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__año_lectivo=año_actual
        ).select_related('asignatura')
        
        asignatura_ids = asignaturas_docente.values_list('asignatura__id', flat=True)
        
        if not asignatura_ids:
            return Logro.objects.none()
        
        return Logro.objects.filter(
            asignatura_id__in=asignatura_ids,
            periodo_academico__año_lectivo=año_actual
        )
    
    def form_valid(self, form):
        messages.success(self.request, 'Logro actualizado exitosamente.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Por favor corrija los errores en el formulario.')
        return super().form_invalid(form)
    
class EliminarLogroView(LoginRequiredMixin, DocenteRequiredMixin, DocenteBaseView, DeleteView):
    """Vista para eliminar un logro"""
    model = Logro
    template_name = 'docentes/logros/logro_confirm_delete.html'
    success_url = reverse_lazy('docentes:lista_logros')
    
    def get_queryset(self):
        docente = self.get_docente()
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        if not año_actual or not docente:
            return Logro.objects.none()
        
        # Obtener las asignaturas que dicta el docente
        asignaturas_docente = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__año_lectivo=año_actual
        ).select_related('asignatura')
        
        asignatura_ids = asignaturas_docente.values_list('asignatura__id', flat=True)
        
        if not asignatura_ids:
            return Logro.objects.none()
        
        return Logro.objects.filter(
            asignatura_id__in=asignatura_ids,
            periodo_academico__año_lectivo=año_actual
        )
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Logro eliminado exitosamente.')
        return super().delete(request, *args, **kwargs)

# debug.py
@login_required
def debug_docente(request):
    """Vista de depuración para verificar el objeto docente"""
    user = request.user
    
    # Intenta obtener el docente de diferentes maneras
    docente_via_filter = Docente.objects.filter(usuario=user).first()
    
    # Verifica si tiene el atributo docente_profile
    has_docente_profile_attr = hasattr(user, 'docente_profile')
    
    if has_docente_profile_attr:
        # Intenta acceder al atributo
        try:
            profile_value = user.docente_profile
            profile_type = type(profile_value).__name__
            
            # Verifica si es un manager
            is_manager = hasattr(profile_value, 'all')
            
            # Si es manager, intenta obtener el primer objeto
            if is_manager:
                docente_via_profile = profile_value.first()
                profile_exists = profile_value.exists()
            else:
                docente_via_profile = profile_value
                profile_exists = True
                
        except Exception as e:
            profile_value = None
            profile_type = 'Error'
            is_manager = False
            docente_via_profile = None
            profile_exists = False
            error_msg = str(e)
    else:
        profile_value = None
        profile_type = 'No tiene atributo'
        is_manager = False
        docente_via_profile = None
        profile_exists = False
        error_msg = 'No tiene atributo docente_profile'
    
    context = {
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        
        'has_docente_profile': has_docente_profile_attr,
        'docente_via_filter': docente_via_filter,
        'docente_via_filter_id': docente_via_filter.id if docente_via_filter else None,
        
        'profile_type': profile_type,
        'is_manager': is_manager,
        'docente_via_profile': docente_via_profile,
        'profile_exists': profile_exists,
        
        'error': error_msg if 'error_msg' in locals() else None,
    }
    
    return render(request, 'docentes/debug_docente.html', context)