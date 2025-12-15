from decimal import Decimal
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from estudiantes.models import Estudiante, Nota, Acudiente, Matricula
from matricula.models import AsignaturaGradoAñoLectivo, PeriodoAcademico
from academico.models import HorarioClase, Logro
from comportamiento.models import Comportamiento
from gestioncolegio.models import Colegio, RecursosColegio, AñoLectivo
from gestioncolegio.views import RoleRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views import View
from django.http import HttpResponse, Http404
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO 
import os
from django.db.models import Q
from django.contrib import messages
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from django.core.exceptions import ObjectDoesNotExist

# ReportLab imports
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from estudiantes.mixins import PeriodoActualMixin

# =============================================
# VISTAS BASE Y PRINCIPALES
# =============================================

class BaseEstudianteView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """Vista base para estudiantes con contexto común"""
    allowed_roles = ['Estudiante', 'Administrador', 'Rector', 'Docente']
    
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        try:
            # Obtener estudiante según el tipo de usuario
            if user.tipo_usuario.nombre == 'Estudiante':
                estudiante = Estudiante.objects.get(usuario=user)
            else:
                # Para admin/rector/docente, obtener estudiante por parámetro
                estudiante_id = self.kwargs.get('estudiante_id')
                if estudiante_id:
                    estudiante = Estudiante.objects.get(id=estudiante_id)
                else:
                    estudiante = None
            
            if estudiante:
                context['estudiante_obj'] = estudiante
                context['estudiante'] = {
                    'id': estudiante.id,
                    'nombre_completo': f"{estudiante.usuario.nombres} {estudiante.usuario.apellidos}",
                    'nombres': estudiante.usuario.nombres,
                    'apellidos': estudiante.usuario.apellidos,
                    'grado_actual': estudiante.grado_actual.grado.nombre if estudiante.grado_actual else 'No asignado',
                    'año_lectivo': estudiante.grado_actual.año_lectivo.anho if estudiante.grado_actual else 'No asignado',
                    'año_lectivo_id': estudiante.grado_actual.año_lectivo.id if estudiante.grado_actual else None,
                    'foto_url': estudiante.foto.url if estudiante.foto else None,
                    'usuario': {
                        'tipo_documento': estudiante.usuario.tipo_documento.nombre if estudiante.usuario.tipo_documento else None,
                        'numero_documento': estudiante.usuario.numero_documento,
                        'email': estudiante.usuario.email,
                        'telefono': estudiante.usuario.telefono,
                        'direccion': estudiante.usuario.direccion,
                    }
                }
                
                # Periodos académicos del año actual
                if estudiante.grado_actual:
                    año_lectivo = estudiante.grado_actual.año_lectivo
                    periodos = PeriodoAcademico.objects.filter(
                        año_lectivo=año_lectivo
                    ).select_related('periodo').order_by('fecha_inicio')
                    
                    context['periodos_academicos'] = periodos
                    
                    # Determinar periodo actual usando la función inteligente
                    hoy = timezone.now().date()
                    periodo_actual = self.obtener_periodo_actual_inteligente(año_lectivo, hoy)
                    
                    context['periodo_actual'] = periodo_actual
                
                # Acudientes
                acudientes = Acudiente.objects.filter(estudiante=estudiante)
                context['acudientes'] = acudientes
                
        except Exception as e:
            print(f"Error en BaseEstudianteView: {e}")
            context['error'] = "Error al cargar datos del estudiante"
        
        return context

class PerfilEstudianteView(BaseEstudianteView):
    """Perfil completo del estudiante"""
    template_name = 'estudiantes/perfil_estudiante.html'
    allowed_roles = ['Estudiante', 'Administrador', 'Rector', 'Docente']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtener estudiante del usuario
        estudiante = Estudiante.objects.filter(usuario=self.request.user).first()
        context['estudiante'] = estudiante

        # Obtener período actual
        periodo_actual = PeriodoAcademico.objects.filter(
            año_lectivo__estado=True,
            estado=True
        ).order_by('-fecha_inicio').first()

        context['periodo_actual'] = periodo_actual

        return context

class SeleccionarAñoLectivoView(LoginRequiredMixin, RoleRequiredMixin, TemplateView, PeriodoActualMixin):
    """Vista para seleccionar año lectivo"""
    template_name = 'estudiantes/seleccionar_año_lectivo.html'
    allowed_roles = ['Estudiante', 'Administrador', 'Rector', 'Docente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Obtener estudiante según tipo de usuario
            if self.request.user.tipo_usuario.nombre == 'Estudiante':
                estudiante = get_object_or_404(Estudiante, usuario=self.request.user)
                context['es_estudiante'] = True
            else:
                # Para admin/rector/docente
                estudiante_id = self.kwargs.get('estudiante_id') or self.request.GET.get('estudiante_id')
                if estudiante_id:
                    estudiante = get_object_or_404(Estudiante, id=estudiante_id)
                else:
                    # Si no hay estudiante_id, no mostrar nada
                    context['error'] = "Debes especificar un estudiante"
                    return context
                context['es_estudiante'] = False
            
            context['estudiante'] = estudiante
            
            # Obtener TODOS los años lectivos del estudiante (activos e inactivos)
            años_lectivos_info = []
            
            # Primero, obtener el año lectivo actual del sistema
            año_actual_sistema = AñoLectivo.objects.filter(estado=True).first()
            context['año_actual_sistema'] = año_actual_sistema
            
            # Obtener todas las matrículas del estudiante
            for matricula in estudiante.matriculas.all().order_by('-año_lectivo__anho'):
                año_info = {
                    'id': matricula.año_lectivo.id,
                    'anho': matricula.año_lectivo.anho,
                    'grado': matricula.grado_año_lectivo.grado.nombre if matricula.grado_año_lectivo else 'No asignado',
                    'sede': matricula.sede.nombre,
                    'estado_matricula': matricula.get_estado_display(),
                    'es_actual': matricula.estado in ['ACT', 'PEN'] and matricula.año_lectivo.estado,
                    'es_año_activo_sistema': matricula.año_lectivo.estado,
                    'fecha_inicio': matricula.año_lectivo.fecha_inicio,
                    'fecha_fin': matricula.año_lectivo.fecha_fin,
                    'periodos': PeriodoAcademico.objects.filter(
                        año_lectivo=matricula.año_lectivo
                    ).order_by('fecha_inicio')
                }
                años_lectivos_info.append(año_info)
            
            context['años_lectivos'] = años_lectivos_info
            
        except Exception as e:
            context['error'] = f"Error al cargar años lectivos: {str(e)}"
        
        return context

class InformeAcademicoEstudianteView(BaseEstudianteView, PeriodoActualMixin):
    """Informe académico detallado del estudiante"""
    template_name = 'estudiantes/informe_academico.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if not context.get('estudiante_obj'):
            return context
            
        try:
            estudiante = context['estudiante_obj']
            periodo_id = self.kwargs.get('periodo_id')
            
            if periodo_id:
                # Obtener el período solicitado (puede ser de cualquier año)
                periodo = get_object_or_404(PeriodoAcademico, id=periodo_id)
                
                # Verificar que el estudiante tenga matrícula en ese año lectivo
                tiene_matricula = estudiante.matriculas.filter(
                    año_lectivo=periodo.año_lectivo,
                    estado__in=['ACT', 'PEN', 'INA', 'RET']
                ).exists()
                
                if not tiene_matricula:
                    context['error'] = f"El estudiante no estuvo matriculado en el año lectivo {periodo.año_lectivo.anho}"
                    return context
                    
                context['periodo_detalle'] = periodo
                
                # Obtener TODOS los períodos académicos de ESE año específico
                periodos_año = PeriodoAcademico.objects.filter(
                    año_lectivo=periodo.año_lectivo
                ).order_by('fecha_inicio')
                
                context['periodos_academicos'] = periodos_año
                
                # Si el año del período no es el actual, mostrar advertencia
                año_actual = AñoLectivo.objects.filter(estado=True).first()
                if año_actual and periodo.año_lectivo.id != año_actual.id:
                    context['año_no_actual'] = True
                    context['año_lectivo_periodo'] = periodo.año_lectivo
                
            else:
                # Si no hay período específico, usar el actual o el primero disponible
                periodo = context.get('periodo_actual')
                if periodo:
                    context['periodo_detalle'] = periodo
                    
                    # Obtener períodos del año actual
                    if estudiante.grado_actual:
                        año_lectivo = estudiante.grado_actual.año_lectivo
                        periodos_año = PeriodoAcademico.objects.filter(
                            año_lectivo=año_lectivo
                        ).order_by('fecha_inicio')
                        context['periodos_academicos'] = periodos_año
        
            # Obtener datos del informe si hay período
            if 'periodo_detalle' in context and context['periodo_detalle']:
                periodo = context['periodo_detalle']
                context.update(self._get_detalle_informe(estudiante, periodo))
                
        except Exception as e:
            print(f"Error en InformeAcademicoEstudianteView: {e}")
            context['error'] = "Error al cargar el informe académico"
        
        return context
    
    def _get_detalle_informe(self, estudiante, periodo):
        """Obtiene el detalle del informe académico para un estudiante en un período específico"""
        try:
            # Buscar la matrícula del estudiante para el año lectivo del período
            matricula = Matricula.objects.filter(
                estudiante=estudiante,
                año_lectivo=periodo.año_lectivo
            ).first()
            
            if not matricula:
                return {'error': 'No se encontró matrícula para este período'}
            
            # Obtener el grado del estudiante en ese año
            grado_año_lectivo = matricula.grado_año_lectivo
            
            # Obtener todas las asignaturas del grado en ese año lectivo
            asignaturas_grado = AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo=grado_año_lectivo,
                sede=matricula.sede
            ).select_related('asignatura', 'docente__usuario')
            
            # Preparar datos detallados de asignaturas
            asignaturas_detalle = []
            
            for asignatura_grado in asignaturas_grado:
                # Buscar la nota del estudiante para esta asignatura en este período
                nota = Nota.objects.filter(
                    estudiante=estudiante,
                    asignatura_grado_año_lectivo=asignatura_grado,
                    periodo_academico=periodo
                ).first()
                
                # Buscar logros para esta asignatura, grado y período
                logro = Logro.objects.filter(
                    asignatura=asignatura_grado.asignatura,
                    periodo_academico=periodo,
                    grado=grado_año_lectivo.grado
                ).first()
                
                # Determinar el logro alcanzado basado en la calificación
                logro_alcanzado = None
                if nota and logro:
                    # Asignar descripción del logro según calificación
                    calificacion = nota.calificacion
                    if calificacion >= 4.6:
                        logro_alcanzado = logro.descripcion_superior
                    elif calificacion >= 4.0:
                        logro_alcanzado = logro.descripcion_alto
                    elif calificacion >= 3.0:
                        logro_alcanzado = logro.descripcion_basico
                    else:
                        logro_alcanzado = logro.descripcion_bajo
                
                # Determinar desempeño
                desempeno = None
                if nota:
                    if nota.calificacion >= 4.6:
                        desempeno = "Superior"
                    elif nota.calificacion >= 4.0:
                        desempeno = "Alto"
                    elif nota.calificacion >= 3.0:
                        desempeno = "Básico"
                    else:
                        desempeno = "Bajo"
                
                # Obtener nombre del docente
                docente_nombre = None
                if asignatura_grado.docente and asignatura_grado.docente.usuario:
                    docente_nombre = asignatura_grado.docente.usuario.get_full_name()
                
                asignaturas_detalle.append({
                    'id': asignatura_grado.asignatura.id,
                    'nombre': asignatura_grado.asignatura.nombre,
                    'codigo': asignatura_grado.asignatura.codigo if hasattr(asignatura_grado.asignatura, 'codigo') else '',
                    'tiene_nota': nota is not None,
                    'calificacion': float(nota.calificacion) if nota else None,
                    'desempeno': desempeno,
                    'logro': logro_alcanzado or (logro.tema if logro else None),
                    'docente': docente_nombre,
                    'area': asignatura_grado.asignatura.area.nombre if asignatura_grado.asignatura.area else '',
                })
            
            # Obtener comportamientos del estudiante en este período
            comportamientos_detalle = Comportamiento.objects.filter(
                estudiante=estudiante,
                periodo_academico=periodo
            ).select_related('docente__usuario')
            
            return {
                'asignaturas_detalle': asignaturas_detalle,
                'comportamientos_detalle': comportamientos_detalle,
                'matricula': matricula,
                'grado_nombre': grado_año_lectivo.grado.nombre,
            }
            
        except Exception as e:
            print(f"Error en _get_detalle_informe: {e}")
            return {'error': 'Error al obtener detalles del informe'}
    
    def get_periodo_actual(self, estudiante):
        """Obtiene el período actual del estudiante"""
        try:
            if hasattr(estudiante, 'matricula_actual') and estudiante.matricula_actual:
                matricula = estudiante.matricula_actual
                año_lectivo = matricula.año_lectivo
                
                # Buscar el período más reciente que aún no ha terminado o el último
                hoy = timezone.now().date()
                periodo = PeriodoAcademico.objects.filter(
                    año_lectivo=año_lectivo,
                    estado=True
                ).filter(
                    Q(fecha_fin__gte=hoy) | Q(fecha_fin=None)
                ).order_by('-fecha_inicio').first()
                
                # Si no hay período futuro o actual, tomar el último período
                if not periodo:
                    periodo = PeriodoAcademico.objects.filter(
                        año_lectivo=año_lectivo,
                        estado=True
                    ).order_by('-fecha_inicio').first()
                
                return periodo
        except Exception as e:
            print(f"Error obteniendo período actual: {e}")
        
        return None    

