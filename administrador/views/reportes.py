"""
Módulo de Reportes - Administrador
"""
import csv
import xlwt
from datetime import datetime, date, timedelta
from django.db.models import Q, Count, Avg, Max, Min, Sum, F, FloatField, Case, When
from django.db.models.functions import TruncMonth, TruncYear, Cast
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.generic import View, TemplateView
from django.core.exceptions import PermissionDenied
from collections import defaultdict
import json
from django.db.models.functions import ExtractMonth, ExtractDay, ExtractYear
from django.db.models import ExpressionWrapper, Value

from gestioncolegio.mixins import RoleRequiredMixin
from usuarios.models import Usuario, Docente
from estudiantes.models import Estudiante, Matricula, Nota, Acudiente
from academico.models import Grado, Asignatura, Periodo, Logro, Area, NivelEscolar
from comportamiento.models import Comportamiento, Asistencia, Inconsistencia
from gestioncolegio.models import Sede, AñoLectivo, ConfiguracionGeneral, Colegio
from matricula.models import PeriodoAcademico, AsignaturaGradoAñoLectivo, GradoAñoLectivo

# ========== VISTAS PRINCIPALES DE REPORTES ==========

class DashboardReportesView(RoleRequiredMixin, TemplateView):
    """Dashboard principal de reportes"""
    template_name = 'administrador/reportes/dashboard.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener año lectivo actual
        try:
            config = ConfiguracionGeneral.objects.first()
            año_actual = config.año_lectivo_actual if config else None
        except:
            año_actual = None
        
        años_lectivos = AñoLectivo.objects.filter(estado=True).order_by('-anho')
        
        # Estadísticas rápidas
        total_estudiantes = Estudiante.objects.filter(estado=True).count()
        total_docentes = Docente.objects.filter(estado=True).count()
        
        # Estudiantes activos en año actual
        estudiantes_activos = 0
        if año_actual:
            estudiantes_activos = Matricula.objects.filter(
                año_lectivo=año_actual,
                estado='ACT'
            ).count()
        
        # Notas recientes
        notas_recientes = Nota.objects.select_related(
            'estudiante__usuario',
            'asignatura_grado_año_lectivo__asignatura'
        ).order_by('-created_at')[:5]
        
        # Comportamientos recientes
        comportamientos_recientes = Comportamiento.objects.select_related(
            'estudiante__usuario',
            'docente__usuario'
        ).order_by('-created_at')[:5]
        
        context.update({
            'año_actual': año_actual,
            'años_lectivos': años_lectivos,
            'sedes': Sede.objects.filter(estado=True),
            'grados': Grado.objects.all(),
            'total_estudiantes': total_estudiantes,
            'total_docentes': total_docentes,
            'estudiantes_activos': estudiantes_activos,
            'notas_recientes': notas_recientes,
            'comportamientos_recientes': comportamientos_recientes,
        })
        
        return context

import json
from datetime import datetime
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from gestioncolegio.mixins import RoleRequiredMixin
from usuarios.models import Usuario
from estudiantes.models import Estudiante, Matricula
from gestioncolegio.models import Sede, AñoLectivo
from academico.models import Grado

class ReporteEstudiantesView(RoleRequiredMixin, TemplateView):
    """Reporte de estudiantes con filtros avanzados"""
    template_name = 'administrador/reportes/estudiantes.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Parámetros de filtro
        sede_id = self.request.GET.get('sede')
        grado_id = self.request.GET.get('grado')
        año_lectivo_id = self.request.GET.get('año_lectivo')
        estado = self.request.GET.get('estado')
        edad_min = self.request.GET.get('edad_min')
        edad_max = self.request.GET.get('edad_max')
        genero = self.request.GET.get('genero')
        
        # Obtener el año lectivo si se especificó
        año_lectivo_obj = None
        if año_lectivo_id:
            try:
                año_lectivo_obj = AñoLectivo.objects.get(id=año_lectivo_id)
            except AñoLectivo.DoesNotExist:
                año_lectivo_obj = None
        
        # Base query
        estudiantes = Estudiante.objects.filter(estado=True).select_related(
            'usuario'
        ).prefetch_related('matriculas')
        
        # Aplicar filtros - IMPORTANTE: Usar distinct para evitar duplicados
        if sede_id:
            estudiantes = estudiantes.filter(matriculas__sede_id=sede_id).distinct()
        
        if grado_id:
            estudiantes = estudiantes.filter(matriculas__grado_año_lectivo__grado_id=grado_id).distinct()
        
        if año_lectivo_id:
            # Filtrar estudiantes que tuvieron matrícula en ese año específico
            estudiantes = estudiantes.filter(matriculas__año_lectivo_id=año_lectivo_id).distinct()
        
        if estado:
            # Si hay año lectivo, filtrar por estado en ese año específico
            if año_lectivo_id:
                estudiantes = estudiantes.filter(
                    matriculas__año_lectivo_id=año_lectivo_id,
                    matriculas__estado=estado
                ).distinct()
            else:
                estudiantes = estudiantes.filter(matriculas__estado=estado).distinct()
        
        if genero:
            estudiantes = estudiantes.filter(usuario__sexo=genero).distinct()
        
        # Convertir QuerySet a lista para poder filtrar por edad
        estudiantes_list = list(estudiantes)
        
        # Obtener datos de matrícula según el año filtrado
        estudiantes_con_datos = []
        for estudiante in estudiantes_list:
            # Determinar qué matrícula mostrar según el filtro
            matricula_a_mostrar = None
            
            if año_lectivo_obj:
                # Obtener la matrícula específica del año filtrado
                matricula_a_mostrar = estudiante.matriculas.filter(
                    año_lectivo=año_lectivo_obj
                ).select_related(
                    'sede',
                    'grado_año_lectivo__grado',
                    'año_lectivo'
                ).first()
            else:
                # Si no se filtró por año, mostrar matrícula actual
                matricula_a_mostrar = estudiante.matricula_actual
            
            # Calcular edad del estudiante
            edad = None
            if estudiante.usuario.fecha_nacimiento:
                from datetime import date
                today = date.today()
                born = estudiante.usuario.fecha_nacimiento
                edad = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            
            # Aplicar filtros de edad
            if edad_min and edad_min != '' and edad and edad < int(edad_min):
                continue
            if edad_max and edad_max != '' and edad and edad > int(edad_max):
                continue
            
            estudiantes_con_datos.append({
                'estudiante': estudiante,
                'matricula': matricula_a_mostrar,  # Cambiado de matricula_actual a matricula
                'edad': edad,
                'año_filtrado': año_lectivo_obj.anho if año_lectivo_obj else None
            })
        
        # Estadísticas
        total_estudiantes = len(estudiantes_con_datos)
        masculinos = len([e for e in estudiantes_con_datos if e['estudiante'].usuario.sexo == 'M'])
        femeninos = len([e for e in estudiantes_con_datos if e['estudiante'].usuario.sexo == 'F'])
        otros = total_estudiantes - (masculinos + femeninos)
        
        estadisticas = {
            'total': total_estudiantes,
            'masculinos': masculinos,
            'femeninos': femeninos,
            'otros': otros,
            'porcentaje_masculinos': (masculinos / total_estudiantes * 100) if total_estudiantes > 0 else 0,
            'porcentaje_femeninos': (femeninos / total_estudiantes * 100) if total_estudiantes > 0 else 0,
            'porcentaje_otros': (otros / total_estudiantes * 100) if total_estudiantes > 0 else 0,
        }
        
        # Distribución por grado (solo si hay filtro de año lectivo)
        distribucion_grado = []
        if año_lectivo_id:
            try:
                matriculas = Matricula.objects.filter(
                    año_lectivo_id=año_lectivo_id
                ).values(
                    'grado_año_lectivo__grado__nombre'
                ).annotate(
                    total=Count('id')
                ).order_by('grado_año_lectivo__grado__nombre')
                
                distribucion_grado = list(matriculas)
            except Exception as e:
                print(f"Error obteniendo distribución por grado: {e}")
        
        # PREPARAR DATOS PARA GRÁFICOS
        # (mantén tu código existente para gráficos aquí)
        
        # Contexto final
        context.update({
            'estudiantes_con_datos': estudiantes_con_datos,
            'estadisticas': estadisticas,
            'distribucion_grado': distribucion_grado,
            'sedes': Sede.objects.filter(estado=True),
            'grados': Grado.objects.all(),
            'años_lectivos': AñoLectivo.objects.all().order_by('-anho'),
            'filtros': {
                'sede': sede_id,
                'grado': grado_id,
                'año_lectivo': año_lectivo_id,
                'estado': estado,
                'edad_min': edad_min,
                'edad_max': edad_max,
                'genero': genero,
            },
            'año_lectivo_filtrado': año_lectivo_obj
        })
        
        return context

