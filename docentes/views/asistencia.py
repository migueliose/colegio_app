from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Count, Avg
from datetime import datetime, date, timedelta
import json
import calendar

from usuarios.models import Docente
from estudiantes.models import Estudiante, Matricula
from comportamiento.models import Asistencia
from academico.models import Grado, Asignatura, Periodo
from matricula.models import PeriodoAcademico, AsignaturaGradoAñoLectivo, GradoAñoLectivo
from gestioncolegio.models import AñoLectivo, Sede

@login_required
def asistencia_principal(request):
    """Vista principal para gestión de asistencia"""
    docente = get_object_or_404(Docente, usuario=request.user)
    
    # Obtener año lectivo actual
    año_actual = AñoLectivo.objects.filter(estado=True).first()
    
    # Obtener cursos del docente en el año actual
    cursos = []
    if año_actual:
        # Obtener todas las asignaturas que dicta el docente en el año actual
        asignaturas_dictadas = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__año_lectivo=año_actual
        ).select_related(
            'grado_año_lectivo__grado',
            'asignatura',
            'sede',
            'grado_año_lectivo__año_lectivo'
        ).distinct()
        
        # Agrupar por grado_año_lectivo y sede
        cursos_dict = {}
        for asignatura in asignaturas_dictadas:
            key = f"{asignatura.grado_año_lectivo.id}-{asignatura.sede.id}"
            if key not in cursos_dict:
                cursos_dict[key] = {
                    'grado_año_lectivo': asignatura.grado_año_lectivo,
                    'grado': asignatura.grado_año_lectivo.grado,
                    'sede': asignatura.sede,
                    'año_lectivo': año_actual,
                    'asignaturas': []
                }
            # Agregar asignatura si no está ya en la lista
            if asignatura.asignatura not in cursos_dict[key]['asignaturas']:
                cursos_dict[key]['asignaturas'].append(asignatura.asignatura)
        
        cursos = list(cursos_dict.values())
    
    # Obtener periodos académicos del año actual
    periodos = []
    if año_actual:
        periodos = PeriodoAcademico.objects.filter(
            año_lectivo=año_actual,
            estado=True
        ).select_related('periodo').order_by('periodo__nombre')
    
    # Obtener la semana actual
    hoy = timezone.now().date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    fin_semana = inicio_semana + timedelta(days=6)
    
    # Días hábiles de la semana actual (lunes a viernes)
    dias_semana = []
    for i in range(5):  # Lunes a Viernes (0-4)
        dia = inicio_semana + timedelta(days=i)
        dias_semana.append({
            'fecha': dia,
            'nombre': calendar.day_name[dia.weekday()],
            'nombre_corto': calendar.day_abbr[dia.weekday()],
            'es_hoy': dia == hoy
        })
    
    # Estadísticas generales del docente
    total_estudiantes = 0
    if cursos:
        for curso in cursos:
            # Contar estudiantes en cada curso
            estudiantes_count = Matricula.objects.filter(
                grado_año_lectivo=curso['grado_año_lectivo'],
                estado__in=['ACT', 'PEN']
            ).count()
            total_estudiantes += estudiantes_count
    
    context = {
        'cursos': cursos,
        'periodos': periodos,
        'dias_semana': dias_semana,
        'hoy': hoy,
        'año_actual': año_actual,
        'total_estudiantes': total_estudiantes,
        'total_cursos': len(cursos),
    }
    
    return render(request, 'docentes/asistencia/principal.html', context)

