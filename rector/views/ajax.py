# rector/views/ajax.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import JsonResponse
import json
from datetime import date
from django.utils import timezone
from datetime import timedelta, datetime

from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Avg, Q, Sum, Max, Min
from gestioncolegio.models import AñoLectivo, Sede, ConfiguracionGeneral

from usuarios.models import Usuario, Docente, Usuario
from estudiantes.models import Acudiente, Estudiante, Matricula, Nota
from comportamiento.models import Comportamiento, Asistencia, Inconsistencia
from matricula.models import (PeriodoAcademico, AsignaturaGradoAñoLectivo, Grado,
                                GradoAñoLectivo, DocenteSede, Periodo, Asignatura)
from academico.models import Grado, Asignatura, Area, NivelEscolar, Logro, HorarioClase
from gestioncolegio.mixins import RoleRequiredMixin
from ..forms.formularios_seguimiento import *

# ================== VISTAS AJAX PARA DATOS RÁPIDOS ==================
class GetEstudiantesByGradoView(View):
    """Obtener estudiantes por grado (AJAX)"""
    
    def get(self, request):
        grado_id = request.GET.get('grado_id')
        año_id = request.GET.get('año_id')
        
        estudiantes = []
        
        if grado_id and año_id:
            # Obtener estudiantes matriculados en ese grado y año
            matriculas = Matricula.objects.filter(
                grado_año_lectivo__grado__id=grado_id,
                año_lectivo__id=año_id
            ).select_related(
                'estudiante__usuario',
                'grado_año_lectivo__grado',
                'sede'
            )
            
            estudiantes = [
                {
                    'id': mat.estudiante.id,
                    'nombre': mat.estudiante.usuario.get_full_name(),
                    'documento': mat.estudiante.usuario.numero_documento,
                    'grado': mat.grado_año_lectivo.grado.nombre,
                    'sede': mat.sede.nombre,
                    'estado_matricula': mat.get_estado_display(),
                    'estado_estudiante': 'Activo' if mat.estudiante.estado else 'Inactivo'
                }
                for mat in matriculas
            ]
        
        return JsonResponse({'estudiantes': estudiantes})

class QuitarAsignaturaDocenteAjaxView(RoleRequiredMixin, View):
    """Quitar asignatura de un docente (AJAX)"""
    allowed_roles = ['Rector']
    
    def post(self, request, asignatura_id):
        try:
            asignatura = AsignaturaGradoAñoLectivo.objects.get(id=asignatura_id)
            docente_nombre = asignatura.docente.usuario.get_full_name()
            asignatura_nombre = asignatura.asignatura.nombre
            
            # Quitar asignación
            asignatura.docente = None
            asignatura.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Asignatura "{asignatura_nombre}" quitada del docente "{docente_nombre}"'
            })
        except AsignaturaGradoAñoLectivo.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Asignatura no encontrada'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class QuitarSedeDocenteAjaxView(RoleRequiredMixin, View):
    """Quitar sede de un docente (AJAX)"""
    allowed_roles = ['Rector']
    
    def post(self, request, sede_id):
        try:
            sede_asignada = DocenteSede.objects.get(id=sede_id)
            docente_nombre = sede_asignada.docente.usuario.get_full_name()
            sede_nombre = sede_asignada.sede.nombre
            
            # Desactivar la asignación
            sede_asignada.estado = False
            sede_asignada.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Sede "{sede_nombre}" quitada del docente "{docente_nombre}"'
            })
        except DocenteSede.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Asignación de sede no encontrada'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        
class ToggleDocenteEstadoAjaxView(View):
    """Cambiar estado de docente via AJAX"""
    
    def post(self, request, pk):
        try:
            docente = Docente.objects.get(pk=pk)
            docente.estado = not docente.estado
            docente.save()
            
            return JsonResponse({
                'success': True,
                'nuevo_estado': docente.estado,
                'mensaje': f'Docente {"activado" if docente.estado else "desactivado"} correctamente'
            })
        except Docente.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Docente no encontrado'
            })
        
class GetDocentesBySedeView(View):
    """Obtener docentes por sede (AJAX)"""
    
    def get(self, request):
        sede_id = request.GET.get('sede_id')
        año_id = request.GET.get('año_id')
        
        docentes = []
        
        if sede_id and año_id:
            # Obtener docentes asignados a esa sede en ese año
            asignaciones = DocenteSede.objects.filter(
                sede__id=sede_id,
                año_lectivo__id=año_id,
                estado=True
            ).select_related('docente__usuario')
            
            docentes = [
                {
                    'id': asig.docente.id,
                    'nombre': asig.docente.usuario.get_full_name(),
                    'documento': asig.docente.usuario.numero_documento,
                    'fecha_asignacion': asig.fecha_asignacion.strftime('%d/%m/%Y'),
                    'estado': 'Activo' if asig.docente.estado else 'Inactivo'
                }
                for asig in asignaciones
            ]
        
        return JsonResponse({'docentes': docentes})

class ToggleEstudianteEstadoAjaxView(View):
    """Cambiar estado de estudiante via AJAX"""
    
    def post(self, request, pk):
        try:
            estudiante = Estudiante.objects.get(pk=pk)
            estudiante.estado = not estudiante.estado
            estudiante.save()
            
            return JsonResponse({
                'success': True,
                'nuevo_estado': estudiante.estado,
                'mensaje': f'Estudiante {"activado" if estudiante.estado else "desactivado"} correctamente'
            })
        except Estudiante.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Estudiante no encontrado'
            })

class GetGradosByNivelAñoSedeView(LoginRequiredMixin, View):
    """Obtener grados por nivel, año y sede (AJAX)"""
    
    def get(self, request):
        nivel_id = request.GET.get('nivel')
        año_id = request.GET.get('año')
        sede_id = request.GET.get('sede')
        
        try:
            grados = []
            
            if nivel_id and año_id:
                # Obtener año lectivo
                año_lectivo = AñoLectivo.objects.get(id=año_id)
                
                # Filtrar grados por nivel escolar y año lectivo
                grados_año_lectivo = GradoAñoLectivo.objects.filter(
                    año_lectivo=año_lectivo,
                    grado__nivel_escolar__id=nivel_id,
                    estado=True
                ).select_related('grado', 'grado__nivel_escolar')
                
                # Si hay sede, filtrar también por sede
                # (Asumiendo que hay una relación entre GradoAñoLectivo y Sede)
                # Si no hay relación directa, puedes omitir este filtro
                
                for gal in grados_año_lectivo:
                    grados.append({
                        'id': gal.id,
                        'nombre': gal.grado.nombre,
                        'nivel': gal.grado.nivel_escolar.nombre,
                        'descripcion': f"{gal.grado.nombre} - {gal.grado.nivel_escolar.nombre}"
                    })
                
                return JsonResponse({
                    'success': True,
                    'grados': grados,
                    'total': len(grados)
                })
            
            return JsonResponse({
                'success': False,
                'error': 'Parámetros incompletos',
                'grados': []
            })
            
        except AñoLectivo.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Año lectivo no encontrado',
                'grados': []
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'grados': []
            })
        
#============================para matricula ===================================
class BuscarAcudientesAjaxView(RoleRequiredMixin, View):
    """Buscar acudientes existentes (AJAX)"""
    allowed_roles = ['Rector']
    
    def get(self, request):
        documento = request.GET.get('documento', '').strip()
        nombre = request.GET.get('nombre', '').strip()
        email = request.GET.get('email', '').strip()
        
        # Construir la consulta
        usuarios_qs = Usuario.objects.filter(
            tipo_usuario__nombre='Acudiente'  # Solo usuarios tipo Acudiente
        ).select_related('tipo_usuario', 'tipo_documento')
        
        # Aplicar filtros
        if documento:
            usuarios_qs = usuarios_qs.filter(numero_documento__icontains=documento)
        
        if nombre:
            usuarios_qs = usuarios_qs.filter(
                Q(nombres__icontains=nombre) | Q(apellidos__icontains=nombre)
            )
        
        if email:
            usuarios_qs = usuarios_qs.filter(email__icontains=email)
        
        # Limitar resultados
        usuarios_qs = usuarios_qs[:20]
        
        # Preparar datos para respuesta JSON
        acudientes = []
        for usuario in usuarios_qs:
            # Verificar si ya es acudiente de este estudiante
            estudiante_id = request.GET.get('estudiante_id')
            es_acudiente_actual = False
            
            if estudiante_id:
                es_acudiente_actual = Acudiente.objects.filter(
                    estudiante_id=estudiante_id,
                    acudiente=usuario
                ).exists()
            
            acudientes.append({
                'id': usuario.id,
                'nombre_completo': usuario.get_full_name(),
                'nombres': usuario.nombres,
                'apellidos': usuario.apellidos,
                'tipo_documento': usuario.tipo_documento.nombre if usuario.tipo_documento else '',
                'numero_documento': usuario.numero_documento,
                'email': usuario.email or '',
                'telefono': usuario.telefono or '',
                'direccion': usuario.direccion or '',
                'estudiante_actual': es_acudiente_actual,
                'total_estudiantes': Acudiente.objects.filter(acudiente=usuario).count()
            })
        
        return JsonResponse({
            'success': True,
            'acudientes': acudientes,
            'total': len(acudientes)
        })

