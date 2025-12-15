"""
Mixins para vistas Django - Proporcionan funcionalidades reutilizables
Versión completa pero sin conflictos MRO
gestioncolegio/mixins/mixin.py
"""
import datetime
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from estudiantes.models import Estudiante

# =============================================
# MIXINS BASE
# =============================================

class BaseContextMixin:
    """Mixin base que proporciona contexto común a todas las vistas"""
    
    def get_base_context(self):
        """Contexto base común para todas las vistas"""
        context = {}
        try:
            # Importaciones locales para evitar problemas
            from gestioncolegio.models import Colegio, AñoLectivo
            
            # Información del colegio
            context['colegio_info'] = Colegio.objects.filter(estado=True).first()
            
            # Año lectivo actual
            context['año_lectivo_actual'] = AñoLectivo.objects.filter(estado=True).first()
            
            # Fecha actual
            context['fecha_actual'] = datetime.datetime.now()
            context['hoy'] = datetime.date.today()
            
            # Información del usuario actual
            if self.request.user.is_authenticated:
                context['usuario_actual'] = self.request.user
                if hasattr(self.request.user, 'tipo_usuario'):
                    context['rol_usuario'] = self.request.user.tipo_usuario.nombre
            
        except Exception as e:
            print(f"Error obteniendo contexto base: {e}")
        return context
    
    def get_context_data(self, **kwargs):
        """Sobrescribe get_context_data para agregar contexto base"""
        context = super().get_context_data(**kwargs)
        context.update(self.get_base_context())
        return context


class RoleRequiredMixin(UserPassesTestMixin):
    """
    Mixin para verificar roles de usuario
    """
    allowed_roles = []
    permission_denied_message = "No tienes permisos para acceder a esta página."
    redirect_url = 'gestioncolegio:dashboard'
    
    def test_func(self):
        """Verifica que el usuario tenga el rol requerido"""
        user = self.request.user
        
        if not user.is_authenticated:
            return False
        
        # Superusuarios tienen acceso total
        if user.is_superuser:
            return True
        
        # Verificar roles permitidos
        if hasattr(user, 'tipo_usuario') and user.tipo_usuario:
            return user.tipo_usuario.nombre in self.allowed_roles
        
        return False
    
    def handle_no_permission(self):
        """Maneja el acceso denegado"""
        messages.error(self.request, self.permission_denied_message)
        return redirect(self.redirect_url)
    
    def get_context_data(self, **kwargs):
        """Agrega información de permisos al contexto"""
        context = super().get_context_data(**kwargs)
        context['allowed_roles'] = self.allowed_roles
        return context


# =============================================
# MIXINS FUNCIONALES
# =============================================

class PaginationMixin:
    """Mixin para manejar paginación"""
    
    paginate_by = 20
    
    def get_paginate_by(self, queryset):
        return self.request.GET.get('paginate_by', self.paginate_by)
    
    def get_pagination_context(self, queryset, page_size=None):
        if page_size is None:
            page_size = self.get_paginate_by(queryset)
        
        paginator = Paginator(queryset, page_size)
        page_number = self.request.GET.get('page')
        
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        return {
            'page_obj': page_obj,
            'paginator': paginator,
            'is_paginated': paginator.num_pages > 1,
        }
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if hasattr(self, 'paginate_queryset'):
            queryset = self.get_queryset()
            page_size = self.get_paginate_by(queryset)
            
            if page_size:
                pagination_context = self.get_pagination_context(queryset, page_size)
                context.update(pagination_context)
        
        return context


class FilterMixin:
    """Mixin para manejar filtros"""
    
    filter_fields = []
    search_fields = []
    date_filter_fields = []
    
    def get_filter_params(self):
        filter_params = {}
        
        for field in self.filter_fields:
            value = self.request.GET.get(field)
            if value and value != 'all':
                filter_params[field] = value
        
        for field in self.date_filter_fields:
            start = self.request.GET.get(f'{field}_start')
            end = self.request.GET.get(f'{field}_end')
            
            if start:
                filter_params[f'{field}__gte'] = start
            if end:
                filter_params[f'{field}__lte'] = end
        
        return filter_params
    
    def get_search_query(self):
        search_term = self.request.GET.get('search', '').strip()
        if not search_term or not self.search_fields:
            return Q()
        
        query = Q()
        for field in self.search_fields:
            query |= Q(**{f'{field}__icontains': search_term})
        
        return query
    
    def get_filtered_queryset(self, queryset):
        filter_params = self.get_filter_params()
        if filter_params:
            queryset = queryset.filter(**filter_params)
        
        search_query = self.get_search_query()
        if search_query:
            queryset = queryset.filter(search_query)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['filter_params'] = self.request.GET.dict()
        context['current_filters'] = self.get_filter_params()
        context['search_term'] = self.request.GET.get('search', '')
        
        if hasattr(self, 'get_filter_options'):
            context.update(self.get_filter_options())
        
        return context


