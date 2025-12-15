"""
Vistas de dashboard - VERSIÓN SIN SERVICIOS
"""
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.contrib import messages
from datetime import timedelta

# Mixins
from gestioncolegio.mixins import RoleRequiredMixin

# Modelos básicos
from estudiantes.models import Estudiante, Matricula, Nota, Acudiente
from usuarios.models import Docente, Usuario
from gestioncolegio.models import AñoLectivo, Sede, Colegio, AuditoriaSistema
from matricula.models import AsignaturaGradoAñoLectivo, PeriodoAcademico
from django.utils import timezone
from comportamiento.models import Asistencia, Comportamiento


class DashboardView(RoleRequiredMixin, TemplateView):
    """Dashboard principal - SIN SERVICIOS"""
    template_name = 'gestioncolegio/dashboard.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente', 'Estudiante', 'Acudiente']
    
    def get(self, request, *args, **kwargs):
        """Redirigir según rol"""
        user = request.user
        
        # Verificar si el usuario tiene tipo_usuario asignado
        if hasattr(user, 'tipo_usuario') and user.tipo_usuario:
            rol = user.tipo_usuario.nombre
            
            dashboards = {
                'Estudiante': 'dashboard_estudiante',
                'Acudiente': 'dashboard_acudiente', 
                'Docente': 'dashboard_docente',
                'Administrador': 'dashboard_administrador',
                'Rector': 'dashboard_rector'
            }
            
            if rol in dashboards:
                return redirect('gestioncolegio:' + dashboards[rol])
        
        # Si no tiene tipo_usuario o es None, verificar si es superuser
        elif user.is_superuser:
            return redirect('gestioncolegio:dashboard_administrador')
        
        # Redirigir a login si no está autenticado
        elif not user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(self.request.get_full_path())
        
        # Si está autenticado pero no tiene tipo_usuario, mostrar dashboard básico
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Datos básicos
        context['año_lectivo_actual'] = AñoLectivo.objects.filter(estado=True).first()
        return context