class ReporteNotasView(RoleRequiredMixin, TemplateView):
    """Reporte de notas individuales y grupales"""
    template_name = 'administrador/reportes/notas.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener parámetros
        periodo_id = self.request.GET.get('periodo')
        grado_id = self.request.GET.get('grado')
        asignatura_id = self.request.GET.get('asignatura')
        sede_id = self.request.GET.get('sede')
        estudiante_id = self.request.GET.get('estudiante')
        tipo_reporte = self.request.GET.get('tipo', 'grupal')
        
        context.update({
            'periodos': PeriodoAcademico.objects.filter(estado=True).select_related('periodo', 'año_lectivo'),
            'grados': Grado.objects.all(),
            'asignaturas': Asignatura.objects.all(),
            'sedes': Sede.objects.filter(estado=True),
            'estudiantes': Estudiante.objects.filter(estado=True).select_related('usuario'),
            'tipo_reporte': tipo_reporte,
            'filtros': {
                'periodo_id': periodo_id,
                'grado_id': grado_id,
                'asignatura_id': asignatura_id,
                'sede_id': sede_id,
                'estudiante_id': estudiante_id,
            }
        })
        
        # Cargar datos según el tipo de reporte
        if tipo_reporte == 'individual' and estudiante_id:
            estudiante = get_object_or_404(Estudiante, id=estudiante_id)
            notas = Nota.objects.filter(
                estudiante=estudiante
            ).select_related(
                'asignatura_grado_año_lectivo__asignatura',
                'periodo_academico__periodo',
                'periodo_academico__año_lectivo'
            )
            
            if periodo_id:
                notas = notas.filter(periodo_academico_id=periodo_id)
            
            # Calcular promedios por asignatura
            promedios_asignatura = {}
            for nota in notas:
                asignatura_nombre = nota.asignatura_grado_año_lectivo.asignatura.nombre
                if asignatura_nombre not in promedios_asignatura:
                    promedios_asignatura[asignatura_nombre] = {'suma': 0, 'count': 0}
                promedios_asignatura[asignatura_nombre]['suma'] += float(nota.calificacion)
                promedios_asignatura[asignatura_nombre]['count'] += 1
            
            # Convertir a formato final
            promedios = {}
            for asignatura, datos in promedios_asignatura.items():
                promedios[asignatura] = round(datos['suma'] / datos['count'], 2) if datos['count'] > 0 else 0
            
            context.update({
                'estudiante': estudiante,
                'notas_individuales': notas,
                'promedios': promedios,
                'promedio_general': round(sum(promedios.values()) / len(promedios), 2) if promedios else 0,
            })
        
        elif tipo_reporte == 'grupal':
            notas = Nota.objects.all().select_related(
                'estudiante__usuario',
                'asignatura_grado_año_lectivo__asignatura',
                'periodo_academico__periodo'
            )
            
            if periodo_id:
                notas = notas.filter(periodo_academico_id=periodo_id)
            
            if grado_id:
                notas = notas.filter(
                    asignatura_grado_año_lectivo__grado_año_lectivo__grado_id=grado_id
                )
            
            if asignatura_id:
                notas = notas.filter(
                    asignatura_grado_año_lectivo__asignatura_id=asignatura_id
                )
            
            if sede_id:
                notas = notas.filter(
                    asignatura_grado_año_lectivo__sede_id=sede_id
                )
            
            # Agrupar datos para tabla
            datos_grupales = []
            # Primero agrupar por estudiante
            estudiantes_notas = {}
            for nota in notas:
                estudiante_id = nota.estudiante.id
                if estudiante_id not in estudiantes_notas:
                    estudiantes_notas[estudiante_id] = {
                        'estudiante': nota.estudiante,
                        'notas': [],
                        'suma': 0,
                        'count': 0
                    }
                estudiantes_notas[estudiante_id]['notas'].append(nota)
                estudiantes_notas[estudiante_id]['suma'] += float(nota.calificacion)
                estudiantes_notas[estudiante_id]['count'] += 1
            
            # Preparar datos para template
            for estudiante_id, datos in estudiantes_notas.items():
                datos_grupales.append({
                    'estudiante': datos['estudiante'],
                    'notas': datos['notas'],
                    'promedio': round(datos['suma'] / datos['count'], 2) if datos['count'] > 0 else 0,
                    'cantidad_notas': datos['count']
                })
            
            # Estadísticas generales
            total_notas = notas.count()
            promedio_general = notas.aggregate(Avg('calificacion'))['calificacion__avg'] or 0
            
            context.update({
                'datos_grupales': datos_grupales,
                'estadisticas': {
                    'total_notas': total_notas,
                    'promedio_general': round(promedio_general, 2),
                    'max_nota': notas.aggregate(Max('calificacion'))['calificacion__max'] or 0,
                    'min_nota': notas.aggregate(Min('calificacion'))['calificacion__min'] or 0,
                    'total_estudiantes': len(estudiantes_notas),
                }
            })
        
        return context
    
    def post(self, request):
        """Exportar reporte de notas"""
        export_format = request.POST.get('export_format')
        tipo_reporte = request.POST.get('tipo_reporte')
        
        if tipo_reporte == 'individual':
            return self.exportar_boletin_individual(request, export_format)
        else:
            return self.exportar_notas_grupales(request, export_format)
    
    def exportar_boletin_individual(self, request, export_format):
        """Exportar boletín individual de notas"""
        estudiante_id = request.POST.get('estudiante_id')
        periodo_id = request.POST.get('periodo_id')
        
        estudiante = get_object_or_404(Estudiante, id=estudiante_id)
        notas = Nota.objects.filter(
            estudiante=estudiante
        ).select_related(
            'asignatura_grado_año_lectivo__asignatura',
            'periodo_academico__periodo'
        )
        
        if periodo_id:
            notas = notas.filter(periodo_academico_id=periodo_id)
        
        if export_format == 'pdf':
            return self.exportar_boletin_pdf(estudiante, notas)
        elif export_format == 'excel':
            return self.exportar_boletin_excel(estudiante, notas)
        
        return JsonResponse({'error': 'Formato no válido'}, status=400)
    
    def exportar_boletin_pdf(self, estudiante, notas):
        """Exportar boletín a PDF"""
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        
        response = HttpResponse(content_type='application/pdf')
        filename = f"boletin_{estudiante.usuario.apellidos}_{estudiante.usuario.nombres}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Crear documento
        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Título
        title = Paragraph(f"BOLETÍN DE NOTAS - {estudiante.usuario.get_full_name()}", styles['Title'])
        elements.append(title)
        
        # Información del estudiante
        info_text = f"""
        <b>Documento:</b> {estudiante.usuario.numero_documento}<br/>
        <b>Grado Actual:</b> {estudiante.grado_actual.grado.nombre if estudiante.grado_actual else 'No asignado'}<br/>
        <b>Fecha de Reporte:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}
        """
        info = Paragraph(info_text, styles['Normal'])
        elements.append(info)
        elements.append(Paragraph("<br/>", styles['Normal']))
        
        # Tabla de notas
        if notas.exists():
            # Preparar datos para la tabla
            table_data = [['Asignatura', 'Periodo', 'Calificación', 'Observaciones']]
            
            for nota in notas:
                table_data.append([
                    nota.asignatura_grado_año_lectivo.asignatura.nombre,
                    nota.periodo_academico.periodo.nombre,
                    str(nota.calificacion),
                    nota.observaciones[:30] if nota.observaciones else ''
                ])
            
            # Crear tabla
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            elements.append(table)
            
            # Calcular promedio
            promedio = notas.aggregate(Avg('calificacion'))['calificacion__avg'] or 0
            promedio_text = Paragraph(f"<br/><b>Promedio General:</b> {round(promedio, 2)}", styles['Normal'])
            elements.append(promedio_text)
        else:
            elements.append(Paragraph("<b>No hay notas registradas</b>", styles['Normal']))
        
        # Construir PDF
        doc.build(elements)
        return response

class ReporteAsistenciaView(RoleRequiredMixin, TemplateView):
    """Reporte de asistencia"""
    template_name = 'administrador/reportes/asistencia.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener parámetros
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        sede_id = self.request.GET.get('sede')
        grado_id = self.request.GET.get('grado')
        estudiante_id = self.request.GET.get('estudiante')
        
        # Convertir fechas
        if fecha_inicio:
            try:
                fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            except:
                fecha_inicio = None
        
        if fecha_fin:
            try:
                fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            except:
                fecha_fin = None
        
        # Base query
        asistencias = Asistencia.objects.all().select_related(
            'estudiante__usuario',
            'periodo_academico__año_lectivo'
        )
        
        # Aplicar filtros
        if fecha_inicio:
            asistencias = asistencias.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            asistencias = asistencias.filter(fecha__lte=fecha_fin)
        if sede_id:
            asistencias = asistencias.filter(
                estudiante__matriculas__sede_id=sede_id
            )
        if grado_id:
            asistencias = asistencias.filter(
                estudiante__matriculas__grado_año_lectivo__grado_id=grado_id
            )
        if estudiante_id:
            asistencias = asistencias.filter(estudiante_id=estudiante_id)
        
        # Calcular estadísticas
        total_registros = asistencias.count()
        asistencias_totales = asistencias.filter(estado='A').count()
        faltas_totales = asistencias.filter(estado='F').count()
        faltas_justificadas = asistencias.filter(estado='J').count()
        
        porcentaje_asistencia = (asistencias_totales / total_registros * 100) if total_registros > 0 else 0
        
        # Agrupar por estudiante para tabla resumen
        asistencias_por_estudiante = []
        if not estudiante_id:  # Solo si no se filtró por estudiante específico
            estudiantes_ids = asistencias.values_list('estudiante', flat=True).distinct()
            
            for est_id in estudiantes_ids:
                asist_est = asistencias.filter(estudiante_id=est_id)
                total_asist = asist_est.filter(estado='A').count()
                total_faltas = asist_est.filter(estado='F').count()
                total_justificadas = asist_est.filter(estado='J').count()
                total_reg = asist_est.count()
                
                porcentaje = (total_asist / total_reg * 100) if total_reg > 0 else 0
                
                estudiante_obj = asist_est.first().estudiante
                
                asistencias_por_estudiante.append({
                    'estudiante': estudiante_obj,
                    'total_asistencias': total_asist,
                    'total_faltas': total_faltas,
                    'total_justificadas': total_justificadas,
                    'porcentaje_asistencia': round(porcentaje, 2),
                    'total_registros': total_reg,
                })
        
        # Asistencias detalladas para tabla principal
        asistencias_detalladas = asistencias.order_by('-fecha')[:100]  # Limitar a 100 registros
        
        context.update({
            'asistencias_detalladas': asistencias_detalladas,
            'asistencias_por_estudiante': asistencias_por_estudiante,
            'estadisticas': {
                'total_registros': total_registros,
                'asistencias_totales': asistencias_totales,
                'faltas_totales': faltas_totales,
                'faltas_justificadas': faltas_justificadas,
                'porcentaje_asistencia': round(porcentaje_asistencia, 2),
            },
            'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d') if fecha_inicio else '',
            'fecha_fin': fecha_fin.strftime('%Y-%m-%d') if fecha_fin else '',
            'sedes': Sede.objects.filter(estado=True),
            'grados': Grado.objects.all(),
            'estudiantes': Estudiante.objects.filter(estado=True).select_related('usuario'),
            'filtros': {
                'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d') if fecha_inicio else '',
                'fecha_fin': fecha_fin.strftime('%Y-%m-%d') if fecha_fin else '',
                'sede_id': sede_id,
                'grado_id': grado_id,
                'estudiante_id': estudiante_id,
            }
        })
        
        return context

class ReporteComportamientoView(RoleRequiredMixin, TemplateView):
    """Reporte de comportamiento"""
    template_name = 'administrador/reportes/comportamiento.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener parámetros
        periodo_id = self.request.GET.get('periodo')
        tipo = self.request.GET.get('tipo')
        categoria = self.request.GET.get('categoria')
        docente_id = self.request.GET.get('docente')
        estudiante_id = self.request.GET.get('estudiante')
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        
        # Base query
        comportamientos = Comportamiento.objects.all().select_related(
            'estudiante__usuario',
            'periodo_academico__periodo',
            'docente__usuario'
        )
        
        # Aplicar filtros
        if periodo_id:
            comportamientos = comportamientos.filter(periodo_academico_id=periodo_id)
        if tipo:
            comportamientos = comportamientos.filter(tipo=tipo)
        if categoria:
            comportamientos = comportamientos.filter(categoria=categoria)
        if docente_id:
            comportamientos = comportamientos.filter(docente_id=docente_id)
        if estudiante_id:
            comportamientos = comportamientos.filter(estudiante_id=estudiante_id)
        if fecha_inicio:
            try:
                fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                comportamientos = comportamientos.filter(fecha__gte=fecha_inicio)
            except:
                pass
        if fecha_fin:
            try:
                fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                comportamientos = comportamientos.filter(fecha__lte=fecha_fin)
            except:
                pass
        
        # Estadísticas
        total_comportamientos = comportamientos.count()
        positivos = comportamientos.filter(tipo='Positivo').count()
        negativos = comportamientos.filter(tipo='Negativo').count()
        
        # Agrupar por categoría
        por_categoria = []
        for cat_val, cat_label in Comportamiento.CATEGORIAS:
            total_cat = comportamientos.filter(categoria=cat_val).count()
            positivos_cat = comportamientos.filter(categoria=cat_val, tipo='Positivo').count()
            negativos_cat = comportamientos.filter(categoria=cat_val, tipo='Negativo').count()
            
            por_categoria.append({
                'categoria': cat_label,
                'total': total_cat,
                'positivos': positivos_cat,
                'negativos': negativos_cat,
                'porcentaje_positivos': (positivos_cat / total_cat * 100) if total_cat > 0 else 0,
                'porcentaje_negativos': (negativos_cat / total_cat * 100) if total_cat > 0 else 0,
            })
        
        # Top estudiantes
        top_positivos = comportamientos.filter(tipo='Positivo').values(
            'estudiante__usuario__nombres',
            'estudiante__usuario__apellidos',
            'estudiante_id'
        ).annotate(
            total=Count('id')
        ).order_by('-total')[:10]
        
        top_negativos = comportamientos.filter(tipo='Negativo').values(
            'estudiante__usuario__nombres',
            'estudiante__usuario__apellidos',
            'estudiante_id'
        ).annotate(
            total=Count('id')
        ).order_by('-total')[:10]
        
        # Calcular ratios
        ratio_positivo = round((positivos / total_comportamientos * 100), 2) if total_comportamientos > 0 else 0
        ratio_negativo = round((negativos / total_comportamientos * 100), 2) if total_comportamientos > 0 else 0

        context.update({
            'comportamientos': comportamientos.order_by('-fecha')[:50],  # Limitar a 50
            'estadisticas': {
                'total': total_comportamientos,
                'positivos': positivos,
                'negativos': negativos,                
                'ratio_positivo': ratio_positivo,
                'ratio_negativo': ratio_negativo,
            },
            'por_categoria': por_categoria,
            'top_positivos': top_positivos,
            'top_negativos': top_negativos,
            'periodos': PeriodoAcademico.objects.filter(estado=True).select_related('periodo'),
            'docentes': Docente.objects.filter(estado=True).select_related('usuario'),
            'estudiantes': Estudiante.objects.filter(estado=True).select_related('usuario'),
            'categorias': Comportamiento.CATEGORIAS,
            'tipos_comportamiento': Comportamiento.TIPOS_COMPORTAMIENTO,
            'filtros': {
                'periodo_id': periodo_id,
                'tipo': tipo,
                'categoria': categoria,
                'docente_id': docente_id,
                'estudiante_id': estudiante_id,
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
            }
        })
        
        return context