class DocenteAccessMixin(RoleRequiredMixin):
    """Mixin específico para acceso de docentes"""
    
    allowed_roles = ['Docente', 'Administrador', 'Rector']
    
    def get_docente(self):
        try:
            from usuarios.models import Docente
            return Docente.objects.get(usuario=self.request.user)
        except Docente.DoesNotExist:
            return None
    
    def test_func(self):
        if not super().test_func():
            return False
        
        if self.request.user.tipo_usuario.nombre == 'Docente':
            return self.get_docente() is not None
        
        return True
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        docente = self.get_docente()
        if docente:
            context['docente'] = docente
        return context


class NotificationMixin:
    """Mixin para manejar notificaciones"""
    
    def add_success_message(self, message):
        messages.success(self.request, message)
    
    def add_error_message(self, message):
        messages.error(self.request, message)
    
    def add_warning_message(self, message):
        messages.warning(self.request, message)
    
    def add_info_message(self, message):
        messages.info(self.request, message)
    
    def get_notifications(self, user):
        """Obtiene notificaciones para el usuario"""
        return []
    
    def get_context_data(self, **kwargs):
        """Agrega notificaciones al contexto"""
        context = super().get_context_data(**kwargs)
        
        if self.request.user.is_authenticated:
            context['notifications'] = self.get_notifications(self.request.user)
        
        return context


class DashboardContextMixin(BaseContextMixin):
    """Mixin para contexto de dashboard"""
    
    def get_dashboard_context(self, user):
        context = self.get_base_context()
        
        if not user.is_authenticated:
            return context
        
        if hasattr(user, 'tipo_usuario'):
            rol = user.tipo_usuario.nombre
            
            if rol == 'Docente':
                context.update(self._get_docente_dashboard_context(user))
            elif rol == 'Estudiante':
                context.update(self._get_estudiante_dashboard_context(user))
            elif rol == 'Acudiente':
                context.update(self._get_acudiente_dashboard_context(user))
            elif rol in ['Administrador', 'Rector']:
                context.update(self._get_admin_dashboard_context(user))
        
        return context
    
    def _get_docente_dashboard_context(self, user):
        try:
            from usuarios.models import Docente
            from matricula.models import AsignaturaGradoAñoLectivo
            from estudiantes.models import Estudiante
            
            docente = Docente.objects.get(usuario=user)
            
            mis_asignaturas = AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente,
                grado_año_lectivo__año_lectivo__estado=True
            )
            
            estudiantes = Estudiante.objects.filter(
                matriculas__grado_año_lectivo__asignaturas_grado__docente=docente,
                matriculas__año_lectivo__estado=True,
                matriculas__estado__in=['ACT', 'PEN']
            ).distinct()
            
            return {
                'docente': docente,
                'mis_asignaturas': mis_asignaturas[:6],
                'total_asignaturas': mis_asignaturas.count(),
                'total_estudiantes': estudiantes.count(),
            }
            
        except Exception as e:
            print(f"Error obteniendo contexto docente: {e}")
            return {}
    
    def _get_estudiante_dashboard_context(self, user):
        try:
            from estudiantes.models import Estudiante, Nota
            from comportamiento.models import Comportamiento, Asistencia
            from matricula.models import PeriodoAcademico
            
            estudiante = Estudiante.objects.filter(usuario=user).first()
            if not estudiante:
                return {}
            
            periodo_actual = PeriodoAcademico.objects.filter(
                año_lectivo__estado=True,
                estado=True
            ).order_by('-fecha_inicio').first()
            
            notas_data = []
            if periodo_actual and estudiante.grado_actual:
                notas = Nota.objects.filter(
                    estudiante=estudiante,
                    periodo_academico=periodo_actual
                ).select_related('asignatura_grado_año_lectivo__asignatura')
                
                for nota in notas:
                    if nota.calificacion:
                        notas_data.append({
                            'asignatura': nota.asignatura_grado_año_lectivo.asignatura.nombre,
                            'calificacion': float(nota.calificacion)
                        })
            
            comportamientos = Comportamiento.objects.filter(
                estudiante=estudiante
            ).select_related('docente__usuario').order_by('-fecha')[:5]
            
            asistencia_data = {'porcentaje': 0, 'total': 0, 'asistencias': 0}
            if periodo_actual:
                asistencias = Asistencia.objects.filter(
                    estudiante=estudiante,
                    periodo_academico=periodo_actual
                )
                total = asistencias.count()
                if total > 0:
                    asistencia_data = {
                        'porcentaje': round(asistencias.filter(estado='A').count() / total * 100, 1),
                        'total': total,
                        'asistencias': asistencias.filter(estado='A').count()
                    }
            
            return {
                'estudiante': estudiante,
                'notas': notas_data,
                'comportamientos': list(comportamientos),
                'asistencia': asistencia_data
            }
            
        except Exception as e:
            print(f"Error obteniendo contexto estudiante: {e}")
            return {}
    
    def _get_acudiente_dashboard_context(self, user):
        try:
            from estudiantes.models import Acudiente
            
            estudiantes_acargo = Acudiente.objects.filter(
                acudiente=user
            ).select_related('estudiante__usuario')
            
            return {
                'estudiantes_acargo': list(estudiantes_acargo),
                'total_estudiantes_acargo': estudiantes_acargo.count()
            }
            
        except Exception as e:
            print(f"Error obteniendo contexto acudiente: {e}")
            return {}
    
    def _get_admin_dashboard_context(self, user):
        try:
            from usuarios.models import Usuario
            from estudiantes.models import Matricula
            from gestioncolegio.models import Sede
            
            estadisticas = {
                'total_estudiantes': Estudiante.objects.filter(estado=True).count(),
                'total_docentes': Usuario.objects.filter(
                    tipo_usuario__nombre='Docente',
                    estado=True
                ).count(),
                'total_usuarios': Usuario.objects.filter(estado=True).count(),
                'total_sedes': Sede.objects.filter(estado=True).count(),
            }
            
            return {
                'estadisticas': estadisticas,
                'es_superusuario': user.is_superuser
            }
            
        except Exception as e:
            print(f"Error obteniendo contexto admin: {e}")
            return {}