class VerificarDocumentoAcudienteAjaxView(RoleRequiredMixin, View):
    """Verificar si un documento ya está registrado como acudiente (AJAX)"""
    allowed_roles = ['Rector']
    
    def get(self, request):
        numero_documento = request.GET.get('numero_documento', '').strip()
        estudiante_id = request.GET.get('estudiante_id')
        
        if not numero_documento:
            return JsonResponse({'error': 'Número de documento requerido'}, status=400)
        
        try:
            # Buscar usuario por documento
            usuario = Usuario.objects.filter(
                numero_documento=numero_documento,
                tipo_usuario__nombre='Acudiente'
            ).first()
            
            if usuario:
                # Verificar si ya es acudiente de este estudiante
                es_acudiente_actual = False
                if estudiante_id:
                    es_acudiente_actual = Acudiente.objects.filter(
                        estudiante_id=estudiante_id,
                        acudiente=usuario
                    ).exists()
                
                # Obtener estudiantes que ya tiene a cargo
                estudiantes_asociados = Acudiente.objects.filter(
                    acudiente=usuario
                ).select_related('estudiante__usuario')[:5]
                
                estudiantes_info = []
                for relacion in estudiantes_asociados:
                    estudiantes_info.append({
                        'id': relacion.estudiante.id,
                        'nombre': relacion.estudiante.usuario.get_full_name(),
                        'parentesco': relacion.parentesco,
                        'documento': relacion.estudiante.usuario.numero_documento
                    })
                
                return JsonResponse({
                    'existe': True,
                    'usuario': {
                        'id': usuario.id,
                        'nombre_completo': usuario.get_full_name(),
                        'nombres': usuario.nombres,
                        'apellidos': usuario.apellidos,
                        'tipo_documento': usuario.tipo_documento.nombre if usuario.tipo_documento else '',
                        'email': usuario.email or '',
                        'telefono': usuario.telefono or '',
                        'direccion': usuario.direccion or '',
                    },
                    'es_acudiente_actual': es_acudiente_actual,
                    'estudiantes_asociados': estudiantes_info,
                    'total_estudiantes': len(estudiantes_info)
                })
            else:
                return JsonResponse({
                    'existe': False,
                    'mensaje': 'Documento no registrado como acudiente'
                })
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

class CrearRelacionAcudienteAjaxView(RoleRequiredMixin, View):
    """Crear relación acudiente-estudiante (AJAX)"""
    allowed_roles = ['Rector']
    
    def post(self, request):
        try:
            data = request.POST
            estudiante_id = data.get('estudiante_id')
            acudiente_id = data.get('acudiente_id')
            parentesco = data.get('parentesco')
            
            if not all([estudiante_id, acudiente_id, parentesco]):
                return JsonResponse({
                    'success': False,
                    'error': 'Todos los campos son requeridos'
                }, status=400)
            
            # Verificar que existan
            estudiante = Estudiante.objects.get(id=estudiante_id)
            acudiente = Usuario.objects.get(id=acudiente_id)
            
            # Verificar que no exista ya la relación
            if Acudiente.objects.filter(estudiante=estudiante, acudiente=acudiente).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Este acudiente ya está asignado al estudiante'
                }, status=400)
            
            # Crear la relación
            relacion = Acudiente.objects.create(
                estudiante=estudiante,
                acudiente=acudiente,
                parentesco=parentesco
            )
            
            return JsonResponse({
                'success': True,
                'relacion_id': relacion.id,
                'mensaje': 'Acudiente asignado exitosamente',
                'acudiente': {
                    'id': acudiente.id,
                    'nombre_completo': acudiente.get_full_name(),
                    'parentesco': parentesco,
                    'documento': acudiente.numero_documento,
                    'telefono': acudiente.telefono or '',
                    'email': acudiente.email or ''
                }
            })
            
        except Estudiante.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Estudiante no encontrado'
            }, status=404)
        except Usuario.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Acudiente no encontrado'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
        
class GetEstadisticasGradoAjaxView(RoleRequiredMixin, View):
    """Obtener estadísticas detalladas de un grado (AJAX)"""
    allowed_roles = ['Rector']
    
    def get(self, request):
        grado_id = request.GET.get('grado_id')
        año_id = request.GET.get('año_id')
        sede_id = request.GET.get('sede_id')
        
        try:
            if not grado_id or not año_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Grado y año lectivo requeridos'
                })
            
            grado = Grado.objects.get(id=grado_id)
            año_lectivo = AñoLectivo.objects.get(id=año_id)
            
            # Construir filtros base
            filters = {
                'grado_año_lectivo__grado': grado,
                'año_lectivo': año_lectivo,
                'estado': 'ACT'
            }
            
            if sede_id and sede_id != 'todos':
                filters['sede__id'] = sede_id
            
            # Estadísticas de estudiantes
            matriculas = Matricula.objects.filter(**filters)
            total_estudiantes = matriculas.count()
            
            # Desglose por sexo
            estudiantes_sexo = matriculas.values(
                'estudiante__usuario__sexo'
            ).annotate(
                total=Count('id')
            )
            
            sexo_counts = {'M': 0, 'F': 0}
            for item in estudiantes_sexo:
                if item['estudiante__usuario__sexo'] in sexo_counts:
                    sexo_counts[item['estudiante__usuario__sexo']] = item['total']
            
            # Estadísticas de notas
            nota_filters = {
                'estudiante__matriculas__grado_año_lectivo__grado': grado,
                'periodo_academico__año_lectivo': año_lectivo
            }
            
            if sede_id and sede_id != 'todos':
                nota_filters['estudiante__matriculas__sede__id'] = sede_id
            
            notas_stats = Nota.objects.filter(**nota_filters).aggregate(
                promedio=Avg('calificacion'),
                maximo=Max('calificacion'),
                minimo=Min('calificacion'),
                total=Count('id')
            )
            
            # Asignaturas del grado en este año
            asignaturas_filters = {
                'grado_año_lectivo__grado': grado,
                'grado_año_lectivo__año_lectivo': año_lectivo
            }
            
            if sede_id and sede_id != 'todos':
                asignaturas_filters['sede__id'] = sede_id
            
            total_asignaturas = AsignaturaGradoAñoLectivo.objects.filter(
                **asignaturas_filters
            ).count()
            
            docentes_asignados = AsignaturaGradoAñoLectivo.objects.filter(
                **asignaturas_filters,
                docente__isnull=False
            ).values('docente').distinct().count()
            
            return JsonResponse({
                'success': True,
                'grado': {
                    'id': grado.id,
                    'nombre': grado.nombre,
                    'nivel': grado.nivel_escolar.nombre
                },
                'año_lectivo': {
                    'id': año_lectivo.id,
                    'nombre': año_lectivo.anho,
                    'sede': año_lectivo.sede.nombre if sede_id == 'todos' else 'Filtrado'
                },
                'estadisticas': {
                    'total_estudiantes': total_estudiantes,
                    'estudiantes_masculinos': sexo_counts['M'],
                    'estudiantes_femeninos': sexo_counts['F'],
                    'promedio_notas': round(notas_stats['promedio'] or 0, 2),
                    'nota_maxima': notas_stats['maximo'] or 0,
                    'nota_minima': notas_stats['minimo'] or 0,
                    'total_notas': notas_stats['total'] or 0,
                    'total_asignaturas': total_asignaturas,
                    'docentes_asignados': docentes_asignados
                }
            })
            
        except Grado.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Grado no encontrado'
            })
        except AñoLectivo.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Año lectivo no encontrado'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        
class ToggleGradoAñoLectivoAjaxView(RoleRequiredMixin, View):
    """Activar/desactivar grado en año lectivo (AJAX)"""
    allowed_roles = ['Rector']
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            grado_año_id = data.get('grado_año_id')
            
            if not grado_año_id:
                return JsonResponse({
                    'success': False,
                    'error': 'ID requerido'
                })
            
            grado_año = GradoAñoLectivo.objects.get(id=grado_año_id)
            grado_año.estado = not grado_año.estado
            grado_año.save()
            
            return JsonResponse({
                'success': True,
                'nuevo_estado': grado_año.estado,
                'mensaje': f'Grado {"activado" if grado_año.estado else "desactivado"} en el año lectivo'
            })
            
        except GradoAñoLectivo.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Relación no encontrada'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        