class SeleccionarAñoLectivoView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """Vista para seleccionar año lectivo para reportes"""
    template_name = 'estudiantes/seleccionar_año_lectivo.html'
    allowed_roles = ['Estudiante', 'Administrador', 'Rector', 'Docente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener estudiante
        if self.request.user.tipo_usuario.nombre == 'Estudiante':
            estudiante = get_object_or_404(Estudiante, usuario=self.request.user)
        else:
            estudiante_id = self.kwargs.get('estudiante_id')
            if estudiante_id:
                estudiante = get_object_or_404(Estudiante, id=estudiante_id)
            else:
                estudiante_id_get = self.request.GET.get('estudiante_id')
                if estudiante_id_get:
                    estudiante = get_object_or_404(Estudiante, id=estudiante_id_get)
                else:
                    # Para admin/docente viendo perfil de estudiante
                    estudiante = None
        
        if estudiante:
            # Obtener todos los años lectivos en los que el estudiante estuvo matriculado
            matriculas = estudiante.matriculas.filter(
                estado__in=['ACT', 'INA', 'RET']  # Matrículas activas, inactivas o retiradas
            ).select_related('año_lectivo').order_by('-año_lectivo__anho')
            
            años_lectivos = []
            for matricula in matriculas:
                # Obtener periodos académicos de ese año lectivo
                periodos = PeriodoAcademico.objects.filter(
                    año_lectivo=matricula.año_lectivo
                ).order_by('fecha_inicio')
                
                años_lectivos.append({
                    'id': matricula.año_lectivo.id,
                    'anho': matricula.año_lectivo.anho,
                    'grado': matricula.grado_año_lectivo.grado.nombre if matricula.grado_año_lectivo else 'No asignado',
                    'sede': matricula.sede.nombre,
                    'periodos': periodos,
                    'es_actual': matricula.estado == 'ACT' and matricula.año_lectivo.estado,
                    'estado_matricula': matricula.get_estado_display(),
                })
            
            context.update({
                'estudiante': estudiante,
                'años_lectivos': años_lectivos,
                'tipo_reporte': self.request.GET.get('tipo', 'notas'),  # 'notas' o 'final'
                'periodo_id': self.request.GET.get('periodo_id'),
            })
        
        return context
    
# =============================================
# VISTAS DE PDFs PARA ESTUDIANTES
# =============================================

class ExportarInformePDFView(LoginRequiredMixin, RoleRequiredMixin, View):
    """Exporta informe académico a PDF"""
    allowed_roles = ['Estudiante', 'Administrador', 'Rector', 'Docente']
    
    def get(self, request, *args, **kwargs):
        try:
            from gestioncolegio.models import Colegio
            from estudiantes.models import Estudiante
            from matricula.models import PeriodoAcademico
            
            # Obtener período desde los parámetros de la URL
            periodo_id = kwargs.get('periodo_id')
            if not periodo_id:
                return HttpResponse("Parámetro periodo_id requerido", status=400)
                
            periodo_obj = PeriodoAcademico.objects.get(id=periodo_id)
            
            # Obtener estudiante - manejar tanto acceso normal como admin
            estudiante_id = kwargs.get('estudiante_id')
            if estudiante_id:
                # Acceso de admin/docente (con estudiante_id en URL)
                estudiante_obj = Estudiante.objects.get(id=estudiante_id)
            elif request.user.tipo_usuario.nombre == 'Estudiante':
                # Acceso del propio estudiante
                estudiante_obj = Estudiante.objects.get(usuario=request.user)
            else:
                # Para otros roles sin estudiante_id, usar parámetro GET
                estudiante_id_get = request.GET.get('estudiante_id')
                if estudiante_id_get:
                    estudiante_obj = Estudiante.objects.get(id=estudiante_id_get)
                else:
                    return HttpResponse("Estudiante no especificado", status=400)
            
            # Obtener colegio
            colegio = Colegio.objects.filter(estado=True).first()
            if not colegio:
                return HttpResponse("Configuración del colegio no encontrada", status=400)
            
            # Construir contexto - MÉTODO COMPLETADO
            context = self._construir_contexto_informe(estudiante_obj, periodo_obj, colegio)
            
            # Configurar respuesta PDF
            response = HttpResponse(content_type='application/pdf')
            filename = f"informe_{estudiante_obj.usuario.nombres.replace(' ', '_')}_{periodo_obj.periodo.nombre}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            # Generar PDF
            template = get_template('estudiantes/informe_pdf.html')
            html = template.render(context)
            
            pisa_status = pisa.CreatePDF(
                html,
                dest=response,
                encoding='UTF-8'
            )
            
            if pisa_status.err:
                return HttpResponse('Error al generar PDF', status=500)
            
            return response
            
        except PeriodoAcademico.DoesNotExist:
            return HttpResponse("Período no encontrado", status=404)
        except Estudiante.DoesNotExist:
            return HttpResponse("Estudiante no encontrado", status=404)
        except Exception as e:
            print(f"Error generando PDF: {e}")
            return HttpResponse("Error interno del servidor", status=500)
    
    def _construir_contexto_informe(self, estudiante, periodo, colegio):
        """Construye el contexto para el informe PDF usando la misma lógica que InformeAcademicoEstudianteView"""
        try:
            # Obtener notas del período (MISMA LÓGICA)
            notas = Nota.objects.filter(
                estudiante=estudiante,
                periodo_academico=periodo
            ).select_related('asignatura_grado_año_lectivo__asignatura')

            # Obtener asignaturas del grado (MISMA LÓGICA)
            asignaturas_grado = AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo=estudiante.grado_actual
            ).select_related('asignatura', 'docente__usuario')

            # Obtener logros para cada asignatura (MISMA LÓGICA)
            logros = Logro.objects.filter(
                grado=estudiante.grado_actual.grado,
                periodo_academico=periodo
            ).select_related('asignatura')

            asignaturas_data = []
            total_calificaciones = 0
            asignaturas_evaluadas = 0
            
            for ag in asignaturas_grado:
                nota = notas.filter(asignatura_grado_año_lectivo=ag).first()
                
                # Buscar el logro correspondiente a esta asignatura (MISMA LÓGICA)
                logro_asignatura = logros.filter(asignatura=ag.asignatura).first()
                logro_texto = ""
                
                if logro_asignatura and nota and nota.calificacion:
                    calificacion = float(nota.calificacion)
                    # Determinar qué descripción de logro mostrar según la calificación (MISMA LÓGICA)
                    if calificacion >= 4.5 and logro_asignatura.descripcion_superior:
                        logro_texto = logro_asignatura.descripcion_superior
                    elif calificacion >= 4.0 and logro_asignatura.descripcion_alto:
                        logro_texto = logro_asignatura.descripcion_alto
                    elif calificacion >= 3.5 and logro_asignatura.descripcion_basico:
                        logro_texto = logro_asignatura.descripcion_basico
                    elif logro_asignatura.descripcion_bajo:
                        logro_texto = logro_asignatura.descripcion_bajo
                    elif logro_asignatura.tema:
                        logro_texto = logro_asignatura.tema

                item = {
                    'nombre': ag.asignatura.nombre,
                    'docente': f"{ag.docente.usuario.nombres} {ag.docente.usuario.apellidos}" if ag.docente else 'Sin asignar',
                    'tiene_nota': nota is not None,
                    'logro': logro_texto,
                    'calificacion': None,
                    'desempeno': 'Sin calificar'
                }
                
                if item['tiene_nota'] and nota.calificacion:
                    try:
                        calificacion = round(float(nota.calificacion), 1)
                        desempeno = self._calcular_desempeno(calificacion)
                        
                        item.update({
                            'calificacion': calificacion,
                            'desempeno': desempeno,
                        })
                        
                        total_calificaciones += calificacion
                        asignaturas_evaluadas += 1
                        
                    except (ValueError, TypeError):
                        pass
                
                asignaturas_data.append(item)
            
            # Calcular promedio
            promedio_general = total_calificaciones / asignaturas_evaluadas if asignaturas_evaluadas > 0 else 0
            
            # Obtener comportamientos para este período
            from comportamiento.models import Comportamiento
            comportamientos_detalle = Comportamiento.objects.filter(
                estudiante=estudiante,
                periodo_academico=periodo
            ).select_related('docente__usuario').order_by('-fecha')
            
            # Obtener recursos del colegio
            try:
                recursos = colegio.recursos
            except ObjectDoesNotExist:
                recursos = None
            
            # Construir contexto completo (CON LOS MISMOS NOMBRES DE VARIABLES)
            return {
                'estudiante': {
                    'nombre_completo': f"{estudiante.usuario.nombres} {estudiante.usuario.apellidos}",
                    'grado_actual': estudiante.grado_actual.grado.nombre if estudiante.grado_actual else 'No asignado',
                    'año_lectivo': estudiante.grado_actual.año_lectivo.anho if estudiante.grado_actual else 'No asignado',
                    'usuario': {
                        'tipo_documento': estudiante.usuario.tipo_documento.nombre if estudiante.usuario.tipo_documento else 'Documento',
                        'numero_documento': estudiante.usuario.numero_documento,
                    }
                },
                'periodo_detalle': periodo,  # IMPORTANTE: mismo nombre que en la vista HTML
                'asignaturas_detalle': asignaturas_data,  # IMPORTANTE: mismo nombre que en la vista HTML
                'comportamientos_detalle': comportamientos_detalle,  # Para el PDF si lo necesitas
                'colegio': colegio,
                'recursos': recursos,
                'promedio_general': round(promedio_general, 2),
                'total_asignaturas': len(asignaturas_data),
                'asignaturas_evaluadas': asignaturas_evaluadas,
                'fecha_generacion': timezone.now(),
            }
            
        except Exception as e:
            print(f"Error construyendo contexto informe: {e}")
            # Retornar contexto vacío pero con estructura
            return {
                'estudiante': {},
                'periodo_detalle': periodo,
                'asignaturas_detalle': [],
                'comportamientos_detalle': [],
                'colegio': colegio,
                'promedio_general': 0,
            }

    def _calcular_desempeno(self, calificacion):
        """Calcula el desempeño - MISMA LÓGICA que InformeAcademicoEstudianteView"""
        if calificacion >= 4.5:
            return 'Superior'
        elif calificacion >= 3.8:
            return 'Alto'
        elif calificacion >= 3.0:
            return 'Básico'
        return 'Bajo'

    def _calcular_desempeno(self, calificacion):
        """Calcula el desempeño basado en la calificación"""
        if calificacion >= 4.5:
            return 'Superior'
        elif calificacion >= 4.0:
            return 'Alto'
        elif calificacion >= 3.0:
            return 'Básico'
        return 'Bajo'


