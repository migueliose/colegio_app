"""
Vistas académicas simplificadas
"""
import logging
from django.views.generic import ListView, TemplateView
from django.db.models import Count, Case, Value, When, IntegerField

# Mixins
from gestioncolegio.mixins import RoleRequiredMixin

# Models
from academico.models import Asignatura, HorarioClase, Grado, NivelEscolar
from matricula.models import AsignaturaGradoAñoLectivo, GradoAñoLectivo, PeriodoAcademico
from usuarios.models import Docente
from estudiantes.models import Estudiante
from gestioncolegio.models import AñoLectivo, Sede

logger = logging.getLogger(__name__)

from django.db.models import Q

class AsignaturasListView(RoleRequiredMixin, ListView):
    """Lista de asignaturas - CORREGIDA"""
    template_name = 'academico/asignaturas_list.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    model = Asignatura
    context_object_name = 'asignaturas'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Asignatura.objects.select_related(
            'area', 
            'area__nivel_escolar'
        )
        
        # Si el usuario es docente, filtrar SOLO sus asignaturas
        if self.request.user.tipo_usuario.nombre == 'Docente':
            try:
                docente = Docente.objects.get(usuario=self.request.user)
                
                # Obtener IDs de asignaturas que el docente dicta
                asignaturas_docente_ids = AsignaturaGradoAñoLectivo.objects.filter(
                    docente=docente,
                    grado_año_lectivo__año_lectivo__estado=True
                ).values_list('asignatura_id', flat=True).distinct()
                
                # Aplicar filtro de asignaturas del docente
                queryset = queryset.filter(id__in=asignaturas_docente_ids)
                
                # Si no tiene asignaturas, retornar vacío inmediatamente
                if not asignaturas_docente_ids:
                    return Asignatura.objects.none()
                    
            except Docente.DoesNotExist:
                return Asignatura.objects.none()
        
        # FILTROS
        nivel_id = self.request.GET.get('nivel_id')
        grado_id = self.request.GET.get('grado_id')
        
        # Filtrar por nivel escolar
        if nivel_id:
            queryset = queryset.filter(area__nivel_escolar_id=nivel_id)
        
        # Filtrar por grado
        if grado_id:
            # Para docentes: verificar que también dicten esa asignatura en ese grado
            if self.request.user.tipo_usuario.nombre == 'Docente':
                try:
                    docente = Docente.objects.get(usuario=self.request.user)
                    # Asignaturas que el docente dicta en ese grado específico
                    asignaturas_grado_docente_ids = AsignaturaGradoAñoLectivo.objects.filter(
                        docente=docente,
                        grado_año_lectivo__grado_id=grado_id,
                        grado_año_lectivo__año_lectivo__estado=True
                    ).values_list('asignatura_id', flat=True).distinct()
                    
                    queryset = queryset.filter(id__in=asignaturas_grado_docente_ids)
                    
                except Docente.DoesNotExist:
                    return Asignatura.objects.none()
            else:
                # Para administradores/rectores: todas las asignaturas del grado
                asignaturas_grado_ids = AsignaturaGradoAñoLectivo.objects.filter(
                    grado_año_lectivo__grado_id=grado_id,
                    grado_año_lectivo__año_lectivo__estado=True
                ).values_list('asignatura_id', flat=True).distinct()
                
                queryset = queryset.filter(id__in=asignaturas_grado_ids)
        
        # Ordenar por nombre del nivel escolar, luego área, luego asignatura
        queryset = queryset.annotate(
            orden_nivel=Case(
                When(area__nivel_escolar__nombre='Preescolar', then=Value(1)),
                When(area__nivel_escolar__nombre='Primaria', then=Value(2)),
                default=Value(99),
                output_field=IntegerField()
            )
        ).order_by(
            'orden_nivel',
            'area__nombre',
            'nombre'
        )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Obtener docente si es necesario
            docente = None
            if self.request.user.tipo_usuario.nombre == 'Docente':
                docente = Docente.objects.get(usuario=self.request.user)
            
            # Niveles escolares para filtro (basado en asignaturas visibles)
            queryset = self.get_queryset()
            niveles_ids = queryset.values_list('area__nivel_escolar_id', flat=True).distinct()
            
            context['niveles_escolares'] = NivelEscolar.objects.filter(
                id__in=niveles_ids
            ).annotate(
                orden_personalizado=Case(
                    When(nombre='Preescolar', then=Value(1)),
                    When(nombre='Primaria', then=Value(2)),
                    default=Value(99),
                    output_field=IntegerField()
                )
            ).order_by('orden_personalizado')
            
            # Grados para filtro
            if docente:
                # Para docentes: solo grados donde dicta asignaturas
                grados_ids = AsignaturaGradoAñoLectivo.objects.filter(
                    docente=docente,
                    grado_año_lectivo__año_lectivo__estado=True,
                    asignatura__in=queryset  # Solo asignaturas visibles actualmente
                ).values_list('grado_año_lectivo__grado_id', flat=True).distinct()
            else:
                # Para administradores/rectores: todos los grados con asignaturas
                grados_ids = AsignaturaGradoAñoLectivo.objects.filter(
                    grado_año_lectivo__año_lectivo__estado=True,
                    asignatura__in=queryset
                ).values_list('grado_año_lectivo__grado_id', flat=True).distinct()
            
            # Ordenar grados
            order = {
                'Prejardin': 1, 'Jardin': 2, 'Transicion': 3,
                'Primero': 4, 'Segundo': 5, 'Tercero': 6, 
                'Cuarto': 7, 'Quinto': 8
            }
            
            whens = [When(nombre=nombre, then=Value(order_value)) 
                    for nombre, order_value in order.items()]
            
            context['grados'] = Grado.objects.filter(
                id__in=grados_ids
            ).annotate(
                orden_grado=Case(*whens, default=Value(99), output_field=IntegerField())
            ).order_by('orden_grado')
            
            # Para cada asignatura, obtener los grados donde se dicta
            asignaturas_con_grados = []
            for asignatura in context['asignaturas']:
                if docente:
                    # Para docentes: solo grados donde él dicta esta asignatura
                    grados_asignatura = AsignaturaGradoAñoLectivo.objects.filter(
                        docente=docente,
                        asignatura=asignatura,
                        grado_año_lectivo__año_lectivo__estado=True
                    ).select_related('grado_año_lectivo__grado')
                else:
                    # Para administradores/rectores: todos los grados donde se dicta
                    grados_asignatura = AsignaturaGradoAñoLectivo.objects.filter(
                        asignatura=asignatura,
                        grado_año_lectivo__año_lectivo__estado=True
                    ).select_related('grado_año_lectivo__grado')
                
                asignaturas_con_grados.append({
                    'asignatura': asignatura,
                    'grados': grados_asignatura
                })
            
            context['asignaturas_con_grados'] = asignaturas_con_grados
            
        except Exception as e:
            print(f"Error en get_context_data: {e}")
            context['niveles_escolares'] = NivelEscolar.objects.none()
            context['grados'] = Grado.objects.none()
            context['asignaturas_con_grados'] = []
        
        return context