class DashboardAcudienteView(RoleRequiredMixin, TemplateView):
    """Dashboard acudiente - COMPLETO"""
    template_name = 'acudiente/dashboard_acudiente.html'
    allowed_roles = ['Acudiente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Obtener acudientes relacionados con el usuario actual
            acudientes = Acudiente.objects.filter(
                acudiente=self.request.user
            ).select_related(
                'estudiante__usuario'  # Solo el usuario del estudiante
            )
            
            if not acudientes.exists():
                messages.warning(self.request, "No tiene estudiantes asignados como acudiente")
                context['user_acudientes'] = []  # Cambiado a user_acudientes para el menú
                context['estudiantes_acargo'] = []
                context['estadisticas_generales'] = {}
                context['año_lectivo_actual'] = None
                return context
            
            # Obtener año lectivo actual
            año_lectivo_actual = AñoLectivo.objects.filter(estado=True).first()
            
            # Obtener matrículas activas para optimizar
            estudiante_ids = [a.estudiante.id for a in acudientes]
            matriculas_activas = {}
            
            if año_lectivo_actual:
                matriculas = Matricula.objects.filter(
                    estudiante_id__in=estudiante_ids,
                    año_lectivo=año_lectivo_actual,
                    estado__in=['ACT', 'PEN']
                ).select_related(
                    'grado_año_lectivo__grado',
                    'sede',
                    'año_lectivo'
                )
                
                for matricula in matriculas:
                    matriculas_activas[matricula.estudiante_id] = {
                        'grado': matricula.grado_año_lectivo.grado.nombre,
                        'sede': matricula.sede.nombre,
                        'matricula_obj': matricula
                    }
            
            # Preparar datos para estudiantes
            estudiantes_data = []
            
            for acudiente_obj in acudientes:
                estudiante_obj = acudiente_obj.estudiante
                
                # Obtener matrícula actual si existe
                matricula_info = matriculas_activas.get(estudiante_obj.id)
                
                estudiante_info = {
                    'acudiente': acudiente_obj,
                    'estudiante': estudiante_obj,
                    'matricula_info': matricula_info,  # Información de matrícula
                    'parentesco': acudiente_obj.parentesco,
                    'notas_recientes': self.get_notas_recientes(estudiante_obj),
                    'faltas_recientes': self.get_faltas_recientes(estudiante_obj),
                    'comportamientos_recientes': self.get_comportamientos_recientes(estudiante_obj),
                    'promedio_general': self.get_promedio_general(estudiante_obj),
                    'estado_matricula': self.get_estado_matricula(estudiante_obj),
                }
                estudiantes_data.append(estudiante_info)
            
            # Contexto para el menú
            context['user_acudientes'] = acudientes  # Para el menú
            context['matriculas_activas'] = matriculas_activas  # Información de matrículas
            
            # Contexto para el dashboard
            context['estudiantes_acargo'] = estudiantes_data
            context['acudientes'] = acudientes  # También puedes mantener esto
            
            # Año lectivo actual (importante para documentos PDF)
            context['año_lectivo_actual'] = año_lectivo_actual
            
            # Período académico actual
            if año_lectivo_actual:
                periodo_actual = PeriodoAcademico.objects.filter(
                    año_lectivo=año_lectivo_actual,
                    estado=True
                ).first()
                context['periodo_actual'] = periodo_actual
            
            # Calcular estadísticas
            context['estadisticas_generales'] = self.calcular_estadisticas_generales(estudiantes_data)
            
            # Fecha actual
            context['fecha_actual'] = timezone.now()
            
        except Exception as e:
            messages.error(self.request, f"Error al cargar dashboard: {str(e)}")
            print(f"Error en dashboard acudiente: {e}")
            context['user_acudientes'] = []  # Asegurar que existe
            context['estudiantes_acargo'] = []
            context['estadisticas_generales'] = {}
            context['año_lectivo_actual'] = None
        
        return context
    
    def get_notas_recientes(self, estudiante):
        """Obtiene las notas más recientes del estudiante"""
        try:
            # Obtener año lectivo actual
            año_lectivo_actual = AñoLectivo.objects.filter(estado=True).first()
            if not año_lectivo_actual:
                return []
            
            # Obtener notas del año actual
            notas = Nota.objects.filter(
                estudiante=estudiante,
                periodo_academico__año_lectivo=año_lectivo_actual
            ).select_related(
                'asignatura_grado_año_lectivo__asignatura',
                'periodo_academico__periodo'
            ).order_by('-created_at')[:5]
            
            return notas
            
        except Exception as e:
            print(f"Error obteniendo notas recientes: {e}")
            return []
    
    def get_faltas_recientes(self, estudiante):
        """Obtiene las faltas recientes del estudiante"""
        try:
            # Obtener año lectivo actual
            año_lectivo_actual = AñoLectivo.objects.filter(estado=True).first()
            if not año_lectivo_actual:
                return []
            
            # Obtener faltas (asistencias con estado 'F') del último mes
            hace_un_mes = timezone.now() - timezone.timedelta(days=30)
            
            faltas = Asistencia.objects.filter(
                estudiante=estudiante,
                estado='F',  # Faltas
                periodo_academico__año_lectivo=año_lectivo_actual,
                fecha__gte=hace_un_mes
            ).select_related('periodo_academico__periodo').order_by('-fecha')[:5]
            
            return faltas
            
        except Exception as e:
            print(f"Error obteniendo faltas recientes: {e}")
            return []
    
    def get_comportamientos_recientes(self, estudiante):
        """Obtiene los comportamientos recientes del estudiante"""
        try:
            # Obtener año lectivo actual
            año_lectivo_actual = AñoLectivo.objects.filter(estado=True).first()
            if not año_lectivo_actual:
                return []
            
            # Obtener comportamientos del último mes
            hace_un_mes = timezone.now() - timezone.timedelta(days=30)
            
            comportamientos = Comportamiento.objects.filter(
                estudiante=estudiante,
                periodo_academico__año_lectivo=año_lectivo_actual,
                fecha__gte=hace_un_mes
            ).select_related(
                'docente__usuario',
                'periodo_academico__periodo'
            ).order_by('-fecha')[:5]
            
            return comportamientos
            
        except Exception as e:
            print(f"Error obteniendo comportamientos recientes: {e}")
            return []
    
    def get_promedio_general(self, estudiante):
        """Calcula el promedio general del estudiante"""
        try:
            # Obtener año lectivo actual
            año_lectivo_actual = AñoLectivo.objects.filter(estado=True).first()
            if not año_lectivo_actual:
                return 0.0
            
            # Obtener todas las notas del año
            notas = Nota.objects.filter(
                estudiante=estudiante,
                periodo_academico__año_lectivo=año_lectivo_actual,
                calificacion__isnull=False
            ).exclude(calificacion=0)
            
            if notas.exists():
                total = sum(float(nota.calificacion) for nota in notas)
                promedio = total / notas.count()
                return round(promedio, 1)
            
            return 0.0
            
        except Exception as e:
            print(f"Error calculando promedio: {e}")
            return 0.0
    
    def get_estado_matricula(self, estudiante):
        """Obtiene el estado de la matrícula del estudiante"""
        try:
            matricula = estudiante.matricula_actual
            if matricula:
                return {
                    'estado': matricula.get_estado_display(),
                    'grado': matricula.grado_año_lectivo.grado.nombre,
                    'sede': matricula.sede.nombre,
                    'año_lectivo': matricula.año_lectivo.anho,
                    'matricula_obj': matricula
                }
            return None
            
        except Exception as e:
            print(f"Error obteniendo estado de matrícula: {e}")
            return None
    
    def calcular_estadisticas_generales(self, estudiantes_data):
        """Calcula estadísticas generales de todos los estudiantes"""
        estadisticas = {
            'total_estudiantes': len(estudiantes_data),
            'estudiantes_con_notas': 0,
            'estudiantes_con_faltas': 0,
            'estudiantes_con_buen_rendimiento': 0,
            'estudiantes_con_rendimiento_regular': 0,
            'estudiantes_con_rendimiento_bajo': 0,
            'total_faltas': 0,
            'promedio_general': 0.0,
        }
        
        if not estudiantes_data:
            return estadisticas
        
        # Calcular estadísticas
        promedios = []
        for estudiante_info in estudiantes_data:
            # Contar estudiantes con notas
            if estudiante_info['notas_recientes']:
                estadisticas['estudiantes_con_notas'] += 1
            
            # Contar estudiantes con faltas
            if estudiante_info['faltas_recientes']:
                estadisticas['estudiantes_con_faltas'] += 1
                estadisticas['total_faltas'] += len(estudiante_info['faltas_recientes'])
            
            # Categorizar por rendimiento
            promedio = estudiante_info['promedio_general']
            promedios.append(promedio)
            
            if promedio >= 4.0:
                estadisticas['estudiantes_con_buen_rendimiento'] += 1
            elif promedio >= 3.0:
                estadisticas['estudiantes_con_rendimiento_regular'] += 1
            elif promedio > 0:
                estadisticas['estudiantes_con_rendimiento_bajo'] += 1
        
        # Calcular promedio general de todos los estudiantes
        if promedios:
            estadisticas['promedio_general'] = round(sum(promedios) / len(promedios), 1)
        
        return estadisticas

class DashboardRectorView(RoleRequiredMixin, TemplateView):
    """Dashboard rector - SIN SERVICIOS"""
    template_name = 'gestioncolegio/dashboard_rector.html'
    allowed_roles = ['Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas para rector
        context['total_estudiantes'] = Estudiante.objects.filter(estado=True).count()
        context['total_docentes'] = Docente.objects.filter(estado=True).count()
        context['total_sedes'] = Sede.objects.filter(estado=True).count()
        
        # Matrículas por año
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if año_actual:
            context['matriculas_actual'] = Matricula.objects.filter(
                año_lectivo=año_actual
            ).count()
        
        return context
    
class DashboardAdministradorView(RoleRequiredMixin, TemplateView):
    """Dashboard administrador"""
    template_name = 'administrador/dashboard_administrador.html'
    allowed_roles = ['Administrador']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Agregar el usuario actual al contexto
        context['current_user'] = self.request.user
        
        # Estadísticas básicas
        context['total_usuarios'] = Usuario.objects.filter(is_active=True).count()
        context['total_estudiantes'] = Estudiante.objects.filter(estado=True).count()
        context['total_docentes'] = Docente.objects.filter(estado=True).count()
        context['total_matriculas'] = Matricula.objects.filter(estado='ACT').count()
        
        # Año actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if año_actual:
            context['año_lectivo_actual'] = año_actual
            context['matriculas_actual'] = Matricula.objects.filter(
                año_lectivo=año_actual,
                estado='ACT'
            ).count()
        else:
            context['matriculas_actual'] = 0
        
        # Información del colegio
        colegio_info = Colegio.objects.filter(estado=True).first()
        if colegio_info:
            context['colegio_info'] = colegio_info
        
        # Últimas actividades (auditoría)
        context['ultimas_actividades'] = AuditoriaSistema.objects.select_related(
            'usuario'
        ).order_by('-created_at')[:10]
        
        return context

class DashboardDocenteView(RoleRequiredMixin, TemplateView):
    """Dashboard docente - VERSIÓN OPTIMIZADA"""
    template_name = 'docentes/dashboard_docente.html'
    allowed_roles = ['Docente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            docente = Docente.objects.get(usuario=self.request.user)
            context['docente'] = docente
            
            # Obtener año lectivo actual
            from gestioncolegio.models import AñoLectivo
            año_lectivo_actual = AñoLectivo.objects.filter(estado=True).first()
            
            if not año_lectivo_actual:
                return self.get_valores_por_defecto()
            
            # 1. Asignaturas con paginación
            context.update(self.obtener_asignaturas_paginadas(docente))
            
            # 2. Estadísticas principales
            context.update(self.calcular_estadisticas_principales(docente, año_lectivo_actual))
            
            # 3. Detalle de calificaciones pendientes por periodo
            if context.get('periodo_actual'):
                context['detalle_pendientes'] = self.calcular_detalle_pendientes(
                    docente, año_lectivo_actual, context['periodo_actual']
                )
            
        except Docente.DoesNotExist:
            messages.error(self.request, "Perfil de docente no encontrado")
            context.update(self.get_valores_por_defecto())
        
        return context
    
    def obtener_asignaturas_paginadas(self, docente):
        """Obtiene asignaturas del docente con paginación"""
        mis_asignaturas_query = docente.asignaturas_dictadas.filter(
            grado_año_lectivo__año_lectivo__estado=True
        ).select_related(
            'asignatura',
            'grado_año_lectivo__grado',
            'sede'
        ).order_by('asignatura__nombre')
        
        page = self.request.GET.get('page_asignaturas', 1)
        paginator = Paginator(mis_asignaturas_query, 6)
        
        try:
            asignaturas_paginadas = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            asignaturas_paginadas = paginator.page(1)
        
        return {
            'mis_asignaturas': asignaturas_paginadas,
            'asignaturas_paginator': paginator
        }
    
    def calcular_estadisticas_principales(self, docente, año_lectivo_actual):
        """Calcula las estadísticas principales con una sola consulta optimizada"""
        from estudiantes.models import Matricula, Nota
        from matricula.models import PeriodoAcademico
        
        resultados = {
            'total_asignaturas': 0,
            'total_estudiantes': 0,
            'calificaciones_pendientes': 0,
            'periodo_actual': None,
            'grados_dictados': []
        }
        
        try:
            # 1. Grados del docente
            grados_docente = docente.asignaturas_dictadas.filter(
                grado_año_lectivo__año_lectivo__estado=True
            ).values_list('grado_año_lectivo__grado_id', flat=True).distinct()
            
            resultados['grados_dictados'] = list(grados_docente)
            
            # 2. Total de asignaturas
            resultados['total_asignaturas'] = docente.asignaturas_dictadas.filter(
                grado_año_lectivo__año_lectivo__estado=True
            ).count()
            
            # 3. Estudiantes únicos del docente
            resultados['total_estudiantes'] = Matricula.objects.filter(
                grado_año_lectivo__grado_id__in=grados_docente,
                año_lectivo=año_lectivo_actual,
                estado__in=['ACT', 'PEN', 'INA', 'RET', 'OTRO']
            ).values_list('estudiante_id', flat=True).distinct().count()
            
            # 4. Período actual
            periodo_actual = PeriodoAcademico.objects.filter(
                año_lectivo=año_lectivo_actual,
                estado=True
            ).first()
            resultados['periodo_actual'] = periodo_actual
            
            # 5. Calificaciones pendientes (solo si hay periodo actual)
            if periodo_actual:
                # Obtener todas las asignaturas del docente con sus grados
                asignaturas_grados = docente.asignaturas_dictadas.filter(
                    grado_año_lectivo__año_lectivo=año_lectivo_actual
                ).select_related('grado_año_lectivo__grado')
                
                total_pendientes = 0
                
                for ag in asignaturas_grados:
                    # Estudiantes del grado de esta asignatura
                    estudiantes_grado = Matricula.objects.filter(
                        grado_año_lectivo=ag.grado_año_lectivo,
                        año_lectivo=año_lectivo_actual,
                    estado__in=['ACT', 'PEN', 'INA', 'RET', 'OTRO']
                    ).values_list('estudiante_id', flat=True)
                    
                    # Estudiantes ya calificados en esta asignatura
                    estudiantes_calificados = Nota.objects.filter(
                        asignatura_grado_año_lectivo=ag,
                        periodo_academico=periodo_actual
                    ).values_list('estudiante_id', flat=True)
                    
                    # Convertir a sets y calcular diferencia
                    estudiantes_set = set(estudiantes_grado)
                    calificados_set = set(estudiantes_calificados)
                    pendientes = len(estudiantes_set - calificados_set)
                    
                    total_pendientes += pendientes
                
                resultados['calificaciones_pendientes'] = total_pendientes
            
        except Exception as e:
            print(f"Error en calcular_estadisticas_principales: {str(e)}")
        
        return resultados
    
    def calcular_detalle_pendientes(self, docente, año_lectivo_actual, periodo_actual):
        """Calcula detalle de pendientes por asignatura"""
        from estudiantes.models import Matricula, Nota
        
        try:
            detalle = []
            asignaturas_docente = docente.asignaturas_dictadas.filter(
                grado_año_lectivo__año_lectivo=año_lectivo_actual
            ).select_related(
                'asignatura',
                'grado_año_lectivo__grado'
            )
            
            for ag in asignaturas_docente:
                # Contar estudiantes del grado
                total_estudiantes = Matricula.objects.filter(
                    grado_año_lectivo=ag.grado_año_lectivo,
                    año_lectivo=año_lectivo_actual,
                    estado__in=['ACT', 'PEN', 'INA', 'RET', 'OTRO']
                ).count()
                
                # Contar estudiantes calificados
                calificados = Nota.objects.filter(
                    asignatura_grado_año_lectivo=ag,
                    periodo_academico=periodo_actual
                ).count()
                
                pendientes = total_estudiantes - calificados
                
                if pendientes > 0:
                    detalle.append({
                        'asignatura': ag.asignatura.nombre,
                        'grado': ag.grado_año_lectivo.grado.nombre,
                        'total_estudiantes': total_estudiantes,
                        'calificados': calificados,
                        'pendientes': pendientes,
                        'porcentaje': round((calificados / total_estudiantes * 100), 1) if total_estudiantes > 0 else 0
                    })
            
            return detalle
            
        except Exception as e:
            print(f"Error en calcular_detalle_pendientes: {str(e)}")
            return []
    
    def get_valores_por_defecto(self):
        """Valores por defecto"""
        return {
            'total_estudiantes': 0,
            'total_asignaturas': 0,
            'calificaciones_pendientes': 0,
            'periodo_actual': None,
            'grados_dictados': [],
            'detalle_pendientes': []
        }
    
class DashboardEstudianteView(RoleRequiredMixin, TemplateView):
    """Dashboard estudiante - Con manejo inteligente de años lectivos"""
    template_name = 'estudiantes/dashboard_estudiante.html'
    allowed_roles = ['Estudiante']
    
    def dispatch(self, request, *args, **kwargs):
        """Verificar si el estudiante está inactivo antes de mostrar el dashboard"""
        # Primero, verificar si el usuario está autenticado
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        try:
            # Verificar si el usuario tiene un perfil de estudiante
            estudiante = Estudiante.objects.filter(usuario=request.user).first()
            
            if not estudiante.estado:
                # Si el estudiante existe pero está inactivo, redirigir a cuenta_inactiva
                messages.warning(request, "Tu cuenta de estudiante se encuentra inactiva. Contacta al administrador.")
                return redirect('estudiantes:cuenta_inactiva')
            
        except Exception as e:
            print(f"Error verificando estado del estudiante: {e}")
        
        # Si pasa todas las verificaciones, continuar con la vista normal
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # 1. Obtener estudiante
            estudiante = Estudiante.objects.get(usuario=self.request.user)
            
            # Guardar objeto estudiante completo en contexto
            context['estudiante_obj'] = estudiante
            context['estudiante'] = {
                'id': estudiante.id,
                'nombres': estudiante.usuario.nombres,
                'apellidos': estudiante.usuario.apellidos,
                'nombre_completo': f"{estudiante.usuario.nombres} {estudiante.usuario.apellidos}",
                'foto_url': estudiante.foto.url if estudiante.foto else None,
                'estado': estudiante.estado,
            }
            
            # 2. LÓGICA INTELIGENTE PARA AÑO LECTIVO
            hoy = timezone.now().date()
            
            # Opción A: Buscar año lectivo activo del estudiante (matrícula ACT o PEN)
            matricula_actual = estudiante.matriculas.filter(
                estado__in=['ACT', 'PEN'],
                año_lectivo__estado=True,
                año_lectivo__fecha_inicio__lte=hoy,
                año_lectivo__fecha_fin__gte=hoy
            ).select_related(
                'año_lectivo', 'grado_año_lectivo__grado', 'sede'
            ).first()
            
            # Opción B: Si no hay matrícula en año activo, buscar último año matriculado
            if not matricula_actual:
                matricula_actual = estudiante.matriculas.filter(
                    estado__in=['ACT', 'PEN', 'INA']
                ).select_related(
                    'año_lectivo', 'grado_año_lectivo__grado', 'sede'
                ).order_by('-año_lectivo__anho').first()
            
            # Si hay matrícula, configurar contexto
            if matricula_actual:
                context['matricula_actual'] = matricula_actual
                context['año_lectivo_actual'] = matricula_actual.año_lectivo
                context['grado_actual'] = matricula_actual.grado_año_lectivo.grado.nombre
                context['sede_actual'] = matricula_actual.sede.nombre
                
                # 3. OBTENER PERÍODO ACTUAL
                periodo_actual = self.obtener_periodo_actual_inteligente(
                    matricula_actual.año_lectivo, hoy
                )
                context['periodo_actual'] = periodo_actual
                
                # 4. OBTENER DATOS DEL PERÍODO ACTUAL
                if periodo_actual:
                    # Notas del período
                    notas_periodo = Nota.objects.filter(
                        estudiante=estudiante,
                        periodo_academico=periodo_actual
                    ).select_related(
                        'asignatura_grado_año_lectivo__asignatura',
                        'asignatura_grado_año_lectivo__asignatura__area'
                    )
                    
                    # Formatear notas para el dashboard
                    notas_formateadas = []
                    for nota in notas_periodo:
                        notas_formateadas.append({
                            'nombre': nota.asignatura_grado_año_lectivo.asignatura.nombre,
                            'calificacion': float(nota.calificacion) if nota.calificacion else None,
                            'area': nota.asignatura_grado_año_lectivo.asignatura.area.nombre if nota.asignatura_grado_año_lectivo.asignatura.area else 'General',
                        })
                    
                    context['notas_periodo_actual'] = notas_formateadas
                    
                    # Estadísticas de notas
                    if notas_formateadas:
                        calificaciones = [n['calificacion'] for n in notas_formateadas if n['calificacion'] is not None]
                        if calificaciones:
                            context['promedio_actual'] = sum(calificaciones) / len(calificaciones)
                            context['nota_maxima'] = max(calificaciones)
                            context['nota_minima'] = min(calificaciones)
                    
                    # 5. COMPORTAMIENTOS RECIENTES
                    comportamientos = Comportamiento.objects.filter(
                        estudiante=estudiante,
                        periodo_academico__año_lectivo=matricula_actual.año_lectivo
                    ).select_related(
                        'docente__usuario',
                        'periodo_academico__periodo'
                    ).order_by('-fecha')[:5]  # SOLO AQUÍ aplicamos slice después de todo
        
                    context['comportamientos_recientes'] = list(comportamientos)  # Convertir a lista para evitar problemas
                    
                    # Estadísticas de comportamiento
                    if comportamientos:
                        positivos = sum(1 for c in comportamientos if c.tipo == 'Positivo')
                        negativos = sum(1 for c in comportamientos if c.tipo == 'Negativo')
                        context['comportamientos_positivos'] = positivos
                        context['comportamientos_negativos'] = negativos
            
            # 6. TODOS LOS AÑOS LECTIVOS DEL ESTUDIANTE (SIN SLICE)
            años_lectivos_estudiante = AñoLectivo.objects.filter(
                matriculas__estudiante=estudiante,
                matriculas__estado__in=['ACT', 'INA', 'RET']
            ).distinct().order_by('-anho')
            
            context['años_lectivos_estudiante'] = años_lectivos_estudiante
            
            # 7. MATRÍCULAS ANTERIORES (CORREGIDO - slice al final)
            if matricula_actual:
                # Primero aplicar todos los filtros, luego el slice
                matriculas_anteriores_qs = estudiante.matriculas.filter(
                    estado__in=['INA', 'RET']
                ).exclude(id=matricula_actual.id).select_related(
                    'año_lectivo', 'grado_año_lectivo__grado', 'sede'
                ).order_by('-año_lectivo__anho')
                
                # Ahora aplicar el slice
                matriculas_anteriores = list(matriculas_anteriores_qs[:5])
            else:
                # Sin matrícula actual, tomar las últimas 5
                matriculas_anteriores = list(
                    estudiante.matriculas.filter(
                        estado__in=['INA', 'RET']
                    ).select_related(
                        'año_lectivo', 'grado_año_lectivo__grado', 'sede'
                    ).order_by('-año_lectivo__anho')[:5]
                )
            
            context['matriculas_anteriores'] = matriculas_anteriores
            
            # 8. DOCUMENTOS DISPONIBLES POR AÑO (CORREGIDO)
            documentos_por_año = []
            for año in años_lectivos_estudiante:
                # Obtener matrícula para este año
                matricula_año = estudiante.matriculas.filter(
                    año_lectivo=año
                ).first()
                
                documentos_año = {
                    'año': año,
                    'matricula': matricula_año,
                    'tiene_notas': Nota.objects.filter(
                        estudiante=estudiante,
                        periodo_academico__año_lectivo=año
                    ).exists(),
                    'tiene_comportamientos': Comportamiento.objects.filter(
                        estudiante=estudiante,
                        periodo_academico__año_lectivo=año
                    ).exists(),
                }
                
                # Verificar si tiene boletín final (notas del 4to período)
                periodo_cuarto = PeriodoAcademico.objects.filter(
                    año_lectivo=año,
                    periodo__nombre='Cuarto'
                ).first()
                
                if periodo_cuarto:
                    documentos_año['tiene_boletin_final'] = Nota.objects.filter(
                        estudiante=estudiante,
                        periodo_academico=periodo_cuarto
                    ).exists()
                else:
                    documentos_año['tiene_boletin_final'] = False
                
                documentos_por_año.append(documentos_año)
            
            context['documentos_por_año'] = documentos_por_año
            
            # 9. ESTADÍSTICAS GLOBALES
            context['total_años_cursados'] = años_lectivos_estudiante.count()
            
            if matricula_actual:
                context['es_año_actual'] = matricula_actual.año_lectivo.estado
            else:
                context['es_año_actual'] = False
                context['mensaje_estado'] = "Actualmente no estás matriculado en el año lectivo en curso"
            
            # 10. ASISTENCIA (si hay período actual)
            if 'periodo_actual' in context and context['periodo_actual']:
                # Primero el QuerySet completo, luego count
                asistencias_qs = Asistencia.objects.filter(
                    estudiante=estudiante,
                    periodo_academico=context['periodo_actual']
                )
                
                if asistencias_qs.exists():
                    total = asistencias_qs.count()
                    # Para contar asistencias positivas, usar otro QuerySet
                    asistio_qs = Asistencia.objects.filter(
                        estudiante=estudiante,
                        periodo_academico=context['periodo_actual'],
                        estado='A'
                    )
                    asistio = asistio_qs.count()
                    
                    porcentaje = (asistio / total) * 100 if total > 0 else 0
                    context['porcentaje_asistencia'] = round(porcentaje, 1)
                    context['total_asistencias'] = total
                    context['asistencias_positivas'] = asistio
        
        except Estudiante.DoesNotExist:
            messages.error(self.request, "No tienes un perfil de estudiante asociado")
            context['error'] = "No tienes un perfil de estudiante asociado"
        except Exception as e:
            messages.error(self.request, f"Error al cargar el dashboard: {str(e)}")
            context['error'] = str(e)
            print(f"Error en DashboardEstudianteView: {e}")
            import traceback
            traceback.print_exc()
        
        return context
    
    def obtener_periodo_actual_inteligente(self, año_lectivo, hoy):
        """Obtiene el período académico actual o más reciente"""
        if not año_lectivo:
            return None
        
        try:
            # 1. Buscar período activo que contenga la fecha actual
            periodo = PeriodoAcademico.objects.filter(
                año_lectivo=año_lectivo,
                fecha_inicio__lte=hoy,
                fecha_fin__gte=hoy
            ).first()
            
            if periodo:
                return periodo
            
            # 2. Buscar último período que terminó
            periodo = PeriodoAcademico.objects.filter(
                año_lectivo=año_lectivo,
                fecha_fin__lt=hoy
            ).order_by('-fecha_fin').first()
            
            if periodo:
                return periodo
            
            # 3. Buscar próximo período
            periodo = PeriodoAcademico.objects.filter(
                año_lectivo=año_lectivo,
                fecha_inicio__gt=hoy
            ).order_by('fecha_inicio').first()
            
            if periodo:
                return periodo
            
            # 4. Usar cualquier período del año
            return PeriodoAcademico.objects.filter(
                año_lectivo=año_lectivo
            ).first()
            
        except Exception as e:
            print(f"Error obteniendo período: {e}")
            return None