@login_required
def asistencia_calendario(request, curso_id, periodo_id):
    """Vista de calendario de asistencia para un curso específico"""
    docente = get_object_or_404(Docente, usuario=request.user)
    grado_año_lectivo = get_object_or_404(GradoAñoLectivo, id=curso_id)
    periodo_academico = get_object_or_404(PeriodoAcademico, id=periodo_id)
    
    # Verificar que el docente tenga asignaturas en este curso
    if not AsignaturaGradoAñoLectivo.objects.filter(
        docente=docente,
        grado_año_lectivo=grado_año_lectivo
    ).exists():
        messages.error(request, 'No tiene permiso para ver la asistencia de este curso.')
        return redirect('docentes:asistencia_principal')
    
    # Obtener estudiantes matriculados en este curso
    estudiantes = Estudiante.objects.filter(
        matriculas__grado_año_lectivo=grado_año_lectivo,
        matriculas__estado__in=['ACT', 'PEN']
    ).select_related('usuario').distinct()
    
    # Obtener el mes y año actual
    hoy = timezone.now().date()
    mes = request.GET.get('mes', hoy.month)
    año = request.GET.get('año', hoy.year)
    
    try:
        mes = int(mes)
        año = int(año)
    except:
        mes = hoy.month
        año = hoy.year
    
    # Calcular días del mes
    cal = calendar.monthcalendar(año, mes)
    
    # Lista de nombres de meses para usar en la plantilla
    meses_nombres = [
        '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]
    
    # Nombres de los meses anterior y siguiente
    if mes == 1:
        mes_anterior = 12
        año_anterior = año - 1
    else:
        mes_anterior = mes - 1
        año_anterior = año
        
    if mes == 12:
        mes_siguiente = 1
        año_siguiente = año + 1
    else:
        mes_siguiente = mes + 1
        año_siguiente = año
    
    # Obtener rango de fechas del mes
    primera_fecha = date(año, mes, 1)
    if mes == 12:
        ultima_fecha = date(año + 1, 1, 1) - timedelta(days=1)
    else:
        ultima_fecha = date(año, mes + 1, 1) - timedelta(days=1)
    
    # Obtener asistencias del mes
    asistencias = Asistencia.objects.filter(
        estudiante__in=estudiantes,
        periodo_academico=periodo_academico,
        fecha__range=[primera_fecha, ultima_fecha]
    ).select_related('estudiante__usuario')
    
    # Organizar asistencias por día y tipo
    asistencias_por_dia = {}
    for asistencia in asistencias:
        key = f"{asistencia.estudiante.id}_{asistencia.fecha.strftime('%Y-%m-%d')}"
        if key not in asistencias_por_dia:
            asistencias_por_dia[key] = asistencia.estado
    
    # Agrupar conteos por día (para mostrar en el calendario)
    conteos_por_dia = {}
    for fecha in asistencias.values_list('fecha', 'estado'):
        fecha_str = fecha[0].strftime('%Y-%m-%d')
        if fecha_str not in conteos_por_dia:
            conteos_por_dia[fecha_str] = {'A': 0, 'F': 0, 'J': 0}
        conteos_por_dia[fecha_str][fecha[1]] += 1
    
    # Calcular estadísticas por estudiante para el mes
    estudiantes_con_estadisticas = []
    for estudiante in estudiantes:
        # Filtrar asistencias del estudiante en el mes
        asistencias_estudiante = asistencias.filter(estudiante=estudiante)
        asistencias_count = asistencias_estudiante.filter(estado='A').count()
        faltas_count = asistencias_estudiante.filter(estado='F').count()
        justificadas_count = asistencias_estudiante.filter(estado='J').count()
        total_registros = asistencias_count + faltas_count + justificadas_count
        
        if total_registros > 0:
            porcentaje = (asistencias_count / total_registros) * 100
        else:
            porcentaje = 0
        
        estudiantes_con_estadisticas.append({
            'estudiante': estudiante,
            'asistencias_count': asistencias_count,
            'faltas_count': faltas_count,
            'justificadas_count': justificadas_count,
            'porcentaje': round(porcentaje, 1)
        })
    
    # Calcular días hábiles del mes (lunes a viernes)
    dias_habiles_mes = 0
    fecha_temp = primera_fecha
    while fecha_temp <= ultima_fecha:
        if fecha_temp.weekday() < 5:  # 0-4 = lunes a viernes
            dias_habiles_mes += 1
        fecha_temp += timedelta(days=1)
    
    context = {
        'grado_año_lectivo': grado_año_lectivo,
        'periodo_academico': periodo_academico,
        'estudiantes': estudiantes_con_estadisticas,
        'calendario': cal,
        'mes_actual': mes,
        'año_actual': año,
        'mes_nombre': meses_nombres[mes],  # Usar nuestra lista
        'meses_nombres': meses_nombres,    # Pasar la lista completa
        'mes_anterior': mes_anterior,
        'año_anterior': año_anterior,
        'mes_siguiente': mes_siguiente,
        'año_siguiente': año_siguiente,
        'asistencias_dict': asistencias_por_dia,  # Diccionario simple
        'asistencias_por_dia': conteos_por_dia,   # Diccionario con conteos
        'hoy': hoy,
        'primera_fecha': primera_fecha,
        'ultima_fecha': ultima_fecha,
        'dias_habiles_mes': dias_habiles_mes,
        'docente': docente,
    }
    
    return render(request, 'docentes/asistencia/calendario.html', context)

@login_required
def registrar_asistencia(request):
    """Registrar asistencia individual o masiva"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            fecha_str = data.get('fecha')
            curso_id = data.get('curso_id')
            periodo_id = data.get('periodo_id')
            asistencias = data.get('asistencias', [])
            
            # Validar datos
            if not all([fecha_str, curso_id, periodo_id]):
                return JsonResponse({'success': False, 'error': 'Datos incompletos'})
            
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            grado_año_lectivo = get_object_or_404(GradoAñoLectivo, id=curso_id)
            periodo_academico = get_object_or_404(PeriodoAcademico, id=periodo_id)
            
            # Verificar que el docente tenga permiso
            docente = get_object_or_404(Docente, usuario=request.user)
            if not AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente,
                grado_año_lectivo=grado_año_lectivo
            ).exists():
                return JsonResponse({'success': False, 'error': 'No tiene permiso para este curso'})
            
            # Verificar que la fecha sea un día hábil (lunes a viernes)
            if fecha.weekday() >= 5:  # 5 = sábado, 6 = domingo
                return JsonResponse({'success': False, 'error': 'No se puede registrar asistencia en fines de semana'})
            
            # Verificar que no sea una fecha futura
            if fecha > timezone.now().date():
                return JsonResponse({'success': False, 'error': 'No se puede registrar asistencia para fechas futuras'})
            
            # Verificar que la fecha esté dentro del periodo académico
            if not (periodo_academico.fecha_inicio <= fecha <= periodo_academico.fecha_fin):
                return JsonResponse({
                    'success': False, 
                    'error': f'La fecha debe estar entre {periodo_academico.fecha_inicio} y {periodo_academico.fecha_fin}'
                })
            
            # Si no hay asistencias específicas, obtener todos los estudiantes del curso
            if not asistencias:
                estudiantes = Estudiante.objects.filter(
                    matriculas__grado_año_lectivo=grado_año_lectivo,
                    matriculas__estado__in=['ACT', 'PEN']
                ).distinct()
                
                asistencias = []
                for estudiante in estudiantes:
                    asistencias.append({
                        'estudiante_id': estudiante.id,
                        'estado': 'A',  # Por defecto Asistió
                        'justificacion': ''
                    })
            
            # Registrar asistencias
            registros_creados = 0
            registros_actualizados = 0
            errores = []
            
            for asistencia_data in asistencias:
                estudiante_id = asistencia_data.get('estudiante_id')
                estado = asistencia_data.get('estado')
                justificacion = asistencia_data.get('justificacion', '')
                
                if not estudiante_id or not estado:
                    errores.append(f'Datos incompletos para estudiante {estudiante_id}')
                    continue
                
                estudiante = Estudiante.objects.filter(id=estudiante_id).first()
                if not estudiante:
                    errores.append(f'Estudiante con ID {estudiante_id} no encontrado')
                    continue
                
                # Verificar que el estudiante esté matriculado en el curso
                if not estudiante.matriculas.filter(
                    grado_año_lectivo=grado_año_lectivo,
                    estado__in=['ACT', 'PEN']
                ).exists():
                    errores.append(f'El estudiante {estudiante_id} no está matriculado en este curso')
                    continue
                
                # Validar estado
                if estado not in ['A', 'F', 'J']:
                    errores.append(f'Estado inválido para estudiante {estudiante_id}')
                    continue
                
                # Si es justificada, requerir justificación
                if estado == 'J' and not justificacion:
                    justificacion = 'Justificada por docente'
                
                # Buscar o crear registro de asistencia
                asistencia, created = Asistencia.objects.update_or_create(
                    estudiante=estudiante,
                    periodo_academico=periodo_academico,
                    fecha=fecha,
                    defaults={
                        'estado': estado,
                        'justificacion': justificacion if justificacion else None
                    }
                )
                
                if created:
                    registros_creados += 1
                else:
                    registros_actualizados += 1
            
            mensaje = f'Asistencia registrada: {registros_creados} creados, {registros_actualizados} actualizados'
            if errores:
                mensaje += f'. Errores: {", ".join(errores[:3])}'  # Mostrar solo primeros 3 errores
            
            return JsonResponse({
                'success': True,
                'message': mensaje,
                'creados': registros_creados,
                'actualizados': registros_actualizados,
                'errores': len(errores)
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Error en el formato de datos JSON'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
def registrar_asistencia_masiva(request):
    """Registrar asistencia masiva para todos los estudiantes de un curso"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            fecha_str = data.get('fecha')
            curso_id = data.get('curso_id')
            periodo_id = data.get('periodo_id')
            estado = data.get('estado')
            justificacion = data.get('justificacion', '')
            
            # Validar datos
            if not all([fecha_str, curso_id, periodo_id, estado]):
                return JsonResponse({'success': False, 'error': 'Datos incompletos'})
            
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            grado_año_lectivo = get_object_or_404(GradoAñoLectivo, id=curso_id)
            periodo_academico = get_object_or_404(PeriodoAcademico, id=periodo_id)
            
            # Verificar que el docente tenga permiso
            docente = get_object_or_404(Docente, usuario=request.user)
            if not AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente,
                grado_año_lectivo=grado_año_lectivo
            ).exists():
                return JsonResponse({'success': False, 'error': 'No tiene permiso para este curso'})
            
            # Verificar que la fecha sea un día hábil
            if fecha.weekday() >= 5:
                return JsonResponse({'success': False, 'error': 'No se puede registrar asistencia en fines de semana'})
            
            # Verificar que no sea una fecha futura
            if fecha > timezone.now().date():
                return JsonResponse({'success': False, 'error': 'No se puede registrar asistencia para fechas futuras'})
            
            # Validar estado
            if estado not in ['A', 'F', 'J']:
                return JsonResponse({'success': False, 'error': 'Estado inválido'})
            
            # Si es justificada, requerir justificación
            if estado == 'J' and not justificacion:
                justificacion = 'Justificada por docente (registro masivo)'
            
            # Obtener todos los estudiantes del curso
            estudiantes = Estudiante.objects.filter(
                matriculas__grado_año_lectivo=grado_año_lectivo,
                matriculas__estado__in=['ACT', 'PEN']
            ).distinct()
            
            # Registrar asistencia para todos los estudiantes
            registros_creados = 0
            registros_actualizados = 0
            
            for estudiante in estudiantes:
                asistencia, created = Asistencia.objects.update_or_create(
                    estudiante=estudiante,
                    periodo_academico=periodo_academico,
                    fecha=fecha,
                    defaults={
                        'estado': estado,
                        'justificacion': justificacion if justificacion else None
                    }
                )
                
                if created:
                    registros_creados += 1
                else:
                    registros_actualizados += 1
            
            return JsonResponse({
                'success': True,
                'message': f'Asistencia masiva registrada para {len(estudiantes)} estudiantes',
                'total_estudiantes': len(estudiantes),
                'creados': registros_creados,
                'actualizados': registros_actualizados,
                'estado': estado
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
def justificar_asistencia(request):
    """Justificar una asistencia específica"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            asistencia_id = data.get('asistencia_id')
            justificacion = data.get('justificacion', '')
            
            if not asistencia_id:
                return JsonResponse({'success': False, 'error': 'ID de asistencia requerido'})
            
            if not justificacion:
                return JsonResponse({'success': False, 'error': 'Justificación requerida'})
            
            asistencia = get_object_or_404(Asistencia, id=asistencia_id)
            
            # Verificar que el docente tenga permiso
            docente = get_object_or_404(Docente, usuario=request.user)
            
            # Verificar que el docente tenga asignaturas en el curso del estudiante
            matricula_estudiante = asistencia.estudiante.matricula_actual
            if matricula_estudiante:
                if not AsignaturaGradoAñoLectivo.objects.filter(
                    docente=docente,
                    grado_año_lectivo=matricula_estudiante.grado_año_lectivo
                ).exists():
                    return JsonResponse({'success': False, 'error': 'No tiene permiso para justificar esta asistencia'})
            
            asistencia.estado = 'J'  # Falta justificada
            asistencia.justificacion = justificacion
            asistencia.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Asistencia justificada correctamente',
                'asistencia_id': asistencia.id,
                'estudiante': asistencia.estudiante.usuario.get_full_name()
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
def asistencia_historico(request, estudiante_id):
    """Ver histórico de asistencia de un estudiante"""
    estudiante = get_object_or_404(Estudiante, id=estudiante_id)
    docente = get_object_or_404(Docente, usuario=request.user)
    
    # Verificar que el estudiante esté en algún curso del docente en el año actual
    año_actual = AñoLectivo.objects.filter(estado=True).first()
    
    if año_actual:
        # Obtener cursos del docente en el año actual
        cursos_docente = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__año_lectivo=año_actual
        ).values_list('grado_año_lectivo', flat=True).distinct()
        
        # Verificar si el estudiante está en alguno de esos cursos
        if not estudiante.matriculas.filter(
            grado_año_lectivo__in=cursos_docente,
            año_lectivo=año_actual
        ).exists():
            messages.error(request, 'No tiene permiso para ver la asistencia de este estudiante.')
            return redirect('docentes:asistencia_principal')
    
    # Obtener matrícula actual
    matricula_actual = estudiante.matricula_actual
    periodo_actual = None
    
    if matricula_actual and año_actual:
        # Obtener periodo académico actual
        periodo_actual = PeriodoAcademico.objects.filter(
            año_lectivo=año_actual,
            estado=True,
            fecha_inicio__lte=timezone.now().date(),
            fecha_fin__gte=timezone.now().date()
        ).first()
    
    # Obtener todos los periodos académicos del estudiante
    periodos_estudiante = PeriodoAcademico.objects.filter(
        año_lectivo__matriculas__estudiante=estudiante
    ).select_related('año_lectivo', 'periodo').distinct().order_by('-año_lectivo__anho', 'periodo__nombre')
    
    # Filtrar por periodo si se especifica
    periodo_id = request.GET.get('periodo_id')
    periodo_filtrado = None
    if periodo_id:
        periodo_filtrado = get_object_or_404(PeriodoAcademico, id=periodo_id)
        asistencias = Asistencia.objects.filter(
            estudiante=estudiante,
            periodo_academico=periodo_filtrado
        ).select_related('periodo_academico__año_lectivo', 'periodo_academico__periodo').order_by('-fecha')
    else:
        # Obtener todas las asistencias del estudiante
        asistencias = Asistencia.objects.filter(
            estudiante=estudiante
        ).select_related('periodo_academico__año_lectivo', 'periodo_academico__periodo').order_by('-fecha')
    
    # Estadísticas generales
    total_asistencias = asistencias.count()
    asistencias_count = asistencias.filter(estado='A').count()
    faltas_count = asistencias.filter(estado='F').count()
    justificadas_count = asistencias.filter(estado='J').count()
    
    if total_asistencias > 0:
        porcentaje_asistencia = (asistencias_count / total_asistencias) * 100
    else:
        porcentaje_asistencia = 0
    
    # Estadísticas por periodo
    estadisticas_periodo = []
    for periodo in periodos_estudiante:
        asistencias_periodo = Asistencia.objects.filter(
            estudiante=estudiante,
            periodo_academico=periodo
        )
        total_periodo = asistencias_periodo.count()
        if total_periodo > 0:
            asist_periodo = asistencias_periodo.filter(estado='A').count()
            porcentaje_periodo = (asist_periodo / total_periodo) * 100
            
            estadisticas_periodo.append({
                'periodo': periodo,
                'total': total_periodo,
                'asistencias': asist_periodo,
                'faltas': asistencias_periodo.filter(estado='F').count(),
                'justificadas': asistencias_periodo.filter(estado='J').count(),
                'porcentaje': round(porcentaje_periodo, 1)
            })
    
    context = {
        'estudiante': estudiante,
        'matricula_actual': matricula_actual,
        'periodo_actual': periodo_actual,
        'periodo_filtrado': periodo_filtrado,
        'asistencias': asistencias,
        'periodos_estudiante': periodos_estudiante,
        'estadisticas_periodo': estadisticas_periodo,
        'total_asistencias': total_asistencias,
        'asistencias_count': asistencias_count,
        'faltas_count': faltas_count,
        'justificadas_count': justificadas_count,
        'porcentaje_asistencia': round(porcentaje_asistencia, 2),
        'docente': docente,
    }
    
    return render(request, 'docentes/asistencia/historico.html', context)

@login_required
def reporte_asistencia_curso(request, curso_id, periodo_id):
    """Generar reporte de asistencia para un curso"""
    docente = get_object_or_404(Docente, usuario=request.user)
    grado_año_lectivo = get_object_or_404(GradoAñoLectivo, id=curso_id)
    periodo_academico = get_object_or_404(PeriodoAcademico, id=periodo_id)
    
    # Verificar que el docente tenga permiso
    if not AsignaturaGradoAñoLectivo.objects.filter(
        docente=docente,
        grado_año_lectivo=grado_año_lectivo
    ).exists():
        messages.error(request, 'No tiene permiso para ver este reporte.')
        return redirect('docentes:asistencia_principal')
    
    # Obtener estudiantes del curso
    estudiantes = Estudiante.objects.filter(
        matriculas__grado_año_lectivo=grado_año_lectivo,
        matriculas__estado__in=['ACT', 'PEN']
    ).select_related('usuario').distinct().order_by('usuario__apellidos', 'usuario__nombres')
    
    # Obtener todas las fechas del periodo
    fecha_inicio = periodo_academico.fecha_inicio
    fecha_fin = periodo_academico.fecha_fin
    
    # Calcular días hábiles del periodo (lunes a viernes)
    dias_habiles = []
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        if fecha_actual.weekday() < 5:  # Lunes a Viernes
            dias_habiles.append(fecha_actual)
        fecha_actual += timedelta(days=1)
    
    # Obtener asistencias del periodo
    asistencias = Asistencia.objects.filter(
        estudiante__in=estudiantes,
        periodo_academico=periodo_academico,
        fecha__range=[fecha_inicio, fecha_fin]
    ).select_related('estudiante__usuario')
    
    # Organizar datos para el reporte
    reporte_data = []
    total_asistencias_general = 0
    total_faltas_general = 0
    total_justificadas_general = 0
    
    for estudiante in estudiantes:
        estudiante_asistencias = asistencias.filter(estudiante=estudiante)
        
        # Contar por tipo
        asistencias_count = estudiante_asistencias.filter(estado='A').count()
        faltas_count = estudiante_asistencias.filter(estado='F').count()
        justificadas_count = estudiante_asistencias.filter(estado='J').count()
        
        total_registros = asistencias_count + faltas_count + justificadas_count
        
        # Sumar al total general
        total_asistencias_general += asistencias_count
        total_faltas_general += faltas_count
        total_justificadas_general += justificadas_count
        
        # Calcular porcentaje
        if total_registros > 0:
            porcentaje = (asistencias_count / total_registros) * 100
        else:
            porcentaje = 0
        
        # Obtener detalle por día
        detalle_dias = {}
        for dia in dias_habiles:
            asistencia_dia = estudiante_asistencias.filter(fecha=dia).first()
            if asistencia_dia:
                detalle_dias[dia] = asistencia_dia.estado
            else:
                detalle_dias[dia] = '-'
        
        reporte_data.append({
            'estudiante': estudiante,
            'asistencias': asistencias_count,
            'faltas': faltas_count,
            'justificadas': justificadas_count,
            'total': total_registros,
            'porcentaje': round(porcentaje, 2),
            'detalle_dias': detalle_dias
        })
    
    # Calcular porcentajes generales
    total_registros_general = total_asistencias_general + total_faltas_general + total_justificadas_general
    if total_registros_general > 0:
        porcentaje_asistencias_general = (total_asistencias_general / total_registros_general) * 100
        porcentaje_faltas_general = (total_faltas_general / total_registros_general) * 100
        porcentaje_justificadas_general = (total_justificadas_general / total_registros_general) * 100
    else:
        porcentaje_asistencias_general = porcentaje_faltas_general = porcentaje_justificadas_general = 0
    
    context = {
        'grado_año_lectivo': grado_año_lectivo,
        'periodo_academico': periodo_academico,
        'estudiantes': estudiantes,
        'dias_habiles': dias_habiles,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'reporte_data': reporte_data,
        'total_dias_habiles': len(dias_habiles),
        'total_estudiantes': len(estudiantes),
        'total_asistencias_general': total_asistencias_general,
        'total_faltas_general': total_faltas_general,
        'total_justificadas_general': total_justificadas_general,
        'porcentaje_asistencias_general': round(porcentaje_asistencias_general, 2),
        'porcentaje_faltas_general': round(porcentaje_faltas_general, 2),
        'porcentaje_justificadas_general': round(porcentaje_justificadas_general, 2),
        'docente': docente,
    }
    
    return render(request, 'docentes/asistencia/reporte.html', context)