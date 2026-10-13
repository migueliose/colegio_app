# rector/views/academico.py
from django.views.generic import CreateView, UpdateView, DeleteView, DetailView, ListView, TemplateView
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
import json
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404

#
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from datetime import datetime
from django.http import HttpResponse, HttpResponseRedirect

# Mixins y modelos
from gestioncolegio.mixins import RoleRequiredMixin
# Modelos
from estudiantes.models import Estudiante, Matricula, Nota
from gestioncolegio.models import AñoLectivo
from comportamiento.models import Asistencia, Comportamiento
from matricula.models import GradoAñoLectivo
from academico.models import Grado, NivelEscolar
# Formularios
from ..forms.formularios_academicco import *

# ================== LISTA DE MATRÍCULAS ==================
class MatriculaListView(RoleRequiredMixin, ListView):
    """Lista de todas las matrículas con filtros"""
    template_name = 'rector/matricula/matricula_list.html'
    allowed_roles = ['Rector']
    model = Matricula
    context_object_name = 'matriculas'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Matricula.objects.select_related(
            'estudiante__usuario',
            'año_lectivo__sede__colegio',
            'grado_año_lectivo__grado__nivel_escolar',
            'sede'
        ).order_by('-created_at')
        
        # Filtros
        año_filter = self.request.GET.get('año')
        sede_filter = self.request.GET.get('sede')
        grado_filter = self.request.GET.get('grado')
        estado_filter = self.request.GET.get('estado')
        search = self.request.GET.get('search')
        
        if año_filter and año_filter != 'todos':
            queryset = queryset.filter(año_lectivo_id=año_filter)
        
        if sede_filter and sede_filter != 'todas':
            queryset = queryset.filter(sede_id=sede_filter)
        
        if grado_filter and grado_filter != 'todos':
            queryset = queryset.filter(grado_año_lectivo_id=grado_filter)
        
        if estado_filter and estado_filter != 'todos':
            queryset = queryset.filter(estado=estado_filter)
        
        if search:
            queryset = queryset.filter(
                Q(estudiante__usuario__nombres__icontains=search) |
                Q(estudiante__usuario__apellidos__icontains=search) |
                Q(estudiante__usuario__numero_documento__icontains=search) |
                Q(codigo_matricula__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Agregar opciones de filtro
        context['años_lectivos'] = AñoLectivo.objects.filter(estado=True).order_by('-anho')
        context['sedes'] = Sede.objects.filter(estado=True)
        context['grados_año_lectivo'] = GradoAñoLectivo.objects.filter(estado=True).select_related('grado')
        
        # Estadísticas
        total = Matricula.objects.count()
        activas = Matricula.objects.filter(estado='ACT').count()
        pendientes = Matricula.objects.filter(estado='PEN').count()
        pre_matriculas = Matricula.objects.filter(estado='PRE').count()
        
        context['estadisticas'] = {
            'total': total,
            'activas': activas,
            'pendientes': pendientes,
            'pre_matriculas': pre_matriculas,
            'activas_porcentaje': round((activas / total * 100) if total > 0 else 0, 1),
            'pendientes_porcentaje': round((pendientes / total * 100) if total > 0 else 0, 1),
        }
        
        # Parámetros actuales para mantener filtros
        context['filtros_actuales'] = {
            'año': self.request.GET.get('año', 'todos'),
            'sede': self.request.GET.get('sede', 'todas'),
            'grado': self.request.GET.get('grado', 'todos'),
            'estado': self.request.GET.get('estado', 'todos'),
            'search': self.request.GET.get('search', ''),
        }
        
        return context

# ================== DETALLE DE MATRÍCULA ==================
class MatriculaDetailView(RoleRequiredMixin, DetailView):
    """Detalle completo de una matrícula"""
    template_name = 'rector/matricula/matricula_detail.html'
    allowed_roles = ['Rector']
    model = Matricula
    context_object_name = 'matricula'
    
    def get_object(self, queryset=None):
        return get_object_or_404(
            Matricula.objects.select_related(
                'estudiante__usuario',
                'año_lectivo__sede__colegio',
                'grado_año_lectivo__grado__nivel_escolar',
                'sede'
            ),
            pk=self.kwargs['pk']
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        matricula = self.object
        
        # Agregar información relacionada
        context['acudientes'] = Acudiente.objects.filter(
            estudiante=matricula.estudiante
        ).select_related('acudiente')
        
        # Notas del año (si las hay)
        from estudiantes.models import Nota
        context['notas'] = Nota.objects.filter(
            estudiante=matricula.estudiante,
            periodo_academico__año_lectivo=matricula.año_lectivo
        ).select_related(
            'asignatura_grado_año_lectivo__asignatura',
            'periodo_academico__periodo'
        ).order_by('periodo_academico__periodo__nombre')
        
        # Asistencias (estadísticas)
        from comportamiento.models import Asistencia
        asistencias = Asistencia.objects.filter(
            estudiante=matricula.estudiante,
            periodo_academico__año_lectivo=matricula.año_lectivo
        )
        
        if asistencias.exists():
            total_asistencias = asistencias.count()
            asistio = asistencias.filter(estado='A').count()
            falto = asistencias.filter(estado='F').count()
            justificado = asistencias.filter(estado='J').count()
            
            context['estadisticas_asistencia'] = {
                'total': total_asistencias,
                'asistio': asistio,
                'falto': falto,
                'justificado': justificado,
                'porcentaje_asistencia': round((asistio / total_asistencias * 100) if total_asistencias > 0 else 0, 1)
            }
        else:
            context['estadisticas_asistencia'] = None
        
        # Comportamientos
        from comportamiento.models import Comportamiento
        context['comportamientos'] = Comportamiento.objects.filter(
            estudiante=matricula.estudiante,
            periodo_academico__año_lectivo=matricula.año_lectivo
        ).order_by('-fecha')[:10]
        
        # Historial de matrículas del estudiante (excluyendo la actual)
        context['historial_matriculas'] = Matricula.objects.filter(
            estudiante=matricula.estudiante
        ).exclude(pk=matricula.pk).select_related(
            'año_lectivo', 'grado_año_lectivo__grado', 'sede'
        ).order_by('-año_lectivo__anho')
        
        return context

# ================== ACTUALIZAR MATRÍCULA (versión desde lista) ==================
class MatriculaUpdateFromListView(RoleRequiredMixin, UpdateView):
    """Actualizar matrícula desde la lista de matrículas"""
    template_name = 'rector/matricula/matricula_edit.html'
    allowed_roles = ['Rector']
    form_class = MatriculaForm
    model = Matricula
    context_object_name = 'matricula'
    
    def get_object(self, queryset=None):
        return get_object_or_404(
            Matricula.objects.select_related(
                'estudiante__usuario',
                'año_lectivo',
                'grado_año_lectivo__grado__nivel_escolar',
                'sede'
            ),
            pk=self.kwargs['pk']
        )
    
    def get_form_kwargs(self):
        """Pasar el estudiante al formulario"""
        kwargs = super().get_form_kwargs()
        kwargs['estudiante'] = self.object.estudiante
        return kwargs
    
    def get_initial(self):
        """Establecer valores iniciales"""
        initial = super().get_initial()
        
        # Agregar nivel basado en el grado actual
        if self.object.grado_año_lectivo:
            initial['nivel'] = self.object.grado_año_lectivo.grado.nivel_escolar
        
        return initial
    
    def form_valid(self, form):
        """Procesar formulario válido"""
        messages.success(
            self.request, 
            f'Matrícula actualizada exitosamente para {self.object.estudiante.usuario.get_full_name()}'
        )
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirigir a la lista de matrículas"""
        return reverse_lazy('rector:matricula_list')
    
    def get_context_data(self, **kwargs):
        """Agregar contexto adicional"""
        context = super().get_context_data(**kwargs)
        
        context.update({
            'titulo': f'Editar Matrícula - {self.object.estudiante.usuario.get_full_name()}',
            'accion': 'editar',
            'matricula_actual': self.object,
            'niveles': NivelEscolar.objects.all(),
        })
        
        return context

class MatriculaDeleteFromListView(RoleRequiredMixin, DeleteView):
    """Eliminar matrícula desde la lista de matrículas"""
    template_name = 'rector/matricula/matricula_confirm_delete_list.html'
    allowed_roles = ['Rector']
    model = Matricula
    
    def get_object(self, queryset=None):
        return get_object_or_404(
            Matricula.objects.select_related(
                'estudiante__usuario',
                'grado_año_lectivo__grado',
                'sede',
                'año_lectivo'
            ),
            pk=self.kwargs['pk']
        )
    
    def get_success_url(self):
        messages.success(self.request, 'Matrícula eliminada exitosamente')
        return reverse_lazy('rector:matricula_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        matricula = self.object
        
        # Verificar si hay notas asociadas
        tiene_notas = Nota.objects.filter(
            estudiante=matricula.estudiante,
            periodo_academico__año_lectivo=matricula.año_lectivo
        ).exists()
        
        # Verificar si hay asistencias asociadas
        tiene_asistencias = Asistencia.objects.filter(
            estudiante=matricula.estudiante,
            periodo_academico__año_lectivo=matricula.año_lectivo
        ).exists()
        
        # Verificar si hay comportamientos asociados
        tiene_comportamientos = Comportamiento.objects.filter(
            estudiante=matricula.estudiante,
            periodo_academico__año_lectivo=matricula.año_lectivo
        ).exists()
        
        context.update({
            'matricula': matricula,
            'estudiante': matricula.estudiante,
            'titulo': f'Eliminar Matrícula - {matricula.estudiante.usuario.get_full_name()}',
            'tiene_notas': tiene_notas,
            'tiene_asistencias': tiene_asistencias,
            'tiene_comportamientos': tiene_comportamientos,
            'tiene_datos_asociados': tiene_notas or tiene_asistencias or tiene_comportamientos,
        })
        
        return context
    
    def delete(self, request, *args, **kwargs):
        matricula = self.get_object()
        
        # Verificar si hay datos asociados antes de eliminar
        tiene_notas = Nota.objects.filter(
            estudiante=matricula.estudiante,
            periodo_academico__año_lectivo=matricula.año_lectivo
        ).exists()
        
        if tiene_notas:
            messages.error(
                request,
                'No se puede eliminar la matrícula porque tiene calificaciones registradas.'
            )
            return redirect('rector:matricula_list')
        
        # También podrías verificar otros datos asociados
        tiene_asistencias = Asistencia.objects.filter(
            estudiante=matricula.estudiante,
            periodo_academico__año_lectivo=matricula.año_lectivo
        ).exists()
        
        if tiene_asistencias:
            messages.error(
                request,
                'No se puede eliminar la matrícula porque tiene registros de asistencia.'
            )
            return redirect('rector:matricula_list')
        
        return super().delete(request, *args, **kwargs)
    
# ================== MATRÍCULA DESDE LISTA ==================
class MatriculaRapidaView(RoleRequiredMixin, TemplateView):
    """Vista para matrícula rápida (similar a acudientes)"""
    template_name = 'rector/matricula/matricula_rapida.html'
    allowed_roles = ['Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener año lectivo actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_actual
        
        # Sedes activas
        context['sedes'] = Sede.objects.filter(estado=True)
        
        # Niveles escolares
        context['niveles'] = NivelEscolar.objects.all()
        
        # Formularios
        context['form_matricula'] = MatriculaForm()
        context['form_estudiante'] = EstudianteCreateForm()
        
        # Estadísticas de matrículas del año actual
        if año_actual:
            context['estadisticas_matriculas'] = {
                'total': Matricula.objects.filter(año_lectivo=año_actual).count(),
                'activas': Matricula.objects.filter(año_lectivo=año_actual, estado='ACT').count(),
                'pendientes': Matricula.objects.filter(año_lectivo=año_actual, estado='PEN').count(),
                'pre_matriculas': Matricula.objects.filter(año_lectivo=año_actual, estado='PRE').count(),
            }
        
        return context
# ================== CREAR / EDITAR / ELIMINAR MATRÍCULA ==================desde estudiante        
class MatriculaCreateView(RoleRequiredMixin, CreateView):
    """Crear nueva matrícula para un estudiante"""
    template_name = 'rector/matricula/matricula_form.html'
    allowed_roles = ['Rector']
    form_class = MatriculaForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['estudiante'] = get_object_or_404(Estudiante, pk=self.kwargs['pk'])
        return kwargs
    
    def get_initial(self):
        initial = super().get_initial()
        estudiante = get_object_or_404(Estudiante, pk=self.kwargs['pk'])
        
        # Obtener año lectivo actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        if año_actual:
            initial['año_lectivo'] = año_actual
            
            # Si el estudiante tiene matrículas anteriores
            matricula_anterior = estudiante.matriculas.order_by('-created_at').first()
            if matricula_anterior:
                # Sugerir sede
                initial['sede'] = matricula_anterior.sede
                
                # Sugerir siguiente grado
                grado_actual = matricula_anterior.grado_año_lectivo.grado
                
                # Buscar siguiente grado
                orden_grados = ['Prejardin', 'Jardin', 'Transicion', 'Primero', 'Segundo', 'Tercero', 'Cuarto', 'Quinto']
                try:
                    indice_actual = orden_grados.index(grado_actual.nombre)
                    if indice_actual + 1 < len(orden_grados):
                        siguiente_nombre = orden_grados[indice_actual + 1]
                        siguiente_grado = Grado.objects.filter(nombre=siguiente_nombre).first()
                        if siguiente_grado:
                            grado_año_lectivo = GradoAñoLectivo.objects.filter(
                                grado=siguiente_grado,
                                año_lectivo=año_actual,
                                estado=True
                            ).first()
                            if grado_año_lectivo:
                                initial['grado_año_lectivo'] = grado_año_lectivo
                except ValueError:
                    pass
        
        # Estado por defecto
        initial['estado'] = 'PRE'  # Pre-matrícula
        
        return initial
    
    def form_valid(self, form):
        estudiante = get_object_or_404(Estudiante, pk=self.kwargs['pk'])
        form.instance.estudiante = estudiante
        
        # Generar código de matrícula
        from django.utils import timezone
        import random
        import string
        
        año = timezone.now().year
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        form.instance.codigo_matricula = f"MAT-{año}-{random_str}"
        
        messages.success(self.request, 'Matrícula creada exitosamente')
        return super().form_valid(form)
    
    def get_success_url(self):
        estudiante_pk = self.kwargs['pk']
        return reverse_lazy('rector:estudiante_detail', kwargs={'pk': estudiante_pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante = get_object_or_404(Estudiante, pk=self.kwargs['pk'])
        context['estudiante'] = estudiante
        context['titulo'] = f'Nueva Matrícula - {estudiante.usuario.get_full_name()}'
        
        # Agregar niveles escolares para el select
        context['niveles'] = NivelEscolar.objects.all()
        
        return context
    
class MatriculaUpdateView(RoleRequiredMixin, UpdateView):
    """Actualizar matrícula existente"""
    template_name = 'rector/matricula/matricula_form.html'
    allowed_roles = ['Rector']
    form_class = MatriculaForm
    
    def get_object(self):
        """Obtener la matrícula a editar"""
        return get_object_or_404(Matricula, pk=self.kwargs['matricula_pk'])
    
    def get_form_kwargs(self):
        """Pasar el estudiante al formulario"""
        kwargs = super().get_form_kwargs()
        kwargs['estudiante'] = self.object.estudiante
        return kwargs
    
    def get_initial(self):
        """Establecer valores iniciales"""
        initial = super().get_initial()
        
        # Agregar nivel basado en el grado actual
        if self.object.grado_año_lectivo:
            initial['nivel'] = self.object.grado_año_lectivo.grado.nivel_escolar
        
        return initial
    
    def form_valid(self, form):
        """Procesar formulario válido"""
        messages.success(
            self.request, 
            f'Matrícula actualizada exitosamente para {self.object.estudiante.usuario.get_full_name()}'
        )
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Manejar formulario inválido"""
        messages.error(
            self.request,
            'Error al actualizar la matrícula. Por favor, revise los datos.'
        )
        return super().form_invalid(form)
    
    def get_success_url(self):
        """URL de redirección después de éxito"""
        estudiante_pk = self.object.estudiante.pk
        return reverse_lazy('rector:estudiante_detail', kwargs={'pk': estudiante_pk})
    
    def get_context_data(self, **kwargs):
        """Agregar contexto adicional"""
        context = super().get_context_data(**kwargs)
        
        context.update({
            'estudiante': self.object.estudiante,
            'titulo': f'Editar Matrícula - {self.object.estudiante.usuario.get_full_name()}',
            'accion': 'editar',
            'matricula_actual': self.object,
        })
        
        return context
    
class MatriculaDeleteView(RoleRequiredMixin, DeleteView):
    """Eliminar matrícula"""
    template_name = 'rector/matricula/matricula_confirm_delete.html'
    allowed_roles = ['Rector']
    
    def get_object(self):
        return get_object_or_404(Matricula, pk=self.kwargs['matricula_pk'])
    
    def get_success_url(self):
        estudiante_pk = self.kwargs['pk']
        messages.success(self.request, 'Matrícula eliminada exitosamente')
        return reverse_lazy('rector:estudiante_detail', kwargs={'pk': estudiante_pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante = get_object_or_404(Estudiante, pk=self.kwargs['pk'])
        context['estudiante'] = estudiante
        context['titulo'] = f'Eliminar Matrícula - {estudiante.usuario.get_full_name()}'
        return context

# ================== AJAX PARA FILTROS DE MATRÍCULA ==================
class GetMatriculasFiltradasAjaxView(LoginRequiredMixin, View):
    """Obtener matrículas filtradas para AJAX"""
    
    def get(self, request, *args, **kwargs):
        try:
            filtros = request.GET
            
            queryset = Matricula.objects.select_related(
                'estudiante__usuario',
                'año_lectivo__sede__colegio',
                'grado_año_lectivo__grado__nivel_escolar',
                'sede'
            ).order_by('-created_at')
            
            # Aplicar filtros
            if filtros.get('año') and filtros.get('año') != 'todos':
                queryset = queryset.filter(año_lectivo_id=filtros.get('año'))
            
            if filtros.get('sede') and filtros.get('sede') != 'todas':
                queryset = queryset.filter(sede_id=filtros.get('sede'))
            
            if filtros.get('grado') and filtros.get('grado') != 'todos':
                queryset = queryset.filter(grado_año_lectivo_id=filtros.get('grado'))
            
            if filtros.get('estado') and filtros.get('estado') != 'todos':
                queryset = queryset.filter(estado=filtros.get('estado'))
            
            if filtros.get('search'):
                search = filtros.get('search')
                queryset = queryset.filter(
                    Q(estudiante__usuario__nombres__icontains=search) |
                    Q(estudiante__usuario__apellidos__icontains=search) |
                    Q(estudiante__usuario__numero_documento__icontains=search) |
                    Q(codigo_matricula__icontains=search)
                )
            
            # Paginación
            page = int(filtros.get('page', 1))
            per_page = int(filtros.get('per_page', 20))
            start = (page - 1) * per_page
            end = start + per_page
            
            total = queryset.count()
            matriculas_page = queryset[start:end]
            
            # Preparar datos para JSON
            matriculas_data = []
            for matricula in matriculas_page:
                matriculas_data.append({
                    'id': matricula.id,
                    'codigo': matricula.codigo_matricula,
                    'estudiante': {
                        'id': matricula.estudiante.id,
                        'nombre': matricula.estudiante.usuario.get_full_name(),
                        'documento': matricula.estudiante.usuario.numero_documento,
                        'foto_url': matricula.estudiante.foto.url if matricula.estudiante.foto else None,
                    },
                    'año_lectivo': {
                        'id': matricula.año_lectivo.id,
                        'anho': matricula.año_lectivo.anho,
                        'sede_nombre': matricula.año_lectivo.sede.nombre,
                    },
                    'grado': {
                        'nombre': matricula.grado_año_lectivo.grado.nombre,
                        'nivel': matricula.grado_año_lectivo.grado.nivel_escolar.nombre,
                    },
                    'sede': matricula.sede.nombre,
                    'fecha_matricula': matricula.fecha_matricula.strftime('%d/%m/%Y'),
                    'estado': matricula.get_estado_display(),
                    'estado_clase': {
                        'ACT': 'success',
                        'PEN': 'warning',
                        'PRE': 'info',
                        'INA': 'secondary',
                        'RET': 'danger'
                    }.get(matricula.estado, 'secondary'),
                    'url_detalle': reverse_lazy('rector:matricula_detail', kwargs={'pk': matricula.id}),
                    'url_editar': reverse_lazy('rector:matricula_edit', kwargs={'pk': matricula.id}),
                })
            
            return JsonResponse({
                'success': True,
                'matriculas': matriculas_data,
                'total': total,
                'page': page,
                'total_pages': (total + per_page - 1) // per_page,
                'has_previous': page > 1,
                'has_next': end < total,
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

# ================== BUSCAR ESTUDIANTES PARA MATRÍCULA ==================
class BuscarEstudiantesMatriculaAjaxView(RoleRequiredMixin, View):
    """Buscar estudiantes para matrícula (AJAX)"""
    allowed_roles = ['Rector']
    
    def get(self, request):
        documento = request.GET.get('documento', '').strip()
        nombre = request.GET.get('nombre', '').strip()
        
        # Construir la consulta
        estudiantes_qs = Estudiante.objects.filter(
            estado=True
        ).select_related('usuario').prefetch_related('matriculas__año_lectivo')
        
        # Aplicar filtros
        if documento:
            estudiantes_qs = estudiantes_qs.filter(
                usuario__numero_documento__icontains=documento
            )
        
        if nombre:
            estudiantes_qs = estudiantes_qs.filter(
                Q(usuario__nombres__icontains=nombre) | 
                Q(usuario__apellidos__icontains=nombre)
            )
        
        # Limitar resultados
        estudiantes_qs = estudiantes_qs[:20]
        
        # Preparar datos para respuesta JSON
        estudiantes = []
        for estudiante in estudiantes_qs:
            # Obtener matrícula del año actual
            año_actual = AñoLectivo.objects.filter(estado=True).first()
            tiene_matricula_actual = False
            matricula_actual = None
            
            if año_actual:
                matricula_actual = estudiante.matriculas.filter(
                    año_lectivo=año_actual
                ).first()
                tiene_matricula_actual = matricula_actual is not None
            
            estudiantes.append({
                'id': estudiante.id,
                'nombre_completo': estudiante.usuario.get_full_name(),
                'nombres': estudiante.usuario.nombres,
                'apellidos': estudiante.usuario.apellidos,
                'tipo_documento': estudiante.usuario.tipo_documento.nombre if estudiante.usuario.tipo_documento else '',
                'numero_documento': estudiante.usuario.numero_documento,
                'email': estudiante.usuario.email or '',
                'telefono': estudiante.usuario.telefono or '',
                'edad': estudiante.usuario.edad or '',
                'fecha_nacimiento': estudiante.usuario.fecha_nacimiento.strftime('%d/%m/%Y') if estudiante.usuario.fecha_nacimiento else '',
                'tiene_matricula_actual': tiene_matricula_actual,
                'matricula_actual': {
                    'grado': matricula_actual.grado_año_lectivo.grado.nombre if matricula_actual else None,
                    'sede': matricula_actual.sede.nombre if matricula_actual else None,
                    'estado': matricula_actual.get_estado_display() if matricula_actual else None,
                } if matricula_actual else None,
                'matriculas_anteriores': estudiante.matriculas.exclude(
                    año_lectivo=año_actual
                ).count() if año_actual else 0,
                'url_detalle': reverse_lazy('rector:estudiante_detail', kwargs={'pk': estudiante.id}),
                'foto_url': estudiante.foto.url if estudiante.foto else None,
            })
        
        return JsonResponse({
            'success': True,
            'estudiantes': estudiantes,
            'total': len(estudiantes)
        })

# ================== VERIFICAR DOCUMENTO ESTUDIANTE ==================
class VerificarDocumentoEstudianteAjaxView(RoleRequiredMixin, View):
    """Verificar si un documento ya está registrado como estudiante (AJAX)"""
    allowed_roles = ['Rector']
    
    def get(self, request):
        numero_documento = request.GET.get('numero_documento', '').strip()
        
        if not numero_documento:
            return JsonResponse({'error': 'Número de documento requerido'}, status=400)
        
        try:
            # Buscar usuario por documento
            usuario = Usuario.objects.filter(
                numero_documento=numero_documento,
                tipo_usuario__nombre='Estudiante'
            ).first()
            
            if usuario:
                # Verificar si ya es estudiante
                estudiante = Estudiante.objects.filter(usuario=usuario).first()
                
                if estudiante:
                    # Obtener matrículas
                    matriculas = estudiante.matriculas.select_related(
                        'grado_año_lectivo__grado',
                        'sede',
                        'año_lectivo'
                    ).order_by('-año_lectivo__anho')[:5]
                    
                    matriculas_info = []
                    for matricula in matriculas:
                        matriculas_info.append({
                            'id': matricula.id,
                            'año': matricula.año_lectivo.anho,
                            'grado': matricula.grado_año_lectivo.grado.nombre,
                            'sede': matricula.sede.nombre,
                            'estado': matricula.get_estado_display(),
                        })
                    
                    return JsonResponse({
                        'existe': True,
                        'tipo': 'estudiante',
                        'usuario': {
                            'id': usuario.id,
                            'nombre_completo': usuario.get_full_name(),
                            'nombres': usuario.nombres,
                            'apellidos': usuario.apellidos,
                            'tipo_documento': usuario.tipo_documento.nombre if usuario.tipo_documento else '',
                            'email': usuario.email or '',
                            'telefono': usuario.telefono or '',
                            'direccion': usuario.direccion or '',
                            'fecha_nacimiento': usuario.fecha_nacimiento.strftime('%d/%m/%Y') if usuario.fecha_nacimiento else '',
                        },
                        'estudiante': {
                            'id': estudiante.id,
                            'estado': estudiante.estado,
                            'matriculas': matriculas_info,
                            'total_matriculas': len(matriculas_info)
                        },
                        'mensaje': 'Documento ya registrado como estudiante'
                    })
                else:
                    return JsonResponse({
                        'existe': True,
                        'tipo': 'usuario',
                        'usuario': {
                            'id': usuario.id,
                            'nombre_completo': usuario.get_full_name(),
                            'nombres': usuario.nombres,
                            'apellidos': usuario.apellidos,
                            'tipo_documento': usuario.tipo_documento.nombre if usuario.tipo_documento else '',
                            'email': usuario.email or '',
                            'telefono': usuario.telefono or '',
                            'direccion': usuario.direccion or '',
                            'fecha_nacimiento': usuario.fecha_nacimiento.strftime('%d/%m/%Y') if usuario.fecha_nacimiento else '',
                        },
                        'mensaje': 'Documento registrado como usuario pero no como estudiante'
                    })
            else:
                return JsonResponse({
                    'existe': False,
                    'mensaje': 'Documento no registrado en el sistema'
                })
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

# ================== CREAR ESTUDIANTE Y MATRICULAR ==================
class CrearEstudianteMatriculaAjaxView(RoleRequiredMixin, View):
    """Crear estudiante nuevo y matricularlo (AJAX) - VERSIÓN CORREGIDA"""
    allowed_roles = ['Rector']
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            # 1. Crear estudiante usando el formulario
            form_data = {
                'nombres': data.get('usuario', {}).get('nombres', ''),
                'apellidos': data.get('usuario', {}).get('apellidos', ''),
                'tipo_documento': data.get('usuario', {}).get('tipo_documento'),
                'numero_documento': data.get('usuario', {}).get('numero_documento', ''),
                'email': data.get('usuario', {}).get('email', ''),
                'telefono': data.get('usuario', {}).get('telefono', ''),
                'direccion': data.get('usuario', {}).get('direccion', ''),
                'sexo': data.get('usuario', {}).get('sexo', ''),
                'fecha_nacimiento': data.get('usuario', {}).get('fecha_nacimiento', ''),
            }
            
            # Crear formulario y validar
            form = EstudianteCreateForm(data=form_data)
            
            if not form.is_valid():
                errors = form.errors.as_json()
                return JsonResponse({
                    'success': False,
                    'error': 'Error en los datos del estudiante',
                    'errors': json.loads(errors)
                }, status=400)
            
            # Guardar estudiante
            estudiante = form.save()
            
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
            
            # Generar código de matrícula si no se generó automáticamente
            if not matricula.codigo_matricula:
                from django.utils import timezone
                import random
                import string
                
                año = timezone.now().year
                random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                matricula.codigo_matricula = f"MAT-{año}-{random_str}"
                matricula.save()
            
            # 3. Crear acudientes si se proporcionaron
            acudientes_data = data.get('acudientes', [])
            acudientes_creados = []
            
            for acudiente_data in acudientes_data:
                # Verificar si el acudiente ya existe
                acudiente_doc = acudiente_data.get('numero_documento')
                acudiente_existente = Usuario.objects.filter(
                    numero_documento=acudiente_doc,
                    tipo_usuario__nombre='Acudiente'
                ).first()
                
                if acudiente_existente:
                    acudiente_usuario = acudiente_existente
                else:
                    # Crear nuevo acudiente
                    tipo_acudiente, _ = TipoUsuario.objects.get_or_create(
                        nombre='Acudiente',
                        defaults={'nombre': 'Acudiente'}
                    )
                    
                    # Crear formulario para acudiente (podrías tener un formulario específico)
                    acudiente_usuario = Usuario.objects.create_user(
                        username=acudiente_doc,
                        password=acudiente_doc,
                        tipo_usuario=tipo_acudiente,
                        nombres=acudiente_data.get('nombres', ''),
                        apellidos=acudiente_data.get('apellidos', ''),
                        numero_documento=acudiente_doc,
                        email=acudiente_data.get('email', ''),
                        telefono=acudiente_data.get('telefono', ''),
                        # Nota: Necesitarías más campos según tu modelo
                    )
                
                # Crear relación acudiente-estudiante
                parentesco = acudiente_data.get('parentesco')
                
                if not Acudiente.objects.filter(
                    estudiante=estudiante,
                    acudiente=acudiente_usuario
                ).exists():
                    relacion = Acudiente.objects.create(
                        estudiante=estudiante,
                        acudiente=acudiente_usuario,
                        parentesco=parentesco
                    )
                    
                    acudientes_creados.append({
                        'id': acudiente_usuario.id,
                        'nombre': acudiente_usuario.get_full_name(),
                        'parentesco': parentesco,
                        'documento': acudiente_usuario.numero_documento
                    })
            
            return JsonResponse({
                'success': True,
                'estudiante': {
                    'id': estudiante.id,
                    'nombre': estudiante.usuario.get_full_name(),
                    'documento': estudiante.usuario.numero_documento,
                    'url_detalle': reverse_lazy('rector:estudiante_detail', kwargs={'pk': estudiante.id})
                },
                'matricula': {
                    'id': matricula.id,
                    'codigo': matricula.codigo_matricula,
                    'estado': matricula.get_estado_display(),
                    'url_detalle': reverse_lazy('rector:matricula_detail', kwargs={'pk': matricula.id})
                },
                'acudientes': acudientes_creados,
                'total_acudientes': len(acudientes_creados),
                'mensaje': 'Estudiante creado y matriculado exitosamente'
            })
            
        except Exception as e:
            import traceback
            print(f"Error: {e}")
            print(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
        
# ================== MATRICULAR ESTUDIANTE EXISTENTE ==================
class MatricularEstudianteExistenteAjaxView(RoleRequiredMixin, View):
    """Matricular un estudiante existente (AJAX)"""
    allowed_roles = ['Rector']
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            estudiante_id = data.get('estudiante_id')
            matricula_data = data.get('matricula', {})
            
            if not estudiante_id:
                return JsonResponse({
                    'success': False,
                    'error': 'ID de estudiante requerido'
                }, status=400)
            
            estudiante = Estudiante.objects.get(id=estudiante_id)
            
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
            
            # Generar código de matrícula si no se generó automáticamente
            if not matricula.codigo_matricula:
                from django.utils import timezone
                import random
                import string
                
                año = timezone.now().year
                random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                matricula.codigo_matricula = f"MAT-{año}-{random_str}"
                matricula.save()
            
            return JsonResponse({
                'success': True,
                'estudiante': {
                    'id': estudiante.id,
                    'nombre': estudiante.usuario.get_full_name(),
                    'documento': estudiante.usuario.numero_documento,
                    'url_detalle': reverse_lazy('rector:estudiante_detail', kwargs={'pk': estudiante.id})
                },
                'matricula': {
                    'id': matricula.id,
                    'codigo': matricula.codigo_matricula,
                    'estado': matricula.get_estado_display(),
                    'url_detalle': reverse_lazy('rector:matricula_detail', kwargs={'pk': matricula.id})
                },
                'mensaje': 'Estudiante matriculado exitosamente'
            })
            
        except Estudiante.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Estudiante no encontrado'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
        
# ================== EXPORTAR MATRÍCULAS ==================
class ExportarMatriculasView(RoleRequiredMixin, View):
    """Exportar matrículas a Excel o PDF"""
    allowed_roles = ['Rector']
    
    def post(self, request, *args, **kwargs):
        formato = request.POST.get('formato', 'excel')
        columnas = request.POST.getlist('columnas[]', [])
        
        # Obtener matrículas filtradas
        queryset = Matricula.objects.select_related(
            'estudiante__usuario',
            'año_lectivo__sede__colegio',
            'grado_año_lectivo__grado__nivel_escolar',
            'sede'
        ).order_by('-created_at')
        
        # Aplicar filtros (similar a MatriculaListView)
        año_filter = request.POST.get('año')
        sede_filter = request.POST.get('sede')
        grado_filter = request.POST.get('grado')
        estado_filter = request.POST.get('estado')
        search = request.POST.get('search')
        
        if año_filter and año_filter != 'todos':
            queryset = queryset.filter(año_lectivo_id=año_filter)
        
        if sede_filter and sede_filter != 'todas':
            queryset = queryset.filter(sede_id=sede_filter)
        
        if grado_filter and grado_filter != 'todos':
            queryset = queryset.filter(grado_año_lectivo_id=grado_filter)
        
        if estado_filter and estado_filter != 'todos':
            queryset = queryset.filter(estado=estado_filter)
        
        if search:
            queryset = queryset.filter(
                Q(estudiante__usuario__nombres__icontains=search) |
                Q(estudiante__usuario__apellidos__icontains=search) |
                Q(estudiante__usuario__numero_documento__icontains=search) |
                Q(codigo_matricula__icontains=search)
            )
        
        if formato == 'excel':
            return self.exportar_excel(queryset, columnas)
        elif formato == 'pdf':
            return self.exportar_pdf(queryset, columnas)
        else:  # CSV
            return self.exportar_csv(queryset, columnas)
    
    def exportar_excel(self, queryset, columnas):
        # Preparar datos
        data = []
        headers = []
        
        # Definir columnas según selección
        columnas_mapping = {
            'estudiante': 'Estudiante',
            'documento': 'Documento',
            'codigo': 'Código Matrícula',
            'año': 'Año Lectivo',
            'grado': 'Grado',
            'nivel': 'Nivel',
            'sede': 'Sede',
            'fecha': 'Fecha Matrícula',
            'estado': 'Estado',
        }
        
        # Seleccionar columnas a mostrar
        if not columnas:
            columnas = ['estudiante', 'documento', 'grado', 'estado']
        
        for key in columnas:
            if key in columnas_mapping:
                headers.append(columnas_mapping[key])
        
        # Agregar datos
        for matricula in queryset:
            row = []
            for col in columnas:
                if col == 'estudiante':
                    row.append(matricula.estudiante.usuario.get_full_name())
                elif col == 'documento':
                    row.append(matricula.estudiante.usuario.numero_documento)
                elif col == 'codigo':
                    row.append(matricula.codigo_matricula)
                elif col == 'año':
                    row.append(matricula.año_lectivo.anho)
                elif col == 'grado':
                    row.append(matricula.grado_año_lectivo.grado.nombre)
                elif col == 'nivel':
                    row.append(matricula.grado_año_lectivo.grado.nivel_escolar.nombre)
                elif col == 'sede':
                    row.append(matricula.sede.nombre)
                elif col == 'fecha':
                    row.append(matricula.fecha_matricula.strftime('%d/%m/%Y'))
                elif col == 'estado':
                    row.append(matricula.get_estado_display())
            data.append(row)
        
        # Crear DataFrame
        df = pd.DataFrame(data, columns=headers)
        
        # Crear archivo Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Matrículas', index=False)
            worksheet = writer.sheets['Matrículas']
            
            # Ajustar ancho de columnas
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Crear respuesta
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=matriculas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return response
    
    def exportar_pdf(self, queryset, columnas):
        # Implementar exportación PDF similar a Excel
        # ...
        pass
    
    def exportar_csv(self, queryset, columnas):
        # Implementar exportación CSV
        # ...
        pass