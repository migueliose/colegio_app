"""
Vistas AJAX corregidas - SIN USAR distinct(field)
"""
import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.template.loader import render_to_string
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from datetime import datetime, timedelta
from django.utils import timezone

# Modelos básicos
from estudiantes.models import Estudiante, Nota
from usuarios.models import Docente
from matricula.models import AsignaturaGradoAñoLectivo, PeriodoAcademico, GradoAñoLectivo
from comportamiento.models import Comportamiento, Asistencia
from academico.models import Asignatura
from gestioncolegio.models import AñoLectivo
from docentes.mixins import DocenteRequiredMixin, DocenteBaseView, DocenteContextMixin
from .comportamiento import get_docente_usuario

@require_GET
@login_required
def obtener_asignaturas_docente(request):
    """Obtiene las asignaturas que enseña el docente por grado - CORREGIDO"""
    grado_id = request.GET.get('grado_id')
    if not grado_id:
        return JsonResponse({'error': 'grado_id requerido'}, status=400)
    
    try:
        docente = Docente.objects.get(usuario=request.user)
        
        # Obtener IDs de asignaturas únicas
        asignaturas_ids = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__grado_id=grado_id,
            grado_año_lectivo__año_lectivo__estado=True
        ).values_list('asignatura_id', flat=True).distinct()
        
        # Obtener las asignaturas completas
        asignaturas = Asignatura.objects.filter(id__in=asignaturas_ids).order_by('nombre')
        
        asignaturas_data = [
            {
                'id': asignatura.id,
                'nombre': asignatura.nombre
            }
            for asignatura in asignaturas
        ]
        
        return JsonResponse({'asignaturas': asignaturas_data})
        
    except Docente.DoesNotExist:
        return JsonResponse({'error': 'No es docente'}, status=403)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_GET
@login_required
def obtener_periodos_docente(request):
    """Obtiene los períodos académicos disponibles"""
    try:
        periodos = PeriodoAcademico.objects.filter(
            año_lectivo__estado=True,
            estado=True
        ).select_related('periodo', 'año_lectivo').order_by('fecha_inicio')
        
        periodos_data = [
            {
                'id': periodo.id,
                'nombre': f"{periodo.periodo.nombre} - {periodo.año_lectivo.anho}"
            }
            for periodo in periodos
        ]
        
        return JsonResponse({'periodos': periodos_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_GET
@login_required
def obtener_notas_estudiantes(request):
    """Obtiene estudiantes y sus notas para calificar - CORREGIDO"""
    grado_id = request.GET.get('grado_id')
    asignatura_id = request.GET.get('asignatura_id')
    periodo_id = request.GET.get('periodo_id')
    
    if not all([grado_id, asignatura_id, periodo_id]):
        return JsonResponse({'error': 'Faltan parámetros'}, status=400)
    
    try:
        # Verificar que el usuario sea docente
        docente = Docente.objects.get(usuario=request.user)
        
        # Verificar que el docente enseña esta asignatura en este grado
        asignatura_grado = get_object_or_404(
            AsignaturaGradoAñoLectivo,
            docente=docente,
            grado_año_lectivo__grado_id=grado_id,
            asignatura_id=asignatura_id,
            grado_año_lectivo__año_lectivo__estado=True
        )
        
        # Obtener año lectivo actual
        from gestioncolegio.models import AñoLectivo
        año_lectivo_actual = AñoLectivo.objects.filter(estado=True).first()
        if not año_lectivo_actual:
            return JsonResponse({'error': 'No hay año lectivo activo'}, status=400)
        
        # Obtener estudiantes matriculados en el grado en el año actual
        from estudiantes.models import Matricula
        estudiantes_ids = Matricula.objects.filter(
            grado_año_lectivo__grado_id=grado_id,
            año_lectivo=año_lectivo_actual,
            estado__in=['ACT', 'PEN', 'INA', 'RET', 'OTRO']
        ).values_list('estudiante_id', flat=True).distinct()
        
        estudiantes = Estudiante.objects.filter(
            id__in=estudiantes_ids,
            #estado=True
        ).select_related('usuario')
        
        estudiantes_data = []
        for estudiante in estudiantes:
            # Buscar nota existente
            nota = Nota.objects.filter(
                estudiante=estudiante,
                asignatura_grado_año_lectivo=asignatura_grado,
                periodo_academico_id=periodo_id
            ).first()
            
            estudiantes_data.append({
                'estudiante': estudiante,
                'calificacion': nota.calificacion if nota else None,
                'observaciones': nota.observaciones if nota else ''
            })
        
        # Contexto para el template
        context = {
            'estudiantes_data': estudiantes_data,
            'grado_seleccionado': asignatura_grado.grado_año_lectivo.grado,
            'asignatura_seleccionada': asignatura_grado.asignatura,
            'periodo_seleccionado': get_object_or_404(PeriodoAcademico, id=periodo_id)
        }
        
        html = render_to_string(
            'docentes/notas/lista_estudiantes_calificar.html',
            context,
            request=request
        )
        
        return HttpResponse(html)
        
    except Docente.DoesNotExist:
        return JsonResponse({'error': 'No es docente'}, status=403)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
@login_required
def guardar_notas(request):
    """Guarda las calificaciones de estudiantes"""
    try:
        # Obtener datos del formulario
        grado_id = request.POST.get('grado_id')
        asignatura_id = request.POST.get('asignatura_id')
        periodo_id = request.POST.get('periodo_id')
        
        if not all([grado_id, asignatura_id, periodo_id]):
            return JsonResponse({'error': 'Datos incompletos'}, status=400)
        
        # Verificar que el usuario sea docente
        docente = Docente.objects.get(usuario=request.user)
        
        # Verificar que el docente enseña esta asignatura
        asignatura_grado = get_object_or_404(
            AsignaturaGradoAñoLectivo,
            docente=docente,
            grado_año_lectivo__grado_id=grado_id,
            asignatura_id=asignatura_id
        )
        
        periodo = get_object_or_404(PeriodoAcademico, id=periodo_id)
        
        # Procesar cada estudiante
        estudiantes_actualizados = 0
        estudiantes_nuevos = 0
        
        for key, value in request.POST.items():
            if key.startswith('nota_'):
                estudiante_id = key.replace('nota_', '')
                calificacion = value.strip()
                
                if calificacion:  # Solo procesar si hay calificación
                    estudiante = get_object_or_404(Estudiante, id=estudiante_id)
                    
                    nota, created = Nota.objects.update_or_create(
                        estudiante=estudiante,
                        asignatura_grado_año_lectivo=asignatura_grado,
                        periodo_academico=periodo,
                        defaults={
                            'calificacion': calificacion,
                            'observaciones': request.POST.get(f'observacion_{estudiante_id}', '').strip()
                        }
                    )
                    
                    if created:
                        estudiantes_nuevos += 1
                    else:
                        estudiantes_actualizados += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Calificaciones guardadas: {estudiantes_nuevos} nuevas, {estudiantes_actualizados} actualizadas',
            'nuevas': estudiantes_nuevos,
            'actualizadas': estudiantes_actualizados
        })
        
    except Docente.DoesNotExist:
        return JsonResponse({'error': 'No es docente'}, status=403)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_GET