class ActualizarEstadisticasAjaxView(RoleRequiredMixin, View):
    """Actualizar estadísticas del dashboard (AJAX)"""
    allowed_roles = ['Rector']
    
    def get(self, request):
        try:
            # Obtener año lectivo actual
            año_actual = AñoLectivo.objects.filter(estado=True).first()
            
            # Estadísticas básicas
            total_estudiantes = Estudiante.objects.filter(estado=True).count()
            total_docentes = Docente.objects.filter(estado=True).count()
            
            # Promedio general (simplificado)
            promedio_general = 0
            if año_actual:
                notas = Nota.objects.filter(
                    periodo_academico__año_lectivo=año_actual
                ).aggregate(promedio=Avg('calificacion'))
                promedio_general = round(notas['promedio'] or 0, 1)
            
            # Estudiantes por nivel (si hay año actual)
            estudiantes_por_nivel = []
            if año_actual:
                from academico.models import NivelEscolar
                for nivel in NivelEscolar.objects.all():
                    count = Matricula.objects.filter(
                        grado_año_lectivo__grado__nivel_escolar=nivel,
                        año_lectivo=año_actual,
                        estado='ACT'
                    ).count()
                    estudiantes_por_nivel.append({
                        'nivel': nivel.nombre,
                        'estudiantes': count
                    })
            
            return JsonResponse({
                'success': True,
                'estadisticas': {
                    'total_estudiantes': total_estudiantes,
                    'total_docentes': total_docentes,
                    'promedio_general': promedio_general,
                    'estudiantes_por_nivel': estudiantes_por_nivel
                },
                'timestamp': request.GET.get('timestamp', '')
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        
class GetEstadisticasDashboardAjaxView(RoleRequiredMixin, View):
    """Obtener estadísticas completas para dashboard (AJAX)"""
    allowed_roles = ['Rector']
    
    def get(self, request):
        try:
            año_actual = AñoLectivo.objects.filter(estado=True).first()
            
            if not año_actual:
                return JsonResponse({
                    'success': False,
                    'error': 'No hay año lectivo activo'
                })
            
            # Estadísticas principales
            estadisticas = {
                'total_estudiantes': Matricula.objects.filter(
                    año_lectivo=año_actual,
                    estado='ACT'
                ).count(),
                'total_docentes': Docente.objects.filter(estado=True).count(),
                'grados_activos': GradoAñoLectivo.objects.filter(
                    año_lectivo=año_actual,
                    estado=True
                ).count(),
                'promedio_general': 0  # Se calculará después
            }
            
            # Calcular promedio general
            notas_stats = Nota.objects.filter(
                periodo_academico__año_lectivo=año_actual
            ).aggregate(
                promedio=Avg('calificacion'),
                total=Count('id')
            )
            
            if notas_stats['total'] > 0:
                estadisticas['promedio_general'] = round(notas_stats['promedio'], 1)
            
            # Estudiantes nuevos en el último mes (simplificado)
            from datetime import datetime, timedelta
            from django.utils import timezone
            
            ultimo_mes = timezone.now() - timedelta(days=30)
            estadisticas['estudiantes_nuevos'] = Matricula.objects.filter(
                año_lectivo=año_actual,
                created_at__gte=ultimo_mes,
                estado='ACT'
            ).count()
            
            # Estadísticas por nivel
            from academico.models import NivelEscolar
            niveles_stats = []
            
            for nivel in NivelEscolar.objects.all():
                estudiantes_nivel = Matricula.objects.filter(
                    grado_año_lectivo__grado__nivel_escolar=nivel,
                    año_lectivo=año_actual,
                    estado='ACT'
                ).count()
                
                # Promedio por nivel
                notas_nivel = Nota.objects.filter(
                    estudiante__matriculas__grado_año_lectivo__grado__nivel_escolar=nivel,
                    periodo_academico__año_lectivo=año_actual
                ).aggregate(promedio=Avg('calificacion'))
                
                niveles_stats.append({
                    'id': nivel.id,
                    'nombre': nivel.nombre,
                    'estudiantes': estudiantes_nivel,
                    'promedio': round(notas_nivel['promedio'] or 0, 1),
                    'grados': nivel.grados.count()
                })
            
            # Actividad reciente (últimas 5 matrículas)
            actividades = []
            matriculas_recientes = Matricula.objects.filter(
                año_lectivo=año_actual
            ).select_related(
                'estudiante__usuario',
                'grado_año_lectivo__grado'
            ).order_by('-created_at')[:5]
            
            for matricula in matriculas_recientes:
                actividades.append({
                    'tipo': 'matricula',
                    'titulo': f'Matrícula registrada',
                    'descripcion': f'{matricula.estudiante.usuario.get_full_name()} en {matricula.grado_año_lectivo.grado.nombre}',
                    'fecha': matricula.created_at.strftime('%H:%M'),
                    'icono': 'bi-person-plus'
                })
            
            return JsonResponse({
                'success': True,
                'año_lectivo': {
                    'id': año_actual.id,
                    'nombre': año_actual.anho,
                    'sede': año_actual.sede.nombre
                },
                'estadisticas': estadisticas,
                'niveles': niveles_stats,
                'actividades': actividades
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        
#================== filtrado ajax para asignar asignaturas docentes ==========================
class GetGradosBySedeAñoAjaxView(LoginRequiredMixin, View):
    """Obtener grados por sede y año (AJAX)"""
    
    def get(self, request):
        sede_id = request.GET.get('sede_id')
        año_id = request.GET.get('año_id')
        
        try:
            if sede_id and año_id:
                año_lectivo = AñoLectivo.objects.get(id=año_id)
                
                # Grados que tienen asignaturas o matrículas en esta sede
                grados_disponibles = GradoAñoLectivo.objects.filter(
                    año_lectivo=año_lectivo,
                    estado=True
                ).filter(
                    Q(asignaturas_grado__sede__id=sede_id) |
                    Q(matriculas__sede__id=sede_id)
                ).distinct().select_related('grado', 'grado__nivel_escolar')
                
                grados = []
                for grado_año in grados_disponibles:
                    grados.append({
                        'id': grado_año.grado.id,
                        'nombre': grado_año.grado.nombre,
                        'nivel': grado_año.grado.nivel_escolar.nombre,
                        'descripcion': f"{grado_año.grado.nombre} - {grado_año.grado.nivel_escolar.nombre}"
                    })
                
                return JsonResponse({
                    'success': True,
                    'grados': grados,
                    'total': len(grados)
                })
            
            return JsonResponse({
                'success': False,
                'error': 'Parámetros incompletos',
                'grados': []
            })
            
        except AñoLectivo.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Año lectivo no encontrado',
                'grados': []
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'grados': []
            })

class GetAsignaturasByGradoDocenteAjaxView(LoginRequiredMixin, View):
    """Obtener asignaturas por grado (AJAX)"""
    
    def get(self, request):
        grado_id = request.GET.get('grado_id')
        docente_id = request.GET.get('docente_id')
        
        try:
            if grado_id:
                grado = Grado.objects.get(id=grado_id)
                docente = Docente.objects.get(id=docente_id) if docente_id else None
                
                # Asignaturas del nivel del grado
                asignaturas = Asignatura.objects.filter(
                    area__nivel_escolar=grado.nivel_escolar
                ).select_related('area').order_by('nombre')
                
                # Filtrar asignaturas ya asignadas al docente en el año actual
                año_actual = AñoLectivo.objects.filter(estado=True).first()
                if año_actual and docente:
                    asignaturas_asignadas = AsignaturaGradoAñoLectivo.objects.filter(
                        docente=docente,
                        grado_año_lectivo__grado=grado,
                        grado_año_lectivo__año_lectivo=año_actual
                    ).values_list('asignatura_id', flat=True)
                    
                    # Excluir asignaturas ya asignadas
                    asignaturas = asignaturas.exclude(id__in=asignaturas_asignadas)
                
                asignaturas_list = []
                for asignatura in asignaturas:
                    asignaturas_list.append({
                        'id': asignatura.id,
                        'nombre': asignatura.nombre,
                        'area': asignatura.area.nombre,
                        'nivel': asignatura.area.nivel_escolar.nombre,
                        'ih': asignatura.ih or 'No especificada'
                    })
                
                return JsonResponse({
                    'success': True,
                    'asignaturas': asignaturas_list,
                    'total': len(asignaturas_list)
                })
            
            return JsonResponse({
                'success': False,
                'error': 'Grado requerido',
                'asignaturas': []
            })
            
        except Grado.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Grado no encontrado',
                'asignaturas': []
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'asignaturas': []
            })

class GetGradoInfoAjaxView(LoginRequiredMixin, View):
    """Obtener información de un grado (AJAX)"""
    
    def get(self, request, grado_id):
        try:
            grado = Grado.objects.get(id=grado_id)
            
            return JsonResponse({
                'success': True,
                'grado': {
                    'id': grado.id,
                    'nombre': grado.nombre,
                    'nivel': grado.nivel_escolar.nombre,
                    'descripcion': f"{grado.nombre} - {grado.nivel_escolar.nombre}"
                }
            })
            
        except Grado.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Grado no encontrado'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        
#================== Ajax para areas y asignaturas ==========================
class GetAreaInfoAjaxView(RoleRequiredMixin, View):
    """Obtener información de un área (AJAX)"""
    allowed_roles = ['Rector']
    
    def get(self, request):
        area_id = request.GET.get('area_id')
        
        try:
            area = Area.objects.get(id=area_id)
            
            return JsonResponse({
                'success': True,
                'area': {
                    'id': area.id,
                    'nombre': area.nombre,
                    'nivel': area.nivel_escolar.nombre,
                    'total_asignaturas': area.asignaturas.count(),
                    'total_grados': area.nivel_escolar.grados.count()
                }
            })
        except Area.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Área no encontrada'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        
class CheckAsignaturaAjaxView(RoleRequiredMixin, View):
    """Verificar si una asignatura ya existe (AJAX)"""
    allowed_roles = ['Rector']
    
    def get(self, request):
        nombre = request.GET.get('nombre')
        area_id = request.GET.get('area_id')
        asignatura_id = request.GET.get('asignatura_id')
        
        try:
            if nombre and area_id:
                # Buscar asignaturas con el mismo nombre en la misma área
                qs = Asignatura.objects.filter(
                    nombre__iexact=nombre,
                    area_id=area_id
                )
                
                if asignatura_id:
                    qs = qs.exclude(id=asignatura_id)
                
                if qs.exists():
                    return JsonResponse({
                        'exists': True,
                        'message': f'Ya existe una asignatura con el nombre "{nombre}" en esta área'
                    })
                
                return JsonResponse({
                    'exists': False,
                    'message': 'Nombre disponible'
                })
            
            return JsonResponse({
                'success': False,
                'error': 'Parámetros incompletos'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class GetGradoInfoAjaxView(RoleRequiredMixin, View):
    """Obtener información de un grado (AJAX)"""
    allowed_roles = ['Rector']
    
    def get(self, request, grado_id):
        try:
            grado = Grado.objects.get(id=grado_id)
            
            # Contar áreas del nivel
            total_areas = Area.objects.filter(nivel_escolar=grado.nivel_escolar).count()
            
            # Contar asignaturas del nivel
            total_asignaturas = Asignatura.objects.filter(
                area__nivel_escolar=grado.nivel_escolar
            ).count()
            
            return JsonResponse({
                'success': True,
                'grado': {
                    'id': grado.id,
                    'nombre': grado.nombre,
                    'nivel': grado.nivel_escolar.nombre,
                    'total_areas': total_areas,
                    'total_asignaturas': total_asignaturas
                }
            })
        except Grado.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Grado no encontrado'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class GetAsignaturasByGradoAjaxView(RoleRequiredMixin, View):
    """Obtener asignaturas por grado (AJAX)"""
    allowed_roles = ['Rector']
    
    def get(self, request):
        grado_id = request.GET.get('grado_id')
        
        try:
            if not grado_id:
                return JsonResponse({
                    'success': False,
                    'error': 'ID de grado requerido',
                    'asignaturas': []
                })
            
            grado = Grado.objects.get(id=grado_id)
            
            # Obtener asignaturas del nivel del grado
            asignaturas = Asignatura.objects.filter(
                area__nivel_escolar=grado.nivel_escolar
            ).select_related('area').order_by('nombre')
            
            asignaturas_list = []
            for asignatura in asignaturas:
                asignaturas_list.append({
                    'id': asignatura.id,
                    'nombre': asignatura.nombre,
                    'area': asignatura.area.nombre,
                    'ih': asignatura.ih or 'No especificada'
                })
            
            return JsonResponse({
                'success': True,
                'asignaturas': asignaturas_list,
                'total': len(asignaturas_list)
            })
            
        except Grado.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Grado no encontrado',
                'asignaturas': []
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'asignaturas': []
            })
        