class ExportMixin:
    """Mixin para exportar datos a diferentes formatos"""
    
    export_formats = ['csv', 'excel']
    export_filename = 'export'
    
    def get_export_data(self):
        """Obtiene datos para exportar - debe ser implementado en la vista"""
        raise NotImplementedError("Debe implementar get_export_data()")
    
    def export_csv(self, data):
        """Exporta datos a CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{self.export_filename}.csv"'
        
        writer = csv.writer(response)
        
        # Escribir encabezados
        if data and len(data) > 0:
            writer.writerow(data[0].keys())
            
            # Escribir datos
            for row in data:
                writer.writerow(row.values())
        
        return response
    
    def handle_export(self, format_type):
        """Maneja la exportación según el formato"""
        data = self.get_export_data()
        
        if format_type == 'csv':
            return self.export_csv(data)
        else:
            raise ValueError(f"Formato de exportación no válido: {format_type}")


class CacheMixin:
    """Mixin para manejar caché en vistas"""
    
    cache_timeout = 300
    cache_key_prefix = 'view_cache_'
    
    def get_cache_key(self):
        path = self.request.get_full_path()
        user_id = self.request.user.id if self.request.user.is_authenticated else 'anonymous'
        return f"{self.cache_key_prefix}{user_id}_{hash(path)}"
    
    def get_cached_data(self):
        from django.core.cache import cache
        cache_key = self.get_cache_key()
        return cache.get(cache_key)
    
    def set_cached_data(self, data):
        from django.core.cache import cache
        cache_key = self.get_cache_key()
        cache.set(cache_key, data, self.cache_timeout)
    
    def invalidate_cache(self):
        from django.core.cache import cache
        cache_key = self.get_cache_key()
        cache.delete(cache_key)


# =============================================
# MIXINS COMPUESTOS
# =============================================

class SimpleCRUDMixin:
    """Mixin simple para operaciones CRUD"""
    
    success_message = "Operación realizada correctamente."
    error_message = "Ocurrió un error al procesar la operación."
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, self.success_message)
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, self.error_message)
        return super().form_invalid(form)


class BaseViewMixin(LoginRequiredMixin, BaseContextMixin):
    """Mixin base para todas las vistas que requieren login y contexto"""
    pass


class ListViewBaseMixin(PaginationMixin, FilterMixin):
    """Mixin base para vistas de listado"""
    pass


class DashboardViewMixin(DashboardContextMixin, NotificationMixin):
    """Mixin compuesto para dashboards"""
    pass