class ConstanciaEstudioPDFView(View):
    """Genera la constancia de estudio en formato PDF (solo ReportLab)."""

    MARGINS = {
        'left': 2 * cm,
        'right': 2 * cm,
        'top': 1.5 * cm,
        'bottom': 1.8 * cm
    }

    def _obtener_o_crear_recursos(self, colegio):
        """Obtiene o crea los recursos del colegio si no existen"""
        try:
            # Intentar obtener los recursos existentes
            return colegio.recursos
        except ObjectDoesNotExist:
            # Si no existen, crear unos por defecto
            recursos = RecursosColegio.objects.create(
                colegio=colegio,
                sitio_web='https://colegiocrishadai.edu.co',
                email='migueliose@colegiocrishadai.edu.co',
                telefono='+57 123 456 7890',
            )
            return recursos

    def get(self, request, *args, **kwargs):
        try:
            # Obtener estudiante según parámetro de URL o GET
            estudiante_id = kwargs.get('estudiante_id') or request.GET.get('estudiante_id')
            
            # Obtener año lectivo según parámetro
            año_lectivo_id = kwargs.get('año_lectivo_id') or request.GET.get('año_lectivo_id')
            
            if not estudiante_id:
                # Si no hay estudiante_id en URL, verificar si es el propio estudiante
                if hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario.nombre == 'Estudiante':
                    estudiante = get_object_or_404(Estudiante, usuario=request.user)
                else:
                    return HttpResponse("Estudiante no especificado", status=400)
            else:
                # Para admin/rector/docente, obtener estudiante por parámetro
                estudiante = get_object_or_404(Estudiante, id=estudiante_id)
            
            # Obtener año lectivo
            año_lectivo = None
            matricula_año = None  # Para almacenar la matrícula específica del año
            
            if año_lectivo_id:
                año_lectivo = get_object_or_404(AñoLectivo, id=año_lectivo_id)
                # Buscar matrícula específica para este año
                matricula_año = estudiante.matriculas.filter(
                    año_lectivo=año_lectivo,
                    estado__in=['ACT', 'INA', 'RET']  # Aceptar matrículas activas, inactivas o retiradas
                ).first()
            else:
                # Si no se especifica año, usar el actual del estudiante
                if estudiante.grado_actual:
                    año_lectivo = estudiante.grado_actual.año_lectivo
                    matricula_año = estudiante.matricula_actual
                else:
                    # Buscar último año lectivo del estudiante
                    ultima_matricula = estudiante.matriculas.filter(
                        estado__in=['ACT', 'INA', 'RET']
                    ).order_by('-año_lectivo__anho').first()
                    
                    if ultima_matricula:
                        año_lectivo = ultima_matricula.año_lectivo
                        matricula_año = ultima_matricula
                    else:
                        return HttpResponse("No se encontró año lectivo para el estudiante", status=400)
            
            # Verificar si la matrícula del año es diferente a la actual
            es_año_anterior = False
            if matricula_año and estudiante.matricula_actual:
                es_año_anterior = matricula_año.id != estudiante.matricula_actual.id
            elif matricula_año and not estudiante.matricula_actual:
                # Si no hay matrícula actual pero sí hay matrícula del año, es año anterior
                es_año_anterior = True
            
            colegio = Colegio.objects.filter(estado=True).first()

            if not colegio:
                raise Http404("Configuración del colegio no encontrada")

            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=self.MARGINS['right'],
                leftMargin=self.MARGINS['left'],
                topMargin=self.MARGINS['top'],
                bottomMargin=self.MARGINS['bottom']
            )

            # Pasar la matrícula específica del año y si es año anterior
            elements = self._construir_elementos(estudiante, colegio, año_lectivo, matricula_año, es_año_anterior)

            doc.build(
                elements,
                onFirstPage=self._agregar_marca_agua,
                onLaterPages=self._agregar_marca_agua
            )

            pdf = buffer.getvalue()
            buffer.close()

            nombre_archivo = f"constancia_{estudiante.usuario.nombres.replace(' ', '_')}_{año_lectivo.anho if año_lectivo else ''}_{timezone.now().strftime('%Y%m%d')}.pdf"
            response = HttpResponse(pdf, content_type="application/pdf")
            response["Content-Disposition"] = f'inline; filename="{nombre_archivo}"'
            return response

        except Estudiante.DoesNotExist:
            return HttpResponse("Estudiante no encontrado", status=404)
        
        except Exception as e:
            print(f"Error generando constancia: {e}")
            return HttpResponse("Error interno del servidor", status=500)

    # -------------------- MARCA DE AGUA --------------------
    def _agregar_marca_agua(self, canvas, doc):
        """Agrega marca de agua institucional."""
        try:
            colegio = Colegio.objects.filter(estado=True).first()
            if colegio:
                # Verificar si existe el objeto recursos
                try:
                    recursos = self._obtener_o_crear_recursos(colegio)
                    if recursos.escudo and os.path.exists(recursos.escudo.path):
                        logo_path = recursos.escudo.path
                        canvas.saveState()
                        canvas.setFillAlpha(0.07)

                        # Centrar imagen
                        page_width, page_height = doc.pagesize
                        wm_w, wm_h = 12 * cm, 12 * cm
                        x = (page_width - wm_w) / 2
                        y = (page_height - wm_h) / 2

                        canvas.drawImage(
                            logo_path, x, y, width=wm_w, height=wm_h,
                            preserveAspectRatio=True, mask='auto'
                        )
                        canvas.restoreState()
                        return
                except (ObjectDoesNotExist, AttributeError, ValueError, OSError) as e:
                    print(f"Error con recursos en marca de agua: {e}")
                    # Si hay algún error, usar marca de agua de texto
                    
            self._agregar_marca_agua_texto(canvas, doc)
        except Exception as e:
            print(f"Error en marca de agua: {e}")
            self._agregar_marca_agua_texto(canvas, doc)

    def _agregar_marca_agua_texto(self, canvas, doc):
        """Marca de agua de texto como fallback"""
        try:
            canvas.saveState()
            canvas.setFont("Helvetica-Bold", 50)
            canvas.setFillAlpha(0.07)
            canvas.rotate(45)
            canvas.drawCentredString(doc.pagesize[0] / 2, doc.pagesize[1] / 3, "CONSTANCIA DE ESTUDIO")
            canvas.restoreState()
        except Exception as e:
            print(f"Error en marca de agua de texto: {e}")

    # -------------------- CONSTRUCCIÓN --------------------
    def _construir_elementos(self, estudiante, colegio, año_lectivo, matricula_año=None, es_año_anterior=False):
        styles = self._crear_estilos()
        elements = []

        elements.extend(self._crear_encabezado(colegio, styles))
        elements.extend(self._crear_titulo_constancia(styles))
        elements.extend(self._crear_contenido(estudiante, colegio, styles, año_lectivo, matricula_año, es_año_anterior))
        elements.extend(self._crear_firma_y_sello(estudiante, styles, año_lectivo))
        elements.extend(self._crear_pie_pagina(colegio, estudiante, styles, año_lectivo))

        return elements

    # -------------------- ESTILOS --------------------
    def _crear_estilos(self):
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="TituloColegio", fontSize=18, alignment=1, fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="Subtitulo", fontSize=11, alignment=1))
        styles.add(ParagraphStyle(name="TituloConstancia", fontSize=14, alignment=1, spaceAfter=15, fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="TextoNormal", fontSize=12, alignment=4, leading=15))
        styles.add(ParagraphStyle(name="TextoResaltado", fontSize=12, alignment=4, leading=15, backColor=colors.whitesmoke))
        styles.add(ParagraphStyle(name="Sello", fontSize=9, textColor=colors.HexColor("#0A4BA0")))
        styles.add(ParagraphStyle(name="PiePagina", fontSize=9, alignment=1, textColor=colors.HexColor("#444")))
        styles.add(ParagraphStyle(name="FirmaNombre", fontSize=12, alignment=2, fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="FirmaCargo", fontSize=11, alignment=2))
        return styles

    # -------------------- SECCIONES --------------------
    def _crear_encabezado(self, colegio, styles):
        """Crear encabezado con manejo de errores para recursos"""
        logo = None
        try:
            # Obtener recursos (se crearán automáticamente si no existen)
            recursos = self._obtener_o_crear_recursos(colegio)
            if recursos.escudo and os.path.exists(recursos.escudo.path):
                logo = Image(recursos.escudo.path, width=80, height=80)
        except (ObjectDoesNotExist, AttributeError, ValueError, OSError) as e:
            print(f"Error cargando logo: {e}")
            # Continuar sin logo

        logo_cell = logo or Paragraph("ESCUDO<br/>NO DISPONIBLE", styles["Subtitulo"])

        # Información del colegio con valores por defecto
        resolucion = colegio.resolucion if colegio.resolucion else "---"
        dane = colegio.dane if colegio.dane else "---"
        direccion = colegio.direccion if colegio.direccion else "Valledupar - Cesar"

        info = [
            Paragraph("COLEGIO CRISTIANO EL SHADAI", styles["TituloColegio"]),
            Paragraph(f"Resolución de Estudios N.º {resolucion}", styles["Subtitulo"]),
            Paragraph(f"<b>COD. DANE {dane}</b>", styles["Subtitulo"]),
            Paragraph("Educación Preescolar – Básica Primaria", styles["Subtitulo"]),
            Paragraph(direccion, styles["Subtitulo"])
        ]
        info_table = Table([[line] for line in info])

        header = Table([[logo_cell, info_table]], colWidths=[3 * cm, 13 * cm])
        header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))

        linea = Table([[""]], colWidths=[16 * cm])
        linea.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 2, colors.black)]))

        return [header, Spacer(1, 10), linea, Spacer(1, 25)]

    def _crear_titulo_constancia(self, styles):
        return [Paragraph("CONSTANCIA DE ESTUDIO", styles["TituloConstancia"])]

    def _crear_contenido(self, estudiante, colegio, styles, año_lectivo, matricula_año=None, es_año_anterior=False):
        """Contenido principal de la constancia"""
        tipo_doc = estudiante.usuario.tipo_documento.nombre if estudiante.usuario.tipo_documento else "Documento"
        fecha = self._formatear_fecha_espanol()

        # Obtener información del grado según la matrícula del año específico
        grado_info = "No asignado"
        if matricula_año and matricula_año.grado_año_lectivo:
            grado_info = matricula_año.grado_año_lectivo.grado.nombre
        elif estudiante.grado_actual:
            grado_info = estudiante.grado_actual.grado.nombre
        
        año_lectivo_info = str(año_lectivo.anho) if año_lectivo else "No asignado"

        contenido = [
            Paragraph(
                f"El suscrito director(a) del <b>COLEGIO CRISTIANO EL SHADAI</b>, "
                f"institución educativa reconocida oficialmente mediante Resolución N.º {colegio.resolucion}, "
                f"con código DANE {colegio.dane},", styles["TextoNormal"]
            ),
            Spacer(1, 10),
            Paragraph("<b>CERTIFICA:</b>", styles["TextoNormal"]),
            Spacer(1, 5),
        ]

        # Texto diferente según si es año actual o anterior
        if es_año_anterior:
            # Texto para año anterior (usar pasado)
            texto_est = (
                f"Que, <b>{estudiante.usuario.nombres} {estudiante.usuario.apellidos}</b>, identificado(a) con "
                f"{tipo_doc} N.º <b>{estudiante.usuario.numero_documento}</b>, "
                f"<b>estuvo matriculado(a)</b> en esta institución educativa <b>cursando el grado "
                f"{grado_info}</b>, durante el año lectivo <b>{año_lectivo_info}</b>."
            )
        else:
            # Texto para año actual (usar presente)
            texto_est = (
                f"Que, <b>{estudiante.usuario.nombres} {estudiante.usuario.apellidos}</b>, identificado(a) con "
                f"{tipo_doc} N.º <b>{estudiante.usuario.numero_documento}</b>, "
                f"se encuentra matriculado(a) en esta institución educativa cursando el grado "
                f"<b>{grado_info}</b>, en el presente año lectivo "
                f"<b>{año_lectivo_info}</b>."
            )

        bloque = Table([[Paragraph(texto_est, styles["TextoNormal"])]], colWidths=[14 * cm])
        bloque.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
            ("LEFTPADDING", (0, 0), (-1, -1), 15),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("LINEBEFORE", (0, 0), (-1, -1), 3, colors.black)
        ]))
        contenido.extend([bloque, Spacer(1, 15)])

        # Texto adicional según si es año anterior
        if es_año_anterior:
            contenido.append(Paragraph(
                f"La presente constancia de estudio cursado se expide en Valledupar, a los <b>{fecha}</b>, "
                "para ser presentada ante las autoridades o instituciones que así lo requieran.",
                styles["TextoNormal"]
            ))
        else:
            contenido.append(Paragraph(
                f"La presente constancia se expide en Valledupar, a los <b>{fecha}</b>, "
                "para ser presentada ante las autoridades o instituciones que así lo requieran.",
                styles["TextoNormal"]
            ))
        
        contenido.append(Paragraph("Constancia que se firma en señal de conformidad.", styles["TextoNormal"]))
        contenido.append(Spacer(1, 60))
        
        return contenido

    def _crear_firma_y_sello(self, estudiante, styles, año_lectivo):
        """Firma y sello en la misma línea"""
        fecha = self._formatear_fecha_espanol()

        # Sello
        año_lectivo_str = str(año_lectivo.anho) if año_lectivo else "No_asignado"
        
        sello_text = (
            f"Constancia generada electrónicamente<br/>{fecha}<br/>"
            f"Código: {estudiante.usuario.numero_documento}-{año_lectivo_str}"
        )
        sello = Table([[Paragraph(sello_text, styles["Sello"])]], colWidths=[5 * cm])
        sello.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0A4BA0")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F8FF")),
            ("PADDING", (0, 0), (-1, -1), 8)
        ]))

        # Firma
        firma = Table([
            [Paragraph("María Mederis Madero Garrido", styles["FirmaNombre"])],
            [Paragraph("Directora - Colegio Cristiano El Shadai", styles["FirmaCargo"])]
        ], colWidths=[8 * cm])

        # Combinar en una fila
        fila = Table([[sello, firma]], colWidths=[7 * cm, 8 * cm])
        fila.setStyle(TableStyle([
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP")
        ]))
        return [Spacer(1, 30), fila, Spacer(1, 20)]

    def _crear_pie_pagina(self, colegio, estudiante, styles, año_lectivo):
        """Pie de página con manejo seguro de recursos"""
        try:
            # Obtener información de contacto
            direccion = colegio.direccion if colegio.direccion else "Dirección no especificada"
            
            # Obtener recursos (se crearán automáticamente si no existen)
            try:
                recursos = self._obtener_o_crear_recursos(colegio)
                telefono = recursos.telefono or ""
                celular = getattr(recursos, "celular", "") or ""
                email = recursos.email or ""
                web = recursos.sitio_web or ""
            except Exception as e:
                print(f"Error obteniendo recursos para pie de página: {e}")
                telefono = celular = email = web = ""

            año_lectivo_str = str(año_lectivo.anho) if año_lectivo else "No especificado"
            
            lineas = [
                "<b>COLEGIO CRISTIANO EL SHADAI</b>",
                f"{direccion}" + (f" | Tel: {telefono}" if telefono else "") + (f" | Cel: {celular}" if celular else ""),
                (f"Email: {email}" if email else "") + (f" | Web: {web}" if web else ""),
                f"Constancia de: {estudiante.usuario.nombres} {estudiante.usuario.apellidos} | Año: {año_lectivo_str} | Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}"
            ]
            
            # Filtrar líneas vacías
            lineas = [linea for linea in lineas if linea.strip()]
            texto = "<br/>".join(lineas)

            linea = Table([[""]], colWidths=[15 * cm])
            linea.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 1, colors.HexColor('#888'))]))

            return [Spacer(1, 40), linea, Spacer(1, 8), Paragraph(texto, styles["PiePagina"])]

        except Exception as e:
            print(f"Error en pie de página: {e}")
            return [Spacer(1, 40)]

    # -------------------- MÉTODOS AUXILIARES --------------------
    def _formatear_fecha_espanol(self):
        meses = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
        ]
        now = timezone.now()
        return f"{now.day} de {meses[now.month - 1]} de {now.year}"