#================== Ajax GESTION INSTITUCIONAL ==========================
class GetAñosLectivosBySedeAjaxView(RoleRequiredMixin, View):
    """Obtener años lectivos por sede (AJAX)"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        sede_id = request.GET.get('sede_id')
        
        if not sede_id:
            return JsonResponse({'success': False, 'error': 'No se proporcionó sede_id'})
        
        try:
            años_lectivos = AñoLectivo.objects.filter(
                sede_id=sede_id,
                estado=True
            ).order_by('-anho').values('id', 'anho', 'fecha_inicio', 'fecha_fin')
            
            return JsonResponse({
                'success': True,
                'años_lectivos': list(años_lectivos)
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class GetPeriodosByAñoLectivoAjaxView(RoleRequiredMixin, View):
    """Obtener periodos académicos por año lectivo (AJAX)"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        año_lectivo_id = request.GET.get('año_lectivo_id')
        
        if not año_lectivo_id:
            return JsonResponse({'success': False, 'error': 'No se proporcionó año_lectivo_id'})
        
        try:
            periodos = PeriodoAcademico.objects.filter(
                año_lectivo_id=año_lectivo_id
            ).select_related('periodo').order_by('fecha_inicio').values(
                'id', 
                'periodo__nombre',
                'fecha_inicio',
                'fecha_fin',
                'estado'
            )
            
            # Calcular estado actual de cada periodo
            hoy = date.today()
            periodos_data = []
            for periodo in periodos:
                periodo_dict = dict(periodo)
                periodo_dict['periodo_nombre'] = periodo_dict.pop('periodo__nombre')
                
                # Determinar estado
                fecha_inicio = periodo_dict['fecha_inicio']
                fecha_fin = periodo_dict['fecha_fin']
                
                if fecha_fin < hoy:
                    estado_actual = 'finalizado'
                elif fecha_inicio <= hoy <= fecha_fin:
                    estado_actual = 'en_curso'
                else:
                    estado_actual = 'pendiente'
                
                periodo_dict['estado_actual'] = estado_actual
                periodos_data.append(periodo_dict)
            
            return JsonResponse({
                'success': True,
                'periodos': periodos_data
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class GetEstadisticasInstitucionalesAjaxView(RoleRequiredMixin, View):
    """Obtener estadísticas institucionales en tiempo real (AJAX)"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        try:
            # Estadísticas generales
            total_sedes = Sede.objects.filter(estado=True).count()
            total_años_lectivos = AñoLectivo.objects.filter(estado=True).count()
            
            # Obtener año lectivo actual
            config = ConfiguracionGeneral.objects.first()
            año_actual = config.año_lectivo_actual if config else None
            
            if año_actual:
                total_estudiantes = Matricula.objects.filter(
                    año_lectivo=año_actual,
                    estado='ACT'
                ).count()
                
                # CORRECCIÓN: Usar values() con distinct()
                total_docentes_asignados = DocenteSede.objects.filter(
                    año_lectivo=año_actual,
                    estado=True
                ).values('docente').distinct().count()
                
                periodos_configurados = PeriodoAcademico.objects.filter(
                    año_lectivo=año_actual
                ).count()
                
                asignaturas_sin_docente = AsignaturaGradoAñoLectivo.objects.filter(
                    grado_año_lectivo__año_lectivo=año_actual,
                    docente__isnull=True
                ).count()
            else:
                total_estudiantes = 0
                total_docentes_asignados = 0
                periodos_configurados = 0
                asignaturas_sin_docente = 0
            
            return JsonResponse({
                'success': True,
                'estadisticas': {
                    'total_sedes': total_sedes,
                    'total_años_lectivos': total_años_lectivos,
                    'total_estudiantes': total_estudiantes,
                    'total_docentes_asignados': total_docentes_asignados,
                    'periodos_configurados': periodos_configurados,
                    'asignaturas_sin_docente': asignaturas_sin_docente,
                    'año_actual': año_actual.anho if año_actual else None
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class CheckPeriodoSolapamientoAjaxView(RoleRequiredMixin, View):
    """Verificar si hay solapamiento de fechas en periodos (AJAX)"""
    allowed_roles = ['Rector']
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            
            año_lectivo_id = data.get('año_lectivo_id')
            fecha_inicio = data.get('fecha_inicio')
            fecha_fin = data.get('fecha_fin')
            periodo_id = data.get('periodo_id')  # Para edición, excluir el actual
            
            if not all([año_lectivo_id, fecha_inicio, fecha_fin]):
                return JsonResponse({'success': False, 'error': 'Faltan parámetros'})
            
            # Convertir fechas
            from datetime import datetime
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            
            # Buscar periodos que se solapen
            periodos_solapados = PeriodoAcademico.objects.filter(
                año_lectivo_id=año_lectivo_id
            ).filter(
                Q(fecha_inicio__lte=fecha_fin_dt) & Q(fecha_fin__gte=fecha_inicio_dt)
            )
            
            # Excluir el periodo actual si se está editando
            if periodo_id:
                periodos_solapados = periodos_solapados.exclude(id=periodo_id)
            
            if periodos_solapados.exists():
                periodos_info = []
                for periodo in periodos_solapados:
                    periodos_info.append({
                        'nombre': periodo.periodo.nombre,
                        'fecha_inicio': periodo.fecha_inicio.strftime('%d/%m/%Y'),
                        'fecha_fin': periodo.fecha_fin.strftime('%d/%m/%Y')
                    })
                
                return JsonResponse({
                    'success': True,
                    'hay_solapamiento': True,
                    'periodos_solapados': periodos_info
                })
            else:
                return JsonResponse({
                    'success': True,
                    'hay_solapamiento': False
                })
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class GetAsignaturasSinDocenteAjaxView(RoleRequiredMixin, View):
    """Obtener asignaturas sin docente asignado (AJAX)"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        try:
            año_lectivo_id = request.GET.get('año_lectivo_id')
            sede_id = request.GET.get('sede_id')
            
            queryset = AsignaturaGradoAñoLectivo.objects.filter(
                docente__isnull=True
            ).select_related(
                'asignatura',
                'grado_año_lectivo__grado',
                'sede'
            )
            
            if año_lectivo_id:
                queryset = queryset.filter(grado_año_lectivo__año_lectivo_id=año_lectivo_id)
            
            if sede_id:
                queryset = queryset.filter(sede_id=sede_id)
            
            asignaturas = []
            for asignatura in queryset[:20]:  # Limitar a 20 resultados
                asignaturas.append({
                    'id': asignatura.id,
                    'nombre': asignatura.asignatura.nombre,
                    'grado': asignatura.grado_año_lectivo.grado.nombre,
                    'sede': asignatura.sede.nombre,
                    'año_lectivo': asignatura.grado_año_lectivo.año_lectivo.anho
                })
            
            return JsonResponse({
                'success': True,
                'asignaturas': asignaturas,
                'total': queryset.count()
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class ToggleAñoLectivoEstadoAjaxView(RoleRequiredMixin, View):
    """Activar/desactivar año lectivo (AJAX)"""
    allowed_roles = ['Rector']
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            año_lectivo_id = data.get('año_lectivo_id')
            
            if not año_lectivo_id:
                return JsonResponse({'success': False, 'error': 'No se proporcionó año_lectivo_id'})
            
            año_lectivo = AñoLectivo.objects.get(id=año_lectivo_id)
            
            # Cambiar estado
            año_lectivo.estado = not año_lectivo.estado
            año_lectivo.save()
            
            # Si se activa, desactivar otros años lectivos de la misma sede
            if año_lectivo.estado:
                AñoLectivo.objects.filter(
                    sede=año_lectivo.sede,
                    colegio=año_lectivo.colegio
                ).exclude(id=año_lectivo.id).update(estado=False)
            
            return JsonResponse({
                'success': True,
                'nuevo_estado': año_lectivo.estado,
                'mensaje': f'Año lectivo {año_lectivo.anho} {"activado" if año_lectivo.estado else "desactivado"}'
            })
        except AñoLectivo.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Año lectivo no encontrado'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class TogglePeriodoEstadoAjaxView(RoleRequiredMixin, View):
    """Activar/desactivar periodo académico (AJAX)"""
    allowed_roles = ['Rector']
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            periodo_id = data.get('periodo_id')
            
            if not periodo_id:
                return JsonResponse({'success': False, 'error': 'No se proporcionó periodo_id'})
            
            periodo = PeriodoAcademico.objects.get(id=periodo_id)
            
            # Cambiar estado
            periodo.estado = not periodo.estado
            periodo.save()
            
            return JsonResponse({
                'success': True,
                'nuevo_estado': periodo.estado,
                'mensaje': f'Periodo {periodo.periodo.nombre} {"activado" if periodo.estado else "desactivado"}'
            })
        except PeriodoAcademico.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Periodo no encontrado'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class GetSedeInfoAjaxView(RoleRequiredMixin, View):
    """Obtener información detallada de una sede (AJAX)"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        sede_id = request.GET.get('sede_id')
        
        if not sede_id:
            return JsonResponse({'success': False, 'error': 'No se proporcionó sede_id'})
        
        try:
            sede = Sede.objects.get(id=sede_id)
            
            # Obtener estadísticas
            año_actual = AñoLectivo.objects.filter(
                sede=sede,
                estado=True
            ).first()
            
            datos = {
                'id': sede.id,
                'nombre': sede.nombre,
                'direccion': sede.direccion,
                'telefono': sede.telefono or 'No especificado',
                'email': sede.email or 'No especificado',
                'director': sede.director.get_full_name() if sede.director else 'No asignado',
                'estado': sede.estado,
                'colegio': sede.colegio.nombre
            }
            
            if año_actual:
                total_estudiantes = Matricula.objects.filter(
                    sede=sede,
                    año_lectivo=año_actual,
                    estado='ACT'
                ).count()
                
                # CORRECCIÓN: Usar values() con distinct()
                total_docentes = DocenteSede.objects.filter(
                    sede=sede,
                    año_lectivo=año_actual,
                    estado=True
                ).values('docente').distinct().count()
                
                datos.update({
                    'año_actual': año_actual.anho,
                    'total_estudiantes': total_estudiantes,
                    'total_docentes': total_docentes,
                    'fecha_inicio': año_actual.fecha_inicio.strftime('%d/%m/%Y') if año_actual.fecha_inicio else None,
                    'fecha_fin': año_actual.fecha_fin.strftime('%d/%m/%Y') if año_actual.fecha_fin else None
                })
            
            return JsonResponse({
                'success': True,
                'sede': datos
            })
        except Sede.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Sede no encontrada'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class GetDashboardStatsAjaxView(RoleRequiredMixin, View):
    """Obtener estadísticas para el dashboard (AJAX)"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        try:
            from gestioncolegio.models import Colegio
            
            # Colegio
            colegio = Colegio.objects.filter(estado=True).first()
            
            # Configuración general
            config = ConfiguracionGeneral.objects.filter(colegio=colegio).first()
            año_actual = config.año_lectivo_actual if config else None
            
            stats = {
                'colegio_nombre': colegio.nombre if colegio else 'No configurado',
                'año_lectivo_actual': año_actual.anho if año_actual else 'No configurado',
                'sede_actual': año_actual.sede.nombre if año_actual else 'No configurado',
            }
            
            if año_actual:
                # Estudiantes matriculados
                total_estudiantes = Matricula.objects.filter(
                    año_lectivo=año_actual,
                    estado='ACT'
                ).count()
                stats['total_estudiantes'] = total_estudiantes
                
                # Docentes activos
                total_docentes = Docente.objects.filter(estado=True).count()
                stats['total_docentes'] = total_docentes
                
                # Sedes activas
                sedes_activas = Sede.objects.filter(estado=True).count()
                stats['sedes_activas'] = sedes_activas
                
                # Grados activos
                grados_activos = GradoAñoLectivo.objects.filter(
                    año_lectivo=año_actual,
                    estado=True
                ).count()
                stats['grados_activos'] = grados_activos
                
                # Periodos configurados
                periodos_configurados = PeriodoAcademico.objects.filter(
                    año_lectivo=año_actual
                ).count()
                stats['periodos_configurados'] = periodos_configurados
                
                # Asignaturas sin docente
                asignaturas_sin_docente = AsignaturaGradoAñoLectivo.objects.filter(
                    grado_año_lectivo__año_lectivo=año_actual,
                    docente__isnull=True
                ).count()
                stats['asignaturas_sin_docente'] = asignaturas_sin_docente
                
                # Docentes sin asignaturas - CORRECCIÓN
                docentes_con_asignaturas_ids = Docente.objects.filter(
                    asignaturas_dictadas__grado_año_lectivo__año_lectivo=año_actual
                ).values_list('id', flat=True).distinct()
                
                docentes_sin_asignaturas = Docente.objects.filter(
                    estado=True
                ).exclude(
                    id__in=docentes_con_asignaturas_ids
                ).count()
                
                stats['docentes_sin_asignaturas'] = docentes_sin_asignaturas
                
                # Porcentajes
                if total_docentes > 0:
                    stats['porcentaje_asignaturas'] = (len(docentes_con_asignaturas_ids) / total_docentes) * 100
                else:
                    stats['porcentaje_asignaturas'] = 0
                
                # Docentes con sede - CORRECCIÓN
                docentes_con_sede_ids = Docente.objects.filter(
                    sedes_asignadas__año_lectivo=año_actual,
                    sedes_asignadas__estado=True
                ).values_list('id', flat=True).distinct()
                
                stats['docentes_con_sede'] = len(docentes_con_sede_ids)
                
                if total_docentes > 0:
                    stats['porcentaje_sede'] = (len(docentes_con_sede_ids) / total_docentes) * 100
                else:
                    stats['porcentaje_sede'] = 0
            
            return JsonResponse({
                'success': True,
                'stats': stats
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
        
#================== Ajax para matriculas ==========================
class GetGradosByAñoSedeNivelAjaxView(RoleRequiredMixin, View):
    """Obtener grados filtrados por año, sede y nivel (AJAX)"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        año_lectivo_id = request.GET.get('año')
        sede_id = request.GET.get('sede')
        nivel_id = request.GET.get('nivel')
        
        if not all([año_lectivo_id, sede_id, nivel_id]):
            return JsonResponse({
                'success': False,
                'error': 'Faltan parámetros'
            })
        
        try:
            # Filtrar grados
            grados = GradoAñoLectivo.objects.filter(
                año_lectivo_id=año_lectivo_id,
                estado=True
            ).filter(
                Q(matriculas__sede_id=sede_id) |
                Q(asignaturas_grado__sede_id=sede_id)
            ).filter(
                grado__nivel_escolar_id=nivel_id
            ).select_related('grado', 'grado__nivel_escolar').distinct()
            
            grados_list = []
            for grado in grados:
                grados_list.append({
                    'id': grado.id,
                    'nombre': f"{grado.grado.nombre} ({grado.grado.nivel_escolar.nombre})",
                    'grado_nombre': grado.grado.nombre,
                    'nivel': grado.grado.nivel_escolar.nombre,
                    'estado': grado.estado
                })
            
            return JsonResponse({
                'success': True,
                'grados': grados_list
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        
# ========== AJAX PARA SEGUIMIENTO ==========

class GetEstadisticasSeguimientoAjaxView(RoleRequiredMixin, View):
    """Obtener estadísticas de seguimiento actualizadas"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        try:
            periodo_id = request.GET.get('periodo_id')
            grado_id = request.GET.get('grado_id')
            
            # Filtros base
            filtros = {}
            if periodo_id:
                filtros['periodo_academico_id'] = periodo_id
            
            estadisticas = {}
            
            # Comportamientos
            comportamientos = Comportamiento.objects.filter(**filtros)
            estadisticas['total_comportamientos'] = comportamientos.count()
            estadisticas['comportamientos_positivos'] = comportamientos.filter(tipo='Positivo').count()
            estadisticas['comportamientos_negativos'] = comportamientos.filter(tipo='Negativo').count()
            
            # Asistencias
            asistencias = Asistencia.objects.filter(**filtros)
            if asistencias.exists():
                estadisticas['total_asistencias'] = asistencias.count()
                estadisticas['asistencias_asistio'] = asistencias.filter(estado='A').count()
                estadisticas['asistencias_falto'] = asistencias.filter(estado='F').count()
                estadisticas['asistencias_justificadas'] = asistencias.filter(estado='J').count()
                
                estadisticas['porcentaje_asistencia'] = (
                    estadisticas['asistencias_asistio'] / estadisticas['total_asistencias'] * 100
                    if estadisticas['total_asistencias'] > 0 else 0
                )
            
            # Inconsistencias (últimos 30 días)
            fecha_limite = timezone.now() - timedelta(days=30)
            inconsistencias = Inconsistencia.objects.filter(
                fecha__gte=fecha_limite
            )
            estadisticas['inconsistencias_recientes'] = inconsistencias.count()
            
            # Calificaciones
            if periodo_id:
                calificaciones = Nota.objects.filter(periodo_academico_id=periodo_id)
                if calificaciones.exists():
                    promedios = calificaciones.aggregate(
                        promedio=Avg('calificacion'),
                        maximo=Max('calificacion'),
                        minimo=Min('calificacion')
                    )
                    estadisticas['promedio_calificaciones'] = promedios['promedio'] or 0
                    estadisticas['maxima_calificacion'] = promedios['maximo'] or 0
                    estadisticas['minima_calificacion'] = promedios['minimo'] or 0
            
            return JsonResponse({
                'success': True,
                'estadisticas': estadisticas
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class GetEstudiantesPorGradoAjaxView(RoleRequiredMixin, View):
    """Obtener estudiantes activos por grado"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        try:
            grado_id = request.GET.get('grado_id')
            
            if not grado_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Se requiere ID de grado'
                })
            
            # Obtener estudiantes matriculados en el grado
            matriculas = Matricula.objects.filter(
                grado_año_lectivo_id=grado_id,
                estado='ACT'
            ).select_related('estudiante__usuario')
            
            estudiantes = []
            for matricula in matriculas:
                estudiante = matricula.estudiante
                estudiantes.append({
                    'id': estudiante.id,
                    'nombre_completo': estudiante.usuario.get_full_name(),
                    'documento': estudiante.usuario.numero_documento,
                    'estado': estudiante.estado
                })
            
            return JsonResponse({
                'success': True,
                'estudiantes': estudiantes,
                'total': len(estudiantes)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class GetAsistenciasEstudianteAjaxView(RoleRequiredMixin, View):
    """Obtener historial de asistencias de un estudiante"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        try:
            estudiante_id = request.GET.get('estudiante_id')
            fecha_inicio = request.GET.get('fecha_inicio')
            fecha_fin = request.GET.get('fecha_fin')
            
            if not estudiante_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Se requiere ID de estudiante'
                })
            
            # Construir filtros
            filtros = {'estudiante_id': estudiante_id}
            
            if fecha_inicio:
                filtros['fecha__gte'] = fecha_inicio
            if fecha_fin:
                filtros['fecha__lte'] = fecha_fin
            
            # Obtener asistencias
            asistencias = Asistencia.objects.filter(**filtros).select_related(
                'periodo_academico__año_lectivo'
            ).order_by('-fecha')[:50]  # Limitar a 50 registros
            
            asistencias_data = []
            for asistencia in asistencias:
                asistencias_data.append({
                    'fecha': asistencia.fecha.strftime('%Y-%m-%d'),
                    'estado': asistencia.get_estado_display(),
                    'justificacion': asistencia.justificacion or '',
                    'periodo': asistencia.periodo_academico.periodo.nombre,
                    'año': asistencia.periodo_academico.año_lectivo.anho
                })
            
            # Calcular estadísticas
            total = asistencias.count()
            asistio = asistencias.filter(estado='A').count()
            falto = asistencias.filter(estado='F').count()
            justificada = asistencias.filter(estado='J').count()
            
            estadisticas = {
                'total': total,
                'asistio': asistio,
                'falto': falto,
                'justificada': justificada,
                'porcentaje_asistencia': (asistio / total * 100) if total > 0 else 0
            }
            
            return JsonResponse({
                'success': True,
                'asistencias': asistencias_data,
                'estadisticas': estadisticas
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class GetCalificacionesEstudianteAjaxView(RoleRequiredMixin, View):
    """Obtener historial de calificaciones de un estudiante"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        try:
            estudiante_id = request.GET.get('estudiante_id')
            periodo_id = request.GET.get('periodo_id')
            
            if not estudiante_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Se requiere ID de estudiante'
                })
            
            # Construir filtros
            filtros = {'estudiante_id': estudiante_id}
            
            if periodo_id:
                filtros['periodo_academico_id'] = periodo_id
            
            # Obtener calificaciones
            calificaciones = Nota.objects.filter(**filtros).select_related(
                'asignatura_grado_año_lectivo__asignatura',
                'periodo_academico__año_lectivo',
                'periodo_academico__periodo'
            ).order_by('-periodo_academico__fecha_inicio')
            
            calificaciones_data = []
            for calificacion in calificaciones:
                calificaciones_data.append({
                    'asignatura': calificacion.asignatura_grado_año_lectivo.asignatura.nombre,
                    'calificacion': float(calificacion.calificacion),
                    'observaciones': calificacion.observaciones or '',
                    'periodo': calificacion.periodo_academico.periodo.nombre,
                    'año': calificacion.periodo_academico.año_lectivo.anho
                })
            
            # Calcular estadísticas
            if calificaciones.exists():
                promedios = calificaciones.aggregate(
                    promedio=Avg('calificacion'),
                    maximo=Max('calificacion'),
                    minimo=Min('calificacion')
                )
                
                estadisticas = {
                    'total': calificaciones.count(),
                    'promedio': promedios['promedio'] or 0,
                    'maximo': promedios['maximo'] or 0,
                    'minimo': promedios['minimo'] or 0
                }
            else:
                estadisticas = {
                    'total': 0,
                    'promedio': 0,
                    'maximo': 0,
                    'minimo': 0
                }
            
            return JsonResponse({
                'success': True,
                'calificaciones': calificaciones_data,
                'estadisticas': estadisticas
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class GetComportamientosEstudianteAjaxView(RoleRequiredMixin, View):
    """Obtener historial de comportamientos de un estudiante"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        try:
            estudiante_id = request.GET.get('estudiante_id')
            periodo_id = request.GET.get('periodo_id')
            tipo = request.GET.get('tipo')
            
            if not estudiante_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Se requiere ID de estudiante'
                })
            
            # Construir filtros
            filtros = {'estudiante_id': estudiante_id}
            
            if periodo_id:
                filtros['periodo_academico_id'] = periodo_id
            if tipo:
                filtros['tipo'] = tipo
            
            # Obtener comportamientos
            comportamientos = Comportamiento.objects.filter(**filtros).select_related(
                'periodo_academico__año_lectivo',
                'docente__usuario'
            ).order_by('-fecha')[:50]
            
            comportamientos_data = []
            for comportamiento in comportamientos:
                comportamientos_data.append({
                    'fecha': comportamiento.fecha.strftime('%Y-%m-%d'),
                    'tipo': comportamiento.get_tipo_display(),
                    'categoria': comportamiento.get_categoria_display(),
                    'descripcion': comportamiento.descripcion,
                    'periodo': comportamiento.periodo_academico.periodo.nombre,
                    'año': comportamiento.periodo_academico.año_lectivo.anho,
                    'docente': comportamiento.docente.usuario.get_full_name() if comportamiento.docente else 'Sistema'
                })
            
            # Calcular estadísticas
            total = comportamientos.count()
            positivos = comportamientos.filter(tipo='Positivo').count()
            negativos = comportamientos.filter(tipo='Negativo').count()
            
            estadisticas = {
                'total': total,
                'positivos': positivos,
                'negativos': negativos,
                'balance': positivos - negativos
            }
            
            # Distribución por categoría
            categorias = comportamientos.values('categoria').annotate(
                total=Count('id')
            ).order_by('categoria')
            
            return JsonResponse({
                'success': True,
                'comportamientos': comportamientos_data,
                'estadisticas': estadisticas,
                'categorias': list(categorias)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class GetInconsistenciasEstudianteAjaxView(RoleRequiredMixin, View):
    """Obtener historial de inconsistencias de un estudiante"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        try:
            estudiante_id = request.GET.get('estudiante_id')
            fecha_inicio = request.GET.get('fecha_inicio')
            fecha_fin = request.GET.get('fecha_fin')
            
            if not estudiante_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Se requiere ID de estudiante'
                })
            
            # Construir filtros
            filtros = {'estudiante_id': estudiante_id}
            
            if fecha_inicio:
                filtros['fecha__gte'] = fecha_inicio
            if fecha_fin:
                filtros['fecha__lte'] = fecha_fin
            
            # Obtener inconsistencias
            inconsistencias = Inconsistencia.objects.filter(**filtros).order_by('-fecha')
            
            inconsistencias_data = []
            for inconsistencia in inconsistencias:
                inconsistencias_data.append({
                    'fecha': inconsistencia.fecha.strftime('%Y-%m-%d'),
                    'tipo': inconsistencia.tipo,
                    'descripcion': inconsistencia.descripcion
                })
            
            # Calcular estadísticas
            total = inconsistencias.count()
            
            # Tipos más comunes
            tipos = inconsistencias.values('tipo').annotate(
                total=Count('id')
            ).order_by('-total')[:5]
            
            return JsonResponse({
                'success': True,
                'inconsistencias': inconsistencias_data,
                'estadisticas': {
                    'total': total
                },
                'tipos': list(tipos)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class ExportarReporteSeguimientoAjaxView(RoleRequiredMixin, View):
    """Exportar reporte de seguimiento en diferentes formatos"""
    allowed_roles = ['Rector']
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            tipo_reporte = data.get('tipo_reporte')
            formato = data.get('formato', 'pdf')
            filtros = data.get('filtros', {})
            
            # Aquí implementarías la lógica de exportación
            # Por ahora devolvemos un ejemplo
            return JsonResponse({
                'success': True,
                'message': f'Reporte {tipo_reporte} generado en formato {formato}',
                'url': '/media/reportes/reporte_temporal.pdf'  # URL temporal
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

# ===========INCONSISTENCIAS ===========
class AjaxEstadisticasInconsistenciasView(RoleRequiredMixin, View):
    """Obtener estadísticas de inconsistencias en tiempo real"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            hoy = timezone.now().date()
            fecha_limite = hoy - timedelta(days=30)
            
            estadisticas = {
                'ultimos_30_dias': Inconsistencia.objects.filter(
                    fecha__gte=fecha_limite
                ).count(),
                'tipos_unicos': Inconsistencia.objects.values('tipo').distinct().count(),
                'resueltas': Inconsistencia.objects.filter(estado='resuelta').count(),
            }
            
            return JsonResponse({
                'success': True,
                'estadisticas': estadisticas
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class AjaxEliminarInconsistenciasView(RoleRequiredMixin, View):
    """Eliminar múltiples inconsistencias"""
    allowed_roles = ['Rector']
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            
            if not ids:
                return JsonResponse({
                    'success': False,
                    'error': 'No se especificaron IDs'
                })
            
            # Verificar permisos y eliminar
            deleted_count = Inconsistencia.objects.filter(
                id__in=ids
            ).delete()[0]
            
            return JsonResponse({
                'success': True,
                'message': f'{deleted_count} inconsistencia(s) eliminada(s)',
                'deleted_count': deleted_count
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class AjaxMarcarInconsistenciasResueltasView(RoleRequiredMixin, View):
    """Marcar múltiples inconsistencias como resueltas"""
    allowed_roles = ['Rector']
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            
            if not ids:
                return JsonResponse({
                    'success': False,
                    'error': 'No se especificaron IDs'
                })
            
            # Actualizar estado
            updated_count = Inconsistencia.objects.filter(
                id__in=ids
            ).update(
                estado='resuelta',
                fecha_resolucion=timezone.now().date()
            )
            
            return JsonResponse({
                'success': True,
                'message': f'{updated_count} inconsistencia(s) marcada(s) como resueltas',
                'updated_count': updated_count
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class AjaxImportarInconsistenciasView(RoleRequiredMixin, View):
    """Importar inconsistencias desde Excel"""
    allowed_roles = ['Rector']
    
    def post(self, request, *args, **kwargs):
        try:
            import pandas as pd
            from io import BytesIO
            
            archivo = request.FILES.get('archivo_excel')
            if not archivo:
                return JsonResponse({
                    'success': False,
                    'error': 'No se envió archivo'
                })
            
            # Leer archivo Excel
            df = pd.read_excel(BytesIO(archivo.read()))
            
            # Validar columnas requeridas
            columnas_requeridas = ['estudiante_id', 'tipo', 'descripcion']
            for col in columnas_requeridas:
                if col not in df.columns:
                    return JsonResponse({
                        'success': False,
                        'error': f'Falta columna requerida: {col}'
                    })
            
            # Procesar filas
            importados = 0
            errores = []
            
            for index, row in df.iterrows():
                try:
                    # Buscar estudiante
                    estudiante = Estudiante.objects.get(id=row['estudiante_id'])
                    
                    # Crear inconsistencia
                    Inconsistencia.objects.create(
                        estudiante=estudiante,
                        tipo=row['tipo'],
                        descripcion=row['descripcion'],
                        fecha=timezone.now().date()
                    )
                    
                    importados += 1
                    
                except Estudiante.DoesNotExist:
                    errores.append(f"Fila {index + 2}: Estudiante ID {row['estudiante_id']} no encontrado")
                except Exception as e:
                    errores.append(f"Fila {index + 2}: {str(e)}")
            
            return JsonResponse({
                'success': True,
                'importados': importados,
                'errores': errores,
                'total_errores': len(errores)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class AjaxTiposInconsistenciasView(RoleRequiredMixin, View):
    """Obtener lista de tipos de inconsistencias únicos"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        try:
            tipos = Inconsistencia.objects.values_list('tipo', flat=True).distinct().order_by('tipo')
            
            return JsonResponse({
                'success': True,
                'tipos': list(tipos)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class AjaxTiposComunesInconsistenciasView(RoleRequiredMixin, View):
    """Obtener tipos más comunes de inconsistencias"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        try:
            tipos_comunes = Inconsistencia.objects.values('tipo').annotate(
                frecuencia=Count('id')
            ).order_by('-frecuencia')[:10]
            
            return JsonResponse({
                'success': True,
                'tipos': list(tipos_comunes)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class AjaxInformacionEstudianteView(RoleRequiredMixin, View):
    """Obtener información básica de un estudiante"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        try:
            estudiante_id = request.GET.get('estudiante_id')
            if not estudiante_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Se requiere ID de estudiante'
                })
            
            estudiante = Estudiante.objects.get(id=estudiante_id)
            
            data = {
                'id': estudiante.id,
                'nombre_completo': estudiante.usuario.get_full_name(),
                'documento': estudiante.usuario.numero_documento,
                'edad': estudiante.usuario.edad if estudiante.usuario.fecha_nacimiento else None,
                'estado': estudiante.estado,
                'grado_actual': estudiante.grado_actual.grado.nombre if estudiante.grado_actual else None,
                'sede': estudiante.sede_actual.nombre if estudiante.sede_actual else None,
            }
            
            return JsonResponse({
                'success': True,
                'estudiante': data
            })
            
        except Estudiante.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Estudiante no encontrado'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class AjaxHistorialInconsistenciasEstudianteView(RoleRequiredMixin, View):
    """Obtener historial de inconsistencias de un estudiante"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        try:
            estudiante_id = request.GET.get('estudiante_id')
            if not estudiante_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Se requiere ID de estudiante'
                })
            
            inconsistencias = Inconsistencia.objects.filter(
                estudiante_id=estudiante_id
            ).order_by('-fecha')[:10]
            
            data = []
            for inc in inconsistencias:
                data.append({
                    'id': inc.id,
                    'tipo': inc.tipo,
                    'descripcion': inc.descripcion[:100] + '...' if len(inc.descripcion) > 100 else inc.descripcion,
                    'fecha': inc.fecha.strftime('%d/%m/%Y'),
                    'estado': inc.estado if hasattr(inc, 'estado') else 'registrada'
                })
            
            return JsonResponse({
                'success': True,
                'inconsistencias': data
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class AjaxEstadisticasEstudianteView(RoleRequiredMixin, View):
    """Obtener estadísticas de un estudiante"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        try:
            estudiante_id = request.GET.get('estudiante_id')
            if not estudiante_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Se requiere ID de estudiante'
                })
            
            estudiante = Estudiante.objects.get(id=estudiante_id)
            hoy = timezone.now().date()
            inicio_mes = date(hoy.year, hoy.month, 1)
            
            estadisticas = {
                'total_inconsistencias': Inconsistencia.objects.filter(
                    estudiante=estudiante
                ).count(),
                'comportamientos_positivos': Comportamiento.objects.filter(
                    estudiante=estudiante,
                    tipo='Positivo',
                    fecha__gte=inicio_mes
                ).count(),
                'comportamientos_negativos': Comportamiento.objects.filter(
                    estudiante=estudiante,
                    tipo='Negativo',
                    fecha__gte=inicio_mes
                ).count(),
                'porcentaje_asistencia': 0,
                'promedio_calificaciones': 0
            }
            
            # Calcular porcentaje de asistencia
            asistencias = Asistencia.objects.filter(
                estudiante=estudiante,
                fecha__gte=inicio_mes,
                fecha__lte=hoy
            )
            
            if asistencias.exists():
                asistio = asistencias.filter(estado='A').count()
                estadisticas['porcentaje_asistencia'] = (asistio / asistencias.count()) * 100
            
            # Calcular promedio de calificaciones
            notas = Nota.objects.filter(
                estudiante=estudiante
            ).aggregate(promedio=Avg('calificacion'))
            
            if notas['promedio']:
                estadisticas['promedio_calificaciones'] = float(notas['promedio'])
            
            return JsonResponse({
                'success': True,
                'estadisticas': estadisticas
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class AjaxMarcarInconsistenciaResueltaView(RoleRequiredMixin, View):
    """Marcar una inconsistencia como resuelta"""
    allowed_roles = ['Rector']
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            inconsistencia_id = data.get('inconsistencia_id')
            
            if not inconsistencia_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Se requiere ID de inconsistencia'
                })
            
            inconsistencia = Inconsistencia.objects.get(id=inconsistencia_id)
            inconsistencia.estado = 'resuelta'
            inconsistencia.fecha_resolucion = timezone.now().date()
            inconsistencia.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Inconsistencia marcada como resuelta'
            })
            
        except Inconsistencia.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Inconsistencia no encontrada'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class AjaxMarcarInconsistenciaPendienteView(RoleRequiredMixin, View):
    """Marcar una inconsistencia como pendiente"""
    allowed_roles = ['Rector']
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            inconsistencia_id = data.get('inconsistencia_id')
            
            if not inconsistencia_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Se requiere ID de inconsistencia'
                })
            
            inconsistencia = Inconsistencia.objects.get(id=inconsistencia_id)
            inconsistencia.estado = 'pendiente'
            inconsistencia.fecha_resolucion = None
            inconsistencia.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Inconsistencia marcada como pendiente'
            })
            
        except Inconsistencia.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Inconsistencia no encontrada'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class AjaxCompartirInconsistenciaView(RoleRequiredMixin, View):
    """Compartir una inconsistencia por correo"""
    allowed_roles = ['Rector']
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            inconsistencia_id = data.get('inconsistencia_id')
            email = data.get('email')
            mensaje = data.get('mensaje', '')
            incluir_datos_estudiante = data.get('incluir_datos_estudiante', False)
            
            if not inconsistencia_id or not email:
                return JsonResponse({
                    'success': False,
                    'error': 'Se requiere ID de inconsistencia y correo electrónico'
                })
            
            # Aquí implementarías el envío de correo
            # Por ahora solo simulamos el éxito
            
            # Ejemplo de implementación real:
            # from django.core.mail import send_mail
            # send_mail(
            #     subject='Inconsistencia Académica',
            #     message=f'...',
            #     from_email='noreply@colegio.com',
            #     recipient_list=[email]
            # )
            
            return JsonResponse({
                'success': True,
                'message': 'Inconsistencia compartida exitosamente'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class AjaxBuscarEstudiantesView(RoleRequiredMixin, View):
    """Buscar estudiantes para autocompletado"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        try:
            query = request.GET.get('q', '').strip()
            
            if not query or len(query) < 2:
                return JsonResponse({
                    'results': [],
                    'pagination': {'more': False}
                })
            
            # Buscar estudiantes por nombre, apellido o documento
            estudiantes = Estudiante.objects.filter(
                Q(usuario__nombres__icontains=query) |
                Q(usuario__apellidos__icontains=query) |
                Q(usuario__numero_documento__icontains=query),
                estado=True
            ).select_related('usuario')[:20]
            
            results = []
            for estudiante in estudiantes:
                results.append({
                    'id': estudiante.id,
                    'text': f"{estudiante.usuario.get_full_name()} ({estudiante.usuario.numero_documento})"
                })
            
            return JsonResponse({
                'results': results,
                'pagination': {'more': False}
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

class AjaxBuscarEstudiantesActivosView(RoleRequiredMixin, View):
    """Buscar estudiantes activos para formularios"""
    allowed_roles = ['Rector']
    
    def get(self, request, *args, **kwargs):
        try:
            query = request.GET.get('q', '').strip()
            page = int(request.GET.get('page', 1))
            page_size = 20
            
            if not query or len(query) < 2:
                return JsonResponse({
                    'estudiantes': [],
                    'total': 0,
                    'has_more': False
                })
            
            # Buscar estudiantes activos
            estudiantes_qs = Estudiante.objects.filter(
                Q(usuario__nombres__icontains=query) |
                Q(usuario__apellidos__icontains=query) |
                Q(usuario__numero_documento__icontains=query),
                estado=True
            ).select_related('usuario')
            
            total = estudiantes_qs.count()
            
            # Paginación
            start = (page - 1) * page_size
            end = start + page_size
            estudiantes = estudiantes_qs[start:end]
            
            estudiantes_data = []
            for estudiante in estudiantes:
                estudiantes_data.append({
                    'id': estudiante.id,
                    'nombre_completo': estudiante.usuario.get_full_name(),
                    'documento': estudiante.usuario.numero_documento,
                    'grado': estudiante.grado_actual.grado.nombre if estudiante.grado_actual else 'Sin grado',
                    'sede': estudiante.sede_actual.nombre if estudiante.sede_actual else 'Sin sede'
                })
            
            return JsonResponse({
                'success': True,
                'estudiantes': estudiantes_data,
                'total': total,
                'has_more': end < total,
                'page': page
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        
#============= Ajax asistencias ==================
class AsistenciaDetailView(RoleRequiredMixin, DetailView):
    """Detalle de asistencia"""
    template_name = 'rector/seguimiento/asistencia/asistencia_detail.html'
    allowed_roles = ['Rector']
    model = Asistencia
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asistencia = self.object
        
        # Obtener historial de asistencias del estudiante
        historial = Asistencia.objects.filter(
            estudiante=asistencia.estudiante
        ).exclude(id=asistencia.id).select_related(
            'periodo_academico__año_lectivo',
            'periodo_academico__periodo'
        ).order_by('-fecha')[:10]
        
        context['historial_asistencias'] = historial
        
        # Calcular estadísticas del estudiante para el periodo actual
        periodo = asistencia.periodo_academico
        if periodo:
            # Asistencias en este periodo
            asistencias_periodo = Asistencia.objects.filter(
                estudiante=asistencia.estudiante,
                periodo_academico=periodo
            )
            
            total_asistencias = asistencias_periodo.count()
            if total_asistencias > 0:
                asistio_count = asistencias_periodo.filter(estado='A').count()
                falto_count = asistencias_periodo.filter(estado='F').count()
                justificada_count = asistencias_periodo.filter(estado='J').count()
                
                context['estadisticas_periodo'] = {
                    'total': total_asistencias,
                    'asistio': asistio_count,
                    'falto': falto_count,
                    'justificada': justificada_count,
                    'porcentaje_asistencia': (asistio_count / total_asistencias) * 100
                }
            
            # Obtener días del mes actual para estadísticas
            hoy = date.today()
            inicio_mes = date(hoy.year, hoy.month, 1)
            
            asistencias_mes = Asistencia.objects.filter(
                estudiante=asistencia.estudiante,
                fecha__gte=inicio_mes,
                fecha__lte=hoy
            )
            
            total_mes = asistencias_mes.count()
            if total_mes > 0:
                asistio_mes = asistencias_mes.filter(estado='A').count()
                context['porcentaje_asistencia_mes'] = (asistio_mes / total_mes) * 100
                context['total_asistencias_mes'] = total_mes
        
        # Obtener información de matrícula actual
        matricula_actual = asistencia.estudiante.matricula_actual
        if matricula_actual:
            context['matricula_actual'] = matricula_actual
            context['grado_actual'] = matricula_actual.grado_año_lectivo.grado
        
        return context


class AsistenciaUpdateView(RoleRequiredMixin, UpdateView):
    """Editar registro de asistencia"""
    template_name = 'rector/seguimiento/asistencia/asistencia_form.html'
    allowed_roles = ['Rector']
    model = Asistencia
    form_class = AsistenciaForm
    success_url = reverse_lazy('rector:asistencia_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Asistencia actualizada exitosamente.')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Asistencia'
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Establecer el estudiante como inicial si viene de la lista
        if 'estudiante' in self.request.GET:
            estudiante_id = self.request.GET.get('estudiante')
            if estudiante_id:
                kwargs['initial'] = {'estudiante': estudiante_id}
        return kwargs


# ==================== AJAX PARA ASISTENCIA ====================

class AjaxAsistenciaDetalleView(RoleRequiredMixin, View):
    """Obtener detalles de asistencia para modal AJAX"""
    allowed_roles = ['Rector']
    
    def get(self, request, asistencia_id):
        try:
            asistencia = Asistencia.objects.select_related(
                'estudiante__usuario',
                'periodo_academico__año_lectivo',
                'periodo_academico__periodo'
            ).get(id=asistencia_id)
            
            # Obtener información del estudiante
            matricula_actual = asistencia.estudiante.matricula_actual
            
            # Preparar datos para JSON
            data = {
                'id': asistencia.id,
                'estudiante_nombre': asistencia.estudiante.usuario.get_full_name(),
                'estudiante_documento': asistencia.estudiante.usuario.numero_documento,
                'fecha': asistencia.fecha.strftime('%d/%m/%Y'),
                'creado': asistencia.created_at.strftime('%d/%m/%Y %H:%M'),
                'actualizado': asistencia.updated_at.strftime('%d/%m/%Y %H:%M'),
                'periodo_nombre': asistencia.periodo_academico.periodo.nombre,
                'anho': asistencia.periodo_academico.año_lectivo.anho,
                'estado': asistencia.get_estado_display(),
                'estado_html': self.get_estado_html(asistencia.estado),
                'justificacion': asistencia.justificacion,
                'grado_actual': matricula_actual.grado_año_lectivo.grado.nombre if matricula_actual else None,
                'sede_actual': matricula_actual.sede.nombre if matricula_actual else None,
            }
            
            return JsonResponse({
                'success': True,
                'asistencia': data
            })
            
        except Asistencia.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Asistencia no encontrada'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    def get_estado_html(self, estado):
        if estado == 'A':
            return '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Asistió</span>'
        elif estado == 'F':
            return '<span class="badge bg-danger"><i class="bi bi-x-circle me-1"></i>Faltó</span>'
        else:
            return '<span class="badge bg-warning"><i class="bi bi-clock me-1"></i>Justificada</span>'


class AjaxActualizarAsistenciaIndividualView(RoleRequiredMixin, View):
    """Actualizar asistencia individual vía AJAX (para edición rápida)"""
    allowed_roles = ['Rector']
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            asistencia_id = data.get('asistencia_id')
            estado = data.get('estado')
            justificacion = data.get('justificacion', '')
            
            if not asistencia_id or not estado:
                return JsonResponse({
                    'success': False,
                    'error': 'Faltan datos requeridos'
                })
            
            asistencia = Asistencia.objects.get(id=asistencia_id)
            
            # Validar estado
            if estado not in ['A', 'F', 'J']:
                return JsonResponse({
                    'success': False,
                    'error': 'Estado inválido'
                })
            
            # Actualizar asistencia
            asistencia.estado = estado
            asistencia.justificacion = justificacion if estado == 'J' else ''
            asistencia.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Asistencia actualizada exitosamente',
                'estado_display': asistencia.get_estado_display(),
                'estado_html': self.get_estado_html(estado)
            })
            
        except Asistencia.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Asistencia no encontrada'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    def get_estado_html(self, estado):
        if estado == 'A':
            return '<span class="badge bg-success">Asistió</span>'
        elif estado == 'F':
            return '<span class="badge bg-danger">Faltó</span>'
        else:
            return '<span class="badge bg-warning">Justificada</span>'


class AjaxObtenerEstadisticasAsistenciaView(RoleRequiredMixin, View):
    """Obtener estadísticas de asistencia para dashboard AJAX"""
    allowed_roles = ['Rector']
    
    def get(self, request):
        try:
            estudiante_id = request.GET.get('estudiante_id')
            periodo_id = request.GET.get('periodo_id')
            fecha_inicio = request.GET.get('fecha_inicio')
            fecha_fin = request.GET.get('fecha_fin')
            
            # Construir filtros
            filtros = {}
            if estudiante_id:
                filtros['estudiante_id'] = estudiante_id
            if periodo_id:
                filtros['periodo_academico_id'] = periodo_id
            if fecha_inicio:
                filtros['fecha__gte'] = fecha_inicio
            if fecha_fin:
                filtros['fecha__lte'] = fecha_fin
            
            # Obtener asistencias
            asistencias = Asistencia.objects.filter(**filtros)
            total = asistencias.count()
            
            # Calcular estadísticas
            asistio = asistencias.filter(estado='A').count()
            falto = asistencias.filter(estado='F').count()
            justificada = asistencias.filter(estado='J').count()
            
            estadisticas = {
                'total': total,
                'asistio': asistio,
                'falto': falto,
                'justificada': justificada,
                'porcentaje_asistencia': (asistio / total * 100) if total > 0 else 0,
                'porcentaje_faltas': (falto / total * 100) if total > 0 else 0,
                'porcentaje_justificada': (justificada / total * 100) if total > 0 else 0
            }
            
            # Distribución por día de la semana
            distribucion_dias = asistencias.values(
                'fecha__week_day'
            ).annotate(
                total=Count('id'),
                asistio=Count('id', filter=Q(estado='A')),
                falto=Count('id', filter=Q(estado='F')),
                justificada=Count('id', filter=Q(estado='J'))
            ).order_by('fecha__week_day')
            
            # Mapear números de día a nombres
            dias_semana = {
                1: 'Lunes',
                2: 'Martes',
                3: 'Miércoles',
                4: 'Jueves',
                5: 'Viernes',
                6: 'Sábado',
                7: 'Domingo'
            }
            
            distribucion = []
            for item in distribucion_dias:
                dia_num = item['fecha__week_day']
                distribucion.append({
                    'dia': dias_semana.get(dia_num, f'Día {dia_num}'),
                    'total': item['total'],
                    'asistio': item['asistio'],
                    'falto': item['falto'],
                    'justificada': item['justificada']
                })
            
            return JsonResponse({
                'success': True,
                'estadisticas': estadisticas,
                'distribucion_dias': distribucion,
                'filtros': {
                    'estudiante_id': estudiante_id,
                    'periodo_id': periodo_id,
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })