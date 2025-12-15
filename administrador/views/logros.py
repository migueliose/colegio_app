"""
Módulo de Logros Académicos - App Administrador
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View, TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q, Count
import json

from gestioncolegio.mixins import RoleRequiredMixin
from gestioncolegio.models import AñoLectivo, Sede
from usuarios.models import Docente
from matricula.models import GradoAñoLectivo, AsignaturaGradoAñoLectivo, PeriodoAcademico
from estudiantes.models import Estudiante
from academico.models import Logro, Grado, Asignatura, Periodo, Area, NivelEscolar


class GestionLogrosView(RoleRequiredMixin, TemplateView):
    """Vista principal para gestión de logros académicos"""
    template_name = 'administrador/logros/gestion_logros.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener años lectivos activos
        #años_lectivos = AñoLectivo.objects.filter(estado=True).order_by('-anho')
        años_lectivos = AñoLectivo.objects.filter().order_by('-anho')
        # Estadísticas generales
        total_logros = Logro.objects.count()
        total_asignaturas = Asignatura.objects.count()
        total_grados = Grado.objects.count()
        
        context.update({
            'años_lectivos': años_lectivos,
            'total_logros': total_logros,
            'total_asignaturas': total_asignaturas,
            'total_grados': total_grados,
            'title': 'Gestión de Logros Académicos',
        })
        
        return context

class ObtenerGradosPorAñoView(RoleRequiredMixin, View):
    """Obtener grados por año lectivo (AJAX) - VERSIÓN MEJORADA"""
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get(self, request):
        año_lectivo_id = request.GET.get('año_lectivo_id')
        
        if not año_lectivo_id:
            return JsonResponse({'error': 'Año lectivo no especificado'}, status=400)
        
        try:
            año_lectivo = AñoLectivo.objects.get(id=año_lectivo_id)
            
            # Obtener grados del año lectivo
            grados_año = GradoAñoLectivo.objects.filter(
                año_lectivo=año_lectivo,
                estado=True
            ).select_related('grado', 'grado__nivel_escolar')
            
            grados_data = []
            for grado_año in grados_año:
                # Contar asignaturas para este grado en este año
                total_asignaturas = AsignaturaGradoAñoLectivo.objects.filter(
                    grado_año_lectivo=grado_año
                ).count()
                
                # Contar logros existentes para este grado
                total_logros = Logro.objects.filter(
                    grado=grado_año.grado
                ).count()
                
                grados_data.append({
                    'id': grado_año.grado.id,
                    'nombre': grado_año.grado.nombre,
                    'nivel_escolar': grado_año.grado.nivel_escolar.nombre if grado_año.grado.nivel_escolar else 'Sin nivel',
                    'total_asignaturas': total_asignaturas,
                    'total_logros': total_logros,
                    'año_lectivo': año_lectivo.anho,
                    'sede': año_lectivo.sede.nombre if año_lectivo.sede else 'Sin sede',
                })
            
            # Estadísticas generales
            total_grados = len(grados_data)
            
            # Calcular promedio de logros
            promedio_logros = 0
            if total_grados > 0:
                total_logros_sum = sum(g['total_logros'] for g in grados_data)
                promedio_logros = round(total_logros_sum / total_grados, 1)
            
            return JsonResponse({
                'success': True,
                'grados': grados_data,
                'año_lectivo': {
                    'id': año_lectivo.id,
                    'anho': año_lectivo.anho,
                    'sede': año_lectivo.sede.nombre if año_lectivo.sede else 'Sin sede',
                },
                'estadisticas': {
                    'total_grados': total_grados,
                    'promedio_logros': promedio_logros,
                },
            })
            
        except AñoLectivo.DoesNotExist:
            return JsonResponse({'error': 'Año lectivo no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)

class ObtenerAsignaturasPorGradoView(RoleRequiredMixin, View):
    """Obtener asignaturas por grado (AJAX) - VERSIÓN CORREGIDA"""
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get(self, request):
        grado_id = request.GET.get('grado_id')
        año_lectivo_id = request.GET.get('año_lectivo_id')
        
        if not grado_id or not año_lectivo_id:
            return JsonResponse({'error': 'Parámetros incompletos'}, status=400)
        
        try:
            año_lectivo = AñoLectivo.objects.get(id=año_lectivo_id)
            grado = Grado.objects.get(id=grado_id)
            
            # Obtener asignaturas para este grado en el año lectivo
            asignaturas_grado = AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo__grado=grado,
                grado_año_lectivo__año_lectivo=año_lectivo
            ).select_related(
                'asignatura',
                'asignatura__area',
                'sede'
            ).distinct()
            
            # Agrupar asignaturas (pueden estar en múltiples sedes)
            asignaturas_dict = {}
            for ag in asignaturas_grado:
                asignatura = ag.asignatura
                if asignatura.id not in asignaturas_dict:
                    # Contar logros para esta asignatura y grado
                    total_logros = Logro.objects.filter(
                        asignatura=asignatura,
                        grado=grado
                    ).count()
                    
                    asignaturas_dict[asignatura.id] = {
                        'id': asignatura.id,
                        'nombre': asignatura.nombre,
                        'area': asignatura.area.nombre if asignatura.area else '',
                        'ih': asignatura.ih or 'N/A',
                        'total_logros': total_logros,
                        'sedes': []
                    }
                
                # Agregar sede a la lista
                if ag.sede.nombre not in asignaturas_dict[asignatura.id]['sedes']:
                    asignaturas_dict[asignatura.id]['sedes'].append(ag.sede.nombre)
            
            asignaturas_data = list(asignaturas_dict.values())
            
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
                }
                for periodo in periodos
            ]
            
            # CORRECCIÓN: Asegurarnos de que año_lectivo tiene los datos necesarios
            return JsonResponse({
                'success': True,
                'asignaturas': asignaturas_data,
                'periodos': periodos_data,
                'grado': {
                    'id': grado.id,
                    'nombre': grado.nombre,
                    'nivel': grado.nivel_escolar.nombre if grado.nivel_escolar else '',
                },
                # CORRECCIÓN: Enviar año_lectivo como objeto con los datos necesarios
                'año_lectivo': {
                    'id': año_lectivo.id,
                    'anho': año_lectivo.anho,  # ¡AQUÍ ESTABA EL ERROR! Asegurar que existe
                    'sede': año_lectivo.sede.nombre if año_lectivo.sede else '',
                },
            })
            
        except AñoLectivo.DoesNotExist:
            return JsonResponse({'error': 'Año lectivo no encontrado'}, status=404)
        except Grado.DoesNotExist:
            return JsonResponse({'error': 'Grado no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

class CargarLogrosView(RoleRequiredMixin, View):
    """Cargar logros existentes (AJAX)"""
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get(self, request):
        try:
            asignatura_id = request.GET.get('asignatura_id')
            grado_id = request.GET.get('grado_id')
            periodo_id = request.GET.get('periodo_id')
            
            if not all([asignatura_id, grado_id, periodo_id]):
                return JsonResponse({'error': 'Parámetros incompletos'}, status=400)
            
            # Obtener objetos
            asignatura = Asignatura.objects.get(id=asignatura_id)
            grado = Grado.objects.get(id=grado_id)
            periodo = PeriodoAcademico.objects.get(id=periodo_id)
            
            # Obtener logros existentes
            logros = Logro.objects.filter(
                asignatura=asignatura,
                grado=grado,
                periodo_academico=periodo
            ).order_by('tema')
            
            logros_data = []
            for logro in logros:
                logros_data.append({
                    'id': logro.id,
                    'tema': logro.tema or '',
                    'descripcion_superior': logro.descripcion_superior or '',
                    'descripcion_alto': logro.descripcion_alto or '',
                    'descripcion_basico': logro.descripcion_basico or '',
                    'descripcion_bajo': logro.descripcion_bajo or '',
                    'created_at': logro.created_at.strftime('%d/%m/%Y %H:%M'),
                    'updated_at': logro.updated_at.strftime('%d/%m/%Y %H:%M') if logro.updated_at else '',
                })
            
            return JsonResponse({
                'success': True,
                'logros': logros_data,
                'total': len(logros_data),
                'asignatura': {
                    'id': asignatura.id,
                    'nombre': asignatura.nombre,
                    'area': asignatura.area.nombre if asignatura.area else '',
                },
                'grado': {
                    'id': grado.id,
                    'nombre': grado.nombre,
                },
                'periodo': {
                    'id': periodo.id,
                    'nombre': periodo.periodo.nombre,
                },
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class GuardarLogroView(RoleRequiredMixin, View):
    """Guardar o actualizar un logro (AJAX)"""
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            logro_id = data.get('logro_id')
            asignatura_id = data.get('asignatura_id')
            grado_id = data.get('grado_id')
            periodo_id = data.get('periodo_id')
            tema = data.get('tema', '').strip()
            descripcion_superior = data.get('descripcion_superior', '').strip()
            descripcion_alto = data.get('descripcion_alto', '').strip()
            descripcion_basico = data.get('descripcion_basico', '').strip()
            descripcion_bajo = data.get('descripcion_bajo', '').strip()
            
            # Validaciones
            if not all([asignatura_id, grado_id, periodo_id]):
                return JsonResponse({'error': 'Parámetros incompletos'}, status=400)
            
            if not tema:
                return JsonResponse({'error': 'El tema es requerido'}, status=400)
            
            # Obtener objetos
            asignatura = Asignatura.objects.get(id=asignatura_id)
            grado = Grado.objects.get(id=grado_id)
            periodo = PeriodoAcademico.objects.get(id=periodo_id)
            
            if logro_id:
                # Actualizar logro existente
                logro = Logro.objects.get(id=logro_id)
                logro.tema = tema
                logro.descripcion_superior = descripcion_superior
                logro.descripcion_alto = descripcion_alto
                logro.descripcion_basico = descripcion_basico
                logro.descripcion_bajo = descripcion_bajo
                logro.save()
                
                accion = 'actualizado'
                mensaje = 'Logro actualizado exitosamente'
            else:
                # Crear nuevo logro
                logro = Logro.objects.create(
                    asignatura=asignatura,
                    grado=grado,
                    periodo_academico=periodo,
                    tema=tema,
                    descripcion_superior=descripcion_superior,
                    descripcion_alto=descripcion_alto,
                    descripcion_basico=descripcion_basico,
                    descripcion_bajo=descripcion_bajo
                )
                
                accion = 'creado'
                mensaje = 'Logro creado exitosamente'
            
            # Registrar auditoría
            if request.user.is_authenticated and hasattr(request.user, 'usuario'):
                from gestioncolegio.models import AuditoriaSistema
                
                AuditoriaSistema.objects.create(
                    usuario=request.user.usuario,
                    accion='creacion' if not logro_id else 'modificacion',
                    modelo_afectado='Logro',
                    objeto_id=str(logro.id),
                    descripcion=f"Logro {accion}: {tema[:50]}... para {asignatura.nombre} - {grado.nombre}",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            
            return JsonResponse({
                'success': True,
                'logro_id': logro.id,
                'mensaje': mensaje,
                'accion': accion,
                'logro': {
                    'id': logro.id,
                    'tema': logro.tema,
                    'created_at': logro.created_at.strftime('%d/%m/%Y %H:%M'),
                    'updated_at': logro.updated_at.strftime('%d/%m/%Y %H:%M'),
                }
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class EliminarLogroView(RoleRequiredMixin, View):
    """Eliminar un logro (AJAX)"""
    allowed_roles = ['Administrador', 'Rector']
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            logro_id = data.get('logro_id')
            
            if not logro_id:
                return JsonResponse({'error': 'ID de logro requerido'}, status=400)
            
            logro = Logro.objects.get(id=logro_id)
            
            # Guardar información para auditoría
            logro_info = {
                'tema': logro.tema,
                'asignatura': logro.asignatura.nombre,
                'grado': logro.grado.nombre,
                'periodo': logro.periodo_academico.periodo.nombre,
            }
            
            # Eliminar logro
            logro.delete()
            
            # Registrar auditoría
            if request.user.is_authenticated and hasattr(request.user, 'usuario'):
                from gestioncolegio.models import AuditoriaSistema
                
                AuditoriaSistema.objects.create(
                    usuario=request.user.usuario,
                    accion='eliminacion',
                    modelo_afectado='Logro',
                    descripcion=f"Logro eliminado: {logro_info['tema'][:50]}... para {logro_info['asignatura']} - {logro_info['grado']}",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            
            return JsonResponse({
                'success': True,
                'mensaje': 'Logro eliminado exitosamente',
                'logro_eliminado': logro_info
            })
            
        except Logro.DoesNotExist:
            return JsonResponse({'error': 'Logro no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class CopiarLogrosView(RoleRequiredMixin, View):
    """Copiar logros de un período a otro (AJAX)"""
    allowed_roles = ['Administrador', 'Rector']
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            origen_asignatura_id = data.get('origen_asignatura_id')
            origen_grado_id = data.get('origen_grado_id')
            origen_periodo_id = data.get('origen_periodo_id')
            destino_periodo_id = data.get('destino_periodo_id')
            
            if not all([origen_asignatura_id, origen_grado_id, origen_periodo_id, destino_periodo_id]):
                return JsonResponse({'error': 'Parámetros incompletos'}, status=400)
            
            # Verificar que los períodos sean diferentes
            if origen_periodo_id == destino_periodo_id:
                return JsonResponse({'error': 'El período destino debe ser diferente al origen'}, status=400)
            
            # Obtener objetos
            origen_periodo = PeriodoAcademico.objects.get(id=origen_periodo_id)
            destino_periodo = PeriodoAcademico.objects.get(id=destino_periodo_id)
            
            # Obtener logros a copiar
            logros_origen = Logro.objects.filter(
                asignatura_id=origen_asignatura_id,
                grado_id=origen_grado_id,
                periodo_academico=origen_periodo
            )
            
            if not logros_origen.exists():
                return JsonResponse({'error': 'No hay logros para copiar'}, status=400)
            
            # Verificar si ya existen logros en el destino
            logros_destino_existentes = Logro.objects.filter(
                asignatura_id=origen_asignatura_id,
                grado_id=origen_grado_id,
                periodo_academico=destino_periodo
            )
            
            logros_copiados = 0
            logros_omitidos = 0
            
            # Copiar cada logro
            for logro_origen in logros_origen:
                # Verificar si ya existe un logro con el mismo tema
                existe = logros_destino_existentes.filter(
                    tema=logro_origen.tema
                ).exists()
                
                if not existe:
                    Logro.objects.create(
                        asignatura=logro_origen.asignatura,
                        grado=logro_origen.grado,
                        periodo_academico=destino_periodo,
                        tema=logro_origen.tema,
                        descripcion_superior=logro_origen.descripcion_superior,
                        descripcion_alto=logro_origen.descripcion_alto,
                        descripcion_basico=logro_origen.descripcion_basico,
                        descripcion_bajo=logro_origen.descripcion_bajo
                    )
                    logros_copiados += 1
                else:
                    logros_omitidos += 1
            
            # Registrar auditoría
            if request.user.is_authenticated and hasattr(request.user, 'usuario'):
                from gestioncolegio.models import AuditoriaSistema
                
                AuditoriaSistema.objects.create(
                    usuario=request.user.usuario,
                    accion='creacion_masiva',
                    modelo_afectado='Logro',
                    descripcion=f"Copiados {logros_copiados} logros de {origen_periodo.periodo.nombre} a {destino_periodo.periodo.nombre}",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            
            return JsonResponse({
                'success': True,
                'mensaje': f'Copiados {logros_copiados} logros exitosamente',
                'estadisticas': {
                    'copiados': logros_copiados,
                    'omitidos': logros_omitidos,
                    'total_origen': logros_origen.count()
                }
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class ExportarLogrosView(RoleRequiredMixin, View):
    """Exportar logros a diferentes formatos"""
    allowed_roles = ['Administrador', 'Rector']
    
    def get(self, request):
        # Implementar exportación a PDF, Excel, etc.
        pass


class LogrosAjaxView(RoleRequiredMixin, View):
    """Vistas AJAX adicionales para logros"""
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get(self, request):
        tipo = request.GET.get('tipo')
        
        if tipo == 'estadisticas_logros':
            # Obtener estadísticas de logros
            año_lectivo_id = request.GET.get('año_lectivo_id')
            
            try:
                año_lectivo = AñoLectivo.objects.get(id=año_lectivo_id)
                
                # Logros por grado en este año
                logros_por_grado = Logro.objects.filter(
                    periodo_academico__año_lectivo=año_lectivo
                ).values(
                    'grado__nombre'
                ).annotate(
                    total=Count('id')
                ).order_by('grado__nombre')
                
                # Logros por período
                logros_por_periodo = Logro.objects.filter(
                    periodo_academico__año_lectivo=año_lectivo
                ).values(
                    'periodo_academico__periodo__nombre'
                ).annotate(
                    total=Count('id')
                ).order_by('periodo_academico__periodo__nombre')
                
                # Logros por área
                logros_por_area = Logro.objects.filter(
                    periodo_academico__año_lectivo=año_lectivo
                ).values(
                    'asignatura__area__nombre'
                ).annotate(
                    total=Count('id')
                ).order_by('asignatura__area__nombre')
                
                data = {
                    'success': True,
                    'año_lectivo': año_lectivo.anho,
                    'estadisticas': {
                        'logros_por_grado': list(logros_por_grado),
                        'logros_por_periodo': list(logros_por_periodo),
                        'logros_por_area': list(logros_por_area),
                    }
                }
                return JsonResponse(data)
                
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
        
        return JsonResponse({'error': 'Tipo de consulta no válido'}, status=400)