class ObservadorEstudiantePDFView(View):
    """Genera el observador del estudiante en formato PDF filtrado por año lectivo."""

    MARGINS = {
        'left': 2 * cm,
        'right': 2 * cm,
        'top': 1.5 * cm,
        'bottom': 1.5 * cm
    }

    def _obtener_o_crear_recursos(self, colegio):
        """Obtiene o crea los recursos del colegio si no existen"""
        try:
            # Intentar obtener los recursos existentes
            return colegio.recursos
        except ObjectDoesNotExist:
            # Si no existen, crear unos por defecto
            recursos = RecursosColegio.objects.create(
                colegio=colegio,
                sitio_web='https://colegiocrishadai.edu.co',
                email='info@colegiocrishadai.edu.co',
                telefono='+57 123 456 7890',
            )
            return recursos

    def get(self, request, *args, **kwargs):
        try:
            # Obtener estudiante según el tipo de usuario
            if hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario.nombre == 'Estudiante':
                estudiante = get_object_or_404(Estudiante, usuario=request.user)
            else:
                # Para admin/rector/docente, obtener estudiante por parámetro
                estudiante_id = request.GET.get('estudiante_id') or kwargs.get('estudiante_id')
                if estudiante_id:
                    estudiante = get_object_or_404(Estudiante, id=estudiante_id)
                else:
                    return HttpResponse("Estudiante no especificado", status=400)
            
            # Obtener año lectivo de los parámetros (opcional)
            año_lectivo_id = request.GET.get('año_lectivo_id') or kwargs.get('año_lectivo_id')
            
            # Si no se especifica año lectivo, usar el actual del estudiante
            if año_lectivo_id:
                año_lectivo = get_object_or_404(AñoLectivo, id=año_lectivo_id)
            else:
                # Si no se especifica, usar la lógica actual del estudiante
                if hasattr(estudiante, 'matricula_actual') and estudiante.matricula_actual:
                    año_lectivo = estudiante.matricula_actual.año_lectivo
                else:
                    # Buscar el año lectivo más reciente en el que estuvo matriculado
                    ultima_matricula = estudiante.matriculas.filter(
                        estado__in=['ACT', 'INA', 'RET']
                    ).select_related('año_lectivo').order_by('-año_lectivo__anho').first()
                    
                    if ultima_matricula:
                        año_lectivo = ultima_matricula.año_lectivo
                    else:
                        año_lectivo = None

            # Determinar tipo de documento
            tipo_documento = request.GET.get('tipo', 'observador')  # 'observador' o 'boletin_final'
            
            # Obtener observaciones del estudiante para el año lectivo
            from comportamiento.models import Comportamiento
            
            if año_lectivo:
                # Filtrar observaciones por año lectivo
                observaciones = Comportamiento.objects.filter(
                    estudiante=estudiante,
                    periodo_academico__año_lectivo=año_lectivo
                ).select_related(
                    'periodo_academico',
                    'periodo_academico__año_lectivo',
                    'docente',
                    'docente__usuario'
                ).order_by('-fecha', '-created_at')
                
                # Si es boletín final, solo obtener el 4to periodo
                if tipo_documento == 'boletin_final':
                    from academico.models import Periodo
                    periodo_cuarto = Periodo.objects.filter(nombre='Cuarto').first()
                    
                    if periodo_cuarto:
                        observaciones = observaciones.filter(
                            periodo_academico__periodo=periodo_cuarto
                        )
                    
                    # Obtener notas del 4to periodo para el boletín
                    notas_cuarto_periodo = None
                    if periodo_cuarto:
                        periodo_academico_cuarto = PeriodoAcademico.objects.filter(
                            año_lectivo=año_lectivo,
                            periodo=periodo_cuarto
                        ).first()
                        
                        if periodo_academico_cuarto:
                            notas_cuarto_periodo = Nota.objects.filter(
                                estudiante=estudiante,
                                periodo_academico=periodo_academico_cuarto
                            ).select_related(
                                'asignatura_grado_año_lectivo__asignatura',
                                'asignatura_grado_año_lectivo__asignatura__area'
                            ).order_by('asignatura_grado_año_lectivo__asignatura__nombre')
            else:
                observaciones = Comportamiento.objects.filter(
                    estudiante=estudiante
                ).select_related(
                    'periodo_academico',
                    'periodo_academico__año_lectivo',
                    'docente',
                    'docente__usuario'
                ).order_by('-fecha', '-created_at')
            
            colegio = Colegio.objects.filter(estado=True).first()

            if not colegio:
                raise Http404("Configuración del colegio no encontrada")

            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=self.MARGINS['right'],
                leftMargin=self.MARGINS['left'],
                topMargin=self.MARGINS['top'],
                bottomMargin=self.MARGINS['bottom']
            )

            # Construir elementos según el tipo de documento
            if tipo_documento == 'boletin_final':
                elements = self._construir_elementos_boletin_final(
                    estudiante, observaciones, notas_cuarto_periodo, año_lectivo, colegio
                )
            else:
                elements = self._construir_elementos_observador(
                    estudiante, observaciones, año_lectivo, colegio
                )

            doc.build(
                elements,
                onFirstPage=self._agregar_marca_agua,
                onLaterPages=self._agregar_marca_agua
            )

            pdf = buffer.getvalue()
            buffer.close()

            # Nombre del archivo según tipo
            if tipo_documento == 'boletin_final':
                nombre_archivo = f"boletin_final_{estudiante.usuario.nombres.replace(' ', '_')}_{año_lectivo.anho if año_lectivo else 'general'}_{timezone.now().strftime('%Y%m%d')}.pdf"
            else:
                nombre_archivo = f"observador_{estudiante.usuario.nombres.replace(' ', '_')}_{año_lectivo.anho if año_lectivo else 'general'}_{timezone.now().strftime('%Y%m%d')}.pdf"
            
            response = HttpResponse(pdf, content_type="application/pdf")
            response["Content-Disposition"] = f'inline; filename="{nombre_archivo}"'
            return response

        except Estudiante.DoesNotExist:
            return HttpResponse("Estudiante no encontrado", status=404)
        except Exception as e:
            print(f"Error generando observador: {e}")
            return HttpResponse("Error interno del servidor", status=500)

    # -------------------- MARCA DE AGUA --------------------
    def _agregar_marca_agua(self, canvas, doc):
        """Agrega marca de agua institucional."""
        try:
            colegio = Colegio.objects.filter(estado=True).first()
            if colegio:
                # Verificar si existe el objeto recursos
                try:
                    recursos = self._obtener_o_crear_recursos(colegio)
                    if recursos.escudo and os.path.exists(recursos.escudo.path):
                        logo_path = recursos.escudo.path
                        canvas.saveState()
                        canvas.setFillAlpha(0.07)

                        # Centrar imagen
                        page_width, page_height = doc.pagesize
                        wm_w, wm_h = 12 * cm, 12 * cm
                        x = (page_width - wm_w) / 2
                        y = (page_height - wm_h) / 2

                        canvas.drawImage(
                            logo_path, x, y, width=wm_w, height=wm_h,
                            preserveAspectRatio=True, mask='auto'
                        )
                        canvas.restoreState()
                        return
                except (ObjectDoesNotExist, AttributeError, ValueError, OSError) as e:
                    print(f"Error con recursos en marca de agua: {e}")
                    # Si hay algún error, usar marca de agua de texto
                    
            self._agregar_marca_agua_texto(canvas, doc)
        except Exception as e:
            print(f"Error en marca de agua: {e}")
            self._agregar_marca_agua_texto(canvas, doc)

    def _agregar_marca_agua_texto(self, canvas, doc):
        """Marca de agua de texto como fallback"""
        try:
            canvas.saveState()
            canvas.setFont("Helvetica-Bold", 50)
            canvas.setFillAlpha(0.07)
            canvas.rotate(45)
            canvas.drawCentredString(doc.pagesize[0] / 2, doc.pagesize[1] / 3, "OBSERVADOR ESTUDIANTIL")
            canvas.restoreState()
        except Exception as e:
            print(f"Error en marca de agua de texto: {e}")

    # -------------------- CONSTRUCCIÓN OBSERVADOR --------------------
    def _construir_elementos_observador(self, estudiante, observaciones, año_lectivo, colegio):
        styles = self._crear_estilos()
        elements = []

        elements.extend(self._crear_encabezado(colegio, styles))
        elements.extend(self._crear_titulo_observador(styles, año_lectivo))
        elements.extend(self._crear_info_estudiante(estudiante, año_lectivo, styles))
        elements.extend(self._crear_resumen_observaciones(observaciones, styles))
        elements.extend(self._crear_listado_observaciones(observaciones, styles))
        elements.extend(self._crear_firma_y_sello(estudiante, año_lectivo, styles))
        elements.extend(self._crear_pie_pagina(colegio, estudiante, año_lectivo, styles))

        return elements

    # -------------------- CONSTRUCCIÓN BOLETÍN FINAL --------------------
    def _construir_elementos_boletin_final(self, estudiante, observaciones, notas, año_lectivo, colegio):
        styles = self._crear_estilos()
        elements = []

        elements.extend(self._crear_encabezado(colegio, styles))
        elements.extend(self._crear_titulo_boletin_final(styles, año_lectivo))
        elements.extend(self._crear_info_estudiante(estudiante, año_lectivo, styles))
        
        # Agregar tabla de notas del 4to periodo
        if notas:
            elements.extend(self._crear_tabla_notas_boletin(notas, styles))
        
        # Agregar observaciones relevantes
        if observaciones:
            elements.extend(self._crear_observaciones_boletin(observaciones, styles))
        
        # Agregar resumen final y recomendaciones
        elements.extend(self._crear_resumen_final(estudiante, notas, observaciones, año_lectivo, styles))
        elements.extend(self._crear_firma_y_sello_boletin(estudiante, año_lectivo, styles))
        elements.extend(self._crear_pie_pagina(colegio, estudiante, año_lectivo, styles))

        return elements

    # -------------------- ESTILOS --------------------
    def _crear_estilos(self):
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="TituloColegio", fontSize=18, alignment=1, fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="Subtitulo", fontSize=11, alignment=1))
        styles.add(ParagraphStyle(name="TituloDocumento", fontSize=14, alignment=1, spaceAfter=15, fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="TituloBoletin", fontSize=16, alignment=1, spaceAfter=20, fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="TextoNormal", fontSize=12, alignment=4, leading=15))
        styles.add(ParagraphStyle(name="TextoResaltado", fontSize=12, alignment=4, leading=15, backColor=colors.whitesmoke))
        styles.add(ParagraphStyle(name="InfoEstudiante", fontSize=12, alignment=0, fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="InfoTexto", fontSize=12, alignment=0))
        styles.add(ParagraphStyle(name="ObservacionTitulo", fontSize=11, alignment=0, fontName="Helvetica-Bold", spaceAfter=3))
        styles.add(ParagraphStyle(name="ObservacionTexto", fontSize=10, alignment=4, leading=13))
        styles.add(ParagraphStyle(name="ObservacionDetalle", fontSize=9, alignment=0, textColor=colors.HexColor("#666")))
        styles.add(ParagraphStyle(name="TablaEncabezado", fontSize=10, alignment=1, fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="TablaContenido", fontSize=9, alignment=1))
        styles.add(ParagraphStyle(name="TablaAsignatura", fontSize=9, alignment=0))
        styles.add(ParagraphStyle(name="Sello", fontSize=9, textColor=colors.HexColor("#0A4BA0")))
        styles.add(ParagraphStyle(name="PiePagina", fontSize=9, alignment=1, textColor=colors.HexColor("#444")))
        styles.add(ParagraphStyle(name="FirmaNombre", fontSize=12, alignment=2, fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="FirmaCargo", fontSize=11, alignment=2))
        return styles

    # -------------------- SECCIONES OBSERVADOR --------------------
    def _crear_encabezado(self, colegio, styles):
        """Crear encabezado con manejo de errores para recursos"""
        logo = None
        try:
            # Obtener recursos (se crearán automáticamente si no existen)
            recursos = self._obtener_o_crear_recursos(colegio)
            if recursos.escudo and os.path.exists(recursos.escudo.path):
                logo = Image(recursos.escudo.path, width=80, height=80)
        except (ObjectDoesNotExist, AttributeError, ValueError, OSError) as e:
            print(f"Error cargando logo: {e}")
            # Continuar sin logo

        logo_cell = logo or Paragraph("ESCUDO<br/>NO DISPONIBLE", styles["Subtitulo"])

        # Información del colegio con valores por defecto
        resolucion = colegio.resolucion if colegio.resolucion else "---"
        dane = colegio.dane if colegio.dane else "---"
        direccion = colegio.direccion if colegio.direccion else "Valledupar - Cesar"

        info = [
            Paragraph("COLEGIO CRISTIANO EL SHADAI", styles["TituloColegio"]),
            Paragraph(f"Resolución de Estudios N.º {resolucion}", styles["Subtitulo"]),
            Paragraph(f"<b>COD. DANE {dane}</b>", styles["Subtitulo"]),
            Paragraph("Educación Preescolar – Básica Primaria", styles["Subtitulo"]),
            Paragraph(direccion, styles["Subtitulo"])
        ]
        info_table = Table([[line] for line in info])

        header = Table([[logo_cell, info_table]], colWidths=[3 * cm, 13 * cm])
        header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))

        linea = Table([[""]], colWidths=[16 * cm])
        linea.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 2, colors.black)]))

        return [header, Spacer(1, 10), linea, Spacer(1, 25)]

    def _crear_titulo_observador(self, styles, año_lectivo):
        if año_lectivo:
            return [Paragraph(f"OBSERVADOR DEL ESTUDIANTE - AÑO LECTIVO {año_lectivo.anho}", styles["TituloDocumento"])]
        return [Paragraph("OBSERVADOR DEL ESTUDIANTE", styles["TituloDocumento"])]

    def _crear_titulo_boletin_final(self, styles, año_lectivo):
        if año_lectivo:
            return [Paragraph(f"BOLETÍN FINAL - AÑO LECTIVO {año_lectivo.anho}", styles["TituloBoletin"])]
        return [Paragraph("BOLETÍN FINAL", styles["TituloBoletin"])]

    def _crear_info_estudiante(self, estudiante, año_lectivo, styles):
        """Información del estudiante"""
        tipo_doc = estudiante.usuario.tipo_documento.nombre if estudiante.usuario.tipo_documento else "Documento"
        
        # Obtener grado del año lectivo específico
        grado_info = "No asignado"
        if año_lectivo:
            matricula_año = estudiante.matriculas.filter(
                año_lectivo=año_lectivo,
                estado__in=['ACT', 'INA', 'RET']
            ).first()
            
            if matricula_año and matricula_año.grado_año_lectivo:
                grado_info = matricula_año.grado_año_lectivo.grado.nombre

        info_data = [
            [Paragraph("<b>ESTUDIANTE:</b>", styles["InfoEstudiante"]), 
             Paragraph(f"{estudiante.usuario.nombres} {estudiante.usuario.apellidos}", styles["InfoTexto"])],
            [Paragraph("<b>DOCUMENTO:</b>", styles["InfoEstudiante"]), 
             Paragraph(f"{tipo_doc} N.º {estudiante.usuario.numero_documento}", styles["InfoTexto"])],
            [Paragraph("<b>GRADO:</b>", styles["InfoEstudiante"]), 
             Paragraph(grado_info, styles["InfoTexto"])],
        ]

        if año_lectivo:
            info_data.append([
                Paragraph("<b>AÑO LECTIVO:</b>", styles["InfoEstudiante"]),
                Paragraph(año_lectivo.anho, styles["InfoTexto"])
            ])

        tabla_info = Table(info_data, colWidths=[4 * cm, 11 * cm])
        tabla_info.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))

        return [tabla_info, Spacer(1, 20)]

    def _crear_resumen_observaciones(self, observaciones, styles):
        """Resumen estadístico de observaciones"""
        if not observaciones:
            texto = "No se registran observaciones en el observador del estudiante."
            bloque = Table([[Paragraph(texto, styles["TextoNormal"])]], colWidths=[14 * cm])
            bloque.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("LEFTPADDING", (0, 0), (-1, -1), 15),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LINEBEFORE", (0, 0), (-1, -1), 3, colors.black)
            ]))
            return [bloque, Spacer(1, 20)]

        # Estadísticas
        total = len(observaciones)
        positivas = sum(1 for o in observaciones if o.tipo == 'Positivo')
        negativas = total - positivas
        
        categorias = {}
        for obs in observaciones:
            categorias[obs.categoria] = categorias.get(obs.categoria, 0) + 1

        texto_resumen = (
            f"<b>RESUMEN GENERAL</b><br/><br/>"
            f"<b>Total de observaciones:</b> {total}<br/>"
            f"<b>Observaciones positivas:</b> {positivas}<br/>"
            f"<b>Observaciones negativas:</b> {negativas}<br/>"
        )
        
        if categorias:
            texto_resumen += "<br/><b>Distribución por categorías:</b><br/>"
            for cat, count in categorias.items():
                texto_resumen += f"• {cat}: {count}<br/>"

        bloque = Table([[Paragraph(texto_resumen, styles["TextoNormal"])]], colWidths=[14 * cm])
        bloque.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
            ("LEFTPADDING", (0, 0), (-1, -1), 15),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("LINEBEFORE", (0, 0), (-1, -1), 3, colors.black)
        ]))
        return [bloque, Spacer(1, 20)]

    def _crear_listado_observaciones(self, observaciones, styles):
        """Listado detallado de observaciones"""
        if not observaciones:
            return []

        elements = [Paragraph("DETALLE DE OBSERVACIONES REGISTRADAS:", styles["TituloDocumento"]), Spacer(1, 15)]

        # Agrupar por período académico
        observaciones_por_periodo = {}
        for obs in observaciones:
            periodo_nombre = obs.periodo_academico.periodo.nombre if obs.periodo_academico else "Sin período"
            if periodo_nombre not in observaciones_por_periodo:
                observaciones_por_periodo[periodo_nombre] = []
            observaciones_por_periodo[periodo_nombre].append(obs)

        for periodo, obs_periodo in observaciones_por_periodo.items():
            elements.append(Paragraph(f"<b>Período: {periodo}</b>", styles["ObservacionTitulo"]))
            
            for i, obs in enumerate(obs_periodo, 1):
                # Color según tipo
                color_hex = "#2E7D32" if obs.tipo == 'Positivo' else "#C62828"
                
                # Encabezado de observación
                fecha_str = obs.fecha.strftime("%d/%m/%Y")
                titulo = f"Observación #{i} - {fecha_str} - <font color='{color_hex}'>{obs.tipo}</font> - {obs.categoria}"
                
                elements.append(Paragraph(titulo, styles["ObservacionTitulo"]))
                
                # Descripción
                elements.append(Paragraph(obs.descripcion, styles["ObservacionTexto"]))
                
                # Información adicional
                info_adicional = []
                if obs.docente and obs.docente.usuario:
                    docente_nombre = f"{obs.docente.usuario.nombres} {obs.docente.usuario.apellidos}"
                    info_adicional.append(f"Registrado por: {docente_nombre}")
                
                if info_adicional:
                    elements.append(Paragraph(" | ".join(info_adicional), styles["ObservacionDetalle"]))
                
                elements.append(Spacer(1, 8))
            
            elements.append(Spacer(1, 15))

        return elements

    def _crear_tabla_notas_boletin(self, notas, styles):
        """Tabla de notas para el boletín final"""
        if not notas:
            return [Paragraph("No hay calificaciones registradas para este período.", styles["TextoNormal"]), Spacer(1, 20)]

        # Encabezado de la tabla
        encabezados = [
            Paragraph("ASIGNATURA", styles["TablaEncabezado"]),
            Paragraph("AREA", styles["TablaEncabezado"]),
            Paragraph("NOTA", styles["TablaEncabezado"]),
            Paragraph("DESEMPEÑO", styles["TablaEncabezado"])
        ]

        datos_tabla = [encabezados]

        # Llenar datos de la tabla
        for nota in notas:
            # Información de la asignatura
            asignatura_nombre = nota.asignatura_grado_año_lectivo.asignatura.nombre if nota.asignatura_grado_año_lectivo.asignatura else "Asignatura no definida"
            asignatura = Paragraph(asignatura_nombre, styles["TablaAsignatura"])
            
            # Información del área
            area_nombre = ""
            if nota.asignatura_grado_año_lectivo.asignatura and nota.asignatura_grado_año_lectivo.asignatura.area:
                area_nombre = nota.asignatura_grado_año_lectivo.asignatura.area.nombre
            area = Paragraph(area_nombre, styles["TablaContenido"])
            
            # Nota y desempeño
            if nota.calificacion:
                try:
                    calificacion = float(nota.calificacion)
                    nota_texto = Paragraph(f"{calificacion:.1f}", styles["TablaContenido"])
                    desempeno = self._determinar_desempeno_boletin(calificacion)
                    desempeno_texto = Paragraph(desempeno, styles["TablaContenido"])
                except (ValueError, TypeError):
                    nota_texto = Paragraph("N/A", styles["TablaContenido"])
                    desempeno_texto = Paragraph("Error", styles["TablaContenido"])
            else:
                nota_texto = Paragraph("N/A", styles["TablaContenido"])
                desempeno_texto = Paragraph("Sin evaluar", styles["TablaContenido"])
            
            datos_tabla.append([asignatura, area, nota_texto, desempeno_texto])

        # Crear tabla
        tabla = Table(datos_tabla, colWidths=[6 * cm, 4 * cm, 2 * cm, 3 * cm])
        tabla.setStyle(TableStyle([
            # Estilo del encabezado
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0A4BA0")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Estilo del contenido
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),  # Alinear asignatura a la izquierda
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),  # Alinear área a la izquierda
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#DDDDDD")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
        ]))

        return [Paragraph("CALIFICACIONES - CUARTO PERÍODO:", styles["TituloDocumento"]), 
                Spacer(1, 10), tabla, Spacer(1, 20)]

    def _crear_observaciones_boletin(self, observaciones, styles):
        """Observaciones relevantes para el boletín"""
        if not observaciones:
            return []

        elements = [Paragraph("OBSERVACIONES RELEVANTES:", styles["TituloDocumento"]), Spacer(1, 10)]

        # Tomar las últimas 5 observaciones más relevantes
        observaciones_relevantes = observaciones[:5]
        
        for i, obs in enumerate(observaciones_relevantes, 1):
            # Color según tipo
            color_hex = "#2E7D32" if obs.tipo == 'Positivo' else "#C62828"
            
            # Encabezado de observación
            fecha_str = obs.fecha.strftime("%d/%m/%Y")
            titulo = f"• <font color='{color_hex}'>{obs.tipo}</font> - {obs.categoria} ({fecha_str})"
            
            elements.append(Paragraph(titulo, styles["ObservacionTitulo"]))
            
            # Descripción
            elements.append(Paragraph(obs.descripcion, styles["ObservacionTexto"]))
            elements.append(Spacer(1, 8))

        return elements

    def _crear_resumen_final(self, estudiante, notas, observaciones, año_lectivo, styles):
        """Resumen final y recomendaciones"""
        try:
            # Calcular estadísticas de notas
            if notas:
                calificaciones = [float(n.calificacion) for n in notas if n.calificacion]
                promedio = sum(calificaciones) / len(calificaciones) if calificaciones else 0
                max_nota = max(calificaciones) if calificaciones else 0
                min_nota = min(calificaciones) if calificaciones else 0
                
                # Calcular desempeño general
                desempeno_general = self._determinar_desempeno_boletin(promedio)
            else:
                promedio = 0
                max_nota = 0
                min_nota = 0
                desempeno_general = "Sin calificar"
            
            # Estadísticas de observaciones
            if observaciones:
                total_obs = len(observaciones)
                obs_positivas = sum(1 for o in observaciones if o.tipo == 'Positivo')
                obs_negativas = total_obs - obs_positivas
            else:
                total_obs = 0
                obs_positivas = 0
                obs_negativas = 0
            
            # Determinar recomendación final
            if promedio >= 4.5:
                recomendacion = "EXCELENTE RENDIMIENTO ACADÉMICO. El estudiante ha demostrado un desempeño sobresaliente en todas las áreas."
            elif promedio >= 4.0:
                recomendacion = "BUEN RENDIMIENTO ACADÉMICO. El estudiante muestra un buen desempeño académico y actitudinal."
            elif promedio >= 3.5:
                recomendacion = "RENDIMIENTO ACEPTABLE. Se recomienda reforzar algunas áreas académicas para mejorar el desempeño."
            elif promedio >= 3.0:
                recomendacion = "RENDIMIENTO BÁSICO. Se requiere mayor esfuerzo académico y seguimiento constante."
            else:
                recomendacion = "RENDIMIENTO BAJO. Se recomienda plan de mejoramiento académico y seguimiento especializado."
            
            # Ajustar recomendación según observaciones
            if obs_negativas > obs_positivas:
                recomendacion += " Se observa necesidad de mejorar el comportamiento y actitud en el aula."
            
            texto_resumen = (
                f"<b>RESUMEN FINAL DEL AÑO LECTIVO</b><br/><br/>"
                f"<b>Promedio general:</b> {promedio:.2f}<br/>"
                f"<b>Desempeño académico:</b> {desempeno_general}<br/>"
                f"<b>Nota más alta:</b> {max_nota:.1f}<br/>"
                f"<b>Nota más baja:</b> {min_nota:.1f}<br/><br/>"
                f"<b>Observaciones registradas:</b> {total_obs}<br/>"
                f"<b>Observaciones positivas:</b> {obs_positivas}<br/>"
                f"<b>Observaciones negativas:</b> {obs_negativas}<br/><br/>"
                f"<b>RECOMENDACIÓN FINAL:</b><br/>{recomendacion}"
            )

            bloque = Table([[Paragraph(texto_resumen, styles["TextoNormal"])]], colWidths=[14 * cm])
            bloque.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F8FF")),
                ("LEFTPADDING", (0, 0), (-1, -1), 15),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0A4BA0")),
            ]))
            return [bloque, Spacer(1, 20)]

        except Exception as e:
            print(f"Error en resumen final: {e}")
            return [Spacer(1, 20)]

    def _crear_firma_y_sello(self, estudiante, año_lectivo, styles):
        """Firma y sello para observador"""
        fecha = self._formatear_fecha_espanol()

        # Sello
        año_lectivo_str = año_lectivo.anho if año_lectivo else "General"
        sello_text = (
            f"Observador generado electrónicamente<br/>{fecha}<br/>"
            f"Código: {estudiante.usuario.numero_documento}-OBS-{año_lectivo_str}"
        )
        sello = Table([[Paragraph(sello_text, styles["Sello"])]], colWidths=[5 * cm])
        sello.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0A4BA0")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F8FF")),
            ("PADDING", (0, 0), (-1, -1), 8)
        ]))

        # Firma
        firma = Table([
            [Paragraph("María Mederis Madero Garrido", styles["FirmaNombre"])],
            [Paragraph("Directora - Colegio Cristiano El Shadai", styles["FirmaCargo"])]
        ], colWidths=[8 * cm])

        # Combinar en una fila
        fila = Table([[sello, firma]], colWidths=[7 * cm, 8 * cm])
        fila.setStyle(TableStyle([
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP")
        ]))
        return [Spacer(1, 30), fila, Spacer(1, 20)]

    def _crear_firma_y_sello_boletin(self, estudiante, año_lectivo, styles):
        """Firma y sello para boletín final"""
        fecha = self._formatear_fecha_espanol()

        # Sello
        año_lectivo_str = año_lectivo.anho if año_lectivo else "General"
        sello_text = (
            f"Boletín final generado electrónicamente<br/>{fecha}<br/>"
            f"Código: {estudiante.usuario.numero_documento}-BOL-{año_lectivo_str}"
        )
        sello = Table([[Paragraph(sello_text, styles["Sello"])]], colWidths=[5 * cm])
        sello.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0A4BA0")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F8FF")),
            ("PADDING", (0, 0), (-1, -1), 8)
        ]))

        # Firma
        firma = Table([
            [Paragraph("María Mederis Madero Garrido", styles["FirmaNombre"])],
            [Paragraph("Directora - Colegio Cristiano El Shadai", styles["FirmaCargo"])]
        ], colWidths=[8 * cm])

        # Combinar en una fila
        fila = Table([[sello, firma]], colWidths=[7 * cm, 8 * cm])
        fila.setStyle(TableStyle([
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP")
        ]))
        return [Spacer(1, 30), firma, Spacer(1, 20)]

    def _crear_pie_pagina(self, colegio, estudiante, año_lectivo, styles):
        """Pie de página"""
        try:
            # Obtener información de contacto
            direccion = colegio.direccion if colegio.direccion else "Dirección no especificada"
            
            # Obtener recursos (se crearán automáticamente si no existen)
            try:
                recursos = self._obtener_o_crear_recursos(colegio)
                telefono = recursos.telefono or ""
                celular = getattr(recursos, "celular", "") or ""
                email = recursos.email or ""
                web = recursos.sitio_web or ""
            except Exception as e:
                print(f"Error obteniendo recursos para pie de página: {e}")
                telefono = celular = email = web = ""

            año_lectivo_str = año_lectivo.anho if año_lectivo else "Todos los años"
            lineas = [
                "<b>COLEGIO CRISTIANO EL SHADAI</b>",
                f"{direccion}" + (f" | Tel: {telefono}" if telefono else "") + (f" | Cel: {celular}" if celular else ""),
                (f"Email: {email}" if email else "") + (f" | Web: {web}" if web else ""),
                f"Documento de: {estudiante.usuario.nombres} {estudiante.usuario.apellidos} | Año: {año_lectivo_str} | Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}"
            ]
            
            # Filtrar líneas vacías
            lineas = [linea for linea in lineas if linea.strip()]
            texto = "<br/>".join(lineas)

            linea = Table([[""]], colWidths=[15 * cm])
            linea.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 1, colors.HexColor('#888'))]))

            return [Spacer(1, 40), linea, Spacer(1, 8), Paragraph(texto, styles["PiePagina"])]

        except Exception as e:
            print(f"Error en pie de página: {e}")
            return [Spacer(1, 40)]

    # -------------------- MÉTODOS AUXILIARES --------------------
    def _determinar_desempeno_boletin(self, calificacion):
        """Determina el desempeño para el boletín final"""
        if calificacion >= 4.5:
            return "Superior"
        elif calificacion >= 4.0:
            return "Alto"
        elif calificacion >= 3.5:
            return "Básico"
        else:
            return "Bajo"

    def _formatear_fecha_espanol(self):
        meses = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
        ]
        now = timezone.now()
        return f"{now.day} de {meses[now.month - 1]} de {now.year}"