class EstadisticasGeneralesView(RoleRequiredMixin, TemplateView):
    """Dashboard de estadísticas generales"""
    template_name = 'administrador/reportes/estadisticas.html'
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener año actual
        try:
            config = ConfiguracionGeneral.objects.first()
            año_actual = config.año_lectivo_actual if config else None
        except:
            año_actual = None
        
        # Estadísticas básicas
        total_estudiantes = Estudiante.objects.filter(estado=True).count()
        total_docentes = Docente.objects.filter(estado=True).count()
        total_sedes = Sede.objects.filter(estado=True).count()
        
        # Estudiantes activos
        estudiantes_activos = 0
        if año_actual:
            estudiantes_activos = Matricula.objects.filter(
                año_lectivo=año_actual,
                estado='ACT'
            ).count()
        
        # Distribución por género
        distribucion_genero = []
        if año_actual:
            matriculas = Matricula.objects.filter(
                año_lectivo=año_actual,
                estado='ACT'
            ).select_related('estudiante__usuario')
            
            masculinos = sum(1 for m in matriculas if m.estudiante.usuario.sexo == 'M')
            femeninos = sum(1 for m in matriculas if m.estudiante.usuario.sexo == 'F')
            no_especificado = estudiantes_activos - (masculinos + femeninos)
            
            distribucion_genero = [
                {'genero': 'Masculino', 'total': masculinos, 'porcentaje': (masculinos/estudiantes_activos*100) if estudiantes_activos > 0 else 0},
                {'genero': 'Femenino', 'total': femeninos, 'porcentaje': (femeninos/estudiantes_activos*100) if estudiantes_activos > 0 else 0},
                {'genero': 'No especificado', 'total': no_especificado, 'porcentaje': (no_especificado/estudiantes_activos*100) if estudiantes_activos > 0 else 0},
            ]
        
        # Distribución por grado
        distribucion_grado = []
        if año_actual:
            matriculas_grado = Matricula.objects.filter(
                año_lectivo=año_actual,
                estado='ACT'
            ).values(
                'grado_año_lectivo__grado__nombre'
            ).annotate(
                total=Count('id')
            ).order_by('grado_año_lectivo__grado__nombre')
            
            distribucion_grado = list(matriculas_grado)
        
        # Estadísticas de notas
        promedio_general = 0
        tasa_aprobacion = 0
        if año_actual:
            # Notas del año actual
            notas_año = Nota.objects.filter(
                periodo_academico__año_lectivo=año_actual
            )
            
            if notas_año.exists():
                promedio_general = notas_año.aggregate(Avg('calificacion'))['calificacion__avg'] or 0
                
                # Calcular tasa de aprobación (asumiendo 3.0 como mínimo)
                total_notas = notas_año.count()
                aprobados = notas_año.filter(calificacion__gte=3.0).count()
                tasa_aprobacion = (aprobados / total_notas * 100) if total_notas > 0 else 0
        
        # Asistencia promedio
        asistencia_promedio = 0
        if año_actual:
            asistencias_año = Asistencia.objects.filter(
                periodo_academico__año_lectivo=año_actual
            )
            
            if asistencias_año.exists():
                total_asistencias = asistencias_año.count()
                asistencias_real = asistencias_año.filter(estado='A').count()
                asistencia_promedio = (asistencias_real / total_asistencias * 100) if total_asistencias > 0 else 0
        
        # Comportamiento
        comportamientos_positivos = 0
        comportamientos_negativos = 0
        if año_actual:
            comportamientos = Comportamiento.objects.filter(
                periodo_academico__año_lectivo=año_actual
            )
            comportamientos_positivos = comportamientos.filter(tipo='Positivo').count()
            comportamientos_negativos = comportamientos.filter(tipo='Negativo').count()
        
        # Evolución histórica (últimos 5 años)
        evolucion_anual = []
        años = AñoLectivo.objects.all().order_by('-anho')[:5]
        
        for año in años:
            matriculas_año = Matricula.objects.filter(año_lectivo=año, estado='ACT').count()
            evolucion_anual.append({
                'año': año.anho,
                'estudiantes': matriculas_año,
            })
        
        context.update({
            'año_actual': año_actual,
            'estadisticas': {
                'total_estudiantes': total_estudiantes,
                'total_docentes': total_docentes,
                'total_sedes': total_sedes,
                'estudiantes_activos': estudiantes_activos,
                'promedio_general': round(promedio_general, 2),
                'tasa_aprobacion': round(tasa_aprobacion, 2),
                'asistencia_promedio': round(asistencia_promedio, 2),
                'comportamientos_positivos': comportamientos_positivos,
                'comportamientos_negativos': comportamientos_negativos,
                'ratio_comportamiento': round((comportamientos_positivos / (comportamientos_positivos + comportamientos_negativos) * 100), 2) if (comportamientos_positivos + comportamientos_negativos) > 0 else 0,
            },
            'distribucion_genero': distribucion_genero,
            'distribucion_grado': distribucion_grado,
            'evolucion_anual': evolucion_anual,
        })
        
        return context

# ========== VISTAS AJAX PARA DATOS DINÁMICOS ==========

class ObtenerDatosReporteView(RoleRequiredMixin, View):
    """Obtener datos para gráficos y estadísticas dinámicas (AJAX)"""
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get(self, request):
        tipo = request.GET.get('tipo')
        
        if tipo == 'distribucion_grado':
            año_lectivo_id = request.GET.get('año_lectivo_id')
            return self.obtener_distribucion_grado(año_lectivo_id)
        
        elif tipo == 'estadisticas_notas':
            periodo_id = request.GET.get('periodo_id')
            return self.obtener_estadisticas_notas(periodo_id)
        
        elif tipo == 'evolucion_asistencia':
            año_lectivo_id = request.GET.get('año_lectivo_id')
            return self.obtener_evolucion_asistencia(año_lectivo_id)
        
        return JsonResponse({'error': 'Tipo no válido'}, status=400)
    
    def obtener_distribucion_grado(self, año_lectivo_id):
        """Obtener distribución de estudiantes por grado"""
        try:
            if año_lectivo_id:
                año_lectivo = AñoLectivo.objects.get(id=año_lectivo_id)
                datos = Matricula.objects.filter(
                    año_lectivo=año_lectivo,
                    estado='ACT'
                ).values(
                    'grado_año_lectivo__grado__nombre'
                ).annotate(
                    total=Count('id')
                ).order_by('grado_año_lectivo__grado__nombre')
                
                labels = [item['grado_año_lectivo__grado__nombre'] for item in datos]
                valores = [item['total'] for item in datos]
                
                return JsonResponse({
                    'success': True,
                    'labels': labels,
                    'datasets': [{
                        'label': 'Estudiantes por Grado',
                        'data': valores,
                        'backgroundColor': [
                            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
                            '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
                        ]
                    }]
                })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        
        return JsonResponse({'error': 'Año lectivo no especificado'}, status=400)
    
    def obtener_estadisticas_notas(self, periodo_id):
        """Obtener estadísticas de notas por periodo"""
        try:
            if periodo_id:
                periodo = PeriodoAcademico.objects.get(id=periodo_id)
                notas = Nota.objects.filter(periodo_academico=periodo)
                
                # Distribución por rangos de calificación
                rangos = [
                    {'min': 0.0, 'max': 2.9, 'label': 'Bajo (0-2.9)'},
                    {'min': 3.0, 'max': 3.5, 'label': 'Básico (3.0-3.5)'},
                    {'min': 3.6, 'max': 4.0, 'label': 'Alto (3.6-4.0)'},
                    {'min': 4.1, 'max': 5.0, 'label': 'Superior (4.1-5.0)'},
                ]
                
                datos_rangos = []
                for rango in rangos:
                    count = notas.filter(
                        calificacion__gte=rango['min'],
                        calificacion__lte=rango['max']
                    ).count()
                    datos_rangos.append({
                        'rango': rango['label'],
                        'cantidad': count
                    })
                
                # Top 5 asignaturas con mejor promedio
                top_asignaturas = notas.values(
                    'asignatura_grado_año_lectivo__asignatura__nombre'
                ).annotate(
                    promedio=Avg('calificacion'),
                    total=Count('id')
                ).order_by('-promedio')[:5]
                
                return JsonResponse({
                    'success': True,
                    'datos_rangos': list(datos_rangos),
                    'top_asignaturas': list(top_asignaturas),
                    'estadisticas_generales': {
                        'promedio': notas.aggregate(Avg('calificacion'))['calificacion__avg'] or 0,
                        'maxima': notas.aggregate(Max('calificacion'))['calificacion__max'] or 0,
                        'minima': notas.aggregate(Min('calificacion'))['calificacion__min'] or 0,
                        'total': notas.count(),
                    }
                })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        
        return JsonResponse({'error': 'Periodo no especificado'}, status=400)
    
    def obtener_evolucion_asistencia(self, año_lectivo_id):
        """Obtener evolución de asistencia por mes"""
        try:
            if año_lectivo_id:
                año_lectivo = AñoLectivo.objects.get(id=año_lectivo_id)
                
                # Obtener asistencias por mes
                asistencias = Asistencia.objects.filter(
                    periodo_academico__año_lectivo=año_lectivo
                ).annotate(
                    mes=TruncMonth('fecha')
                ).values('mes').annotate(
                    total=Count('id'),
                    presentes=Count('id', filter=Q(estado='A')),
                    porcentaje=(Count('id', filter=Q(estado='A')) * 100.0 / Count('id'))
                ).order_by('mes')
                
                datos = list(asistencias)
                
                return JsonResponse({
                    'success': True,
                    'datos': datos
                })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        
        return JsonResponse({'error': 'Año lectivo no especificado'}, status=400)

# ========== REPORTES ESPECIALIZADOS ==========