@login_required
def obtener_asignaturas_logros(request):
    """Obtiene asignaturas por grado para formulario de logros - CORREGIDO"""
    grado_id = request.GET.get('grado_id')
    if not grado_id:
        return JsonResponse({'error': 'grado_id requerido'}, status=400)
    
    try:
        docente = Docente.objects.get(usuario=request.user)
        
        # Obtener IDs de asignaturas únicas
        asignaturas_ids = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__grado_id=grado_id,
            grado_año_lectivo__año_lectivo__estado=True
        ).values_list('asignatura_id', flat=True).distinct()
        
        # Obtener las asignaturas completas con sus áreas
        asignaturas = Asignatura.objects.filter(
            id__in=asignaturas_ids
        ).select_related('area').order_by('nombre')
        
        asignaturas_data = [
            {
                'id': asignatura.id,
                'nombre': asignatura.nombre,
                'area': asignatura.area.nombre if asignatura.area else 'Sin área'
            }
            for asignatura in asignaturas
        ]
        
        return JsonResponse({
            'success': True,
            'asignaturas': asignaturas_data
        })
        
    except Docente.DoesNotExist:
        return JsonResponse({'error': 'No es docente'}, status=403)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_GET
@login_required
def obtener_asignaturas_por_grado(request):
    """Obtiene asignaturas por grado - CORREGIDO"""
    grado_id = request.GET.get('grado_id')
    if not grado_id:
        return JsonResponse({'error': 'grado_id requerido'}, status=400)
    
    try:
        # Si es docente, filtrar sus asignaturas
        asignaturas_query = AsignaturaGradoAñoLectivo.objects.filter(
            grado_año_lectivo__grado_id=grado_id,
            grado_año_lectivo__año_lectivo__estado=True
        )
        
        if hasattr(request.user, 'docente_profile'):
            docente = request.user.docente_profile
            asignaturas_query = asignaturas_query.filter(docente=docente)
        
        # Obtener asignaturas únicas sin usar distinct(field)
        asignaturas_ids = asignaturas_query.values_list('asignatura_id', flat=True).distinct()
        
        asignaturas = Asignatura.objects.filter(id__in=asignaturas_ids).order_by('nombre')
        
        data = []
        for asignatura in asignaturas:
            data.append({
                'id': asignatura.id,
                'nombre': asignatura.nombre
            })
        
        return JsonResponse({'asignaturas': data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_GET
@login_required
def obtener_estudiantes_por_grado(request):
    """Obtiene estudiantes por grado - CORREGIDO"""
    grado_id = request.GET.get('grado_id')
    if not grado_id:
        return JsonResponse({'error': 'grado_id requerido'}, status=400)
    
    try:
        from estudiantes.models import Matricula
        from gestioncolegio.models import AñoLectivo
        
        # Obtener año lectivo actual
        año_lectivo_actual = AñoLectivo.objects.filter(estado=True).first()
        if not año_lectivo_actual:
            return JsonResponse({'error': 'No hay año lectivo activo'}, status=400)
        
        # Obtener estudiantes matriculados en el grado en el año actual
        estudiantes_ids = Matricula.objects.filter(
            grado_año_lectivo__grado_id=grado_id,
            año_lectivo=año_lectivo_actual,
            estado__in=['ACT', 'PEN', 'INA', 'RET', 'OTRO'] 
        ).values_list('estudiante_id', flat=True).distinct()
        
        estudiantes = Estudiante.objects.filter(
            id__in=estudiantes_ids,
            #estado=True
        ).select_related('usuario')
        
        data = []
        for estudiante in estudiantes:
            data.append({
                'id': estudiante.id,
                'nombre': f"{estudiante.usuario.nombres} {estudiante.usuario.apellidos}",
                'documento': estudiante.usuario.numero_documento or ''
            })
        
        return JsonResponse({'estudiantes': data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
@login_required
def guardar_nota_individual(request):
    """Guarda una nota individual"""
    try:
        data = json.loads(request.body)
        
        estudiante_id = data.get('estudiante_id')
        asignatura_id = data.get('asignatura_id')
        periodo_id = data.get('periodo_id')
        calificacion = data.get('calificacion')
        
        # Validaciones básicas
        if not all([estudiante_id, asignatura_id, periodo_id, calificacion]):
            return JsonResponse({'error': 'Datos incompletos'}, status=400)
        
        # Buscar asignatura-grado
        asignatura_grado = get_object_or_404(
            AsignaturaGradoAñoLectivo,
            asignatura_id=asignatura_id,
            grado_año_lectivo__año_lectivo__estado=True
        )
        
        # Verificar permisos si es docente
        if hasattr(request.user, 'docente_profile'):
            docente = request.user.docente_profile
            if asignatura_grado.docente != docente:
                return JsonResponse({'error': 'Sin permisos'}, status=403)
        
        # Crear o actualizar nota
        nota, created = Nota.objects.update_or_create(
            estudiante_id=estudiante_id,
            asignatura_grado_año_lectivo=asignatura_grado,
            periodo_academico_id=periodo_id,
            defaults={'calificacion': calificacion}
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Nota guardada',
            'created': created,
            'nota_id': nota.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

class AjaxObtenerAsignaturasPorGradoView(LoginRequiredMixin, DocenteRequiredMixin, DocenteContextMixin, View):
    """Vista AJAX para obtener asignaturas por grado"""
    
    def get(self, request):
        grado_id = request.GET.get('grado_id')
        docente = self.get_docente()
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        if not grado_id or not año_actual or not docente:
            return JsonResponse({'asignaturas': [], 'error': 'Datos incompletos'})
        
        # Corregido: Usar distinct() sin argumento 'on'
        asignaturas_docente = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__grado_id=grado_id,
            grado_año_lectivo__año_lectivo=año_actual
        ).select_related('asignatura').distinct()
        
        # Procesar para eliminar duplicados en Python
        asignaturas_unicas = {}
        for a in asignaturas_docente:
            if a.asignatura.id not in asignaturas_unicas:
                asignaturas_unicas[a.asignatura.id] = {
                    'id': a.asignatura.id, 
                    'nombre': a.asignatura.nombre
                }
        
        asignaturas = list(asignaturas_unicas.values())
        
        return JsonResponse({'asignaturas': asignaturas})

class AjaxObtenerPeriodosView(LoginRequiredMixin, DocenteRequiredMixin, DocenteBaseView, View):
    """Vista AJAX para obtener periodos"""
    
    def get(self, request):
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        if not año_actual:
            return JsonResponse({'periodos': [], 'error': 'No hay año lectivo activo'})
        
        periodos = PeriodoAcademico.objects.filter(
            año_lectivo=año_actual,
            estado=True
        ).select_related('periodo')
        
        periodos_list = [
            {'id': p.id, 'nombre': p.periodo.nombre}
            for p in periodos
        ]
        
        return JsonResponse({'periodos': periodos_list})
    
# =============================================
# VISTAS AJAX PARA COMPORTAMIENTO
# =============================================

class AjaxObtenerEstudiantesPorPeriodoView(LoginRequiredMixin, DocenteRequiredMixin, View):
    """Vista AJAX para obtener estudiantes por periodo y docente"""
    
    def get(self, request):
        periodo_id = request.GET.get('periodo_id')
        docente = get_docente_usuario(request.user)
        
        if not periodo_id or not docente:
            return JsonResponse({'estudiantes': [], 'success': False})
        
        try:
            # Obtener el periodo
            periodo = PeriodoAcademico.objects.filter(id=periodo_id).first()
            if not periodo:
                return JsonResponse({'estudiantes': [], 'success': False})
            
            # Obtener grados asignados al docente en el año del periodo
            grados_docente = AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente,
                grado_año_lectivo__año_lectivo=periodo.año_lectivo
            ).values_list('grado_año_lectivo__grado_id', flat=True).distinct()
            
            if not grados_docente:
                return JsonResponse({'estudiantes': [], 'success': False})
            
            # Obtener estudiantes matriculados en esos grados
            estudiantes = Estudiante.objects.filter(
                matriculas__grado_año_lectivo__grado_id__in=grados_docente,
                matriculas__año_lectivo=periodo.año_lectivo,
                matriculas__estado__in=['ACT', 'PEN']
            ).distinct().select_related('usuario')
            
            estudiantes_list = [
                {
                    'id': e.id,
                    'nombre_completo': e.usuario.get_full_name() if e.usuario else '',
                    'documento': e.usuario.numero_documento if e.usuario else '',
                    'grado': e.grado_actual.grado.nombre if e.grado_actual else ''
                }
                for e in estudiantes
            ]
            
            return JsonResponse({
                'estudiantes': estudiantes_list,
                'success': True,
                'total': len(estudiantes_list)
            })
            
        except Exception as e:
            return JsonResponse({
                'estudiantes': [],
                'success': False,
                'error': str(e)
            })


class AjaxResumenComportamientoEstudianteView(LoginRequiredMixin, DocenteRequiredMixin, View):
    """Vista AJAX para obtener resumen de comportamiento de un estudiante"""
    
    def get(self, request):
        estudiante_id = request.GET.get('estudiante_id')
        periodo_id = request.GET.get('periodo_id')
        
        if not estudiante_id:
            return JsonResponse({'success': False, 'error': 'No se especificó estudiante'})
        
        try:
            estudiante = Estudiante.objects.get(id=estudiante_id)
            
            # Filtrar por periodo si está especificado
            filtro = {'estudiante': estudiante}
            if periodo_id:
                filtro['periodo_academico_id'] = periodo_id
            
            # Obtener estadísticas
            comportamientos = Comportamiento.objects.filter(**filtro)
            
            total_positivos = comportamientos.filter(tipo='Positivo').count()
            total_negativos = comportamientos.filter(tipo='Negativo').count()
            total = total_positivos + total_negativos
            
            # Obtener últimos 5 registros
            ultimos = comportamientos.select_related(
                'periodo_academico__periodo', 'docente__usuario'
            ).order_by('-fecha')[:5]
            
            ultimos_list = [
                {
                    'fecha': c.fecha.strftime('%d/%m/%Y'),
                    'tipo': c.tipo,
                    'categoria': c.categoria,
                    'descripcion': c.descripcion[:50] + '...' if len(c.descripcion) > 50 else c.descripcion,
                    'periodo': c.periodo_academico.periodo.nombre if c.periodo_academico else ''
                }
                for c in ultimos
            ]
            
            return JsonResponse({
                'success': True,
                'estudiante': {
                    'nombre': estudiante.usuario.get_full_name() if estudiante.usuario else '',
                    'documento': estudiante.usuario.numero_documento if estudiante.usuario else ''
                },
                'estadisticas': {
                    'total': total,
                    'positivos': total_positivos,
                    'negativos': total_negativos,
                    'balance': total_positivos - total_negativos
                },
                'ultimos_registros': ultimos_list
            })
            
        except Estudiante.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Estudiante no encontrado'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

#======================Asistencias nueva Ajax ===================================

@login_required
def ajax_obtener_estudiantes_curso(request):
    """Obtener estudiantes de un curso específico"""
    if request.method == 'GET':
        try:
            curso_id = request.GET.get('curso_id')
            periodo_id = request.GET.get('periodo_id')
            fecha_str = request.GET.get('fecha', None)
            
            if not curso_id or not periodo_id:
                return JsonResponse({'success': False, 'error': 'Datos incompletos'})
            
            docente = get_object_or_404(Docente, usuario=request.user)
            grado_año_lectivo = get_object_or_404(GradoAñoLectivo, id=curso_id)
            periodo_academico = get_object_or_404(PeriodoAcademico, id=periodo_id)
            
            # Verificar que el docente tenga permiso
            if not AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente,
                grado_año_lectivo=grado_año_lectivo
            ).exists():
                return JsonResponse({'success': False, 'error': 'No tiene permiso para este curso'})
            
            # Obtener estudiantes matriculados en este curso
            estudiantes = Estudiante.objects.filter(
                matriculas__grado_año_lectivo=grado_año_lectivo,
                matriculas__estado__in=['ACT', 'PEN']
            ).select_related('usuario').order_by('usuario__apellidos', 'usuario__nombres').distinct()
            
            # Obtener asistencias si se proporciona una fecha
            asistencias_dict = {}
            if fecha_str:
                try:
                    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                    
                    # Verificar que la fecha esté dentro del periodo
                    if not (periodo_academico.fecha_inicio <= fecha <= periodo_academico.fecha_fin):
                        return JsonResponse({
                            'success': False, 
                            'error': f'La fecha debe estar entre {periodo_academico.fecha_inicio} y {periodo_academico.fecha_fin}'
                        })
                    
                    asistencias = Asistencia.objects.filter(
                        estudiante__in=estudiantes,
                        periodo_academico=periodo_academico,
                        fecha=fecha
                    ).select_related('estudiante__usuario')
                    
                    asistencias_dict = {a.estudiante.id: {
                        'estado': a.estado,
                        'justificacion': a.justificacion,
                        'id': a.id,
                        'fecha': a.fecha.strftime('%Y-%m-%d')
                    } for a in asistencias}
                    
                except ValueError:
                    return JsonResponse({'success': False, 'error': 'Formato de fecha inválido'})
                except Exception as e:
                    return JsonResponse({'success': False, 'error': str(e)})
            
            # Obtener estadísticas generales del curso para el periodo
            total_asistencias_curso = Asistencia.objects.filter(
                estudiante__in=estudiantes,
                periodo_academico=periodo_academico,
                estado='A'
            ).count()
            
            total_faltas_curso = Asistencia.objects.filter(
                estudiante__in=estudiantes,
                periodo_academico=periodo_academico,
                estado='F'
            ).count()
            
            total_justificadas_curso = Asistencia.objects.filter(
                estudiante__in=estudiantes,
                periodo_academico=periodo_academico,
                estado='J'
            ).count()
            
            total_registros_curso = total_asistencias_curso + total_faltas_curso + total_justificadas_curso
            if total_registros_curso > 0:
                porcentaje_curso = (total_asistencias_curso / total_registros_curso) * 100
            else:
                porcentaje_curso = 0
            
            # Preparar datos de estudiantes
            estudiantes_data = []
            for estudiante in estudiantes:
                # Calcular estadísticas individuales del periodo
                asistencias_estudiante = Asistencia.objects.filter(
                    estudiante=estudiante,
                    periodo_academico=periodo_academico
                )
                
                total_individual = asistencias_estudiante.count()
                asistencias_individual = asistencias_estudiante.filter(estado='A').count()
                faltas_individual = asistencias_estudiante.filter(estado='F').count()
                justificadas_individual = asistencias_estudiante.filter(estado='J').count()
                
                if total_individual > 0:
                    porcentaje_individual = (asistencias_individual / total_individual) * 100
                else:
                    porcentaje_individual = 0
                
                estudiante_data = {
                    'id': estudiante.id,
                    'nombre_completo': estudiante.usuario.get_full_name(),
                    'numero_documento': estudiante.usuario.numero_documento,
                    'foto_url': estudiante.foto.url if estudiante.foto else '',
                    'estadisticas': {
                        'total': total_individual,
                        'asistencias': asistencias_individual,
                        'faltas': faltas_individual,
                        'justificadas': justificadas_individual,
                        'porcentaje': round(porcentaje_individual, 1)
                    }
                }
                
                # Agregar información de asistencia para la fecha específica
                if fecha_str and estudiante.id in asistencias_dict:
                    asistencia = asistencias_dict[estudiante.id]
                    estudiante_data['asistencia'] = asistencia
                
                estudiantes_data.append(estudiante_data)
            
            return JsonResponse({
                'success': True,
                'estudiantes': estudiantes_data,
                'total': len(estudiantes_data),
                'curso': {
                    'id': grado_año_lectivo.id,
                    'nombre': f"{grado_año_lectivo.grado.nombre}",
                    'sede': grado_año_lectivo.año_lectivo.sede.nombre,
                    'año_lectivo': grado_año_lectivo.año_lectivo.anho
                },
                'periodo': {
                    'id': periodo_academico.id,
                    'nombre': periodo_academico.periodo.nombre,
                    'fecha_inicio': periodo_academico.fecha_inicio.strftime('%Y-%m-%d'),
                    'fecha_fin': periodo_academico.fecha_fin.strftime('%Y-%m-%d')
                },
                'estadisticas_curso': {
                    'total_asistencias': total_asistencias_curso,
                    'total_faltas': total_faltas_curso,
                    'total_justificadas': total_justificadas_curso,
                    'porcentaje': round(porcentaje_curso, 1)
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
def ajax_obtener_asistencia_dia(request):
    """Obtener asistencia de un día específico"""
    if request.method == 'GET':
        try:
            curso_id = request.GET.get('curso_id')
            periodo_id = request.GET.get('periodo_id')
            fecha_str = request.GET.get('fecha')
            
            if not all([curso_id, periodo_id, fecha_str]):
                return JsonResponse({'success': False, 'error': 'Datos incompletos'})
            
            # Validar fecha
            try:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Formato de fecha inválido'})
            
            # Verificar que no sea fecha futura
            if fecha > timezone.now().date():
                return JsonResponse({'success': False, 'error': 'No se puede consultar asistencia de fechas futuras'})
            
            # Verificar que sea día hábil
            if fecha.weekday() >= 5:
                return JsonResponse({'success': False, 'error': 'No hay clases los fines de semana'})
            
            grado_año_lectivo = get_object_or_404(GradoAñoLectivo, id=curso_id)
            periodo_academico = get_object_or_404(PeriodoAcademico, id=periodo_id)
            
            # Verificar que el docente tenga permiso
            docente = get_object_or_404(Docente, usuario=request.user)
            if not AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente,
                grado_año_lectivo=grado_año_lectivo
            ).exists():
                return JsonResponse({'success': False, 'error': 'No tiene permiso para este curso'})
            
            # Verificar que la fecha esté dentro del periodo
            if not (periodo_academico.fecha_inicio <= fecha <= periodo_academico.fecha_fin):
                return JsonResponse({
                    'success': False, 
                    'error': f'La fecha debe estar entre {periodo_academico.fecha_inicio} y {periodo_academico.fecha_fin}'
                })
            
            # Obtener estudiantes del curso
            estudiantes = Estudiante.objects.filter(
                matriculas__grado_año_lectivo=grado_año_lectivo,
                matriculas__estado__in=['ACT', 'PEN']
            ).select_related('usuario').distinct()
            
            # Obtener asistencias del día
            asistencias = Asistencia.objects.filter(
                estudiante__in=estudiantes,
                periodo_academico=periodo_academico,
                fecha=fecha
            ).select_related('estudiante__usuario')
            
            # Organizar datos
            asistencias_data = []
            for asistencia in asistencias:
                asistencias_data.append({
                    'estudiante_id': asistencia.estudiante.id,
                    'estudiante_nombre': asistencia.estudiante.usuario.get_full_name(),
                    'estudiante_documento': asistencia.estudiante.usuario.numero_documento,
                    'estado': asistencia.estado,
                    'justificacion': asistencia.justificacion,
                    'fecha': asistencia.fecha.strftime('%Y-%m-%d'),
                    'id': asistencia.id,
                    'hora_registro': asistencia.created_at.strftime('%H:%M') if asistencia.created_at else None
                })
            
            # Crear lista completa de estudiantes con su estado
            estudiantes_completos = []
            for estudiante in estudiantes:
                asistencia_estudiante = asistencias.filter(estudiante=estudiante).first()
                if asistencia_estudiante:
                    estado = asistencia_estudiante.estado
                    justificacion = asistencia_estudiante.justificacion
                    asistencia_id = asistencia_estudiante.id
                else:
                    estado = None
                    justificacion = ''
                    asistencia_id = None
                
                estudiantes_completos.append({
                    'estudiante_id': estudiante.id,
                    'estudiante_nombre': estudiante.usuario.get_full_name(),
                    'estudiante_documento': estudiante.usuario.numero_documento,
                    'estado': estado,
                    'justificacion': justificacion,
                    'asistencia_id': asistencia_id
                })
            
            # Estadísticas
            total_estudiantes = estudiantes.count()
            asistencias_count = asistencias.filter(estado='A').count()
            faltas_count = asistencias.filter(estado='F').count()
            justificadas_count = asistencias.filter(estado='J').count()
            sin_registro = total_estudiantes - (asistencias_count + faltas_count + justificadas_count)
            
            # Calcular porcentajes
            if total_estudiantes > 0:
                porcentaje_asistencia = (asistencias_count / total_estudiantes) * 100
                porcentaje_falta = (faltas_count / total_estudiantes) * 100
                porcentaje_justificada = (justificadas_count / total_estudiantes) * 100
                porcentaje_sin_registro = (sin_registro / total_estudiantes) * 100
            else:
                porcentaje_asistencia = porcentaje_falta = porcentaje_justificada = porcentaje_sin_registro = 0
            
            return JsonResponse({
                'success': True,
                'asistencias': asistencias_data,
                'estudiantes_completos': estudiantes_completos,
                'fecha': fecha_str,
                'dia_semana': fecha.strftime('%A'),
                'estadisticas': {
                    'total_estudiantes': total_estudiantes,
                    'asistencias': asistencias_count,
                    'faltas': faltas_count,
                    'justificadas': justificadas_count,
                    'sin_registro': sin_registro,
                    'porcentaje_asistencia': round(porcentaje_asistencia, 1),
                    'porcentaje_falta': round(porcentaje_falta, 1),
                    'porcentaje_justificada': round(porcentaje_justificada, 1),
                    'porcentaje_sin_registro': round(porcentaje_sin_registro, 1)
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
def ajax_obtener_dias_semana(request):
    """Obtener días hábiles de la semana actual o específica"""
    if request.method == 'GET':
        try:
            hoy = timezone.now().date()
            
            # Verificar si se solicita una semana específica
            fecha_str = request.GET.get('fecha', None)
            if fecha_str:
                try:
                    fecha_referencia = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                except ValueError:
                    fecha_referencia = hoy
            else:
                fecha_referencia = hoy
            
            # Obtener inicio de semana (lunes)
            inicio_semana = fecha_referencia - timedelta(days=fecha_referencia.weekday())
            
            # Generar días hábiles (lunes a viernes)
            dias_semana = []
            for i in range(5):
                dia = inicio_semana + timedelta(days=i)
                dias_semana.append({
                    'fecha': dia.strftime('%Y-%m-%d'),
                    'nombre': dia.strftime('%A'),
                    'nombre_corto': dia.strftime('%a'),
                    'dia_mes': dia.day,
                    'mes': dia.strftime('%B'),
                    'mes_corto': dia.strftime('%b'),
                    'año': dia.year,
                    'es_hoy': dia == hoy,
                    'numero_semana': dia.isocalendar()[1]
                })
            
            # Obtener información de periodos académicos activos
            año_actual = AñoLectivo.objects.filter(estado=True).first()
            periodos_semana = []
            if año_actual:
                periodos_semana = PeriodoAcademico.objects.filter(
                    año_lectivo=año_actual,
                    estado=True,
                    fecha_inicio__lte=inicio_semana + timedelta(days=4),
                    fecha_fin__gte=inicio_semana
                ).select_related('periodo')
            
            # Verificar si hay algún feriado o día no lectivo (puedes expandir esta funcionalidad)
            dias_no_lectivos = []  # Aquí podrías integrar con un modelo de días no lectivos
            
            return JsonResponse({
                'success': True,
                'dias': dias_semana,
                'semana_inicio': inicio_semana.strftime('%Y-%m-%d'),
                'semana_fin': (inicio_semana + timedelta(days=4)).strftime('%Y-%m-%d'),
                'hoy': hoy.strftime('%Y-%m-%d'),
                'fecha_referencia': fecha_referencia.strftime('%Y-%m-%d'),
                'periodos_semana': [
                    {
                        'id': p.id,
                        'nombre': p.periodo.nombre,
                        'fecha_inicio': p.fecha_inicio.strftime('%Y-%m-%d'),
                        'fecha_fin': p.fecha_fin.strftime('%Y-%m-%d')
                    } for p in periodos_semana
                ],
                'dias_no_lectivos': dias_no_lectivos,
                'total_dias_habiles': len(dias_semana)
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
def ajax_obtener_cursos_docente(request):
    """Obtener todos los cursos de un docente para el año actual"""
    if request.method == 'GET':
        try:
            docente = get_object_or_404(Docente, usuario=request.user)
            año_actual = AñoLectivo.objects.filter(estado=True).first()
            
            if not año_actual:
                return JsonResponse({'success': False, 'error': 'No hay año lectivo activo'})
            
            # Obtener asignaturas que dicta el docente
            asignaturas = AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente,
                grado_año_lectivo__año_lectivo=año_actual
            ).select_related(
                'grado_año_lectivo__grado',
                'sede',
                'asignatura'
            ).distinct()
            
            # Agrupar por curso (grado_año_lectivo)
            cursos_dict = {}
            for asignatura in asignaturas:
                key = asignatura.grado_año_lectivo.id
                if key not in cursos_dict:
                    # Contar estudiantes en este curso
                    total_estudiantes = Estudiante.objects.filter(
                        matriculas__grado_año_lectivo=asignatura.grado_año_lectivo,
                        matriculas__estado__in=['ACT', 'PEN']
                    ).distinct().count()
                    
                    cursos_dict[key] = {
                        'id': asignatura.grado_año_lectivo.id,
                        'nombre_grado': asignatura.grado_año_lectivo.grado.nombre,
                        'sede': asignatura.sede.nombre,
                        'sede_id': asignatura.sede.id,
                        'total_estudiantes': total_estudiantes,
                        'asignaturas': [],
                        'periodos': []
                    }
                
                # Agregar asignatura
                if asignatura.asignatura.nombre not in [a['nombre'] for a in cursos_dict[key]['asignaturas']]:
                    cursos_dict[key]['asignaturas'].append({
                        'id': asignatura.asignatura.id,
                        'nombre': asignatura.asignatura.nombre
                    })
            
            # Obtener periodos académicos para cada curso
            cursos_list = list(cursos_dict.values())
            for curso in cursos_list:
                grado_año_lectivo = GradoAñoLectivo.objects.get(id=curso['id'])
                periodos = PeriodoAcademico.objects.filter(
                    año_lectivo=grado_año_lectivo.año_lectivo,
                    estado=True
                ).select_related('periodo')
                
                curso['periodos'] = [
                    {
                        'id': p.id,
                        'nombre': p.periodo.nombre,
                        'fecha_inicio': p.fecha_inicio.strftime('%Y-%m-%d'),
                        'fecha_fin': p.fecha_fin.strftime('%Y-%m-%d')
                    } for p in periodos
                ]
            
            return JsonResponse({
                'success': True,
                'cursos': cursos_list,
                'total_cursos': len(cursos_list),
                'año_lectivo': {
                    'id': año_actual.id,
                    'nombre': año_actual.anho
                },
                'docente': docente.usuario.get_full_name()
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
def ajax_obtener_estadisticas_curso(request):
    """Obtener estadísticas detalladas de un curso"""
    if request.method == 'GET':
        try:
            curso_id = request.GET.get('curso_id')
            periodo_id = request.GET.get('periodo_id')
            
            if not curso_id or not periodo_id:
                return JsonResponse({'success': False, 'error': 'Datos incompletos'})
            
            docente = get_object_or_404(Docente, usuario=request.user)
            grado_año_lectivo = get_object_or_404(GradoAñoLectivo, id=curso_id)
            periodo_academico = get_object_or_404(PeriodoAcademico, id=periodo_id)
            
            # Verificar permisos
            if not AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente,
                grado_año_lectivo=grado_año_lectivo
            ).exists():
                return JsonResponse({'success': False, 'error': 'No tiene permiso para este curso'})
            
            # Obtener estudiantes
            estudiantes = Estudiante.objects.filter(
                matriculas__grado_año_lectivo=grado_año_lectivo,
                matriculas__estado__in=['ACT', 'PEN']
            ).distinct()
            
            # Obtener todas las asistencias del periodo
            asistencias = Asistencia.objects.filter(
                estudiante__in=estudiantes,
                periodo_academico=periodo_academico
            ).select_related('estudiante__usuario')
            
            # Calcular días hábiles del periodo
            fecha_actual = periodo_academico.fecha_inicio
            dias_habiles = 0
            while fecha_actual <= periodo_academico.fecha_fin:
                if fecha_actual.weekday() < 5:
                    dias_habiles += 1
                fecha_actual += timedelta(days=1)
            
            # Estadísticas generales
            total_estudiantes = estudiantes.count()
            total_asistencias = asistencias.filter(estado='A').count()
            total_faltas = asistencias.filter(estado='F').count()
            total_justificadas = asistencias.filter(estado='J').count()
            total_registros = total_asistencias + total_faltas + total_justificadas
            
            # Calcular porcentajes
            if total_registros > 0:
                porcentaje_asistencias = (total_asistencias / total_registros) * 100
                porcentaje_faltas = (total_faltas / total_registros) * 100
                porcentaje_justificadas = (total_justificadas / total_registros) * 100
            else:
                porcentaje_asistencias = porcentaje_faltas = porcentaje_justificadas = 0
            
            # Estadísticas por estudiante (top 5 mejor y peor asistencia)
            estadisticas_estudiantes = []
            for estudiante in estudiantes:
                asistencias_est = asistencias.filter(estudiante=estudiante)
                total_est = asistencias_est.count()
                asistencias_est_count = asistencias_est.filter(estado='A').count()
                
                if total_est > 0:
                    porcentaje_est = (asistencias_est_count / total_est) * 100
                else:
                    porcentaje_est = 0
                
                estadisticas_estudiantes.append({
                    'estudiante_id': estudiante.id,
                    'nombre': estudiante.usuario.get_full_name(),
                    'total': total_est,
                    'asistencias': asistencias_est_count,
                    'porcentaje': round(porcentaje_est, 1)
                })
            
            # Ordenar por porcentaje
            estadisticas_estudiantes.sort(key=lambda x: x['porcentaje'], reverse=True)
            
            # Top 5 mejor asistencia
            top_mejor = estadisticas_estudiantes[:5]
            
            # Top 5 peor asistencia (invertir y tomar primeros 5)
            top_peor = sorted(estadisticas_estudiantes, key=lambda x: x['porcentaje'])[:5]
            
            # Estadísticas por día de la semana
            dias_semana_stats = []
            for i in range(5):  # Lunes a Viernes
                asistencias_dia = asistencias.filter(
                    fecha__week_day=(i + 2) % 7 + 1  # Django: 2=Lunes, 3=Martes, etc.
                )
                total_dia = asistencias_dia.count()
                asistencias_dia_count = asistencias_dia.filter(estado='A').count()
                
                if total_dia > 0:
                    porcentaje_dia = (asistencias_dia_count / total_dia) * 100
                else:
                    porcentaje_dia = 0
                
                dias_semana_stats.append({
                    'dia': ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'][i],
                    'total': total_dia,
                    'asistencias': asistencias_dia_count,
                    'porcentaje': round(porcentaje_dia, 1)
                })
            
            return JsonResponse({
                'success': True,
                'estadisticas_generales': {
                    'total_estudiantes': total_estudiantes,
                    'dias_habiles_periodo': dias_habiles,
                    'total_asistencias': total_asistencias,
                    'total_faltas': total_faltas,
                    'total_justificadas': total_justificadas,
                    'total_registros': total_registros,
                    'porcentaje_asistencias': round(porcentaje_asistencias, 1),
                    'porcentaje_faltas': round(porcentaje_faltas, 1),
                    'porcentaje_justificadas': round(porcentaje_justificadas, 1)
                },
                'top_mejor_asistencia': top_mejor,
                'top_peor_asistencia': top_peor,
                'estadisticas_dias_semana': dias_semana_stats,
                'curso': {
                    'id': grado_año_lectivo.id,
                    'nombre': grado_año_lectivo.grado.nombre,
                    'sede': grado_año_lectivo.año_lectivo.sede.nombre
                },
                'periodo': {
                    'id': periodo_academico.id,
                    'nombre': periodo_academico.periodo.nombre
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})