class ReporteNotasPDFView(View):
    """Genera el reporte de notas del estudiante en formato PDF (solo ReportLab)."""

    MARGINS = {
        'left': 2 * cm,
        'right': 2 * cm,
        'top': 1.5 * cm,
        'bottom': 1.5 * cm
    }

    def _obtener_o_crear_recursos(self, colegio):
        """Obtiene o crea los recursos del colegio si no existen"""
        try:
            # Intentar obtener los recursos existentes
            return colegio.recursos
        except ObjectDoesNotExist:
            # Si no existen, crear unos por defecto
            recursos = RecursosColegio.objects.create(
                colegio=colegio,
                sitio_web='https://colegiocrishadai.edu.co',
                email='info@colegiocrishadai.edu.co',
                telefono='+57 123 456 7890',
            )
            return recursos

    def get(self, request, *args, **kwargs):
        try:
            # Determinar el tipo de reporte
            reporte_tipo = kwargs.get('tipo', request.GET.get('tipo', 'notas'))  # 'notas' o 'final'
            
            # Obtener estudiante según el tipo de usuario
            if hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario.nombre == 'Estudiante':
                estudiante = get_object_or_404(Estudiante, usuario=request.user)
            else:
                # Para admin/rector/docente, obtener estudiante por parámetro
                estudiante_id = request.GET.get('estudiante_id') or kwargs.get('estudiante_id')
                if estudiante_id:
                    estudiante = get_object_or_404(Estudiante, id=estudiante_id)
                else:
                    return HttpResponse("Estudiante no especificado", status=400)
            
            # Obtener año lectivo y período según el tipo de reporte
            año_lectivo = None
            periodo = None
            
            if reporte_tipo == 'final':
                # Para boletín final, obtener por año lectivo
                año_lectivo_id = kwargs.get('año_lectivo_id') or request.GET.get('año_lectivo_id')
                if año_lectivo_id:
                    año_lectivo = get_object_or_404(AñoLectivo, id=año_lectivo_id)
                else:
                    # Usar año lectivo actual del estudiante
                    if estudiante.grado_actual:
                        año_lectivo = estudiante.grado_actual.año_lectivo
                    else:
                        # Buscar último año lectivo matriculado
                        ultima_matricula = estudiante.matriculas.filter(
                            estado__in=['ACT', 'INA', 'RET']
                        ).order_by('-año_lectivo__anho').first()
                        if ultima_matricula:
                            año_lectivo = ultima_matricula.año_lectivo
                        else:
                            return HttpResponse("No se encontró año lectivo para el estudiante", status=400)
                
                # Obtener el 4to período del año lectivo
                from academico.models import Periodo
                periodo_cuarto = Periodo.objects.filter(nombre='Cuarto').first()
                if periodo_cuarto and año_lectivo:
                    periodo = PeriodoAcademico.objects.filter(
                        año_lectivo=año_lectivo,
                        periodo=periodo_cuarto
                    ).first()
            else:
                # Para reporte normal, obtener período específico
                periodo_id = kwargs.get('periodo_id') or request.GET.get('periodo_id')
                if periodo_id:
                    periodo = get_object_or_404(PeriodoAcademico, id=periodo_id)
                else:
                    # Obtener período actual del año lectivo activo
                    año_actual = AñoLectivo.objects.filter(estado=True).first()
                    if año_actual:
                        periodo = PeriodoAcademico.objects.filter(
                            año_lectivo=año_actual,
                            estado=True
                        ).order_by('-fecha_inicio').first()
                    else:
                        # Si no hay año activo, usar el último período registrado para el estudiante
                        ultimo_periodo = PeriodoAcademico.objects.filter(
                            año_lectivo__in=estudiante.matriculas.values_list('año_lectivo', flat=True)
                        ).order_by('-fecha_inicio').first()
                        periodo = ultimo_periodo
            
            # Si no se encontró período y es reporte de notas, mostrar error
            if not periodo and reporte_tipo == 'notas':
                return HttpResponse("No se encontró período académico", status=400)
            
            colegio = Colegio.objects.filter(estado=True).first()

            if not colegio:
                raise Http404("Configuración del colegio no encontrada")

            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=self.MARGINS['right'],
                leftMargin=self.MARGINS['left'],
                topMargin=self.MARGINS['top'],
                bottomMargin=self.MARGINS['bottom']
            )

            # Construir elementos según el tipo
            if reporte_tipo == 'final':
                elements = self._construir_elementos_boletin_final(
                    estudiante, periodo, año_lectivo, colegio
                )
            else:
                elements = self._construir_elementos_reporte_notas(
                    estudiante, periodo, colegio
                )

            doc.build(
                elements,
                onFirstPage=self._agregar_marca_agua,
                onLaterPages=self._agregar_marca_agua
            )

            pdf = buffer.getvalue()
            buffer.close()

            # Nombre del archivo según tipo
            if reporte_tipo == 'final':
                nombre_archivo = f"boletin_final_{estudiante.usuario.nombres.replace(' ', '_')}_{año_lectivo.anho if año_lectivo else 'general'}_{timezone.now().strftime('%Y%m%d')}.pdf"
            else:
                nombre_archivo = f"reporte_notas_{estudiante.usuario.nombres.replace(' ', '_')}_{periodo.periodo.nombre if periodo else 'actual'}_{timezone.now().strftime('%Y%m%d')}.pdf"
            
            response = HttpResponse(pdf, content_type="application/pdf")
            response["Content-Disposition"] = f'inline; filename="{nombre_archivo}"'
            return response

        except Estudiante.DoesNotExist:
            return HttpResponse("Estudiante no encontrado", status=404)
        except Exception as e:
            print(f"Error generando reporte de notas: {e}")
            return HttpResponse("Error interno del servidor", status=500)

    # -------------------- MARCA DE AGUA --------------------
    def _agregar_marca_agua(self, canvas, doc):
        """Agrega marca de agua institucional."""
        try:
            colegio = Colegio.objects.filter(estado=True).first()
            if colegio:
                # Verificar si existe el objeto recursos
                try:
                    recursos = self._obtener_o_crear_recursos(colegio)
                    if recursos.escudo and os.path.exists(recursos.escudo.path):
                        logo_path = recursos.escudo.path
                        canvas.saveState()
                        canvas.setFillAlpha(0.07)

                        # Centrar imagen
                        page_width, page_height = doc.pagesize
                        wm_w, wm_h = 12 * cm, 12 * cm
                        x = (page_width - wm_w) / 2
                        y = (page_height - wm_h) / 2

                        canvas.drawImage(
                            logo_path, x, y, width=wm_w, height=wm_h,
                            preserveAspectRatio=True, mask='auto'
                        )
                        canvas.restoreState()
                        return
                except (ObjectDoesNotExist, AttributeError, ValueError, OSError) as e:
                    print(f"Error con recursos en marca de agua: {e}")
                    # Si hay algún error, usar marca de agua de texto
                    
            self._agregar_marca_agua_texto(canvas, doc)
        except Exception as e:
            print(f"Error en marca de agua: {e}")
            self._agregar_marca_agua_texto(canvas, doc)

    def _agregar_marca_agua_texto(self, canvas, doc):
        """Marca de agua de texto como fallback"""
        try:
            canvas.saveState()
            canvas.setFont("Helvetica-Bold", 50)
            canvas.setFillAlpha(0.07)
            canvas.rotate(45)
            canvas.drawCentredString(doc.pagesize[0] / 2, doc.pagesize[1] / 3, "REPORTE DE NOTAS")
            canvas.restoreState()
        except Exception as e:
            print(f"Error en marca de agua de texto: {e}")

    # -------------------- CONSTRUCCIÓN REPORTE NORMAL --------------------
    def _construir_elementos_reporte_notas(self, estudiante, periodo, colegio):
        styles = self._crear_estilos()
        elements = []

        elements.extend(self._crear_encabezado(colegio, styles))
        elements.extend(self._crear_titulo_reporte(styles, periodo))
        elements.extend(self._crear_info_estudiante_periodo(estudiante, periodo, styles))
        
        # Obtener datos de asignaturas
        datos_asignaturas = self._obtener_datos_asignaturas_periodo(estudiante, periodo)
        
        elements.extend(self._crear_resumen_academico(datos_asignaturas, styles))
        elements.extend(self._crear_tabla_notas(datos_asignaturas, styles))
        elements.extend(self._crear_analisis_rendimiento(datos_asignaturas, styles))
        elements.extend(self._crear_firma_y_sello(estudiante, periodo, styles))
        elements.extend(self._crear_pie_pagina(colegio, estudiante, periodo, styles))

        return elements

    # -------------------- CONSTRUCCIÓN BOLETÍN FINAL --------------------
    def _construir_elementos_boletin_final(self, estudiante, periodo, año_lectivo, colegio):
        styles = self._crear_estilos()
        elements = []

        elements.extend(self._crear_encabezado(colegio, styles))
        elements.extend(self._crear_titulo_boletin_final(styles, año_lectivo))
        elements.extend(self._crear_info_estudiante_año(estudiante, año_lectivo, styles))
        
        # Obtener datos de todos los períodos del año
        datos_completos = self._obtener_datos_completos_año(estudiante, año_lectivo)
        
        # Si hay un período específico (4to), mostrar sus notas
        if periodo:
            datos_periodo = self._obtener_datos_asignaturas_periodo(estudiante, periodo)
            elements.extend(self._crear_tabla_notas_final(datos_periodo, periodo, styles))
        
        elements.extend(self._crear_resumen_final(datos_completos, año_lectivo, styles))
        elements.extend(self._crear_analisis_final(datos_completos, styles))
        elements.extend(self._crear_firma_y_sello_final(estudiante, año_lectivo, styles))
        elements.extend(self._crear_pie_pagina_final(colegio, estudiante, año_lectivo, styles))

        return elements

    # -------------------- ESTILOS --------------------
    def _crear_estilos(self):
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="TituloColegio", fontSize=18, alignment=1, fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="Subtitulo", fontSize=11, alignment=1))
        styles.add(ParagraphStyle(name="TituloDocumento", fontSize=14, alignment=1, spaceAfter=15, fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="TituloBoletin", fontSize=16, alignment=1, spaceAfter=20, fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="TextoNormal", fontSize=12, alignment=4, leading=15))
        styles.add(ParagraphStyle(name="TextoResaltado", fontSize=12, alignment=4, leading=15, backColor=colors.whitesmoke))
        styles.add(ParagraphStyle(name="InfoEstudiante", fontSize=12, alignment=0, fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="InfoTexto", fontSize=12, alignment=0))
        styles.add(ParagraphStyle(name="TablaEncabezado", fontSize=10, alignment=1, fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="TablaContenido", fontSize=9, alignment=1))
        styles.add(ParagraphStyle(name="TablaAsignatura", fontSize=9, alignment=0))
        styles.add(ParagraphStyle(name="TablaDesempeno", fontSize=9, alignment=1))
        styles.add(ParagraphStyle(name="AnalisisTitulo", fontSize=11, alignment=0, fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="AnalisisTexto", fontSize=10, alignment=4))
        styles.add(ParagraphStyle(name="Sello", fontSize=9, textColor=colors.HexColor("#0A4BA0")))
        styles.add(ParagraphStyle(name="PiePagina", fontSize=9, alignment=1, textColor=colors.HexColor("#444")))
        styles.add(ParagraphStyle(name="FirmaNombre", fontSize=12, alignment=2, fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="FirmaCargo", fontSize=11, alignment=2))
        return styles

    # -------------------- OBTENCIÓN DE DATOS --------------------
    def _obtener_datos_asignaturas_periodo(self, estudiante, periodo):
        """Obtiene las asignaturas con notas para un período específico"""
        try:
            # Obtener notas del período
            notas = Nota.objects.filter(
                estudiante=estudiante,
                periodo_academico=periodo
            ).select_related('asignatura_grado_año_lectivo__asignatura')

            # Obtener matrícula del estudiante para este período
            año_lectivo = periodo.año_lectivo
            matricula = estudiante.matriculas.filter(
                año_lectivo=año_lectivo,
                estado__in=['ACT', 'INA', 'RET']
            ).first()

            if not matricula or not matricula.grado_año_lectivo:
                return {'asignaturas': [], 'total_asignaturas': 0, 'asignaturas_evaluadas': 0, 'promedio': 0}

            # Obtener asignaturas del grado
            asignaturas_grado = AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo=matricula.grado_año_lectivo,
                sede=matricula.sede
            ).select_related('asignatura', 'docente__usuario')

            # Obtener logros para cada asignatura
            logros = Logro.objects.filter(
                grado=matricula.grado_año_lectivo.grado,
                periodo_academico=periodo
            ).select_related('asignatura')

            asignaturas_data = []
            total_calificaciones = 0
            asignaturas_evaluadas = 0
            
            for ag in asignaturas_grado:
                # Buscar la nota correspondiente
                nota_obj = notas.filter(asignatura_grado_año_lectivo=ag).first()
                
                # Buscar el logro correspondiente
                logro_asignatura = logros.filter(asignatura=ag.asignatura).first()
                logro_texto = ""
                
                if logro_asignatura and nota_obj and nota_obj.calificacion:
                    calificacion = float(nota_obj.calificacion)
                    # Determinar qué descripción de logro mostrar según la calificación
                    if calificacion >= 4.5 and logro_asignatura.descripcion_superior:
                        logro_texto = logro_asignatura.descripcion_superior
                    elif calificacion >= 4.0 and logro_asignatura.descripcion_alto:
                        logro_texto = logro_asignatura.descripcion_alto
                    elif calificacion >= 3.5 and logro_asignatura.descripcion_basico:
                        logro_texto = logro_asignatura.descripcion_basico
                    elif logro_asignatura.descripcion_bajo:
                        logro_texto = logro_asignatura.descripcion_bajo
                    elif logro_asignatura.tema:
                        logro_texto = logro_asignatura.tema

                # Inicializar item con información básica
                item = {
                    'nombre': ag.asignatura.nombre,
                    'docente': f"{ag.docente.usuario.nombres} {ag.docente.usuario.apellidos}" if ag.docente else 'Sin asignar',
                    'area': ag.asignatura.area.nombre if ag.asignatura.area else 'Sin área',
                    'tiene_nota': nota_obj is not None and nota_obj.calificacion is not None,
                    'logro': logro_texto,
                    'calificacion': None,
                    'desempeno': 'Sin calificar'
                }
                
                # Si hay nota, calcular calificación y desempeño
                if item['tiene_nota'] and nota_obj.calificacion:
                    try:
                        calificacion = round(float(nota_obj.calificacion), 1)
                        desempeno = self._determinar_desempeno(calificacion)
                        
                        item.update({
                            'calificacion': calificacion,
                            'desempeno': desempeno,
                            'observaciones': nota_obj.observaciones if hasattr(nota_obj, 'observaciones') else ''
                        })
                        
                        total_calificaciones += calificacion
                        asignaturas_evaluadas += 1
                        
                    except (ValueError, TypeError) as e:
                        print(f"Error procesando calificación: {e}")
                        item['tiene_nota'] = False
                
                asignaturas_data.append(item)
            
            # Calcular estadísticas
            promedio = total_calificaciones / asignaturas_evaluadas if asignaturas_evaluadas > 0 else 0
            
            return {
                'asignaturas': asignaturas_data,
                'total_asignaturas': len(asignaturas_data),
                'asignaturas_evaluadas': asignaturas_evaluadas,
                'promedio': promedio,
                'periodo_nombre': periodo.periodo.nombre if periodo else 'Sin período',
            }
            
        except Exception as e:
            print(f"Error obteniendo datos de asignaturas: {e}")
            return {
                'asignaturas': [],
                'total_asignaturas': 0,
                'asignaturas_evaluadas': 0,
                'promedio': 0,
                'periodo_nombre': 'Error',
            }

    def _obtener_datos_completos_año(self, estudiante, año_lectivo):
        """Obtiene datos completos de todos los períodos del año"""
        try:
            # Obtener todos los períodos del año lectivo
            periodos = PeriodoAcademico.objects.filter(
                año_lectivo=año_lectivo
            ).order_by('fecha_inicio')
            
            datos_periodos = {}
            promedios_periodos = {}
            
            for periodo in periodos:
                datos = self._obtener_datos_asignaturas_periodo(estudiante, periodo)
                datos_periodos[periodo.periodo.nombre] = datos
                promedios_periodos[periodo.periodo.nombre] = datos['promedio']
            
            # Calcular promedio final del año
            promedios_validos = [p for p in promedios_periodos.values() if p > 0]
            promedio_final = sum(promedios_validos) / len(promedios_validos) if promedios_validos else 0
            
            return {
                'periodos': datos_periodos,
                'promedios_periodos': promedios_periodos,
                'promedio_final': promedio_final,
                'total_periodos': len(periodos),
                'año_lectivo': año_lectivo.anho,
            }
            
        except Exception as e:
            print(f"Error obteniendo datos completos del año: {e}")
            return {
                'periodos': {},
                'promedios_periodos': {},
                'promedio_final': 0,
                'total_periodos': 0,
                'año_lectivo': 'Error',
            }

    # -------------------- SECCIONES REPORTE NORMAL --------------------
    def _crear_encabezado(self, colegio, styles):
        """Crear encabezado con manejo de errores para recursos"""
        logo = None
        try:
            # Obtener recursos (se crearán automáticamente si no existen)
            recursos = self._obtener_o_crear_recursos(colegio)
            if recursos.escudo and os.path.exists(recursos.escudo.path):
                logo = Image(recursos.escudo.path, width=80, height=80)
        except (ObjectDoesNotExist, AttributeError, ValueError, OSError) as e:
            print(f"Error cargando logo: {e}")
            # Continuar sin logo

        logo_cell = logo or Paragraph("ESCUDO<br/>NO DISPONIBLE", styles["Subtitulo"])

        # Información del colegio con valores por defecto
        resolucion = colegio.resolucion if colegio.resolucion else "---"
        dane = colegio.dane if colegio.dane else "---"
        direccion = colegio.direccion if colegio.direccion else "Valledupar - Cesar"

        info = [
            Paragraph("COLEGIO CRISTIANO EL SHADAI", styles["TituloColegio"]),
            Paragraph(f"Resolución de Estudios N.º {resolucion}", styles["Subtitulo"]),
            Paragraph(f"<b>COD. DANE {dane}</b>", styles["Subtitulo"]),
            Paragraph("Educación Preescolar – Básica Primaria", styles["Subtitulo"]),
            Paragraph(direccion, styles["Subtitulo"])
        ]
        info_table = Table([[line] for line in info])

        header = Table([[logo_cell, info_table]], colWidths=[3 * cm, 13 * cm])
        header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))

        linea = Table([[""]], colWidths=[16 * cm])
        linea.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 2, colors.black)]))

        return [header, Spacer(1, 10), linea, Spacer(1, 25)]

    def _crear_titulo_reporte(self, styles, periodo):
        if periodo:
            return [Paragraph(f"CERTIFICADO ACADÉMICO DE NOTAS - {periodo.periodo.nombre.upper()}", styles["TituloDocumento"])]
        return [Paragraph("CERTIFICADO ACADÉMICO DE NOTAS", styles["TituloDocumento"])]

    def _crear_titulo_boletin_final(self, styles, año_lectivo):
        if año_lectivo:
            return [Paragraph(f"BOLETÍN FINAL - AÑO LECTIVO {año_lectivo.anho}", styles["TituloBoletin"])]
        return [Paragraph("BOLETÍN FINAL", styles["TituloBoletin"])]

    def _crear_info_estudiante_periodo(self, estudiante, periodo, styles):
        """Información del estudiante y período académico"""
        tipo_doc = estudiante.usuario.tipo_documento.nombre if estudiante.usuario.tipo_documento else "Documento"
        
        # Obtener información del grado para el período
        grado_info = "No asignado"
        año_lectivo_info = "No asignado"
        
        if periodo:
            matricula = estudiante.matriculas.filter(
                año_lectivo=periodo.año_lectivo,
                estado__in=['ACT', 'INA', 'RET']
            ).first()
            
            if matricula and matricula.grado_año_lectivo:
                grado_info = matricula.grado_año_lectivo.grado.nombre
                año_lectivo_info = matricula.año_lectivo.anho

        info_data = [
            [Paragraph("<b>ESTUDIANTE:</b>", styles["InfoEstudiante"]), 
             Paragraph(f"{estudiante.usuario.nombres} {estudiante.usuario.apellidos}", styles["InfoTexto"])],
            [Paragraph("<b>DOCUMENTO:</b>", styles["InfoEstudiante"]), 
             Paragraph(f"{tipo_doc} N.º {estudiante.usuario.numero_documento}", styles["InfoTexto"])],
            [Paragraph("<b>GRADO:</b>", styles["InfoEstudiante"]), 
             Paragraph(grado_info, styles["InfoTexto"])],
            [Paragraph("<b>AÑO LECTIVO:</b>", styles["InfoEstudiante"]), 
             Paragraph(año_lectivo_info, styles["InfoTexto"])],
        ]

        if periodo:
            fecha_inicio = periodo.fecha_inicio.strftime('%d/%m/%Y') if periodo.fecha_inicio else "Fecha no definida"
            fecha_fin = periodo.fecha_fin.strftime('%d/%m/%Y') if periodo.fecha_fin else "Fecha no definida"
            info_data.append([
                Paragraph("<b>PERÍODO:</b>", styles["InfoEstudiante"]),
                Paragraph(f"{periodo.periodo.nombre} - Del {fecha_inicio} al {fecha_fin}", styles["InfoTexto"])
            ])

        tabla_info = Table(info_data, colWidths=[4 * cm, 11 * cm])
        tabla_info.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))

        return [tabla_info, Spacer(1, 20)]

    def _crear_info_estudiante_año(self, estudiante, año_lectivo, styles):
        """Información del estudiante para boletín final"""
        tipo_doc = estudiante.usuario.tipo_documento.nombre if estudiante.usuario.tipo_documento else "Documento"
        
        # Obtener información del grado para el año lectivo
        grado_info = "No asignado"
        
        if año_lectivo:
            matricula = estudiante.matriculas.filter(
                año_lectivo=año_lectivo,
                estado__in=['ACT', 'INA', 'RET']
            ).first()
            
            if matricula and matricula.grado_año_lectivo:
                grado_info = matricula.grado_año_lectivo.grado.nombre

        info_data = [
            [Paragraph("<b>ESTUDIANTE:</b>", styles["InfoEstudiante"]), 
             Paragraph(f"{estudiante.usuario.nombres} {estudiante.usuario.apellidos}", styles["InfoTexto"])],
            [Paragraph("<b>DOCUMENTO:</b>", styles["InfoEstudiante"]), 
             Paragraph(f"{tipo_doc} N.º {estudiante.usuario.numero_documento}", styles["InfoTexto"])],
            [Paragraph("<b>GRADO:</b>", styles["InfoEstudiante"]), 
             Paragraph(grado_info, styles["InfoTexto"])],
            [Paragraph("<b>AÑO LECTIVO:</b>", styles["InfoEstudiante"]), 
             Paragraph(año_lectivo.anho if año_lectivo else "No asignado", styles["InfoTexto"])],
        ]

        tabla_info = Table(info_data, colWidths=[4 * cm, 11 * cm])
        tabla_info.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))

        return [tabla_info, Spacer(1, 20)]

    def _crear_resumen_academico(self, datos_asignaturas, styles):
        """Resumen académico con estadísticas"""
        try:
            asignaturas_data = datos_asignaturas['asignaturas']
            total_asignaturas = datos_asignaturas['total_asignaturas']
            asignaturas_evaluadas = datos_asignaturas['asignaturas_evaluadas']
            promedio = datos_asignaturas['promedio']
            periodo_nombre = datos_asignaturas.get('periodo_nombre', 'Período')
            
            # Calcular distribución de desempeños
            desempenos = {'Superior': 0, 'Alto': 0, 'Básico': 0, 'Bajo': 0, 'Sin calificar': 0}
            for asignatura in asignaturas_data:
                if asignatura['tiene_nota'] and asignatura['desempeno'] in desempenos:
                    desempenos[asignatura['desempeno']] += 1
                else:
                    desempenos['Sin calificar'] += 1

            texto_resumen = (
                f"<b>RESUMEN ACADÉMICO - {periodo_nombre.upper()} PERIODO</b><br/><br/>"
                f"<b>Total de asignaturas:</b> {total_asignaturas}<br/>"
                f"<b>Asignaturas evaluadas:</b> {asignaturas_evaluadas}<br/>"
                f"<b>Promedio general:</b> <font color='{self._color_promedio(promedio)}'>{promedio:.2f}</font><br/>"
                f"<b>Estado académico:</b> {self._estado_academico(promedio)}<br/><br/>"
            )

            texto_resumen += (
                f"<b>Distribución por desempeño:</b><br/>"
                f"• Superior: {desempenos['Superior']} asignatura(s)<br/>"
                f"• Alto: {desempenos['Alto']} asignatura(s)<br/>"
                f"• Básico: {desempenos['Básico']} asignatura(s)<br/>"
                f"• Bajo: {desempenos['Bajo']} asignatura(s)<br/>"
                f"• Sin calificar: {desempenos['Sin calificar']} asignatura(s)"
            )

            bloque = Table([[Paragraph(texto_resumen, styles["TextoNormal"])]], colWidths=[14 * cm])
            bloque.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("LEFTPADDING", (0, 0), (-1, -1), 15),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LINEBEFORE", (0, 0), (-1, -1), 3, colors.black)
            ]))
            return [bloque, Spacer(1, 20)]

        except Exception as e:
            print(f"Error en resumen académico: {e}")
            texto_resumen = "<b>RESUMEN ACADÉMICO</b><br/><br/>No se pudieron cargar los datos académicos."
            bloque = Table([[Paragraph(texto_resumen, styles["TextoNormal"])]], colWidths=[14 * cm])
            bloque.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("LEFTPADDING", (0, 0), (-1, -1), 15),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LINEBEFORE", (0, 0), (-1, -1), 3, colors.black)
            ]))
            return [bloque, Spacer(1, 20)]

    def _crear_tabla_notas(self, datos_asignaturas, styles):
        """Tabla detallada de notas por asignatura"""
        try:
            asignaturas_data = datos_asignaturas['asignaturas']
            
            if not asignaturas_data:
                return [Paragraph("No hay asignaturas registradas para este período.", styles["TextoNormal"]), 
                        Spacer(1, 20)]

            # Encabezado de la tabla
            encabezados = [
                Paragraph("ASIGNATURA", styles["TablaEncabezado"]),
                Paragraph("AREA", styles["TablaEncabezado"]),
                Paragraph("DOCENTE", styles["TablaEncabezado"]),
                Paragraph("NOTA", styles["TablaEncabezado"]),
                Paragraph("DESEMPEÑO", styles["TablaEncabezado"])
            ]

            datos_tabla = [encabezados]

            # Llenar datos de la tabla
            for asignatura in asignaturas_data:
                # Información de la asignatura
                asignatura_nombre = asignatura['nombre']
                asignatura_cell = Paragraph(asignatura_nombre, styles["TablaAsignatura"])
                
                # Información del área
                area_cell = Paragraph(asignatura['area'], styles["TablaContenido"])
                
                # Información del docente
                docente_cell = Paragraph(asignatura['docente'], styles["TablaContenido"])
                
                # Nota y desempeño
                if asignatura['tiene_nota'] and asignatura['calificacion'] is not None:
                    nota_texto = Paragraph(f"{asignatura['calificacion']:.1f}", styles["TablaContenido"])
                    desempeno_texto = Paragraph(asignatura['desempeno'], styles["TablaDesempeno"])
                else:
                    nota_texto = Paragraph("N/A", styles["TablaContenido"])
                    desempeno_texto = Paragraph("Sin evaluar", styles["TablaDesempeno"])
                
                datos_tabla.append([asignatura_cell, area_cell, docente_cell, nota_texto, desempeno_texto])

            # Crear tabla
            tabla = Table(datos_tabla, colWidths=[5 * cm, 3 * cm, 4 * cm, 2 * cm, 3 * cm])
            tabla.setStyle(TableStyle([
                # Estilo del encabezado
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0A4BA0")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Estilo del contenido
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (2, -1), 'LEFT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#DDDDDD")),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ]))

            return [Paragraph("DETALLE DE CALIFICACIONES:", styles["TituloDocumento"]), 
                    Spacer(1, 10), tabla, Spacer(1, 20)]

        except Exception as e:
            print(f"Error creando tabla de notas: {e}")
            return [Paragraph("Error al cargar las calificaciones.", styles["TextoNormal"]), 
                    Spacer(1, 20)]

    def _crear_tabla_notas_final(self, datos_periodo, periodo, styles):
        """Tabla de notas para boletín final (4to período)"""
        try:
            asignaturas_data = datos_periodo['asignaturas']
            
            if not asignaturas_data:
                return [Paragraph(f"No hay calificaciones para el período {periodo.periodo.nombre}.", styles["TextoNormal"]), 
                        Spacer(1, 20)]

            # Encabezado de la tabla
            encabezados = [
                Paragraph("ASIGNATURA", styles["TablaEncabezado"]),
                Paragraph("AREA", styles["TablaEncabezado"]),
                Paragraph("NOTA", styles["TablaEncabezado"]),
                Paragraph("DESEMPEÑO", styles["TablaEncabezado"])
            ]

            datos_tabla = [encabezados]

            # Llenar datos de la tabla
            for asignatura in asignaturas_data:
                # Información de la asignatura
                asignatura_nombre = asignatura['nombre']
                asignatura_cell = Paragraph(asignatura_nombre, styles["TablaAsignatura"])
                
                # Información del área
                area_cell = Paragraph(asignatura['area'], styles["TablaContenido"])
                
                # Nota y desempeño
                if asignatura['tiene_nota'] and asignatura['calificacion'] is not None:
                    nota_texto = Paragraph(f"{asignatura['calificacion']:.1f}", styles["TablaContenido"])
                    desempeno_texto = Paragraph(asignatura['desempeno'], styles["TablaDesempeno"])
                else:
                    nota_texto = Paragraph("N/A", styles["TablaContenido"])
                    desempeno_texto = Paragraph("Sin evaluar", styles["TablaDesempeno"])
                
                datos_tabla.append([asignatura_cell, area_cell, nota_texto, desempeno_texto])

            # Crear tabla
            tabla = Table(datos_tabla, colWidths=[6 * cm, 4 * cm, 2.5 * cm, 3.5 * cm])
            tabla.setStyle(TableStyle([
                # Estilo del encabezado
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0A4BA0")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Estilo del contenido
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#DDDDDD")),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ]))

            return [Paragraph(f"CALIFICACIONES - {periodo.periodo.nombre.upper()} PERÍODO:", styles["TituloDocumento"]), 
                    Spacer(1, 10), tabla, Spacer(1, 20)]

        except Exception as e:
            print(f"Error creando tabla de notas final: {e}")
            return [Spacer(1, 20)]

    def _crear_analisis_rendimiento(self, datos_asignaturas, styles):
        """Análisis del rendimiento académico"""
        try:
            asignaturas_data = datos_asignaturas['asignaturas']
            
            if not asignaturas_data:
                return [Spacer(1, 20)]

            # Calcular estadísticas avanzadas
            calificaciones = [a['calificacion'] for a in asignaturas_data if a['tiene_nota'] and a['calificacion'] is not None]
            if not calificaciones:
                return [Spacer(1, 20)]

            promedio = datos_asignaturas['promedio']
            max_nota = max(calificaciones)
            min_nota = min(calificaciones)
            
            # Determinar fortalezas y áreas de mejora
            fortalezas = [a for a in asignaturas_data if a['calificacion'] and a['calificacion'] >= 4.5]
            mejoras = [a for a in asignaturas_data if a['calificacion'] and a['calificacion'] < 3.5]

            texto_analisis = (
                f"<b>ANÁLISIS DE RENDIMIENTO</b><br/><br/>"
                f"<b>Nota más alta:</b> {max_nota:.1f}<br/>"
                f"<b>Nota más baja:</b> {min_nota:.1f}<br/>"
                f"<b>Rango de calificaciones:</b> {min_nota:.1f} - {max_nota:.1f}<br/><br/>"
            )

            if fortalezas:
                fortalezas_nombres = ", ".join([a['nombre'] for a in fortalezas[:3]])
                texto_analisis += f"<b>Fortalezas académicas:</b> {len(fortalezas)} asignatura(s) con desempeño superior"
                if fortalezas_nombres:
                    texto_analisis += f" ({fortalezas_nombres})"
                texto_analisis += "<br/>"
            
            if mejoras:
                mejoras_nombres = ", ".join([a['nombre'] for a in mejoras[:3]])
                texto_analisis += f"<b>Áreas de mejora:</b> {len(mejoras)} asignatura(s) requieren atención"
                if mejoras_nombres:
                    texto_analisis += f" ({mejoras_nombres})"
                texto_analisis += "<br/>"

            # Recomendación general
            if promedio >= 4.5:
                recomendacion = "Excelente rendimiento académico. Continúa con el mismo esfuerzo y dedicación."
            elif promedio >= 4.0:
                recomendacion = "Buen rendimiento académico. Mantén tu compromiso con los estudios."
            elif promedio >= 3.5:
                recomendacion = "Rendimiento aceptable. Identifica áreas de oportunidad para mejorar."
            else:
                recomendacion = "Se requiere mayor esfuerzo académico. Solicita apoyo a tus docentes."

            texto_analisis += f"<br/><b>Recomendación:</b> {recomendacion}"

            bloque = Table([[Paragraph(texto_analisis, styles["AnalisisTexto"])]], colWidths=[14 * cm])
            bloque.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F8FF")),
                ("LEFTPADDING", (0, 0), (-1, -1), 15),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0A4BA0")),
            ]))

            return [bloque, Spacer(1, 20)]

        except Exception as e:
            print(f"Error en análisis de rendimiento: {e}")
            return [Spacer(1, 20)]

    def _crear_resumen_final(self, datos_completos, año_lectivo, styles):
        """Resumen final para boletín"""
        try:
            promedios_periodos = datos_completos['promedios_periodos']
            promedio_final = datos_completos['promedio_final']
            
            texto_resumen = (
                f"<b>RESUMEN FINAL - AÑO LECTIVO {año_lectivo.anho}</b><br/><br/>"
                f"<b>Promedio final del año:</b> <font color='{self._color_promedio(promedio_final)}'>{promedio_final:.2f}</font><br/>"
                f"<b>Desempeño general:</b> {self._estado_academico(promedio_final)}<br/><br/>"
            )
            
            if promedios_periodos:
                texto_resumen += "<b>Evolución por períodos:</b><br/>"
                for periodo, promedio in promedios_periodos.items():
                    texto_resumen += f"• {periodo}: {promedio:.2f}<br/>"
            
            # Determinar aprobación
            aprobado = promedio_final >= 3.5  # Suponiendo 3.5 como mínimo para aprobar
            estado = "APROBADO" if aprobado else "NO APROBADO"
            color_estado = "#28a745" if aprobado else "#dc3545"
            
            texto_resumen += f"<br/><b>Estado final:</b> <font color='{color_estado}'>{estado}</font>"
            
            bloque = Table([[Paragraph(texto_resumen, styles["TextoNormal"])]], colWidths=[14 * cm])
            bloque.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("LEFTPADDING", (0, 0), (-1, -1), 15),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LINEBEFORE", (0, 0), (-1, -1), 3, colors.black)
            ]))
            return [bloque, Spacer(1, 20)]

        except Exception as e:
            print(f"Error en resumen final: {e}")
            return [Spacer(1, 20)]

    def _crear_analisis_final(self, datos_completos, styles):
        """Análisis final para boletín"""
        try:
            promedios_periodos = datos_completos['promedios_periodos']
            promedio_final = datos_completos['promedio_final']
            
            if not promedios_periodos:
                return [Spacer(1, 20)]
            
            # Calcular tendencia
            valores = list(promedios_periodos.values())
            if len(valores) >= 2:
                tendencia = "Mejorando" if valores[-1] > valores[0] else "Estable" if valores[-1] == valores[0] else "Bajando"
            else:
                tendencia = "Estable"
            
            texto_analisis = (
                f"<b>ANÁLISIS FINAL DEL AÑO</b><br/><br/>"
                f"<b>Tendencia académica:</b> {tendencia}<br/>"
            )
            
            if len(valores) >= 2:
                variacion = ((valores[-1] - valores[0]) / valores[0]) * 100 if valores[0] > 0 else 0
                texto_analisis += f"<b>Variación del año:</b> {variacion:+.1f}%<br/>"
            
            # Recomendación final
            if promedio_final >= 4.5:
                recomendacion = "EXCELENTE DESEMPEÑO. El estudiante ha demostrado un rendimiento sobresaliente durante todo el año académico."
            elif promedio_final >= 4.0:
                recomendacion = "BUEN DESEMPEÑO. El estudiante muestra un rendimiento consistente y compromiso con sus estudios."
            elif promedio_final >= 3.5:
                recomendacion = "DESEMPEÑO ACEPTABLE. Se observa progreso durante el año, se recomienda mantener el esfuerzo."
            elif promedio_final >= 3.0:
                recomendacion = "DESEMPEÑO BÁSICO. Se requiere mayor dedicación y seguimiento para mejorar el rendimiento."
            else:
                recomendacion = "DESEMPEÑO BAJO. Se recomienda plan de mejoramiento y seguimiento especializado para el próximo año."
            
            texto_analisis += f"<br/><b>Recomendación final:</b> {recomendacion}"

            bloque = Table([[Paragraph(texto_analisis, styles["AnalisisTexto"])]], colWidths=[14 * cm])
            bloque.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F8FF")),
                ("LEFTPADDING", (0, 0), (-1, -1), 15),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0A4BA0")),
            ]))

            return [bloque, Spacer(1, 20)]

        except Exception as e:
            print(f"Error en análisis final: {e}")
            return [Spacer(1, 20)]

    # -------------------- FIRMAS Y PIES DE PÁGINA --------------------
    def _crear_firma_y_sello(self, estudiante, periodo, styles):
        """Firma y sello para reporte normal"""
        fecha = self._formatear_fecha_espanol()

        # Sello
        periodo_nombre = periodo.periodo.nombre if periodo else "Actual"
        sello_text = (
            f"Reporte generado electrónicamente<br/>{fecha}<br/>"
            f"Código: {estudiante.usuario.numero_documento}-NOT-{periodo_nombre}"
        )
        sello = Table([[Paragraph(sello_text, styles["Sello"])]], colWidths=[5 * cm])
        sello.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0A4BA0")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F8FF")),
            ("PADDING", (0, 0), (-1, -1), 8)
        ]))

        # Firma
        firma = Table([
            [Paragraph("María Mederis Madero Garrido", styles["FirmaNombre"])],
            [Paragraph("Directora - Colegio Cristiano El Shadai", styles["FirmaCargo"])]
        ], colWidths=[8 * cm])

        # Combinar en una fila
        fila = Table([[sello, firma]], colWidths=[7 * cm, 8 * cm])
        fila.setStyle(TableStyle([
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP")
        ]))
        return [Spacer(1, 30), fila, Spacer(1, 20)]

    def _crear_firma_y_sello_final(self, estudiante, año_lectivo, styles):
        """Firma y sello para boletín final"""
        fecha = self._formatear_fecha_espanol()

        # Sello
        año_lectivo_str = año_lectivo.anho if año_lectivo else "General"
        sello_text = (
            f"Boletín final generado electrónicamente<br/>{fecha}<br/>"
            f"Código: {estudiante.usuario.numero_documento}-BOL-{año_lectivo_str}"
        )
        sello = Table([[Paragraph(sello_text, styles["Sello"])]], colWidths=[5 * cm])
        sello.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0A4BA0")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F8FF")),
            ("PADDING", (0, 0), (-1, -1), 8)
        ]))

        # Firma
        firma = Table([
            [Paragraph("María Mederis Madero Garrido", styles["FirmaNombre"])],
            [Paragraph("Directora - Colegio Cristiano El Shadai", styles["FirmaCargo"])]
        ], colWidths=[8 * cm])

        # Combinar en una fila
        fila = Table([[sello, firma]], colWidths=[7 * cm, 8 * cm])
        fila.setStyle(TableStyle([
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP")
        ]))
        return [Spacer(1, 30), fila, Spacer(1, 20)]

    def _crear_pie_pagina(self, colegio, estudiante, periodo, styles):
        """Pie de página para reporte normal"""
        try:
            direccion = colegio.direccion if colegio.direccion else "Dirección no especificada"
            
            try:
                recursos = self._obtener_o_crear_recursos(colegio)
                telefono = recursos.telefono or ""
                celular = getattr(recursos, "celular", "") or ""
                email = recursos.email or ""
                web = recursos.sitio_web or ""
            except Exception as e:
                telefono = celular = email = web = ""

            periodo_nombre = periodo.periodo.nombre if periodo else "Actual"
            lineas = [
                "<b>COLEGIO CRISTIANO EL SHADAI</b>",
                f"{direccion}" + (f" | Tel: {telefono}" if telefono else "") + (f" | Cel: {celular}" if celular else ""),
                (f"Email: {email}" if email else "") + (f" | Web: {web}" if web else ""),
                f"Reporte de: {estudiante.usuario.nombres} {estudiante.usuario.apellidos} | Período: {periodo_nombre} | Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}"
            ]
            
            lineas = [linea for linea in lineas if linea.strip()]
            texto = "<br/>".join(lineas)

            linea = Table([[""]], colWidths=[15 * cm])
            linea.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 1, colors.HexColor('#888'))]))

            return [Spacer(1, 40), linea, Spacer(1, 8), Paragraph(texto, styles["PiePagina"])]

        except Exception as e:
            print(f"Error en pie de página: {e}")
            return [Spacer(1, 40)]

    def _crear_pie_pagina_final(self, colegio, estudiante, año_lectivo, styles):
        """Pie de página para boletín final"""
        try:
            direccion = colegio.direccion if colegio.direccion else "Dirección no especificada"
            
            try:
                recursos = self._obtener_o_crear_recursos(colegio)
                telefono = recursos.telefono or ""
                celular = getattr(recursos, "celular", "") or ""
                email = recursos.email or ""
                web = recursos.sitio_web or ""
            except Exception as e:
                telefono = celular = email = web = ""

            año_lectivo_str = año_lectivo.anho if año_lectivo else "General"
            lineas = [
                "<b>COLEGIO CRISTIANO EL SHADAI</b>",
                f"{direccion}" + (f" | Tel: {telefono}" if telefono else "") + (f" | Cel: {celular}" if celular else ""),
                (f"Email: {email}" if email else "") + (f" | Web: {web}" if web else ""),
                f"Boletín final de: {estudiante.usuario.nombres} {estudiante.usuario.apellidos} | Año: {año_lectivo_str} | Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}"
            ]
            
            lineas = [linea for linea in lineas if linea.strip()]
            texto = "<br/>".join(lineas)

            linea = Table([[""]], colWidths=[15 * cm])
            linea.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 1, colors.HexColor('#888'))]))

            return [Spacer(1, 40), linea, Spacer(1, 8), Paragraph(texto, styles["PiePagina"])]

        except Exception as e:
            print(f"Error en pie de página: {e}")
            return [Spacer(1, 40)]

    # -------------------- MÉTODOS AUXILIARES --------------------
    def _determinar_desempeno(self, calificacion):
        """Determina el desempeño basado en la calificación"""
        if calificacion >= 4.5:
            return "Superior"
        elif calificacion >= 4.0:
            return "Alto"
        elif calificacion >= 3.5:
            return "Básico"
        else:
            return "Bajo"

    def _color_promedio(self, promedio):
        """Devuelve el color según el promedio"""
        if promedio >= 4.5:
            return "#28a745"
        elif promedio >= 4.0:
            return "#17a2b8"
        elif promedio >= 3.5:
            return "#ffc107"
        else:
            return "#dc3545"

    def _estado_academico(self, promedio):
        """Determina el estado académico"""
        if promedio >= 4.5:
            return "Excelente"
        elif promedio >= 4.0:
            return "Bueno"
        elif promedio >= 3.5:
            return "Aceptable"
        else:
            return "Requiere mejora"

    def _formatear_fecha_espanol(self):
        meses = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
        ]
        now = timezone.now()
        return f"{now.day} de {meses[now.month - 1]} de {now.year}"
    
