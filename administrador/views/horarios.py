# administrador/views/horarios.py (o agregar a views.py)
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from matricula.models import PeriodoAcademico, AsignaturaGradoAñoLectivo
from academico.models import HorarioClase
from gestioncolegio.models import AñoLectivo
from gestioncolegio.mixins import RoleRequiredMixin
from administrador.forms import HorarioClaseForm, HorarioFilterForm

# ========================
# GESTIÓN DE HORARIOS
# ========================

class HorarioListView(RoleRequiredMixin, ListView):
    """Lista de horarios con filtros"""
    model = HorarioClase
    template_name = 'administrador/horarios/horario_list.html'
    context_object_name = 'horarios'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    paginate_by = 50
    
    def get_queryset(self):
        # Obtener año lectivo activo
        año_lectivo = AñoLectivo.objects.filter(estado=True).first()
        
        if not año_lectivo:
            # Si no hay año activo, no mostrar horarios
            return HorarioClase.objects.none()
        
        # Filtrar horarios del año lectivo activo
        queryset = HorarioClase.objects.filter(
            asignatura_grado__grado_año_lectivo__año_lectivo=año_lectivo
        ).select_related(
            'asignatura_grado',
            'asignatura_grado__asignatura',
            'asignatura_grado__grado_año_lectivo__grado',
            'asignatura_grado__docente__usuario'
        ).order_by('dia_semana', 'hora_inicio')
        
        # Aplicar filtros
        tipo_filtro = self.request.GET.get('tipo_filtro')
        grado_id = self.request.GET.get('grado')
        asignatura_id = self.request.GET.get('asignatura')
        docente_id = self.request.GET.get('docente')
        dia_semana = self.request.GET.get('dia_semana')
        
        if grado_id:
            queryset = queryset.filter(
                asignatura_grado__grado_año_lectivo_id=grado_id
            )
        
        if asignatura_id:
            queryset = queryset.filter(
                asignatura_grado__asignatura_id=asignatura_id
            )
        
        if docente_id:
            queryset = queryset.filter(
                asignatura_grado__docente_id=docente_id
            )
        
        if dia_semana:
            queryset = queryset.filter(dia_semana=dia_semana)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener año lectivo activo
        año_lectivo = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo'] = año_lectivo
        
        # Formulario de filtros
        if año_lectivo:
            context['filter_form'] = HorarioFilterForm(
                self.request.GET or None,
                año_lectivo=año_lectivo
            )
        else:
            context['filter_form'] = HorarioFilterForm()
        
        # Estadísticas
        if año_lectivo:
            total_horarios = self.get_queryset().count()
            context['total_horarios'] = total_horarios
            
            # Horarios por día
            dias = ['LUN', 'MAR', 'MIE', 'JUE', 'VIE']
            horarios_por_dia = {}
            for dia in dias:
                horarios_por_dia[dia] = self.get_queryset().filter(dia_semana=dia).count()
            context['horarios_por_dia'] = horarios_por_dia
            
            # Docentes con horarios
            context['docentes_con_horarios'] = self.get_queryset().values(
                'asignatura_grado__docente'
            ).distinct().count()
        
        return context

class HorarioCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    """Crear nuevo horario"""
    model = HorarioClase
    form_class = HorarioClaseForm
    template_name = 'administrador/horarios/horario_form.html'
    success_message = "Horario creado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def dispatch(self, request, *args, **kwargs):
        # Verificar que haya un año lectivo activo
        año_lectivo = AñoLectivo.objects.filter(estado=True).first()
        
        if not año_lectivo:
            messages.error(request, 'No hay un año lectivo activo. Active un año lectivo para crear horarios.')
            return redirect('administrador:horario_list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        año_lectivo = AñoLectivo.objects.filter(estado=True).first()
        kwargs['año_lectivo'] = año_lectivo
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Nuevo Horario'
        context['submit_text'] = 'Crear Horario'
        context['año_lectivo'] = AñoLectivo.objects.filter(estado=True).first()
        return context
    
    def get_success_url(self):
        return reverse_lazy('administrador:horario_list')

class HorarioUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar horario existente"""
    model = HorarioClase
    form_class = HorarioClaseForm
    template_name = 'administrador/horarios/horario_form.html'
    success_message = "Horario actualizado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Obtener el año lectivo del horario actual
        año_lectivo = self.object.asignatura_grado.grado_año_lectivo.año_lectivo
        kwargs['año_lectivo'] = año_lectivo
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Horario'
        context['submit_text'] = 'Actualizar Horario'
        context['año_lectivo'] = self.object.asignatura_grado.grado_año_lectivo.año_lectivo
        return context
    
    def get_success_url(self):
        return reverse_lazy('administrador:horario_list')

class HorarioDeleteView(RoleRequiredMixin, SuccessMessageMixin, DeleteView):
    """Eliminar horario"""
    model = HorarioClase
    template_name = 'administrador/horarios/horario_confirm_delete.html'
    success_message = "Horario eliminado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_success_url(self):
        return reverse_lazy('administrador:horario_list')

class HorarioBulkDeleteView(RoleRequiredMixin, View):
    """Eliminar múltiples horarios"""
    allowed_roles = ['Administrador', 'Rector']
    
    def post(self, request):
        horario_ids = request.POST.getlist('horario_ids')
        
        if not horario_ids:
            messages.error(request, 'No se seleccionaron horarios para eliminar.')
            return redirect('administrador:horario_list')
        
        try:
            horarios = HorarioClase.objects.filter(id__in=horario_ids)
            count = horarios.count()
            horarios.delete()
            
            messages.success(request, f'Se eliminaron {count} horarios exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al eliminar horarios: {str(e)}')
        
        return redirect('administrador:horario_list')

class HorarioGenerarPDFView(RoleRequiredMixin, View):
    """Generar PDF de horarios"""
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get(self, request, tipo=None, id=None):
        # Esta vista generaría PDFs (implementación básica)
        # Necesitarías instalar reportlab o weasyprint
        
        año_lectivo = AñoLectivo.objects.filter(estado=True).first()
        
        if not año_lectivo:
            messages.error(request, 'No hay un año lectivo activo.')
            return redirect('administrador:horario_list')
        
        # Lógica para generar PDF según tipo (grado, docente, asignatura)
        if tipo == 'grado':
            # Generar PDF por grado
            pass
        elif tipo == 'docente':
            # Generar PDF por docente
            pass
        elif tipo == 'asignatura':
            # Generar PDF por asignatura
            pass
        else:
            # Generar PDF completo
            pass
        
        # Por ahora solo redireccionamos
        messages.info(request, 'Funcionalidad de PDF en desarrollo.')
        return redirect('administrador:horario_list')

class HorarioGradoView(RoleRequiredMixin, View):
    """Vista de horarios por grado"""
    template_name = 'administrador/horarios/horario_grado.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get(self, request, grado_id=None):
        año_lectivo = AñoLectivo.objects.filter(estado=True).first()
        
        if not año_lectivo:
            messages.error(request, 'No hay un año lectivo activo.')
            return redirect('administrador:horario_list')
        
        # Obtener todos los grados del año lectivo
        from matricula.models import GradoAñoLectivo
        grados = GradoAñoLectivo.objects.filter(
            año_lectivo=año_lectivo
        ).select_related('grado')
        
        # Si se especifica un grado, mostrar sus horarios
        horarios_por_grado = {}
        if grado_id:
            grado = get_object_or_404(GradoAñoLectivo, id=grado_id, año_lectivo=año_lectivo)
            
            # Obtener horarios organizados por día
            dias = ['LUN', 'MAR', 'MIE', 'JUE', 'VIE']
            horarios_por_dia = {}
            
            for dia in dias:
                horarios = HorarioClase.objects.filter(
                    asignatura_grado__grado_año_lectivo=grado,
                    dia_semana=dia
                ).select_related(
                    'asignatura_grado__asignatura',
                    'asignatura_grado__docente__usuario'
                ).order_by('hora_inicio')
                
                horarios_por_dia[dia] = horarios
            
            context = {
                'año_lectivo': año_lectivo,
                'grados': grados,
                'grado_seleccionado': grado,
                'horarios_por_dia': horarios_por_dia,
                'dias': dias,
            }
        else:
            context = {
                'año_lectivo': año_lectivo,
                'grados': grados,
            }
        
        return render(request, self.template_name, context)

class HorarioDocenteView(RoleRequiredMixin, View):
    """Vista de horarios por docente"""
    template_name = 'administrador/horarios/horario_docente.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get(self, request, docente_id=None):
        año_lectivo = AñoLectivo.objects.filter(estado=True).first()
        
        if not año_lectivo:
            messages.error(request, 'No hay un año lectivo activo.')
            return redirect('administrador:horario_list')
        
        # Obtener todos los docentes con asignaciones en el año lectivo
        from usuarios.models import Docente
        
        docente_ids = list(AsignaturaGradoAñoLectivo.objects.filter(
            grado_año_lectivo__año_lectivo=año_lectivo,
            docente__isnull=False
        ).values_list('docente_id', flat=True).distinct())
        
        docentes = Docente.objects.filter(
            id__in=docente_ids
        ).select_related('usuario').order_by('usuario__apellidos', 'usuario__nombres')
        
        # Si se especifica un docente, mostrar sus horarios
        if docente_id:
            docente = get_object_or_404(Docente, id=docente_id)
            
            # Obtener horarios organizados por día
            dias = ['LUN', 'MAR', 'MIE', 'JUE', 'VIE']
            horarios_por_dia = {}
            
            for dia in dias:
                horarios = HorarioClase.objects.filter(
                    asignatura_grado__docente=docente,
                    asignatura_grado__grado_año_lectivo__año_lectivo=año_lectivo,
                    dia_semana=dia
                ).select_related(
                    'asignatura_grado__asignatura',
                    'asignatura_grado__grado_año_lectivo__grado'
                ).order_by('hora_inicio')
                
                horarios_por_dia[dia] = horarios
            
            context = {
                'año_lectivo': año_lectivo,
                'docentes': docentes,
                'docente_seleccionado': docente,
                'horarios_por_dia': horarios_por_dia,
                'dias': dias,
            }
        else:
            context = {
                'año_lectivo': año_lectivo,
                'docentes': docentes,
            }
        
        return render(request, self.template_name, context)

class HorarioAsignaturaView(RoleRequiredMixin, View):
    """Vista de horarios por asignatura"""
    template_name = 'administrador/horarios/horario_asignatura.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get(self, request, asignatura_id=None):
        año_lectivo = AñoLectivo.objects.filter(estado=True).first()
        
        if not año_lectivo:
            messages.error(request, 'No hay un año lectivo activo.')
            return redirect('administrador:horario_list')
        
        # Obtener todas las asignaturas del año lectivo
        from academico.models import Asignatura

        asignatura_ids = list(AsignaturaGradoAñoLectivo.objects.filter(
            grado_año_lectivo__año_lectivo=año_lectivo
        ).values_list('asignatura_id', flat=True).distinct())
        
        asignaturas = Asignatura.objects.filter(
            id__in=asignatura_ids
        ).order_by('nombre')        

        # Si se especifica una asignatura, mostrar sus horarios
        if asignatura_id:
            asignatura = get_object_or_404(Asignatura, id=asignatura_id)
            
            # Obtener horarios por grado y día
            from matricula.models import GradoAñoLectivo
            grados = GradoAñoLectivo.objects.filter(
                año_lectivo=año_lectivo,
                asignaturas_grado__asignatura=asignatura
            ).distinct().select_related('grado')
            
            horarios_por_grado = {}
            
            for grado in grados:
                dias = ['LUN', 'MAR', 'MIE', 'JUE', 'VIE']
                horarios_por_dia = {}
                
                for dia in dias:
                    horarios = HorarioClase.objects.filter(
                        asignatura_grado__asignatura=asignatura,
                        asignatura_grado__grado_año_lectivo=grado,
                        dia_semana=dia
                    ).select_related(
                        'asignatura_grado__docente__usuario'
                    ).order_by('hora_inicio')
                    
                    horarios_por_dia[dia] = horarios
                
                horarios_por_grado[grado] = horarios_por_dia
            
            context = {
                'año_lectivo': año_lectivo,
                'asignaturas': asignaturas,
                'asignatura_seleccionada': asignatura,
                'grados': grados,
                'horarios_por_grado': horarios_por_grado,
                'dias': ['LUN', 'MAR', 'MIE', 'JUE', 'VIE'],
            }
        else:
            context = {
                'año_lectivo': año_lectivo,
                'asignaturas': asignaturas,
            }
        
        return render(request, self.template_name, context)

class HorarioCalendarioView(RoleRequiredMixin, View):
    """Vista de calendario de horarios"""
    template_name = 'administrador/horarios/horario_calendario.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get(self, request):
        año_lectivo = AñoLectivo.objects.filter(estado=True).first()
        
        if not año_lectivo:
            messages.error(request, 'No hay un año lectivo activo.')
            return redirect('administrador:horario_list')
        
        # Obtener todos los horarios del año lectivo
        horarios = HorarioClase.objects.filter(
            asignatura_grado__grado_año_lectivo__año_lectivo=año_lectivo
        ).select_related(
            'asignatura_grado__asignatura',
            'asignatura_grado__grado_año_lectivo__grado',
            'asignatura_grado__docente__usuario'
        ).order_by('dia_semana', 'hora_inicio')
        
        # Formatear horarios para FullCalendar
        eventos = []
        for horario in horarios:
            # Mapear días a números (0=domingo, 1=lunes, etc.)
            dias_map = {
                'LUN': 1,
                'MAR': 2,
                'MIE': 3,
                'JUE': 4,
                'VIE': 5
            }
            
            dia_numero = dias_map.get(horario.dia_semana, 1)
            
            evento = {
                'id': horario.id,
                'title': f"{horario.asignatura_grado.asignatura.nombre} - {horario.asignatura_grado.grado_año_lectivo.grado.nombre}",
                'daysOfWeek': [str(dia_numero)],  # Días de la semana como array
                'startTime': horario.hora_inicio.strftime('%H:%M'),
                'endTime': horario.hora_fin.strftime('%H:%M'),
                'color': self.get_color_por_grado(horario.asignatura_grado.grado_año_lectivo.grado.nombre),
                'textColor': '#ffffff',
                'extendedProps': {
                    'docente': horario.asignatura_grado.docente.usuario.get_full_name() if horario.asignatura_grado.docente else 'Sin asignar',
                    'salon': horario.salon or 'Sin asignar',
                    'asignatura': horario.asignatura_grado.asignatura.nombre,
                    'grado': horario.asignatura_grado.grado_año_lectivo.grado.nombre,
                }
            }
            eventos.append(evento)
        
        context = {
            'año_lectivo': año_lectivo,
            'eventos': eventos,
            'horarios': horarios,
        }
        
        return render(request, self.template_name, context)
    
    def get_color_por_grado(self, nombre_grado):
        """Asignar colores diferentes por grado"""
        colores = {
            'Prejardin': '#FF6B6B',
            'Jardin': '#4ECDC4',
            'Transicion': '#45B7D1',
            'Primero': '#96CEB4',
            'Segundo': '#FFEAA7',
            'Tercero': '#DDA0DD',
            'Cuarto': '#98D8C8',
            'Quinto': '#F7DC6F',
        }
        return colores.get(nombre_grado, '#6C5CE7')

class HorarioAjaxView(RoleRequiredMixin, View):
    """Vista AJAX para obtener información de horarios"""
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get(self, request):
        tipo = request.GET.get('tipo')
        año_lectivo = AñoLectivo.objects.filter(estado=True).first()
        
        if not año_lectivo:
            return JsonResponse({'error': 'No hay año lectivo activo'}, status=400)
        
        if tipo == 'horarios_grado':
            grado_id = request.GET.get('grado_id')
            if grado_id:
                horarios = HorarioClase.objects.filter(
                    asignatura_grado__grado_año_lectivo_id=grado_id,
                    asignatura_grado__grado_año_lectivo__año_lectivo=año_lectivo
                ).select_related(
                    'asignatura_grado__asignatura',
                    'asignatura_grado__docente__usuario'
                ).order_by('dia_semana', 'hora_inicio')
                
                data = []
                for horario in horarios:
                    data.append({
                        'id': horario.id,
                        'dia': horario.get_dia_semana_display(),
                        'hora_inicio': horario.hora_inicio.strftime('%H:%M'),
                        'hora_fin': horario.hora_fin.strftime('%H:%M'),
                        'asignatura': horario.asignatura_grado.asignatura.nombre,
                        'docente': horario.asignatura_grado.docente.usuario.get_full_name() if horario.asignatura_grado.docente else 'Sin asignar',
                        'salon': horario.salon or 'Sin asignar',
                    })
                
                return JsonResponse({'horarios': data})
        
        elif tipo == 'disponibilidad_docente':
            docente_id = request.GET.get('docente_id')
            dia = request.GET.get('dia')
            hora_inicio = request.GET.get('hora_inicio')
            hora_fin = request.GET.get('hora_fin')
            
            if docente_id and dia and hora_inicio and hora_fin:
                # Verificar si el docente ya tiene un horario en ese día y hora
                from datetime import datetime
                hora_inicio_dt = datetime.strptime(hora_inicio, '%H:%M').time()
                hora_fin_dt = datetime.strptime(hora_fin, '%H:%M').time()
                
                horarios_conflicto = HorarioClase.objects.filter(
                    asignatura_grado__docente_id=docente_id,
                    dia_semana=dia,
                    hora_inicio__lt=hora_fin_dt,
                    hora_fin__gt=hora_inicio_dt
                ).exists()
                
                return JsonResponse({
                    'disponible': not horarios_conflicto,
                    'conflicto': horarios_conflicto
                })
        
        return JsonResponse({'error': 'Tipo de consulta no válido'}, status=400)