class HorariosListView(RoleRequiredMixin, TemplateView):
    """Lista de horarios - SIMPLIFICADA"""
    template_name = 'academico/horarios_list.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener año lectivo actual
        año_lectivo_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_lectivo_actual
        
        # Construir queryset base
        queryset = HorarioClase.objects.select_related(
            'asignatura_grado__asignatura',
            'asignatura_grado__grado_año_lectivo__grado',
            'asignatura_grado__sede',
            'asignatura_grado__docente__usuario'
        ).order_by('dia_semana', 'hora_inicio')
        
        # Filtrar por año lectivo actual
        if año_lectivo_actual:
            queryset = queryset.filter(
                asignatura_grado__grado_año_lectivo__año_lectivo=año_lectivo_actual
            )
        
        # Si es docente, filtrar solo sus horarios
        if self.request.user.tipo_usuario.nombre == 'Docente':
            try:
                docente = Docente.objects.get(usuario=self.request.user)
                queryset = queryset.filter(asignatura_grado__docente=docente)
            except Docente.DoesNotExist:
                queryset = queryset.none()
        
        # Organizar por día
        dias_semana = [
            ('LUN', 'Lunes'),
            ('MAR', 'Martes'), 
            ('MIE', 'Miércoles'),
            ('JUE', 'Jueves'),
            ('VIE', 'Viernes')
        ]
        
        horarios_por_dia = {}
        for codigo, nombre in dias_semana:
            horarios_dia = queryset.filter(dia_semana=codigo)
            if horarios_dia.exists():
                horarios_por_dia[nombre] = list(horarios_dia)
        
        context['horarios_por_dia'] = horarios_por_dia
        context['dias_semana'] = dias_semana
        
        return context

class GradosListView(RoleRequiredMixin, ListView):
    """Lista de grados académicos - SIMPLIFICADA"""
    template_name = 'academico/grados_list.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    model = Grado
    context_object_name = 'grados'
    
    def get_queryset(self):
        return Grado.objects.select_related('nivel_escolar').order_by(
            'nivel_escolar__orden',
            'nombre'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener año lectivo actual
        año_lectivo_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_lectivo_actual
        
        # Estudiantes por grado (solo si hay año lectivo)
        if año_lectivo_actual:
            grados_con_estudiantes = []
            for grado in context['grados']:
                estudiantes = Estudiante.objects.filter(
                    grado_actual__grado=grado,
                    grado_actual__año_lectivo=año_lectivo_actual,
                    estado=True
                ).count()
                
                if estudiantes > 0:
                    grados_con_estudiantes.append({
                        'grado': grado,
                        'estudiantes': estudiantes
                    })
            
            context['grados_con_estudiantes'] = grados_con_estudiantes
        
        return context