class ReporteEstudiantesRiesgoView(RoleRequiredMixin, TemplateView):
    """Reporte de estudiantes en riesgo académico"""
    template_name = 'administrador/reportes/estudiantes_riesgo.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener parámetros
        periodo_id = self.request.GET.get('periodo')
        grado_id = self.request.GET.get('grado')
        sede_id = self.request.GET.get('sede')
        
        # Obtener periodo actual si no se especifica
        periodo = None
        if periodo_id:
            periodo = PeriodoAcademico.objects.get(id=periodo_id)
        else:
            # Buscar el periodo actual o el más reciente
            periodo = PeriodoAcademico.objects.filter(estado=True).order_by('-fecha_fin').first()
        
        if not periodo:
            context['error'] = 'No hay periodos académicos activos'
            return context
        
        # Obtener notas del periodo
        notas_query = Nota.objects.filter(
            periodo_academico=periodo
        ).select_related(
            'estudiante__usuario',
            'asignatura_grado_año_lectivo__asignatura',
            'asignatura_grado_año_lectivo__grado_año_lectivo__grado'
        )
        
        if grado_id:
            notas_query = notas_query.filter(
                asignatura_grado_año_lectivo__grado_año_lectivo__grado_id=grado_id
            )
        
        if sede_id:
            notas_query = notas_query.filter(
                asignatura_grado_año_lectivo__sede_id=sede_id
            )
        
        # Identificar estudiantes en riesgo (promedio < 3.0)
        estudiantes_riesgo = []
        estudiantes_data = {}
        
        for nota in notas_query:
            estudiante_id = nota.estudiante.id
            if estudiante_id not in estudiantes_data:
                estudiantes_data[estudiante_id] = {
                    'estudiante': nota.estudiante,
                    'notas': [],
                    'suma': 0,
                    'count': 0,
                    'asignaturas_bajas': 0
                }
            
            estudiantes_data[estudiante_id]['notas'].append(nota)
            estudiantes_data[estudiante_id]['suma'] += float(nota.calificacion)
            estudiantes_data[estudiante_id]['count'] += 1
            
            if nota.calificacion < 3.0:
                estudiantes_data[estudiante_id]['asignaturas_bajas'] += 1
        
        # Calcular promedios y filtrar estudiantes en riesgo
        for estudiante_id, datos in estudiantes_data.items():
            if datos['count'] > 0:
                promedio = datos['suma'] / datos['count']
                if promedio < 3.0 or datos['asignaturas_bajas'] >= 2:
                    estudiantes_riesgo.append({
                        'estudiante': datos['estudiante'],
                        'promedio': round(promedio, 2),
                        'asignaturas_bajas': datos['asignaturas_bajas'],
                        'total_asignaturas': datos['count'],
                        'notas': datos['notas']
                    })
        
        # Ordenar por promedio (más bajo primero)
        estudiantes_riesgo.sort(key=lambda x: x['promedio'])
        
        context.update({
            'estudiantes_riesgo': estudiantes_riesgo,
            'periodo': periodo,
            'periodos': PeriodoAcademico.objects.filter(estado=True),
            'grados': Grado.objects.all(),
            'sedes': Sede.objects.filter(estado=True),
            'total_riesgo': len(estudiantes_riesgo),
            'filtros': {
                'periodo_id': periodo.id if periodo else None,
                'grado_id': grado_id,
                'sede_id': sede_id,
            }
        })
        
        return context

class ReporteLogrosView(RoleRequiredMixin, TemplateView):
    """Reporte de logros académicos"""
    template_name = 'administrador/reportes/logros.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener parámetros
        año_lectivo_id = self.request.GET.get('año_lectivo')
        grado_id = self.request.GET.get('grado')
        periodo_id = self.request.GET.get('periodo')
        asignatura_id = self.request.GET.get('asignatura')
        
        # Base query para logros
        logros_query = Logro.objects.all().select_related(
            'asignatura__area',
            'grado__nivel_escolar',
            'periodo_academico__periodo',
            'periodo_academico__año_lectivo__sede'
        )
        
        # Aplicar filtros
        if año_lectivo_id:
            logros_query = logros_query.filter(
                periodo_academico__año_lectivo_id=año_lectivo_id
            )
        
        if grado_id:
            logros_query = logros_query.filter(grado_id=grado_id)
        
        if periodo_id:
            logros_query = logros_query.filter(periodo_academico_id=periodo_id)
        
        if asignatura_id:
            logros_query = logros_query.filter(asignatura_id=asignatura_id)
        
        # Agrupar logros
        logros_agrupados = {}
        for logro in logros_query:
            key = f"{logro.grado.nombre}_{logro.asignatura.nombre}"
            if key not in logros_agrupados:
                logros_agrupados[key] = {
                    'grado': logro.grado,
                    'asignatura': logro.asignatura,
                    'logros': [],
                    'por_periodo': {}
                }
            
            logros_agrupados[key]['logros'].append(logro)
            
            # Contar por periodo
            periodo_nombre = logro.periodo_academico.periodo.nombre
            if periodo_nombre not in logros_agrupados[key]['por_periodo']:
                logros_agrupados[key]['por_periodo'][periodo_nombre] = 0
            logros_agrupados[key]['por_periodo'][periodo_nombre] += 1
        
        # Convertir a lista para template
        logros_lista = list(logros_agrupados.values())
        
        # Estadísticas
        total_logros = logros_query.count()
        total_asignaturas = len(logros_agrupados)
        
        # Logros por periodo
        logros_por_periodo = logros_query.values(
            'periodo_academico__periodo__nombre'
        ).annotate(
            total=Count('id')
        ).order_by('periodo_academico__periodo__nombre')
        
        # Logros por grado
        logros_por_grado = logros_query.values(
            'grado__nombre'
        ).annotate(
            total=Count('id')
        ).order_by('grado__nombre')
        
        context.update({
            'logros_agrupados': logros_lista,
            'estadisticas': {
                'total_logros': total_logros,
                'total_asignaturas': total_asignaturas,
                'promedio_por_asignatura': round(total_logros / total_asignaturas, 1) if total_asignaturas > 0 else 0,
            },
            'logros_por_periodo': list(logros_por_periodo),
            'logros_por_grado': list(logros_por_grado),
            'años_lectivos': AñoLectivo.objects.all().order_by('-anho'),
            'grados': Grado.objects.all(),
            'periodos': Periodo.objects.all(),
            'asignaturas': Asignatura.objects.all(),
            'filtros': {
                'año_lectivo_id': año_lectivo_id,
                'grado_id': grado_id,
                'periodo_id': periodo_id,
                'asignatura_id': asignatura_id,
            }
        })
        
        return context

# ========== VISTAS DE EXPORTACIÓN ==========

