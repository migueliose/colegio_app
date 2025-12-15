"""
Módulo de Calificaciones - App Administrador
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View, TemplateView
from django.contrib import messages
from django.db.models import Q, Count, Avg, Max, Min
import json

from gestioncolegio.mixins import RoleRequiredMixin
from gestioncolegio.models import AñoLectivo, Sede
from usuarios.models import Docente, Usuario
from matricula.models import GradoAñoLectivo, AsignaturaGradoAñoLectivo, PeriodoAcademico, DocenteSede
from estudiantes.models import Estudiante, Matricula, Nota
from academico.models import Logro, Grado, Asignatura, Periodo


class GestionCalificacionesView(RoleRequiredMixin, TemplateView):
    """Vista principal para gestión de calificaciones"""
    template_name = 'administrador/calificaciones/gestion_calificaciones.html'
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener años lectivos activos
        #años_lectivos = AñoLectivo.objects.filter(estado=True).order_by('-anho')
        años_lectivos = AñoLectivo.objects.filter().order_by('-anho')
        
        # Estadísticas generales
        total_docentes = Docente.objects.filter(estado=True).count()
        total_estudiantes = Estudiante.objects.filter(estado=True).count()
        total_grados = Grado.objects.count()
        
        context.update({
            'años_lectivos': años_lectivos,
            'total_docentes': total_docentes,
            'total_estudiantes': total_estudiantes,
            'total_grados': total_grados,
            'title': 'Gestión de Calificaciones',
        })
        
        return context


class ObtenerDocentesPorAñoView(RoleRequiredMixin, View):
    """Obtener docentes por año lectivo (AJAX)"""
    allowed_roles = ['Administrador', 'Rector']
    
    def get(self, request):
        año_lectivo_id = request.GET.get('año_lectivo_id')
        
        if not año_lectivo_id:
            return JsonResponse({'error': 'Año lectivo no especificado'}, status=400)
        
        try:
            año_lectivo = AñoLectivo.objects.get(id=año_lectivo_id)
            
            # Obtener docentes con asignaturas en ese año lectivo
            asignaturas = AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo__año_lectivo=año_lectivo,
                docente__isnull=False
            ).select_related('docente', 'docente__usuario', 'sede')
            
            # Agrupar docentes únicos con estadísticas
            docentes_dict = {}
            for asignatura in asignaturas:
                docente = asignatura.docente
                if docente.id not in docentes_dict:
                    # Contar asignaturas del docente
                    total_asignaturas = asignaturas.filter(docente=docente).count()
                    
                    # Contar grados diferentes
                    grados = asignaturas.filter(docente=docente).values(
                        'grado_año_lectivo__grado__nombre'
                    ).distinct().count()
                    
                    docentes_dict[docente.id] = {
                        'id': docente.id,
                        'nombre': docente.usuario.get_full_name(),
                        'identificacion': docente.usuario.numero_documento,
                        'sede': asignatura.sede.nombre,
                        'sede_id': asignatura.sede.id,
                        'total_asignaturas': total_asignaturas,
                        'total_grados': grados,
                        'email': docente.usuario.email or '',
                        'telefono': docente.usuario.telefono or '',
                    }
            
            docentes = list(docentes_dict.values())
            
            # Estadísticas generales del año
            total_docentes = len(docentes)
            total_asignaturas = AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo__año_lectivo=año_lectivo,
                docente__isnull=False
            ).count()
            
            # Docentes con más asignaturas (top 3)
            docentes_top = sorted(docentes, key=lambda x: x['total_asignaturas'], reverse=True)[:3]
            
            return JsonResponse({
                'success': True,
                'docentes': docentes,
                'año_lectivo': {
                    'id': año_lectivo.id,
                    'anho': año_lectivo.anho,
                    'sede': año_lectivo.sede.nombre,
                },
                'estadisticas': {
                    'total_docentes': total_docentes,
                    'total_asignaturas': total_asignaturas,
                    'promedio_asignaturas': round(total_asignaturas / total_docentes, 1) if total_docentes > 0 else 0,
                },
                'docentes_top': docentes_top,
            })
            
        except AñoLectivo.DoesNotExist:
            return JsonResponse({'error': 'Año lectivo no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class ObtenerGradosAsignaturasDocenteView(RoleRequiredMixin, View):
    """Obtener grados y asignaturas de un docente en un año específico (AJAX)"""
    allowed_roles = ['Administrador', 'Rector']
    
    def get(self, request):
        docente_id = request.GET.get('docente_id')
        año_lectivo_id = request.GET.get('año_lectivo_id')
        
        if not docente_id or not año_lectivo_id:
            return JsonResponse({'error': 'Parámetros incompletos'}, status=400)
        
        try:
            año_lectivo = AñoLectivo.objects.get(id=año_lectivo_id)
            docente = Docente.objects.get(id=docente_id)
            
            # Obtener asignaturas dictadas por el docente en ese año
            asignaturas_dictadas = AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo__año_lectivo=año_lectivo,
                docente=docente
            ).select_related(
                'asignatura',
                'asignatura__area',
                'grado_año_lectivo__grado',
                'sede'
            )
            
            # Agrupar por grado y sede
            grados_dict = {}
            total_asignaturas = 0
            
            for asignatura in asignaturas_dictadas:
                grado_key = f"{asignatura.grado_año_lectivo.grado.id}_{asignatura.sede.id}"
                total_asignaturas += 1
                
                if grado_key not in grados_dict:
                    # Obtener estudiantes matriculados en este grado
                    total_estudiantes = Matricula.objects.filter(
                        grado_año_lectivo__grado=asignatura.grado_año_lectivo.grado,
                        sede=asignatura.sede,
                        año_lectivo=año_lectivo,
                        estado__in=['ACT', 'PEN']
                    ).count()
                    
                    grados_dict[grado_key] = {
                        'grado_id': asignatura.grado_año_lectivo.grado.id,
                        'grado_nombre': asignatura.grado_año_lectivo.grado.nombre,
                        'sede_id': asignatura.sede.id,
                        'sede_nombre': asignatura.sede.nombre,
                        'total_estudiantes': total_estudiantes,
                        'asignaturas': []
                    }
                
                # Verificar si ya hay calificaciones para esta asignatura
                total_calificaciones = Nota.objects.filter(
                    asignatura_grado_año_lectivo=asignatura
                ).count()
                
                grados_dict[grado_key]['asignaturas'].append({
                    'id': asignatura.id,
                    'nombre': asignatura.asignatura.nombre,
                    'area': asignatura.asignatura.area.nombre,
                    'ih': asignatura.asignatura.ih or 'N/A',
                    'total_calificaciones': total_calificaciones,
                })
            
            grados = list(grados_dict.values())
            
            # Obtener periodos académicos del año lectivo
            periodos = PeriodoAcademico.objects.filter(
                año_lectivo=año_lectivo,
                estado=True
            ).select_related('periodo').order_by('periodo__nombre')
            
            periodos_data = [
                {
                    'id': periodo.id,
                    'nombre': periodo.periodo.nombre,
                    'fecha_inicio': periodo.fecha_inicio.strftime('%d/%m/%Y'),
                    'fecha_fin': periodo.fecha_fin.strftime('%d/%m/%Y'),
                    'esta_activo': periodo.estado,
                    'dias_restantes': (periodo.fecha_fin - periodo.fecha_inicio).days if periodo.fecha_fin else 0,
                }
                for periodo in periodos
            ]
            
            # Estadísticas del docente
            total_grados = len(grados)
            total_sedes = len(set([g['sede_id'] for g in grados]))
            
            return JsonResponse({
                'success': True,
                'grados': grados,
                'periodos': periodos_data,
                'docente': {
                    'id': docente.id,
                    'nombre': docente.usuario.get_full_name(),
                    'email': docente.usuario.email or '',
                    'telefono': docente.usuario.telefono or '',
                },
                'estadisticas': {
                    'total_grados': total_grados,
                    'total_sedes': total_sedes,
                    'total_asignaturas': total_asignaturas,
                },
            })
            
        except (AñoLectivo.DoesNotExist, Docente.DoesNotExist) as e:
            return JsonResponse({'error': str(e)}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class CargarEstudiantesCalificacionesView(RoleRequiredMixin, View):
    """Cargar estudiantes para calificar (AJAX)"""
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            asignatura_id = data.get('asignatura_id')
            grado_id = data.get('grado_id')
            sede_id = data.get('sede_id')
            periodo_id = data.get('periodo_id')
            
            if not all([asignatura_id, grado_id, sede_id, periodo_id]):
                return JsonResponse({'error': 'Parámetros incompletos'}, status=400)
            
            # Obtener el año lectivo desde el período
            periodo = PeriodoAcademico.objects.get(id=periodo_id)
            año_lectivo = periodo.año_lectivo
            
            # Obtener asignatura específica
            asignatura_grado = AsignaturaGradoAñoLectivo.objects.get(
                id=asignatura_id,
                grado_año_lectivo__grado_id=grado_id,
                sede_id=sede_id,
                grado_año_lectivo__año_lectivo=año_lectivo
            )
            
            # Obtener estudiantes matriculados
            matriculas = Matricula.objects.filter(
                grado_año_lectivo__grado_id=grado_id,
                sede_id=sede_id,
                año_lectivo=año_lectivo,
                estado__in=['ACT', 'PEN']
            ).select_related(
                'estudiante',
                'estudiante__usuario'
            ).order_by('estudiante__usuario__apellidos', 'estudiante__usuario__nombres')
            
            estudiantes_data = []
            notas_ids = []
            
            for matricula in matriculas:
                estudiante = matricula.estudiante
                
                # Obtener nota existente
                nota_existente = Nota.objects.filter(
                    estudiante=estudiante,
                    asignatura_grado_año_lectivo=asignatura_grado,
                    periodo_academico=periodo
                ).first()
                
                # Obtener logros para esta asignatura, grado y período
                logros = Logro.objects.filter(
                    asignatura=asignatura_grado.asignatura,
                    grado_id=grado_id,
                    periodo_academico=periodo
                ).order_by('tema')
                
                # Obtener calificaciones anteriores del estudiante en esta asignatura
                notas_anteriores = Nota.objects.filter(
                    estudiante=estudiante,
                    asignatura_grado_año_lectivo=asignatura_grado
                ).exclude(periodo_academico=periodo).order_by('periodo_academico__periodo__nombre')
                
                promedio_historico = 0
                if notas_anteriores.exists():
                    promedio_historico = sum([n.calificacion for n in notas_anteriores]) / notas_anteriores.count()
                
                estudiante_data = {
                    'id': estudiante.id,
                    'matricula_id': matricula.id,
                    'codigo_matricula': matricula.codigo_matricula,
                    'nombre_completo': estudiante.usuario.get_full_name(),
                    'numero_documento': estudiante.usuario.numero_documento,
                    'email': estudiante.usuario.email or '',
                    'calificacion': float(nota_existente.calificacion) if nota_existente else 0.0,
                    'nota_id': nota_existente.id if nota_existente else None,
                    'observaciones': nota_existente.observaciones if nota_existente else '',
                    'promedio_historico': round(promedio_historico, 1),
                    'total_notas_anteriores': notas_anteriores.count(),
                    'logros': [
                        {
                            'id': logro.id,
                            'tema': logro.tema,
                            'descripciones': {
                                'superior': logro.descripcion_superior or '',
                                'alto': logro.descripcion_alto or '',
                                'basico': logro.descripcion_basico or '',
                                'bajo': logro.descripcion_bajo or '',
                            }
                        }
                        for logro in logros
                    ]
                }
                
                estudiantes_data.append(estudiante_data)
                if nota_existente:
                    notas_ids.append(nota_existente.id)
            
            # Estadísticas generales
            total_estudiantes = len(estudiantes_data)
            estudiantes_con_nota = len(notas_ids)
            estudiantes_sin_nota = total_estudiantes - estudiantes_con_nota
            
            # Calcular estadísticas de calificaciones existentes
            calificaciones_existentes = [e['calificacion'] for e in estudiantes_data if e['calificacion'] > 0]
            estadisticas_calificaciones = {
                'promedio': round(sum(calificaciones_existentes) / len(calificaciones_existentes), 1) if calificaciones_existentes else 0,
                'maxima': max(calificaciones_existentes) if calificaciones_existentes else 0,
                'minima': min(calificaciones_existentes) if calificaciones_existentes else 0,
                'total_calificadas': len(calificaciones_existentes),
            }
            
            return JsonResponse({
                'success': True,
                'estudiantes': estudiantes_data,
                'asignatura': {
                    'id': asignatura_grado.id,
                    'nombre': asignatura_grado.asignatura.nombre,
                    'area': asignatura_grado.asignatura.area.nombre,
                    'ih': asignatura_grado.asignatura.ih or 'N/A',
                },
                'grado': {
                    'id': grado_id,
                    'nombre': asignatura_grado.grado_año_lectivo.grado.nombre,
                },
                'sede': {
                    'id': sede_id,
                    'nombre': asignatura_grado.sede.nombre,
                },
                'periodo': {
                    'id': periodo.id,
                    'nombre': periodo.periodo.nombre,
                    'fecha_inicio': periodo.fecha_inicio.strftime('%d/%m/%Y'),
                    'fecha_fin': periodo.fecha_fin.strftime('%d/%m/%Y'),
                },
                'estadisticas': {
                    'total_estudiantes': total_estudiantes,
                    'estudiantes_con_nota': estudiantes_con_nota,
                    'estudiantes_sin_nota': estudiantes_sin_nota,
                    'porcentaje_calificados': round((estudiantes_con_nota / total_estudiantes * 100), 1) if total_estudiantes > 0 else 0,
                },
                'calificaciones': estadisticas_calificaciones,
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class GuardarCalificacionesView(RoleRequiredMixin, View):
    """Guardar o actualizar calificaciones (AJAX)"""
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            calificaciones = data.get('calificaciones', [])
            asignatura_grado_id = data.get('asignatura_grado_id')
            periodo_id = data.get('periodo_id')
            
            if not calificaciones:
                return JsonResponse({'error': 'No hay calificaciones para guardar'}, status=400)
            
            # Verificar permisos especiales para Docentes
            if request.user.tipo_usuario.nombre == 'Docente':
                docente = Docente.objects.filter(usuario=request.user.usuario).first()
                if docente:
                    # Verificar que el docente tiene permiso sobre esta asignatura
                    asignatura_grado = AsignaturaGradoAñoLectivo.objects.filter(
                        id=asignatura_grado_id,
                        docente=docente
                    ).exists()
                    if not asignatura_grado:
                        return JsonResponse({'error': 'No tiene permiso para calificar esta asignatura'}, status=403)
            
            resultados = {
                'guardadas': 0,
                'actualizadas': 0,
                'errores': []
            }
            
            for calificacion_data in calificaciones:
                try:
                    estudiante_id = calificacion_data.get('estudiante_id')
                    calificacion_valor = calificacion_data.get('calificacion')
                    observaciones = calificacion_data.get('observaciones', '')
                    nota_id = calificacion_data.get('nota_id')
                    
                    # Validar calificación (0-100)
                    calificacion_valor = float(calificacion_valor)
                    if calificacion_valor < 0 or calificacion_valor > 100:
                        resultados['errores'].append({
                            'estudiante_id': estudiante_id,
                            'error': f'Calificación inválida: {calificacion_valor} (debe ser entre 0 y 100)'
                        })
                        continue
                    
                    # Obtener objetos
                    estudiante = Estudiante.objects.get(id=estudiante_id)
                    asignatura_grado = AsignaturaGradoAñoLectivo.objects.get(id=asignatura_grado_id)
                    periodo = PeriodoAcademico.objects.get(id=periodo_id)
                    
                    if nota_id:
                        # Actualizar nota existente
                        nota = Nota.objects.get(id=nota_id)
                        nota.calificacion = calificacion_valor
                        nota.observaciones = observaciones
                        nota.save()
                        resultados['actualizadas'] += 1
                    else:
                        # Crear nueva nota
                        Nota.objects.create(
                            estudiante=estudiante,
                            asignatura_grado_año_lectivo=asignatura_grado,
                            periodo_academico=periodo,
                            calificacion=calificacion_valor,
                            observaciones=observaciones
                        )
                        resultados['guardadas'] += 1
                        
                except Exception as e:
                    resultados['errores'].append({
                        'estudiante_id': estudiante_id,
                        'error': str(e)
                    })
            
            # Registrar auditoría
            if request.user.is_authenticated and hasattr(request.user, 'usuario'):
                from gestioncolegio.models import AuditoriaSistema
                
                AuditoriaSistema.objects.create(
                    usuario=request.user.usuario,
                    accion='modificacion_masiva',
                    modelo_afectado='Nota',
                    descripcion=f"Guardadas {resultados['guardadas']} nuevas y actualizadas {resultados['actualizadas']} calificaciones",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            
            return JsonResponse({
                'success': True,
                'resultados': resultados,
                'mensaje': f"Proceso completado: {resultados['guardadas']} nuevas, {resultados['actualizadas']} actualizadas"
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class ReporteCalificacionesView(RoleRequiredMixin, TemplateView):
    """Reporte de calificaciones por período"""
    template_name = 'administrador/calificaciones/reporte_calificaciones.html'
    allowed_roles = ['Administrador', 'Rector']
    
    def get(self, request, periodo_id):
        periodo = get_object_or_404(PeriodoAcademico, id=periodo_id)
        
        # Obtener todas las calificaciones del período
        calificaciones = Nota.objects.filter(
            periodo_academico=periodo
        ).select_related(
            'estudiante__usuario',
            'asignatura_grado_año_lectivo__asignatura',
            'asignatura_grado_año_lectivo__grado_año_lectivo__grado',
            'asignatura_grado_año_lectivo__grado_año_lectivo__año_lectivo__sede'
        ).order_by(
            'asignatura_grado_año_lectivo__grado_año_lectivo__grado__nombre',
            'estudiante__usuario__apellidos'
        )
        
        # Estadísticas
        total_calificaciones = calificaciones.count()
        total_estudiantes = calificaciones.values('estudiante').distinct().count()
        total_asignaturas = calificaciones.values('asignatura_grado_año_lectivo__asignatura').distinct().count()
        total_grados = calificaciones.values('asignatura_grado_año_lectivo__grado_año_lectivo__grado').distinct().count()
        
        # Calcular promedios
        if total_calificaciones > 0:
            promedio_general = calificaciones.aggregate(Avg('calificacion'))['calificacion__avg']
            calificacion_maxima = calificaciones.aggregate(Max('calificacion'))['calificacion__max']
            calificacion_minima = calificaciones.aggregate(Min('calificacion'))['calificacion__min']
        else:
            promedio_general = calificacion_maxima = calificacion_minima = 0
        
        contexto = {
            'periodo': periodo,
            'calificaciones': calificaciones,
            'total_calificaciones': total_calificaciones,
            'total_estudiantes': total_estudiantes,
            'total_asignaturas': total_asignaturas,
            'total_grados': total_grados,
            'promedio_general': round(promedio_general, 1) if promedio_general else 0,
            'calificacion_maxima': round(calificacion_maxima, 1) if calificacion_maxima else 0,
            'calificacion_minima': round(calificacion_minima, 1) if calificacion_minima else 0,
            'title': f'Reporte de Calificaciones - {periodo.periodo.nombre} ({periodo.año_lectivo.anho})',
        }
        
        return render(request, self.template_name, contexto)


class ExportarCalificacionesView(RoleRequiredMixin, View):
    """Exportar calificaciones a Excel"""
    allowed_roles = ['Administrador', 'Rector']
    
    def get(self, request):
        # Implementar exportación a Excel
        pass


class CalificacionesAjaxView(RoleRequiredMixin, View):
    """Vistas AJAX para calificaciones"""
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get(self, request):
        tipo = request.GET.get('tipo')
        
        if tipo == 'estadisticas_docente':
            # Obtener estadísticas de un docente
            docente_id = request.GET.get('docente_id')
            año_lectivo_id = request.GET.get('año_lectivo_id')
            
            try:
                docente = Docente.objects.get(id=docente_id)
                año_lectivo = AñoLectivo.objects.get(id=año_lectivo_id)
                
                # Calificaciones asignadas por el docente
                calificaciones = Nota.objects.filter(
                    asignatura_grado_año_lectivo__docente=docente,
                    periodo_academico__año_lectivo=año_lectivo
                ).aggregate(
                    total=Count('id'),
                    promedio=Avg('calificacion'),
                    maximo=Max('calificacion'),
                    minimo=Min('calificacion')
                )
                
                # Asignaturas del docente
                asignaturas = AsignaturaGradoAñoLectivo.objects.filter(
                    docente=docente,
                    grado_año_lectivo__año_lectivo=año_lectivo
                ).count()
                
                # Estudiantes calificados
                estudiantes = Nota.objects.filter(
                    asignatura_grado_año_lectivo__docente=docente,
                    periodo_academico__año_lectivo=año_lectivo
                ).values('estudiante').distinct().count()
                
                data = {
                    'success': True,
                    'docente': docente.usuario.get_full_name(),
                    'estadisticas': {
                        'total_calificaciones': calificaciones['total'] or 0,
                        'promedio_calificaciones': round(calificaciones['promedio'] or 0, 1),
                        'calificacion_maxima': round(calificaciones['maximo'] or 0, 1),
                        'calificacion_minima': round(calificaciones['minimo'] or 0, 1),
                        'total_asignaturas': asignaturas,
                        'total_estudiantes': estudiantes,
                    }
                }
                return JsonResponse(data)
                
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
        
        return JsonResponse({'error': 'Tipo de consulta no válido'}, status=400)