# =============================================
# VISTAS DE HORARIO Y ASIGNATURAS
# =============================================

class MiHorarioView(RoleRequiredMixin, TemplateView, PeriodoActualMixin):
    """Vista del horario del estudiante"""
    template_name = 'estudiantes/mi_horario.html'
    allowed_roles = ['Estudiante']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Verificar si el usuario tiene perfil de estudiante
            try:
                estudiante = Estudiante.objects.get(usuario=self.request.user)
            except Estudiante.DoesNotExist:
                messages.error(self.request, "No tienes un perfil de estudiante asociado")
                context['error'] = "No tienes un perfil de estudiante asociado"
                return context
            
            # Obtener matrícula actual
            matricula_actual = estudiante.matricula_actual
            if not matricula_actual:
                messages.warning(self.request, "No tienes una matrícula activa")
                context['error'] = "No tienes una matrícula activa"
                return context
            
            # Obtener el grado_año_lectivo de la matrícula
            grado_año_lectivo = matricula_actual.grado_año_lectivo
            
            # Obtener todas las asignaturas del grado del estudiante
            asignaturas_grado = AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo=grado_año_lectivo,
                sede=matricula_actual.sede
            ).select_related(
                'asignatura',
                'asignatura__area',
                'docente__usuario'
            )
            
            # Obtener horarios para estas asignaturas
            horarios = HorarioClase.objects.filter(
                asignatura_grado__in=asignaturas_grado
            ).select_related(
                'asignatura_grado__asignatura',
                'asignatura_grado__asignatura__area',
                'asignatura_grado__docente__usuario'
            ).order_by('dia_semana', 'hora_inicio')
            
            # Organizar horarios por día de la semana
            dias_semana = {
                'LUN': {'nombre': 'Lunes', 'horarios': []},
                'MAR': {'nombre': 'Martes', 'horarios': []},
                'MIE': {'nombre': 'Miércoles', 'horarios': []},
                'JUE': {'nombre': 'Jueves', 'horarios': []},
                'VIE': {'nombre': 'Viernes', 'horarios': []},
            }
            
            for horario in horarios:
                dia = horario.dia_semana
                if dia in dias_semana:
                    # Calcular duración
                    duracion = self.calcular_duracion(horario.hora_inicio, horario.hora_fin)
                    
                    horario_data = {
                        'id': horario.id,
                        'asignatura': horario.asignatura_grado.asignatura.nombre,
                        'asignatura_obj': horario.asignatura_grado.asignatura,
                        'area': horario.asignatura_grado.asignatura.area.nombre if horario.asignatura_grado.asignatura.area else None,
                        'area_color': self.get_color_for_area(horario.asignatura_grado.asignatura.area.nombre if horario.asignatura_grado.asignatura.area else None),
                        'docente': horario.asignatura_grado.docente.usuario.get_full_name() if horario.asignatura_grado.docente else "Por asignar",
                        'docente_email': horario.asignatura_grado.docente.usuario.email if horario.asignatura_grado.docente else None,
                        'hora_inicio': horario.hora_inicio,
                        'hora_fin': horario.hora_fin,
                        'salon': horario.salon or "Por asignar",
                        'duracion': duracion,
                        'hora_inicio_str': horario.hora_inicio.strftime('%I:%M %p'),
                        'hora_fin_str': horario.hora_fin.strftime('%I:%M %p'),
                    }
                    dias_semana[dia]['horarios'].append(horario_data)
            
            # Calcular estadísticas
            horas_por_asignatura = {}
            for horario in horarios:
                asignatura_nombre = horario.asignatura_grado.asignatura.nombre
                duracion = self.calcular_duracion(horario.hora_inicio, horario.hora_fin)
                
                if asignatura_nombre in horas_por_asignatura:
                    horas_por_asignatura[asignatura_nombre] += duracion
                else:
                    horas_por_asignatura[asignatura_nombre] = duracion
            
            # Determinar día actual
            hoy = timezone.now()
            dias_espanol = {
                0: 'LUN',  # Lunes
                1: 'MAR',  # Martes
                2: 'MIE',  # Miércoles
                3: 'JUE',  # Jueves
                4: 'VIE',  # Viernes
            }
            dia_actual = dias_espanol.get(hoy.weekday())
            
            # Total de horas semanales
            total_horas = sum(horas_por_asignatura.values()) if horas_por_asignatura else 0
            
            context.update({
                'estudiante': estudiante,
                'matricula': matricula_actual,
                'grado': grado_año_lectivo.grado,
                'sede': matricula_actual.sede,
                'dias_semana': dias_semana,
                'horarios_total': horarios,
                'horas_por_asignatura': horas_por_asignatura,
                'dia_actual': dia_actual,
                'hoy': hoy,
                'total_horas_semanales': round(total_horas, 1),
                'total_clases': len(horarios),
                'total_asignaturas': len(horas_por_asignatura),
            })
            
        except Exception as e:
            messages.error(self.request, f"Error al cargar el horario: {str(e)}")
            print(f"Error en MiHorarioView: {e}")
            context['error'] = str(e)
        
        return context
    
    def calcular_duracion(self, hora_inicio, hora_fin):
        """Calcula la duración en horas entre dos horas"""
        try:
            inicio = hora_inicio.hour * 60 + hora_inicio.minute
            fin = hora_fin.hour * 60 + hora_fin.minute
            duracion_minutos = fin - inicio
            return duracion_minutos / 60.0  # Convertir a horas
        except:
            return 1.0  # Valor por defecto
    
    def get_color_for_area(self, area_nombre):
        """Asigna un color único a cada área"""
        colors = {
            'Matemáticas': '#667eea',
            'Ciencias': '#764ba2',
            'Lenguaje': '#4facfe',
            'Sociales': '#00f2fe',
            'Inglés': '#43e97b',
            'Artes': '#38f9d7',
            'Educación Física': '#fa709a',
            'Tecnología': '#fee140',
            'Ética': '#f093fb',
            'Religión': '#667eea',
        }
        return colors.get(area_nombre, '#6c757d')