class ExportarReporteView(RoleRequiredMixin, View):
    """Vista para exportar reportes en diferentes formatos"""
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def post(self, request):
        tipo_reporte = request.POST.get('tipo_reporte')
        formato = request.POST.get('formato')
        
        if not tipo_reporte or not formato:
            return JsonResponse({
                'error': 'Tipo de reporte y formato son requeridos'
            }, status=400)
        
        if tipo_reporte == 'estudiantes':
            return self.exportar_reporte_estudiantes(request, formato)
        elif tipo_reporte == 'notas':
            return self.exportar_reporte_notas(request, formato)
        elif tipo_reporte == 'asistencia':
            return self.exportar_reporte_asistencia(request, formato)
        elif tipo_reporte == 'comportamiento':
            return self.exportar_reporte_comportamiento(request, formato)
        elif tipo_reporte == 'estudiantes_riesgo':
            return self.exportar_reporte_estudiantes_riesgo(request, formato)
        elif tipo_reporte == 'logros':
            return self.exportar_reporte_logros(request, formato)
        
        # SIEMPRE devolver una respuesta
        return JsonResponse({
            'error': 'Tipo de reporte no válido'
        }, status=400)
    
    def exportar_reporte_estudiantes(self, request, formato):
        """Exportar reporte de estudiantes"""
        try:
            # Obtener parámetros del formulario
            sede_id = request.POST.get('sede')
            grado_id = request.POST.get('grado')
            año_lectivo_id = request.POST.get('año_lectivo')
            estado = request.POST.get('estado')
            edad_min = request.POST.get('edad_min')
            edad_max = request.POST.get('edad_max')
            genero = request.POST.get('genero')
            
            # Obtener estudiantes filtrados
            estudiantes = Estudiante.objects.filter(estado=True).select_related('usuario')
            
            if sede_id:
                estudiantes = estudiantes.filter(matriculas__sede_id=sede_id)
            if grado_id:
                estudiantes = estudiantes.filter(matriculas__grado_año_lectivo__grado_id=grado_id)
            if año_lectivo_id:
                estudiantes = estudiantes.filter(matriculas__año_lectivo_id=año_lectivo_id)
            if estado:
                estudiantes = estudiantes.filter(matriculas__estado=estado)
            if genero:
                estudiantes = estudiantes.filter(usuario__sexo=genero)
            
            # Preparar datos para exportación
            encabezados = [
                'ID', 'Documento', 'Nombres', 'Apellidos', 'Fecha Nacimiento', 'Edad', 
                'Género', 'Teléfono', 'Email', 'Sede Actual', 'Grado Actual', 
                'Estado Matrícula', 'Fecha Matrícula'
            ]
            
            datos = []
            for estudiante in estudiantes:
                matricula = estudiante.matricula_actual
                fecha_nacimiento = estudiante.usuario.fecha_nacimiento.strftime('%d/%m/%Y') if estudiante.usuario.fecha_nacimiento else ''
                fecha_matricula = matricula.fecha_matricula.strftime('%d/%m/%Y') if matricula and matricula.fecha_matricula else ''
                
                datos.append([
                    estudiante.id,
                    estudiante.usuario.numero_documento,
                    estudiante.usuario.nombres,
                    estudiante.usuario.apellidos,
                    fecha_nacimiento,
                    estudiante.usuario.edad or '',
                    estudiante.usuario.get_sexo_display() if estudiante.usuario.sexo else '',
                    estudiante.usuario.telefono or '',
                    estudiante.usuario.email or '',
                    matricula.sede.nombre if matricula else '',
                    matricula.grado_año_lectivo.grado.nombre if matricula else '',
                    matricula.get_estado_display() if matricula else '',
                    fecha_matricula
                ])
            
            if formato == 'excel':
                return generar_reporte_excel('estudiantes', encabezados, datos)
            elif formato == 'csv':
                return generar_reporte_csv('estudiantes', encabezados, datos)
            elif formato == 'pdf':
                return self.generar_reporte_pdf('estudiantes', encabezados, datos)
            
            return JsonResponse({'error': 'Formato no soportado'}, status=400)
            
        except Exception as e:
            return JsonResponse({'error': f'Error al exportar: {str(e)}'}, status=500)
    
    def exportar_reporte_notas(self, request, formato):
        """Exportar reporte de notas"""
        try:
            # Obtener parámetros
            periodo_id = request.POST.get('periodo')
            grado_id = request.POST.get('grado')
            asignatura_id = request.POST.get('asignatura')
            sede_id = request.POST.get('sede')
            estudiante_id = request.POST.get('estudiante_id')
            tipo_reporte = request.POST.get('tipo_reporte_original', 'grupal')
            
            # Lógica para obtener notas según parámetros
            notas = Nota.objects.all().select_related(
                'estudiante__usuario',
                'asignatura_grado_año_lectivo__asignatura',
                'periodo_academico__periodo'
            )
            
            if periodo_id:
                notas = notas.filter(periodo_academico_id=periodo_id)
            if grado_id:
                notas = notas.filter(
                    asignatura_grado_año_lectivo__grado_año_lectivo__grado_id=grado_id
                )
            if asignatura_id:
                notas = notas.filter(
                    asignatura_grado_año_lectivo__asignatura_id=asignatura_id
                )
            if sede_id:
                notas = notas.filter(
                    asignatura_grado_año_lectivo__sede_id=sede_id
                )
            if estudiante_id:
                notas = notas.filter(estudiante_id=estudiante_id)
            
            if tipo_reporte == 'individual' and estudiante_id:
                # Exportar boletín individual
                return self.exportar_boletin_individual(request, formato)
            
            # Exportar reporte grupal
            encabezados = ['Estudiante', 'Documento', 'Asignatura', 'Periodo', 'Calificación', 'Observaciones']
            
            datos = []
            for nota in notas:
                datos.append([
                    nota.estudiante.usuario.get_full_name(),
                    nota.estudiante.usuario.numero_documento,
                    nota.asignatura_grado_año_lectivo.asignatura.nombre,
                    nota.periodo_academico.periodo.nombre,
                    str(nota.calificacion),
                    nota.observaciones or ''
                ])
            
            if formato == 'excel':
                return generar_reporte_excel('notas', encabezados, datos)
            elif formato == 'csv':
                return generar_reporte_csv('notas', encabezados, datos)
            
            return JsonResponse({'error': 'Formato no soportado para este reporte'}, status=400)
            
        except Exception as e:
            return JsonResponse({'error': f'Error al exportar: {str(e)}'}, status=500)
    
    def exportar_reporte_asistencia(self, request, formato):
        """Exportar reporte de asistencia"""
        try:
            # Obtener parámetros
            fecha_inicio = request.POST.get('fecha_inicio')
            fecha_fin = request.POST.get('fecha_fin')
            sede_id = request.POST.get('sede')
            grado_id = request.POST.get('grado')
            
            # Obtener asistencias filtradas
            asistencias = Asistencia.objects.all().select_related(
                'estudiante__usuario',
                'periodo_academico__año_lectivo'
            )
            
            if fecha_inicio:
                asistencias = asistencias.filter(fecha__gte=fecha_inicio)
            if fecha_fin:
                asistencias = asistencias.filter(fecha__lte=fecha_fin)
            if sede_id:
                asistencias = asistencias.filter(
                    estudiante__matriculas__sede_id=sede_id
                )
            if grado_id:
                asistencias = asistencias.filter(
                    estudiante__matriculas__grado_año_lectivo__grado_id=grado_id
                )
            
            encabezados = ['Fecha', 'Estudiante', 'Documento', 'Periodo', 'Estado', 'Justificación']
            
            datos = []
            for asistencia in asistencias:
                datos.append([
                    asistencia.fecha.strftime('%d/%m/%Y'),
                    asistencia.estudiante.usuario.get_full_name(),
                    asistencia.estudiante.usuario.numero_documento,
                    asistencia.periodo_academico.periodo.nombre,
                    asistencia.get_estado_display(),
                    asistencia.justificacion or ''
                ])
            
            if formato == 'excel':
                return generar_reporte_excel('asistencia', encabezados, datos)
            elif formato == 'csv':
                return generar_reporte_csv('asistencia', encabezados, datos)
            
            return JsonResponse({'error': 'Formato no soportado'}, status=400)
            
        except Exception as e:
            return JsonResponse({'error': f'Error al exportar: {str(e)}'}, status=500)
    
    def exportar_reporte_comportamiento(self, request, formato):
        """Exportar reporte de comportamiento"""
        try:
            # Obtener parámetros
            periodo_id = request.POST.get('periodo')
            tipo = request.POST.get('tipo')
            categoria = request.POST.get('categoria')
            
            comportamientos = Comportamiento.objects.all().select_related(
                'estudiante__usuario',
                'periodo_academico__periodo',
                'docente__usuario'
            )
            
            if periodo_id:
                comportamientos = comportamientos.filter(periodo_academico_id=periodo_id)
            if tipo:
                comportamientos = comportamientos.filter(tipo=tipo)
            if categoria:
                comportamientos = comportamientos.filter(categoria=categoria)
            
            encabezados = ['Fecha', 'Estudiante', 'Tipo', 'Categoría', 'Descripción', 'Docente', 'Periodo']
            
            datos = []
            for comp in comportamientos:
                datos.append([
                    comp.fecha.strftime('%d/%m/%Y'),
                    comp.estudiante.usuario.get_full_name(),
                    comp.tipo,
                    comp.get_categoria_display(),
                    comp.descripcion,
                    comp.docente.usuario.get_full_name() if comp.docente else 'Sistema',
                    comp.periodo_academico.periodo.nombre
                ])
            
            if formato == 'excel':
                return generar_reporte_excel('comportamiento', encabezados, datos)
            elif formato == 'csv':
                return generar_reporte_csv('comportamiento', encabezados, datos)
            
            return JsonResponse({'error': 'Formato no soportado'}, status=400)
            
        except Exception as e:
            return JsonResponse({'error': f'Error al exportar: {str(e)}'}, status=500)
    
    def exportar_reporte_estudiantes_riesgo(self, request, formato):
        """Exportar reporte de estudiantes en riesgo"""
        try:
            # Obtener parámetros
            periodo_id = request.POST.get('periodo')
            grado_id = request.POST.get('grado')
            sede_id = request.POST.get('sede')
            
            # Esta lógica sería similar a ReporteEstudiantesRiesgoView
            # Por simplicidad, exportaremos un reporte básico
            from estudiantes.models import Nota
            
            notas = Nota.objects.filter(
                periodo_academico_id=periodo_id
            ).select_related(
                'estudiante__usuario',
                'asignatura_grado_año_lectivo__asignatura'
            )
            
            if grado_id:
                notas = notas.filter(
                    asignatura_grado_año_lectivo__grado_año_lectivo__grado_id=grado_id
                )
            
            if sede_id:
                notas = notas.filter(
                    asignatura_grado_año_lectivo__sede_id=sede_id
                )
            
            # Agrupar por estudiante
            estudiantes_data = {}
            for nota in notas:
                estudiante_id = nota.estudiante.id
                if estudiante_id not in estudiantes_data:
                    estudiantes_data[estudiante_id] = {
                        'estudiante': nota.estudiante,
                        'notas': [],
                        'suma': 0,
                        'count': 0
                    }
                estudiantes_data[estudiante_id]['notas'].append(nota)
                estudiantes_data[estudiante_id]['suma'] += float(nota.calificacion)
                estudiantes_data[estudiante_id]['count'] += 1
            
            encabezados = ['Estudiante', 'Documento', 'Promedio', 'Asignaturas Bajas', 'Total Asignaturas']
            
            datos = []
            for estudiante_id, datos_est in estudiantes_data.items():
                if datos_est['count'] > 0:
                    promedio = datos_est['suma'] / datos_est['count']
                    asignaturas_bajas = sum(1 for n in datos_est['notas'] if n.calificacion < 3.0)
                    
                    if promedio < 3.0 or asignaturas_bajas >= 2:
                        datos.append([
                            datos_est['estudiante'].usuario.get_full_name(),
                            datos_est['estudiante'].usuario.numero_documento,
                            round(promedio, 2),
                            asignaturas_bajas,
                            datos_est['count']
                        ])
            
            if formato == 'excel':
                return generar_reporte_excel('estudiantes_riesgo', encabezados, datos)
            elif formato == 'csv':
                return generar_reporte_csv('estudiantes_riesgo', encabezados, datos)
            
            return JsonResponse({'error': 'Formato no soportado'}, status=400)
            
        except Exception as e:
            return JsonResponse({'error': f'Error al exportar: {str(e)}'}, status=500)
    
    def exportar_reporte_logros(self, request, formato):
        """Exportar reporte de logros"""
        try:
            # Obtener parámetros
            año_lectivo_id = request.POST.get('año_lectivo')
            grado_id = request.POST.get('grado')
            periodo_id = request.POST.get('periodo')
            
            logros = Logro.objects.all().select_related(
                'asignatura__area',
                'grado__nivel_escolar',
                'periodo_academico__periodo'
            )
            
            if año_lectivo_id:
                logros = logros.filter(
                    periodo_academico__año_lectivo_id=año_lectivo_id
                )
            if grado_id:
                logros = logros.filter(grado_id=grado_id)
            if periodo_id:
                logros = logros.filter(periodo_academico_id=periodo_id)
            
            encabezados = ['Grado', 'Asignatura', 'Periodo', 'Tema', 'Descripción Superior', 'Descripción Alto', 'Descripción Básico', 'Descripción Bajo']
            
            datos = []
            for logro in logros:
                datos.append([
                    logro.grado.nombre,
                    logro.asignatura.nombre,
                    logro.periodo_academico.periodo.nombre,
                    logro.tema or '',
                    logro.descripcion_superior or '',
                    logro.descripcion_alto or '',
                    logro.descripcion_basico or '',
                    logro.descripcion_bajo or ''
                ])
            
            if formato == 'excel':
                return generar_reporte_excel('logros', encabezados, datos)
            elif formato == 'csv':
                return generar_reporte_csv('logros', encabezados, datos)
            
            return JsonResponse({'error': 'Formato no soportado'}, status=400)
            
        except Exception as e:
            return JsonResponse({'error': f'Error al exportar: {str(e)}'}, status=500)
    
    def exportar_boletin_individual(self, request, formato):
        """Exportar boletín individual de notas"""
        try:
            estudiante_id = request.POST.get('estudiante_id')
            periodo_id = request.POST.get('periodo_id')
            
            if not estudiante_id:
                return JsonResponse({'error': 'ID de estudiante requerido'}, status=400)
            
            estudiante = get_object_or_404(Estudiante, id=estudiante_id)
            notas = Nota.objects.filter(
                estudiante=estudiante
            ).select_related(
                'asignatura_grado_año_lectivo__asignatura',
                'periodo_academico__periodo'
            )
            
            if periodo_id:
                notas = notas.filter(periodo_academico_id=periodo_id)
            
            if formato == 'pdf':
                return self.generar_boletin_pdf(estudiante, notas)
            else:
                return JsonResponse({'error': 'Solo PDF disponible para boletines individuales'}, status=400)
                
        except Exception as e:
            return JsonResponse({'error': f'Error al exportar boletín: {str(e)}'}, status=500)
    
    def generar_boletin_pdf(self, estudiante, notas):
        """Generar boletín en PDF"""
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        response = HttpResponse(content_type='application/pdf')
        filename = f"boletin_{estudiante.usuario.apellidos}_{estudiante.usuario.nombres}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        p = canvas.Canvas(response, pagesize=letter)
        width, height = letter
        
        # Encabezado
        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, height - 100, "BOLETÍN DE NOTAS")
        p.setFont("Helvetica", 12)
        p.drawString(100, height - 130, f"Estudiante: {estudiante.usuario.get_full_name()}")
        p.drawString(100, height - 150, f"Documento: {estudiante.usuario.numero_documento}")
        
        # Tabla de notas
        y = height - 200
        if notas.exists():
            p.setFont("Helvetica-Bold", 10)
            p.drawString(100, y, "ASIGNATURA")
            p.drawString(300, y, "PERIODO")
            p.drawString(400, y, "CALIFICACIÓN")
            
            y -= 20
            p.setFont("Helvetica", 10)
            
            for nota in notas:
                p.drawString(100, y, nota.asignatura_grado_año_lectivo.asignatura.nombre[:30])
                p.drawString(300, y, nota.periodo_academico.periodo.nombre)
                p.drawString(400, y, str(nota.calificacion))
                y -= 15
                
                if y < 100:
                    p.showPage()
                    y = height - 100
                    p.setFont("Helvetica", 10)
            
            # Promedio
            promedio = notas.aggregate(Avg('calificacion'))['calificacion__avg'] or 0
            y -= 20
            p.setFont("Helvetica-Bold", 12)
            p.drawString(100, y, f"PROMEDIO GENERAL: {round(promedio, 2)}")
        else:
            p.drawString(100, y, "No hay notas registradas")
        
        p.showPage()
        p.save()
        return response
    
    def generar_reporte_pdf(self, nombre_reporte, encabezados, datos):
        """Generar reporte genérico en PDF"""
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{nombre_reporte}.pdf"'
        
        p = canvas.Canvas(response, pagesize=letter)
        width, height = letter
        
        # Encabezado
        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, height - 100, f"REPORTE DE {nombre_reporte.upper()}")
        p.setFont("Helvetica", 10)
        p.drawString(100, height - 120, f"Fecha: {timezone.now().strftime('%d/%m/%Y %H:%M')}")
        p.drawString(100, height - 140, f"Total registros: {len(datos)}")
        
        # Tabla
        y = height - 180
        
        # Encabezados
        p.setFont("Helvetica-Bold", 10)
        col_width = (width - 200) / len(encabezados)
        
        for i, header in enumerate(encabezados):
            p.drawString(100 + (i * col_width), y, header[:15])
        
        y -= 20
        p.setFont("Helvetica", 9)
        
        for fila in datos:
            if y < 100:  # Nueva página
                p.showPage()
                y = height - 100
                p.setFont("Helvetica", 9)
            
            for i, valor in enumerate(fila):
                p.drawString(100 + (i * col_width), y, str(valor)[:15])
            
            y -= 15
        
        p.showPage()
        p.save()
        return response

# ========== FUNCIONES AUXILIARES ==========

def generar_reporte_excel(nombre_archivo, encabezados, datos):
    """Función auxiliar para generar archivos Excel"""
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}.xls"'
    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Reporte')
    
    # Estilos
    header_style = xlwt.easyxf(
        'font: bold on; align: horiz center; pattern: pattern solid, fore_color light_green'
    )
    
    # Encabezados
    for col, header in enumerate(encabezados):
        ws.write(0, col, header, header_style)
    
    # Datos
    for row_num, fila in enumerate(datos, 1):
        for col_num, valor in enumerate(fila):
            ws.write(row_num, col_num, str(valor))
    
    # Ajustar ancho de columnas
    for i in range(len(encabezados)):
        ws.col(i).width = 256 * 15
    
    wb.save(response)
    return response

def generar_reporte_csv(nombre_archivo, encabezados, datos):
    """Función auxiliar para generar archivos CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(encabezados)
    
    for fila in datos:
        writer.writerow(fila)
    
    return response

def exportar_estudiantes_excel(self, estudiantes):
    """Exportar lista de estudiantes a Excel"""
    try:
        import xlwt
        
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="estudiantes.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Estudiantes')
        
        # Estilos
        header_style = xlwt.easyxf(
            'font: bold on; align: horiz center; pattern: pattern solid, fore_color light_green'
        )
        date_style = xlwt.easyxf(num_format_str='DD/MM/YYYY')
        
        # Encabezados - AÑADIR COLUMNA DE AÑO LECTIVO
        headers = ['ID', 'Documento', 'Nombres', 'Apellidos', 'Fecha Nacimiento', 'Edad', 
                  'Género', 'Teléfono', 'Email', 'Sede', 'Grado', 
                  'Estado Matrícula', 'Año Lectivo', 'Fecha Matrícula']
        
        for col, header in enumerate(headers):
            ws.write(0, col, header, header_style)
        
        # Datos
        row_num = 1
        for dato in self.get_estudiantes_filtrados():  # Necesitarás implementar este método
            estudiante = dato['estudiante']
            matricula = dato['matricula']
            
            ws.write(row_num, 0, estudiante.id)
            ws.write(row_num, 1, estudiante.usuario.numero_documento)
            ws.write(row_num, 2, estudiante.usuario.nombres)
            ws.write(row_num, 3, estudiante.usuario.apellidos)
            
            if estudiante.usuario.fecha_nacimiento:
                ws.write(row_num, 4, estudiante.usuario.fecha_nacimiento, date_style)
                ws.write(row_num, 5, dato['edad'] or '')
            else:
                ws.write(row_num, 4, '')
                ws.write(row_num, 5, '')
            
            ws.write(row_num, 6, estudiante.usuario.get_sexo_display() if estudiante.usuario.sexo else '')
            ws.write(row_num, 7, estudiante.usuario.telefono or '')
            ws.write(row_num, 8, estudiante.usuario.email or '')
            ws.write(row_num, 9, matricula.sede.nombre if matricula else '')
            ws.write(row_num, 10, matricula.grado_año_lectivo.grado.nombre if matricula else '')
            ws.write(row_num, 11, matricula.get_estado_display() if matricula else '')
            ws.write(row_num, 12, matricula.año_lectivo.anho if matricula else '')
            
            if matricula and matricula.fecha_matricula:
                ws.write(row_num, 13, matricula.fecha_matricula, date_style)
            else:
                ws.write(row_num, 13, '')
            
            row_num += 1
        
        # Ajustar ancho de columnas
        for i in range(len(headers)):
            ws.col(i).width = 256 * 15
        
        wb.save(response)
        return response
        
    except ImportError:
        return JsonResponse({'error': 'xlwt no está instalado'}, status=500)
    except Exception as e:
        return JsonResponse({'error': f'Error al generar Excel: {str(e)}'}, status=500)

#=================== Documentación individual - por estudiantes ================================= 
# administrador/views/reportes.py

class DocumentosEstudianteView(RoleRequiredMixin, TemplateView):
    template_name = 'administrador/reportes/documentos_estudiante.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente', 'Acudiente']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante = get_object_or_404(Estudiante, id=self.kwargs.get('estudiante_id'))
        context['estudiante'] = estudiante

        # Año lectivo actual
        config = ConfiguracionGeneral.objects.first()
        año_lectivo_actual = config.año_lectivo_actual if config else None

        # Años donde el estudiante estuvo matriculado
        años_lectivos = AñoLectivo.objects.filter(
            anho__in=estudiante.años_matriculados
        ).order_by('-anho')

        # Matrículas por año lectivo
        matriculas_por_año = {}

        for año in años_lectivos:
            matricula = estudiante.matriculas.filter(
                año_lectivo=año
            ).select_related(
                'grado_año_lectivo__grado'
            ).first()

            if matricula:
                matriculas_por_año[año.id] = matricula

        # Matrícula activa (año actual)
        matricula_activa = None
        if año_lectivo_actual:
            matricula_activa = estudiante.matriculas.filter(
                año_lectivo=año_lectivo_actual,
                estado='ACT'
            ).select_related(
                'grado_año_lectivo__grado'
            ).first()

        context.update({
            'años_lectivos': años_lectivos,
            'año_lectivo_actual': año_lectivo_actual,
            'matriculas_por_año': matriculas_por_año,
            'matricula_activa': matricula_activa,
            'matricula_actual': estudiante.matricula_actual,  # property
        })

        return context

class RedirigirConstanciaPDFView(RoleRequiredMixin, View):
    """Redirige a la vista de constancia PDF de estudiantes"""
    allowed_roles = ['Administrador', 'Rector', 'Docente', 'Acudiente']
    
    def get(self, request, *args, **kwargs):
        estudiante_id = kwargs.get('estudiante_id')
        año_lectivo_id = kwargs.get('año_lectivo_id')
        
        # Verificar permisos adicionales
        estudiante = get_object_or_404(Estudiante, id=estudiante_id)
        
        # Si el usuario es acudiente, verificar que sea acudiente de este estudiante
        if request.user.tipo_usuario.nombre == 'Acudiente':
            if not estudiante.acudientes.filter(acudiente=request.user).exists():
                raise PermissionDenied("No tiene permisos para acceder a este documento")
        
        return redirect('estudiantes:estudiante_constancia_año_admin', 
                       estudiante_id=estudiante_id, 
                       año_lectivo_id=año_lectivo_id)

class RedirigirObservadorPDFView(RoleRequiredMixin, View):
    """Redirige a la vista de observador PDF de estudiantes"""
    allowed_roles = ['Administrador', 'Rector', 'Docente', 'Acudiente']
    
    def get(self, request, *args, **kwargs):
        estudiante_id = kwargs.get('estudiante_id')
        año_lectivo_id = kwargs.get('año_lectivo_id')
        
        # Verificar permisos
        estudiante = get_object_or_404(Estudiante, id=estudiante_id)
        
        if request.user.tipo_usuario.nombre == 'Acudiente':
            if not estudiante.acudientes.filter(acudiente=request.user).exists():
                raise PermissionDenied("No tiene permisos para acceder a este documento")
        
        return redirect('estudiantes:estudiante_observador_año_admin', 
                       estudiante_id=estudiante_id, 
                       año_lectivo_id=año_lectivo_id)

class RedirigirReporteNotasPDFView(RoleRequiredMixin, View):
    """Redirige a la vista de reporte de notas (boletín) PDF de estudiantes"""
    allowed_roles = ['Administrador', 'Rector', 'Docente', 'Acudiente']
    
    def get(self, request, *args, **kwargs):
        estudiante_id = kwargs.get('estudiante_id')
        año_lectivo_id = kwargs.get('año_lectivo_id')
        
        # Verificar permisos
        estudiante = get_object_or_404(Estudiante, id=estudiante_id)
        
        if request.user.tipo_usuario.nombre == 'Acudiente':
            if not estudiante.acudientes.filter(acudiente=request.user).exists():
                raise PermissionDenied("No tiene permisos para acceder a este documento")
        
        return redirect('estudiantes:estudiante_boletin_final_año_admin', 
                       estudiante_id=estudiante_id, 
                       año_lectivo_id=año_lectivo_id)
    
class EstadisticasDemograficasView(RoleRequiredMixin, TemplateView):
    """Estadísticas demográficas detalladas con gráficos y análisis"""
    template_name = 'administrador/reportes/demograficas.html'
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener parámetros
        año_lectivo_id = self.request.GET.get('año_lectivo')
        sede_id = self.request.GET.get('sede')
        nivel_escolar_id = self.request.GET.get('nivel_escolar')
        
        # Determinar año lectivo
        if año_lectivo_id:
            año_lectivo = get_object_or_404(AñoLectivo, id=año_lectivo_id)
        else:
            # Obtener año actual
            try:
                config = ConfiguracionGeneral.objects.first()
                año_lectivo = config.año_lectivo_actual if config else None
            except:
                año_lectivo = None
        
        # ===== DATOS BASE =====
        hoy = timezone.now().date()
        
        # Matrículas activas filtradas
        matriculas = Matricula.objects.filter(estado='ACT')
        
        if año_lectivo:
            matriculas = matriculas.filter(año_lectivo=año_lectivo)
        
        if sede_id:
            matriculas = matriculas.filter(sede_id=sede_id)
        
        # ===== DISTRIBUCIÓN POR GÉNERO =====
        distribucion_genero = matriculas.values(
            'estudiante__usuario__sexo'
        ).annotate(
            total=Count('id'),
            promedio_edad=Avg(
                ExpressionWrapper(
                    hoy.year - ExtractYear('estudiante__usuario__fecha_nacimiento') -
                    Case(
                        When(
                            ExtractMonth('estudiante__usuario__fecha_nacimiento') > hoy.month,
                            then=Value(1)
                        ),
                        When(
                            ExtractMonth('estudiante__usuario__fecha_nacimiento') == hoy.month,
                            then=Case(
                                When(
                                    ExtractDay('estudiante__usuario__fecha_nacimiento') > hoy.day,
                                    then=Value(1)
                                ),
                                default=Value(0)
                            )
                        ),
                        default=Value(0)
                    ),
                    output_field=FloatField()
                )
            )
        ).order_by('estudiante__usuario__sexo')
        
        # Convertir a formato amigable
        generos = []
        for item in distribucion_genero:
            genero_display = dict(Usuario.SEXO_CHOICES).get(item['estudiante__usuario__sexo'], 'No especificado')
            generos.append({
                'genero': genero_display,
                'codigo': item['estudiante__usuario__sexo'],
                'total': item['total'],
                'porcentaje': round((item['total'] / matriculas.count() * 100), 2) if matriculas.count() > 0 else 0,
                'promedio_edad': round(item['promedio_edad'] or 0, 1),
            })
        
        # ===== DISTRIBUCIÓN POR EDAD =====
        # Calcular edades de todos los estudiantes
        edades = []
        rangos_detallados = {
            '3-5': {'count': 0, 'hombres': 0, 'mujeres': 0, 'desc': 'Preescolar (3-5 años)'},
            '6-7': {'count': 0, 'hombres': 0, 'mujeres': 0, 'desc': 'Primero-Segundo (6-7 años)'},
            '8-9': {'count': 0, 'hombres': 0, 'mujeres': 0, 'desc': 'Tercero-Cuarto (8-9 años)'},
            '10-11': {'count': 0, 'hombres': 0, 'mujeres': 0, 'desc': 'Quinto (10-11 años)'},
            '12+': {'count': 0, 'hombres': 0, 'mujeres': 0, 'desc': 'Bachillerato (12+ años)'},
        }
        
        for matricula in matriculas.select_related('estudiante__usuario'):
            estudiante = matricula.estudiante
            if estudiante.usuario.fecha_nacimiento:
                fecha_nac = estudiante.usuario.fecha_nacimiento
                edad = hoy.year - fecha_nac.year
                if (hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day):
                    edad -= 1
                
                edades.append(edad)
                
                # Clasificar en rangos
                if 3 <= edad <= 5:
                    rango = '3-5'
                elif 6 <= edad <= 7:
                    rango = '6-7'
                elif 8 <= edad <= 9:
                    rango = '8-9'
                elif 10 <= edad <= 11:
                    rango = '10-11'
                elif edad >= 12:
                    rango = '12+'
                else:
                    continue
                
                rangos_detallados[rango]['count'] += 1
                
                # Por género
                if estudiante.usuario.sexo == 'M':
                    rangos_detallados[rango]['hombres'] += 1
                elif estudiante.usuario.sexo == 'F':
                    rangos_detallados[rango]['mujeres'] += 1
        
        # Calcular estadísticas de edad
        if edades:
            promedio_edad = sum(edades) / len(edades)
            moda_edad = max(set(edades), key=edades.count)
            edad_min = min(edades)
            edad_max = max(edades)
        else:
            promedio_edad = moda_edad = edad_min = edad_max = 0
        
        # ===== DISTRIBUCIÓN POR GRADO =====
        distribucion_grado = matriculas.values(
            'grado_año_lectivo__grado__nombre',
            'grado_año_lectivo__grado__nivel_escolar__nombre'
        ).annotate(
            total=Count('id'),
            hombres=Count('id', filter=Q(estudiante__usuario__sexo='M')),
            mujeres=Count('id', filter=Q(estudiante__usuario__sexo='F'))
        ).order_by(
            'grado_año_lectivo__grado__nivel_escolar__nombre',
            'grado_año_lectivo__grado__nombre'
        )
        
        # Preparar datos por grado
        datos_por_grado = []
        for item in distribucion_grado:
            total = item['total']
            datos_por_grado.append({
                'grado': item['grado_año_lectivo__grado__nombre'],
                'nivel': item['grado_año_lectivo__grado__nivel_escolar__nombre'],
                'total': total,
                'hombres': item['hombres'],
                'mujeres': item['mujeres'],
                'porcentaje_hombres': round((item['hombres'] / total * 100), 2) if total > 0 else 0,
                'porcentaje_mujeres': round((item['mujeres'] / total * 100), 2) if total > 0 else 0,
                'densidad': self.calcular_densidad_grado(total),  # Baja, Media, Alta
            })
        
        # ===== DISTRIBUCIÓN POR NIVEL ESCOLAR =====
        distribucion_nivel = matriculas.values(
            'grado_año_lectivo__grado__nivel_escolar__nombre'
        ).annotate(
            total=Count('id'),
            promedio_edad=Avg(
                ExpressionWrapper(
                    hoy.year - ExtractYear('estudiante__usuario__fecha_nacimiento'),
                    output_field=FloatField()
                )
            )
        ).order_by('grado_año_lectivo__grado__nivel_escolar__nombre')
        
        # ===== ACUDIENTES Y CONTACTOS =====
        # Estudiantes con acudientes registrados
        estudiantes_con_acudientes = matriculas.filter(
            estudiante__acudientes__isnull=False
        ).distinct().count()
        
        # Estudiantes con información de contacto completa
        estudiantes_contacto_completo = matriculas.filter(
            estudiante__usuario__telefono__isnull=False,
            estudiante__usuario__email__isnull=False
        ).count()
        
        # ===== ESTADÍSTICAS TEMPORALES =====
        # Matrículas por mes del año
        matriculas_por_mes = Matricula.objects.filter(
            estado='ACT',
            año_lectivo=año_lectivo
        ).annotate(
            mes=ExtractMonth('created_at')
        ).values('mes').annotate(
            total=Count('id')
        ).order_by('mes')
        
        # ===== PREPARAR CONTEXTO FINAL =====
        total_estudiantes = matriculas.count()
        
        context.update({
            # Año lectivo actual
            'año_lectivo': año_lectivo,
            
            # Distribuciones principales
            'distribucion_genero': generos,
            'rangos_edad': rangos_detallados,
            'datos_por_grado': datos_por_grado,
            'distribucion_nivel': list(distribucion_nivel),
            'matriculas_por_mes': list(matriculas_por_mes),
            
            # Estadísticas generales
            'estadisticas': {
                'total_estudiantes': total_estudiantes,
                'promedio_edad': round(promedio_edad, 1),
                'moda_edad': moda_edad,
                'edad_minima': edad_min,
                'edad_maxima': edad_max,
                'desviacion_edad': self.calcular_desviacion_estandar(edades) if edades else 0,
                
                # Contactos
                'estudiantes_con_acudientes': estudiantes_con_acudientes,
                'estudiantes_sin_acudientes': total_estudiantes - estudiantes_con_acudientes,
                'porcentaje_con_acudientes': round((estudiantes_con_acudientes / total_estudiantes * 100), 2) 
                    if total_estudiantes > 0 else 0,
                'estudiantes_contacto_completo': estudiantes_contacto_completo,
                'porcentaje_contacto_completo': round((estudiantes_contacto_completo / total_estudiantes * 100), 2)
                    if total_estudiantes > 0 else 0,
                
                # Densidad
                'grados_con_mas_estudiantes': self.get_top_grados(datos_por_grado, top=3),
                'grados_con_menos_estudiantes': self.get_top_grados(datos_por_grado, top=3, reverse=False),
                
                # Ratio género
                'ratio_hombres_mujeres': self.calcular_ratio_genero(generos),
            },
            
            # Datos para gráficos
            'datos_grafico_genero': self.preparar_datos_grafico_genero(generos),
            'datos_grafico_edad': self.preparar_datos_grafico_edad(rangos_detallados),
            'datos_grafico_grado': self.preparar_datos_grafico_grado(datos_por_grado),
            
            # Filtros
            'sedes': Sede.objects.filter(estado=True),
            'años_lectivos': AñoLectivo.objects.all().order_by('-anho'),
            'niveles_escolares': NivelEscolar.objects.all(),
            
            # Valores actuales de filtros
            'filtros': {
                'año_lectivo_id': año_lectivo.id if año_lectivo else None,
                'sede_id': sede_id,
                'nivel_escolar_id': nivel_escolar_id,
            },
        })
        
        return context
    
    def calcular_densidad_grado(self, total_estudiantes):
        """Calcular densidad de estudiantes por grado"""
        if total_estudiantes >= 35:
            return {'text': 'Alta', 'class': 'danger', 'valor': total_estudiantes}
        elif total_estudiantes >= 25:
            return {'text': 'Media', 'class': 'warning', 'valor': total_estudiantes}
        else:
            return {'text': 'Baja', 'class': 'success', 'valor': total_estudiantes}
    
    def calcular_desviacion_estandar(self, datos):
        """Calcular desviación estándar"""
        import math
        if not datos:
            return 0
        
        n = len(datos)
        media = sum(datos) / n
        varianza = sum((x - media) ** 2 for x in datos) / n
        return round(math.sqrt(varianza), 2)
    
    def get_top_grados(self, datos_por_grado, top=3, reverse=True):
        """Obtener los grados con más/menos estudiantes"""
        sorted_grados = sorted(datos_por_grado, key=lambda x: x['total'], reverse=reverse)
        return sorted_grados[:top]
    
    def calcular_ratio_genero(self, generos):
        """Calcular ratio hombres:mujeres"""
        hombres = next((g for g in generos if g['codigo'] == 'M'), {'total': 0})
        mujeres = next((g for g in generos if g['codigo'] == 'F'), {'total': 0})
        
        if mujeres['total'] > 0:
            ratio = hombres['total'] / mujeres['total']
            return round(ratio, 2)
        return 'N/A'
    
    def preparar_datos_grafico_genero(self, generos):
        """Preparar datos para gráfico de género"""
        return {
            'labels': [g['genero'] for g in generos],
            'datasets': [{
                'label': 'Distribución por Género',
                'data': [g['total'] for g in generos],
                'backgroundColor': ['#36A2EB', '#FF6384', '#FFCE56'],
            }]
        }
    
    def preparar_datos_grafico_edad(self, rangos_edad):
        """Preparar datos para gráfico de edades"""
        return {
            'labels': [rango['desc'] for rango in rangos_edad.values()],
            'datasets': [{
                'label': 'Cantidad de Estudiantes',
                'data': [rango['count'] for rango in rangos_edad.values()],
                'backgroundColor': ['#4BC0C0', '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'],
            }]
        }
    
    def preparar_datos_grafico_grado(self, datos_por_grado):
        """Preparar datos para gráfico por grado"""
        return {
            'labels': [f"{d['grado']} ({d['nivel']})" for d in datos_por_grado],
            'datasets': [
                {
                    'label': 'Hombres',
                    'data': [d['hombres'] for d in datos_por_grado],
                    'backgroundColor': '#36A2EB',
                },
                {
                    'label': 'Mujeres',
                    'data': [d['mujeres'] for d in datos_por_grado],
                    'backgroundColor': '#FF6384',
                }
            ]
        }
    
    def post(self, request):
        """Exportar reporte demográfico"""
        formato = request.POST.get('formato')
        
        if formato == 'excel':
            return self.exportar_excel_demografico(request)
        elif formato == 'pdf':
            return self.exportar_pdf_demografico(request)
        
        return JsonResponse({'error': 'Formato no válido'}, status=400)
    
    def exportar_excel_demografico(self, request):
        """Exportar reporte demográfico a Excel"""
        import xlwt
        
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="estadisticas_demograficas.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        
        # Hoja 1: Resumen General
        ws1 = wb.add_sheet('Resumen')
        
        # Escribir resumen
        ws1.write(0, 0, 'REPORTE DEMOGRÁFICO', self.get_header_style())
        ws1.write(1, 0, f'Fecha: {timezone.now().strftime("%d/%m/%Y %H:%M")}')
        
        # Hoja 2: Distribución por Género
        ws2 = wb.add_sheet('Por Género')
        headers_genero = ['Género', 'Total', 'Porcentaje', 'Promedio Edad']
        for col, header in enumerate(headers_genero):
            ws2.write(0, col, header, self.get_header_style())
        
        # Hoja 3: Distribución por Edad
        ws3 = wb.add_sheet('Por Edad')
        headers_edad = ['Rango de Edad', 'Total', 'Hombres', 'Mujeres']
        for col, header in enumerate(headers_edad):
            ws3.write(0, col, header, self.get_header_style())
        
        wb.save(response)
        return response
    
    def get_header_style(self):
        """Obtener estilo para encabezados"""
        import xlwt
        return xlwt.easyxf('font: bold on; align: horiz center')
    
class ReporteCumpleañosView(RoleRequiredMixin, TemplateView):
    """Reporte completo de cumpleaños por mes, con filtros y estadísticas"""
    template_name = 'administrador/reportes/cumpleanos.html'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener parámetros de filtro
        mes = self.request.GET.get('mes', '')
        sede_id = self.request.GET.get('sede')
        grado_id = self.request.GET.get('grado')
        año_lectivo_id = self.request.GET.get('año_lectivo')
        include_docentes = self.request.GET.get('include_docentes', 'false') == 'true'
        
        # Fechas actuales
        hoy = timezone.now().date()
        mes_actual = hoy.month
        
        # ===== ESTUDIANTES =====
        estudiantes_query = Estudiante.objects.filter(
            usuario__fecha_nacimiento__isnull=False,
            estado=True
        ).select_related('usuario')
        
        # Aplicar filtros a estudiantes
        if sede_id:
            estudiantes_query = estudiantes_query.filter(matriculas__sede_id=sede_id).distinct()
        
        if grado_id:
            estudiantes_query = estudiantes_query.filter(
                matriculas__grado_año_lectivo__grado_id=grado_id
            ).distinct()
        
        if año_lectivo_id:
            estudiantes_query = estudiantes_query.filter(
                matriculas__año_lectivo_id=año_lectivo_id
            ).distinct()
        
        # Filtrar por mes si se especifica
        if mes:
            estudiantes_query = estudiantes_query.filter(
                usuario__fecha_nacimiento__month=mes
            )
        
        # Preparar datos de estudiantes
        cumpleaños_estudiantes = []
        estudiantes_por_mes = defaultdict(list)
        
        for estudiante in estudiantes_query:
            fecha_nac = estudiante.usuario.fecha_nacimiento
            mes_nac = fecha_nac.month
            dia_nac = fecha_nac.day
            
            # Calcular edad actual y edad que cumplirá
            edad_actual = hoy.year - fecha_nac.year
            if (hoy.month, hoy.day) < (mes_nac, dia_nac):
                edad_actual -= 1
            
            edad_a_cumplir = edad_actual + 1
            
            # Determinar si cumple pronto (próximos 30 días)
            fecha_cumple = date(hoy.year, mes_nac, dia_nac)
            dias_restantes = (fecha_cumple - hoy).days
            if dias_restantes < 0:
                fecha_cumple = date(hoy.year + 1, mes_nac, dia_nac)
                dias_restantes = (fecha_cumple - hoy).days
            
            cumple_pronto = dias_restantes <= 30
            
            # Determinar signo zodiacal
            signo_zodiacal = self.get_signo_zodiacal(mes_nac, dia_nac)
            
            datos_estudiante = {
                'tipo': 'Estudiante',
                'persona': estudiante,
                'nombre_completo': estudiante.usuario.get_full_name(),
                'fecha_nacimiento': fecha_nac,
                'dia': dia_nac,
                'mes': mes_nac,
                'edad_actual': edad_actual,
                'edad_a_cumplir': edad_a_cumplir,
                'dias_restantes': dias_restantes,
                'cumple_pronto': cumple_pronto,
                'hoy_cumple': dias_restantes == 0,
                'signo_zodiacal': signo_zodiacal,
                'matricula_actual': estudiante.matricula_actual,
                'contacto': estudiante.usuario.telefono or 'No tiene',
            }
            
            cumpleaños_estudiantes.append(datos_estudiante)
            estudiantes_por_mes[mes_nac].append(datos_estudiante)
        
        # ===== DOCENTES (si se incluyen) =====
        cumpleaños_docentes = []
        docentes_por_mes = defaultdict(list)
        
        if include_docentes:
            docentes_query = Docente.objects.filter(
                usuario__fecha_nacimiento__isnull=False,
                estado=True
            ).select_related('usuario')
            
            if sede_id:
                docentes_query = docentes_query.filter(
                    sedes_asignadas__sede_id=sede_id
                ).distinct()
            
            if año_lectivo_id:
                docentes_query = docentes_query.filter(
                    sedes_asignadas__año_lectivo_id=año_lectivo_id
                ).distinct()
            
            if mes:
                docentes_query = docentes_query.filter(
                    usuario__fecha_nacimiento__month=mes
                )
            
            for docente in docentes_query:
                fecha_nac = docente.usuario.fecha_nacimiento
                mes_nac = fecha_nac.month
                dia_nac = fecha_nac.day
                
                # Calcular edad
                edad_actual = hoy.year - fecha_nac.year
                if (hoy.month, hoy.day) < (mes_nac, dia_nac):
                    edad_actual -= 1
                
                # Días restantes
                fecha_cumple = date(hoy.year, mes_nac, dia_nac)
                dias_restantes = (fecha_cumple - hoy).days
                if dias_restantes < 0:
                    fecha_cumple = date(hoy.year + 1, mes_nac, dia_nac)
                    dias_restantes = (fecha_cumple - hoy).days
                
                datos_docente = {
                    'tipo': 'Docente',
                    'persona': docente,
                    'nombre_completo': docente.usuario.get_full_name(),
                    'fecha_nacimiento': fecha_nac,
                    'dia': dia_nac,
                    'mes': mes_nac,
                    'edad_actual': edad_actual,
                    'dias_restantes': dias_restantes,
                    'cumple_pronto': dias_restantes <= 30,
                    'hoy_cumple': dias_restantes == 0,
                    'signo_zodiacal': self.get_signo_zodiacal(mes_nac, dia_nac),
                    'contacto': docente.usuario.telefono or 'No tiene',
                }
                
                cumpleaños_docentes.append(datos_docente)
                docentes_por_mes[mes_nac].append(datos_docente)
        
        # ===== ESTADÍSTICAS GENERALES =====
        total_personas = len(cumpleaños_estudiantes) + len(cumpleaños_docentes)
        hoy_cumplen = len([p for p in cumpleaños_estudiantes if p['hoy_cumple']]) + \
                      len([p for p in cumpleaños_docentes if p['hoy_cumple']])
        
        # Cumpleaños por mes (todos)
        todos_cumpleaños = cumpleaños_estudiantes + cumpleaños_docentes
        cumpleaños_por_mes_completo = defaultdict(list)
        
        for persona in todos_cumpleaños:
            cumpleaños_por_mes_completo[persona['mes']].append(persona)
        
        # Ordenar por mes
        meses_ordenados = sorted(cumpleaños_por_mes_completo.items())
        
        # Ordenar cada mes por día
        for mes_num, personas in cumpleaños_por_mes_completo.items():
            personas.sort(key=lambda x: x['dia'])
        
        # Distribución por signo zodiacal
        signos_distribucion = defaultdict(int)
        for persona in todos_cumpleaños:
            signos_distribucion[persona['signo_zodiacal']] += 1
        
        # Meses con más cumpleaños
        meses_mas_cumpleaños = sorted(
            [(mes, len(personas)) for mes, personas in cumpleaños_por_mes_completo.items()],
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        # ===== PREPARAR DATOS PARA TEMPLATE =====
        context.update({
            # Datos principales
            'cumpleaños_por_mes': dict(meses_ordenados),
            'mes_actual': mes_actual,
            'dia_actual': hoy.day,
            'hoy': hoy,
            
            # Estadísticas
            'estadisticas': {
                'total_personas': total_personas,
                'total_estudiantes': len(cumpleaños_estudiantes),
                'total_docentes': len(cumpleaños_docentes),
                'hoy_cumplen': hoy_cumplen,
                'mes_actual_cantidad': len(cumpleaños_por_mes_completo.get(mes_actual, [])),
                'proximo_mes_cantidad': len(cumpleaños_por_mes_completo.get(
                    mes_actual + 1 if mes_actual < 12 else 1, []
                )),
                'promedio_edad_estudiantes': self.calcular_promedio_edad(cumpleaños_estudiantes),
                'promedio_edad_docentes': self.calcular_promedio_edad(cumpleaños_docentes),
            },
            
            # Distribuciones
            'signos_distribucion': dict(signos_distribucion),
            'meses_mas_cumpleaños': meses_mas_cumpleaños,
            
            # Filtros disponibles
            'meses': [
                (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
                (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
                (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
            ],
            'sedes': Sede.objects.filter(estado=True),
            'grados': Grado.objects.all(),
            'años_lectivos': AñoLectivo.objects.all().order_by('-anho'),
            
            # Valores de filtros actuales
            'filtros': {
                'mes': int(mes) if mes and mes.isdigit() else '',
                'sede_id': sede_id,
                'grado_id': grado_id,
                'año_lectivo_id': año_lectivo_id,
                'include_docentes': include_docentes,
            },
            
            # Datos para exportación
            'todos_cumpleaños': todos_cumpleaños,
        })
        
        return context
    
    def get_signo_zodiacal(self, mes, dia):
        """Determinar signo zodiacal basado en fecha"""
        if (mes == 3 and dia >= 21) or (mes == 4 and dia <= 19):
            return 'Aries'
        elif (mes == 4 and dia >= 20) or (mes == 5 and dia <= 20):
            return 'Tauro'
        elif (mes == 5 and dia >= 21) or (mes == 6 and dia <= 20):
            return 'Géminis'
        elif (mes == 6 and dia >= 21) or (mes == 7 and dia <= 22):
            return 'Cáncer'
        elif (mes == 7 and dia >= 23) or (mes == 8 and dia <= 22):
            return 'Leo'
        elif (mes == 8 and dia >= 23) or (mes == 9 and dia <= 22):
            return 'Virgo'
        elif (mes == 9 and dia >= 23) or (mes == 10 and dia <= 22):
            return 'Libra'
        elif (mes == 10 and dia >= 23) or (mes == 11 and dia <= 21):
            return 'Escorpio'
        elif (mes == 11 and dia >= 22) or (mes == 12 and dia <= 21):
            return 'Sagitario'
        elif (mes == 12 and dia >= 22) or (mes == 1 and dia <= 19):
            return 'Capricornio'
        elif (mes == 1 and dia >= 20) or (mes == 2 and dia <= 18):
            return 'Acuario'
        else:
            return 'Piscis'
    
    def calcular_promedio_edad(self, personas):
        """Calcular promedio de edad de una lista de personas"""
        if not personas:
            return 0
        
        edades = [p['edad_actual'] for p in personas]
        return round(sum(edades) / len(edades), 1)
    
    def post(self, request):
        """Exportar reporte de cumpleaños"""
        formato = request.POST.get('formato')
        
        if formato == 'excel':
            return self.exportar_excel(request)
        elif formato == 'pdf':
            return self.exportar_pdf(request)
        elif formato == 'csv':
            return self.exportar_csv(request)
        
        return JsonResponse({'error': 'Formato no válido'}, status=400)
    
    def exportar_excel(self, request):
        """Exportar reporte a Excel"""
        import xlwt
        from xlwt import XFStyle, easyxf
        
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="cumpleaños.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Cumpleaños')
        
        # Estilos
        header_style = easyxf(
            'font: bold on; align: horiz center; pattern: pattern solid, fore_color light_blue'
        )
        date_style = easyxf(num_format_str='DD/MM/YYYY')
        hoy_style = easyxf('font: bold on; pattern: pattern solid, fore_color yellow')
        
        # Encabezados
        headers = ['Tipo', 'Nombre', 'Fecha Nacimiento', 'Edad', 'Días Restantes', 
                  'Signo', 'Grado/Año', 'Contacto', 'Observaciones']
        
        for col, header in enumerate(headers):
            ws.write(0, col, header, header_style)
        
        # Obtener datos (simplificado para exportación)
        datos = self.get_export_data(request)
        
        # Escribir datos
        row = 1
        for persona in datos:
            # Determinar estilo si cumple hoy
            estilo = hoy_style if persona.get('hoy_cumple', False) else None
            
            ws.write(row, 0, persona['tipo'], estilo)
            ws.write(row, 1, persona['nombre'], estilo)
            
            if persona['fecha_nac']:
                ws.write(row, 2, persona['fecha_nac'], date_style)
            
            ws.write(row, 3, persona['edad'], estilo)
            ws.write(row, 4, persona['dias_restantes'], estilo)
            ws.write(row, 5, persona['signo'], estilo)
            ws.write(row, 6, persona['grado'], estilo)
            ws.write(row, 7, persona['contacto'], estilo)
            ws.write(row, 8, '', estilo)
            
            row += 1
        
        # Ajustar columnas
        for i in range(len(headers)):
            ws.col(i).width = 256 * 15
        
        wb.save(response)
        return response
    
    def get_export_data(self, request):
        """Obtener datos simplificados para exportación"""
        # Reutilizar la lógica de get_context_data pero simplificada
        context = self.get_context_data()
        
        datos_simplificados = []
        hoy = timezone.now().date()
        
        for mes, personas in context['cumpleaños_por_mes'].items():
            for persona in personas:
                datos_simplificados.append({
                    'tipo': persona['tipo'],
                    'nombre': persona['nombre_completo'],
                    'fecha_nac': persona['fecha_nacimiento'],
                    'edad': persona['edad_actual'],
                    'dias_restantes': persona['dias_restantes'],
                    'signo': persona['signo_zodiacal'],
                    'grado': self.get_grado_info(persona),
                    'contacto': persona['contacto'],
                    'hoy_cumple': persona['hoy_cumple'],
                })
        
        return datos_simplificados
    
    def get_grado_info(self, persona):
        """Obtener información del grado/matrícula"""
        if persona['tipo'] == 'Estudiante':
            matricula = persona['matricula_actual']
            if matricula:
                return f"{matricula.grado_año_lectivo.grado.nombre} - {matricula.año_lectivo.anho}"
        return 'N/A'