class MisAsignaturasView(RoleRequiredMixin, TemplateView, PeriodoActualMixin):
    """Vista de asignaturas del estudiante"""
    template_name = 'estudiantes/mis_asignaturas.html'
    allowed_roles = ['Estudiante']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Verificar si el usuario tiene perfil de estudiante
            try:
                estudiante = Estudiante.objects.get(usuario=self.request.user)
            except Estudiante.DoesNotExist:
                messages.error(self.request, "No tienes un perfil de estudiante asociado")
                context['error'] = "No tienes un perfil de estudiante asociado"
                return context
            
            # Obtener matrícula actual
            matricula_actual = estudiante.matricula_actual
            if not matricula_actual:
                messages.warning(self.request, "No tienes una matrícula activa")
                context['error'] = "No tienes una matrícula activa"
                return context
            
            # Obtener el grado_año_lectivo
            grado_año_lectivo = matricula_actual.grado_año_lectivo
            
            # Obtener asignaturas del grado
            asignaturas_grado = AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo=grado_año_lectivo,
                sede=matricula_actual.sede
            ).select_related(
                'asignatura',
                'asignatura__area',
                'docente__usuario'
            ).order_by('asignatura__nombre')
            
            # Obtener horarios para calcular intensidad horaria
            asignaturas_detalle = []
            total_horas_semanales = 0
            
            for asignatura_grado in asignaturas_grado:
                # Obtener horarios de esta asignatura
                horarios = HorarioClase.objects.filter(
                    asignatura_grado=asignatura_grado
                )
                
                # Calcular horas semanales
                horas_semanales = 0
                for horario in horarios:
                    duracion = self.calcular_duracion(horario.hora_inicio, horario.hora_fin)
                    horas_semanales += duracion
                
                total_horas_semanales += horas_semanales
                
                # Obtener intensidad horaria de la asignatura
                intensidad_horaria = asignatura_grado.asignatura.ih if asignatura_grado.asignatura.ih else None
                
                # Obtener notas del estudiante
                notas = estudiante.notas.filter(
                    asignatura_grado_año_lectivo=asignatura_grado
                ).select_related('periodo_academico')
                
                # Calcular promedio
                promedio = None
                if notas.exists():
                    calificaciones = [float(n.calificacion) for n in notas if n.calificacion is not None]
                    if calificaciones:
                        promedio = sum(calificaciones) / len(calificaciones)
                
                asignaturas_detalle.append({
                    'asignatura': asignatura_grado.asignatura,
                    'asignatura_grado': asignatura_grado,
                    'docente': asignatura_grado.docente,
                    'horas_semanales': round(horas_semanales, 1),
                    'intensidad_horaria': intensidad_horaria,
                    'area': asignatura_grado.asignatura.area,
                    'area_color': self.get_color_for_area(asignatura_grado.asignatura.area.nombre if asignatura_grado.asignatura.area else None),
                    'notas': notas,
                    'promedio': round(promedio, 1) if promedio else None,
                    'tiene_nota': promedio is not None,
                })
            
            # Agrupar por área
            asignaturas_por_area = {}
            for asignatura in asignaturas_detalle:
                area_nombre = asignatura['area'].nombre if asignatura['area'] else "Sin área"
                if area_nombre not in asignaturas_por_area:
                    asignaturas_por_area[area_nombre] = {
                        'asignaturas': [],
                        'total_horas': 0,
                        'color': self.get_color_for_area(area_nombre),
                    }
                asignaturas_por_area[area_nombre]['asignaturas'].append(asignatura)
                asignaturas_por_area[area_nombre]['total_horas'] += asignatura['horas_semanales']
            
            # Calcular promedio general
            promedios_validos = [a['promedio'] for a in asignaturas_detalle if a['promedio'] is not None]
            promedio_general = sum(promedios_validos) / len(promedios_validos) if promedios_validos else None
            
            context.update({
                'estudiante': estudiante,
                'matricula': matricula_actual,
                'grado': grado_año_lectivo.grado,
                'sede': matricula_actual.sede,
                'asignaturas': asignaturas_detalle,
                'asignaturas_por_area': asignaturas_por_area,
                'total_asignaturas': len(asignaturas_detalle),
                'total_horas_semanales': round(total_horas_semanales, 1),
                'promedio_general': round(promedio_general, 1) if promedio_general else None,
            })
            
        except Exception as e:
            messages.error(self.request, f"Error al cargar asignaturas: {str(e)}")
            print(f"Error en MisAsignaturasView: {e}")
            context['error'] = str(e)
        
        return context
    
    def calcular_duracion(self, hora_inicio, hora_fin):
        """Calcula la duración en horas entre dos horas"""
        try:
            inicio = hora_inicio.hour * 60 + hora_inicio.minute
            fin = hora_fin.hour * 60 + hora_fin.minute
            duracion_minutos = fin - inicio
            return duracion_minutos / 60.0
        except:
            return 1.0
    
    def get_color_for_area(self, area_nombre):
        """Asigna un color único a cada área"""
        colors = {
            'Matemáticas': '#667eea',
            'Ciencias': '#764ba2',
            'Lenguaje': '#4facfe',
            'Sociales': '#00f2fe',
            'Inglés': '#43e97b',
            'Artes': '#38f9d7',
            'Educación Física': '#fa709a',
            'Tecnología': '#fee140',
            'Ética': '#f093fb',
            'Religión': '#667eea',
        }
        return colors.get(area_nombre, '#6c757d')
    
class CuentaInactivaView(BaseEstudianteView):
    template_name = 'estudiantes/cuenta_inactiva.html'