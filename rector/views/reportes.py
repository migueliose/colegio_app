# rector/views.py
from django.views.generic import TemplateView, ListView, DetailView
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.views import View
from django.db.models import Avg, Count, Sum, Q, F, Window
from django.utils import timezone
from datetime import timedelta, datetime
import json

import pandas as pd
from io import BytesIO
from django.http import HttpResponse
from django.db.models.functions import Rank, Coalesce


# Mixins y modelos
from gestioncolegio.mixins import RoleRequiredMixin
from gestioncolegio.models import AñoLectivo, Sede, ConfiguracionGeneral
from estudiantes.models import Estudiante, Matricula, Nota, Acudiente
from usuarios.models import Docente, Usuario, TipoUsuario
from matricula.models import AsignaturaGradoAñoLectivo, GradoAñoLectivo, PeriodoAcademico, DocenteSede
from academico.models import Grado, NivelEscolar
from comportamiento.models import Comportamiento, Asistencia, Inconsistencia


class ReportesRectorView(RoleRequiredMixin, TemplateView):
    """Vista para generar reportes"""
    template_name = 'rector/reportes/reportes.html'
    allowed_roles = ['Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Años lectivos disponibles
        context['años_lectivos'] = AñoLectivo.objects.all().order_by('-anho')
        
        # Sedes disponibles
        context['sedes'] = Sede.objects.filter(estado=True)
        
        # Grados y niveles disponibles
        context['grados'] = Grado.objects.select_related('nivel_escolar').all()
        context['niveles'] = NivelEscolar.objects.all().order_by('id')

        # Año actual: se usa cuando el filtro de año está en "Año actual"
        context['año_actual'] = AñoLectivo.objects.filter(estado=True).first()
        
        # Tipos de reporte
        context['tipos_reporte'] = [
            {'id': 'academico', 'nombre': 'Académico', 'icono': 'bi-journal-text'},
            {'id': 'asistencia', 'nombre': 'Asistencia', 'icono': 'bi-calendar-check'},
            {'id': 'comportamiento', 'nombre': 'Comportamiento', 'icono': 'bi-people'},
            {'id': 'matriculas', 'nombre': 'Matrículas', 'icono': 'bi-clipboard-data'},
            {'id': 'docentes', 'nombre': 'Docentes', 'icono': 'bi-person-badge'},
        ]
        
        return context
    
#=================== Documentación individual - por estudiantes ================================= 

class DocumentosEstudianteView(RoleRequiredMixin, TemplateView):
    template_name = 'rector/reportes/documentos_estudiante.html'
    allowed_roles = ['Administrador', 'Rector', 'Rector(a)', 'Docente', 'Acudiente']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante = get_object_or_404(Estudiante, id=self.kwargs.get('estudiante_id'))

        # Un acudiente solo puede ver los documentos de sus estudiantes
        user = self.request.user
        if (not user.is_superuser and user.tipo_usuario and user.tipo_usuario.nombre == 'Acudiente'
                and not estudiante.acudientes.filter(acudiente=user).exists()):
            raise PermissionDenied("No tiene permisos para ver los documentos de este estudiante")

        context['estudiante'] = estudiante

        # Año lectivo actual
        config = ConfiguracionGeneral.objects.first()
        año_lectivo_actual = config.año_lectivo_actual if config else None
        if not año_lectivo_actual:
            año_lectivo_actual = AñoLectivo.objects.filter(estado=True).first()

        # Años cursados: se toman de las matrículas del estudiante (no por el número
        # del año, porque cada sede tiene su propio año lectivo)
        matriculas = estudiante.matriculas.filter(
            estado__in=['ACT', 'INA', 'RET'],
            is_deleted=False,
        ).select_related(
            'año_lectivo', 'grado_año_lectivo__grado', 'sede'
        ).order_by('-año_lectivo__anho')

        matricula_activa = None
        años_anteriores = []
        for matricula in matriculas:
            if año_lectivo_actual and matricula.año_lectivo_id == año_lectivo_actual.id:
                matricula_activa = matricula
            else:
                años_anteriores.append({
                    'año_lectivo': matricula.año_lectivo,
                    'matricula': matricula,
                    'grado': matricula.grado_año_lectivo.grado.nombre if matricula.grado_año_lectivo else '',
                })

        context.update({
            'año_lectivo_actual': año_lectivo_actual,
            'matricula_activa': matricula_activa,
            'años_anteriores': años_anteriores,
            'total_años': len(matriculas),
            'matricula_actual': matricula_activa,
        })

        return context

class RedirigirConstanciaPDFView(RoleRequiredMixin, View):
    """Redirige a la vista de constancia PDF de estudiantes"""
    allowed_roles = ['Administrador', 'Rector', 'Rector(a)', 'Docente', 'Acudiente']
    
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
    allowed_roles = ['Administrador', 'Rector', 'Rector(a)', 'Docente', 'Acudiente']
    
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
    allowed_roles = ['Administrador', 'Rector', 'Rector(a)', 'Docente', 'Acudiente']
    
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

# ================== FIN Documentación individual - por estudiantes ==============================
class ReporteEstudiantesExcelView(RoleRequiredMixin, View):
    """Reporte Excel de datos personales de estudiantes"""
    allowed_roles = ['Rector']
    
    def get(self, request):
        # Parámetros de filtro
        año_id = request.GET.get('año_id')
        sede_id = request.GET.get('sede_id')
        grado_id = request.GET.get('grado_id')
        nivel_id = request.GET.get('nivel_id')
        
        # Filtrar estudiantes matriculados
        matriculas = Matricula.objects.select_related(
            'estudiante__usuario',
            'año_lectivo',
            'sede',
            'grado_año_lectivo__grado__nivel_escolar'
        ).filter(estado='ACT')
        
        if año_id and año_id != 'todos':
            matriculas = matriculas.filter(año_lectivo_id=año_id)
        
        if sede_id and sede_id != 'todas':
            matriculas = matriculas.filter(sede_id=sede_id)
        
        if grado_id and grado_id != 'todos':
            matriculas = matriculas.filter(grado_año_lectivo_id=grado_id)
        
        if nivel_id and nivel_id != 'todos':
            matriculas = matriculas.filter(grado_año_lectivo__grado__nivel_escolar_id=nivel_id)
        
        # Crear DataFrame
        data = []
        for matricula in matriculas:
            estudiante = matricula.estudiante
            usuario = estudiante.usuario
            
            # Obtener acudientes
            acudientes = Acudiente.objects.filter(estudiante=estudiante)
            acudientes_info = "\n".join([f"{ac.acudiente.get_full_name()} ({ac.parentesco})" 
                                         for ac in acudientes[:2]])  # Máximo 2 acudientes
            
            row = {
                'CÓDIGO MATRÍCULA': matricula.codigo_matricula,
                'DOCUMENTO': usuario.numero_documento,
                'TIPO DOCUMENTO': usuario.tipo_documento.nombre if usuario.tipo_documento else '',
                'NOMBRES': usuario.nombres,
                'APELLIDOS': usuario.apellidos,
                'NOMBRE COMPLETO': usuario.get_full_name(),
                'FECHA NACIMIENTO': usuario.fecha_nacimiento.strftime('%d/%m/%Y') if usuario.fecha_nacimiento else '',
                'EDAD': usuario.edad,
                'SEXO': usuario.get_sexo_display() if usuario.sexo else '',
                'DIRECCIÓN': usuario.direccion or '',
                'TELÉFONO': usuario.telefono or '',
                'EMAIL': usuario.email or '',
                'SEDE': matricula.sede.nombre,
                'AÑO LECTIVO': matricula.año_lectivo.anho,
                'GRADO': matricula.grado_año_lectivo.grado.nombre,
                'NIVEL': matricula.grado_año_lectivo.grado.nivel_escolar.nombre,
                'FECHA MATRÍCULA': matricula.fecha_matricula.strftime('%d/%m/%Y'),
                'ESTADO MATRÍCULA': matricula.get_estado_display(),
                'ACUDIENTES': acudientes_info,
                'ESTADO ESTUDIANTE': 'Activo' if estudiante.estado else 'Inactivo',
                'FECHA CREACIÓN': estudiante.created_at.strftime('%d/%m/%Y %H:%M'),
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # Crear archivo Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Estudiantes', index=False)
            worksheet = writer.sheets['Estudiantes']
            
            # Ajustar ancho de columnas
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Configurar respuesta
        fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=reporte_estudiantes_{fecha}.xlsx'
        
        return response

class ReporteDocentesExcelView(RoleRequiredMixin, View):
    """Reporte Excel de docentes con asignaturas y grados asignados"""
    allowed_roles = ['Rector']
    
    def get(self, request):
        # Parámetros de filtro
        año_id = request.GET.get('año_id')
        sede_id = request.GET.get('sede_id')
        
        # Obtener docentes
        docentes = Docente.objects.filter(estado=True).select_related('usuario')
        
        # Filtrar por sede si se especifica
        if sede_id and sede_id != 'todas':
            docentes = docentes.filter(sedes_asignadas__sede_id=sede_id)
        
        # Filtrar por año si se especifica
        if año_id and año_id != 'todos':
            docentes = docentes.filter(
                sedes_asignadas__año_lectivo_id=año_id,
                asignaturas_dictadas__grado_año_lectivo__año_lectivo_id=año_id
            ).distinct()
        
        # Crear DataFrame
        data = []
        for docente in docentes:
            usuario = docente.usuario
            
            # Obtener asignaturas asignadas en el año actual o filtrado
            asignaturas_query = AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente
            ).select_related(
                'asignatura',
                'grado_año_lectivo__grado',
                'sede'
            )
            
            if año_id and año_id != 'todos':
                asignaturas_query = asignaturas_query.filter(
                    grado_año_lectivo__año_lectivo_id=año_id
                )
            
            asignaturas_info = []
            for asignatura in asignaturas_query:
                info = f"{asignatura.asignatura.nombre} ({asignatura.grado_año_lectivo.grado.nombre} - {asignatura.sede.nombre})"
                asignaturas_info.append(info)
            
            # Obtener sedes asignadas
            sedes_query = DocenteSede.objects.filter(
                docente=docente,
                estado=True
            ).select_related('sede', 'año_lectivo')
            
            if año_id and año_id != 'todos':
                sedes_query = sedes_query.filter(año_lectivo_id=año_id)
            
            sedes_info = []
            for sede_asignada in sedes_query:
                info = f"{sede_asignada.sede.nombre} ({sede_asignada.año_lectivo.anho})"
                sedes_info.append(info)
            
            row = {
                'DOCUMENTO': usuario.numero_documento,
                'NOMBRES': usuario.nombres,
                'APELLIDOS': usuario.apellidos,
                'NOMBRE COMPLETO': usuario.get_full_name(),
                'EMAIL': usuario.email or '',
                'TELÉFONO': usuario.telefono or '',
                'ESTADO': 'Activo' if docente.estado else 'Inactivo',
                'FECHA NACIMIENTO': usuario.fecha_nacimiento.strftime('%d/%m/%Y') if usuario.fecha_nacimiento else '',
                'EDAD': usuario.edad,
                'SEXO': usuario.get_sexo_display() if usuario.sexo else '',
                'TOTAL ASIGNATURAS': len(asignaturas_info),
                'ASIGNATURAS ASIGNADAS': "\n".join(asignaturas_info) if asignaturas_info else 'Sin asignaturas',
                'SEDES ASIGNADAS': "\n".join(sedes_info) if sedes_info else 'Sin sedes asignadas',
                'FECHA CREACIÓN': docente.created_at.strftime('%d/%m/%Y %H:%M'),
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # Crear archivo Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Docentes', index=False)
            worksheet = writer.sheets['Docentes']
            
            # Ajustar ancho de columnas
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=reporte_docentes_{fecha}.xlsx'
        
        return response

class ReportePromediosExcelView(RoleRequiredMixin, View):
    """Reporte Excel de promedios generales por periodo de cada estudiante"""
    allowed_roles = ['Rector']
    
    def get(self, request):
        # Parámetros de filtro
        año_id = request.GET.get('año_id')
        sede_id = request.GET.get('sede_id')
        periodo_id = request.GET.get('periodo_id')
        
        if not año_id or año_id == 'todos':
            año_actual = AñoLectivo.objects.filter(estado=True).first()
            if año_actual:
                año_id = año_actual.id
            else:
                return HttpResponse("No hay año lectivo activo", status=400)
        
        # Obtener período
        if periodo_id and periodo_id != 'todos':
            periodo = PeriodoAcademico.objects.get(id=periodo_id)
            periodos = [periodo]
        else:
            periodos = PeriodoAcademico.objects.filter(año_lectivo_id=año_id)
        
        # Obtener estudiantes matriculados
        matriculas = Matricula.objects.filter(
            año_lectivo_id=año_id,
            estado='ACT'
        ).select_related('estudiante__usuario', 'grado_año_lectivo__grado', 'sede')
        
        if sede_id and sede_id != 'todas':
            matriculas = matriculas.filter(sede_id=sede_id)
        
        # Crear DataFrame para cada período
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for periodo in periodos:
                data = []
                
                for matricula in matriculas:
                    estudiante = matricula.estudiante
                    
                    # Obtener todas las notas del estudiante en el período
                    notas = Nota.objects.filter(
                        estudiante=estudiante,
                        periodo_academico=periodo,
                        asignatura_grado_año_lectivo__grado_año_lectivo__año_lectivo_id=año_id
                    ).select_related('asignatura_grado_año_lectivo__asignatura')
                    
                    # Calcular promedio (tomar 0 si no tiene nota)
                    if notas.exists():
                        promedio = notas.aggregate(avg=Avg('calificacion'))['avg']
                        if promedio is None:
                            promedio = 0.0
                    else:
                        promedio = 0.0
                    
                    # Contar asignaturas con y sin nota
                    asignaturas_grado = AsignaturaGradoAñoLectivo.objects.filter(
                        grado_año_lectivo=matricula.grado_año_lectivo
                    )
                    total_asignaturas = asignaturas_grado.count()
                    asignaturas_con_nota = notas.count()
                    asignaturas_sin_nota = total_asignaturas - asignaturas_con_nota
                    
                    row = {
                        'DOCUMENTO': estudiante.usuario.numero_documento,
                        'ESTUDIANTE': estudiante.usuario.get_full_name(),
                        'GRADO': matricula.grado_año_lectivo.grado.nombre,
                        'SEDE': matricula.sede.nombre,
                        'PERIODO': periodo.periodo.nombre,
                        'PROMEDIO GENERAL': round(promedio, 2),
                        'ASIGNATURAS TOTALES': total_asignaturas,
                        'ASIGNATURAS CON NOTA': asignaturas_con_nota,
                        'ASIGNATURAS SIN NOTA': asignaturas_sin_nota,
                        'PORCENTAJE COMPLETADO': round((asignaturas_con_nota / total_asignaturas * 100) if total_asignaturas > 0 else 0, 1),
                        'ESTADO': 'Completo' if asignaturas_con_nota == total_asignaturas else 'Incompleto',
                    }
                    data.append(row)
                
                # Crear DataFrame y ordenar por promedio descendente
                if data:
                    df = pd.DataFrame(data)
                    df = df.sort_values('PROMEDIO GENERAL', ascending=False)
                    
                    # Agregar ranking
                    df['PUESTO'] = range(1, len(df) + 1)
                    
                    # Guardar en hoja del período
                    sheet_name = f"Periodo_{periodo.periodo.nombre}"
                    if len(sheet_name) > 31:  # Excel limita a 31 caracteres
                        sheet_name = sheet_name[:31]
                    
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # Ajustar ancho de columnas
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=reporte_promedios_{fecha}.xlsx'
        
        return response

class ReportePuestosExcelView(RoleRequiredMixin, View):
    """Reporte Excel de primeros, segundos y terceros puestos por grado"""
    allowed_roles = ['Rector']
    
    def get(self, request):
        # Parámetros de filtro
        año_id = request.GET.get('año_id')
        sede_id = request.GET.get('sede_id')
        periodo_id = request.GET.get('periodo_id')
        
        if not año_id or año_id == 'todos':
            año_actual = AñoLectivo.objects.filter(estado=True).first()
            if año_actual:
                año_id = año_actual.id
            else:
                return HttpResponse("No hay año lectivo activo", status=400)
        
        # Obtener período
        if periodo_id and periodo_id != 'todos':
            periodos = [PeriodoAcademico.objects.get(id=periodo_id)]
        else:
            periodos = PeriodoAcademico.objects.filter(año_lectivo_id=año_id)
        
        # Crear DataFrame para cada período
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for periodo in periodos:
                data = []
                
                # Obtener todos los grados del año
                grados = GradoAñoLectivo.objects.filter(
                    año_lectivo_id=año_id,
                    estado=True
                ).select_related('grado')
                
                for grado_año in grados:
                    # Obtener estudiantes del grado
                    matriculas = Matricula.objects.filter(
                        grado_año_lectivo=grado_año,
                        estado='ACT'
                    ).select_related('estudiante__usuario', 'sede')
                    
                    if sede_id and sede_id != 'todas':
                        matriculas = matriculas.filter(sede_id=sede_id)
                    
                    # Calcular promedios por estudiante
                    estudiantes_con_promedio = []
                    for matricula in matriculas:
                        estudiante = matricula.estudiante
                        
                        notas = Nota.objects.filter(
                            estudiante=estudiante,
                            periodo_academico=periodo,
                            asignatura_grado_año_lectivo__grado_año_lectivo=grado_año
                        )
                        
                        if notas.exists():
                            promedio = notas.aggregate(avg=Avg('calificacion'))['avg']
                            if promedio is not None:
                                estudiantes_con_promedio.append({
                                    'estudiante': estudiante,
                                    'promedio': promedio,
                                    'matricula': matricula,
                                    'notas_count': notas.count()
                                })
                    
                    # Ordenar por promedio descendente
                    estudiantes_con_promedio.sort(key=lambda x: x['promedio'], reverse=True)
                    
                    # Tomar primeros 3 puestos
                    for puesto, estudiante_data in enumerate(estudiantes_con_promedio[:3], 1):
                        estudiante = estudiante_data['estudiante']
                        matricula = estudiante_data['matricula']
                        
                        row = {
                            'PUESTO': f'{puesto}° Puesto',
                            'GRADO': grado_año.grado.nombre,
                            'NIVEL': grado_año.grado.nivel_escolar.nombre,
                            'DOCUMENTO': estudiante.usuario.numero_documento,
                            'ESTUDIANTE': estudiante.usuario.get_full_name(),
                            'PROMEDIO': round(estudiante_data['promedio'], 2),
                            'SEDE': matricula.sede.nombre,
                            'PERIODO': periodo.periodo.nombre,
                            'AÑO LECTIVO': grado_año.año_lectivo.anho,
                            'TOTAL ASIGNATURAS': estudiante_data['notas_count'],
                        }
                        data.append(row)
                
                if data:
                    df = pd.DataFrame(data)
                    
                    # Guardar en hoja del período
                    sheet_name = f"Puestos_{periodo.periodo.nombre}"
                    if len(sheet_name) > 31:
                        sheet_name = sheet_name[:31]
                    
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # Ajustar ancho de columnas
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=reporte_puestos_{fecha}.xlsx'
        
        return response

class ReporteMejores10ExcelView(RoleRequiredMixin, View):
    """
    Excel con los 10 mejores estudiantes.
    Filtros (GET): año_id, sede_id, nivel_id (Preescolar / Primaria / todos),
    grado_id y periodo_id.
    - Con un período: ranking por el promedio de ese período.
    - Con "todos": hoja "General" con el promedio de todos los períodos
      calificados del año, y una hoja por cada período.
    Los empates comparten puesto.
    """
    allowed_roles = ['Rector', 'Rector(a)']
    TOP = 10

    def get(self, request):
        año_id = request.GET.get('año_id')
        sede_id = request.GET.get('sede_id')
        nivel_id = request.GET.get('nivel_id')
        grado_id = request.GET.get('grado_id')
        periodo_id = request.GET.get('periodo_id')

        if año_id and año_id != 'todos':
            año = get_object_or_404(AñoLectivo, id=año_id)
        else:
            año = AñoLectivo.objects.filter(estado=True).first()
            if not año:
                return HttpResponse("No hay año lectivo activo", status=400)

        periodos = list(PeriodoAcademico.objects.filter(
            año_lectivo=año
        ).select_related('periodo').order_by('fecha_inicio'))
        periodo_sel = None
        if periodo_id and periodo_id != 'todos':
            periodo_sel = get_object_or_404(PeriodoAcademico, id=periodo_id, año_lectivo=año)

        # Estudiantes con matrícula activa según los filtros
        matriculas = Matricula.objects.filter(
            año_lectivo=año, estado='ACT'
        ).select_related(
            'estudiante__usuario', 'grado_año_lectivo__grado__nivel_escolar', 'sede'
        )
        if sede_id and sede_id != 'todas':
            matriculas = matriculas.filter(sede_id=sede_id)
        if nivel_id and nivel_id != 'todos':
            matriculas = matriculas.filter(grado_año_lectivo__grado__nivel_escolar_id=nivel_id)
        if grado_id and grado_id != 'todos':
            matriculas = matriculas.filter(grado_año_lectivo__grado_id=grado_id)
        matriculas = {m.estudiante_id: m for m in matriculas}

        # Promedio y cantidad de notas por estudiante y período (una sola consulta)
        promedios = {}  # {estudiante_id: {periodo_id: (promedio, cantidad)}}
        filas = Nota.objects.filter(
            estudiante_id__in=matriculas.keys(),
            periodo_academico__in=[periodo_sel] if periodo_sel else periodos,
        ).values('estudiante_id', 'periodo_academico_id').annotate(
            promedio=Avg('calificacion'), cantidad=Count('id')
        )
        for fila in filas:
            if fila['promedio'] is not None:
                promedios.setdefault(fila['estudiante_id'], {})[fila['periodo_academico_id']] = (
                    float(fila['promedio']), fila['cantidad']
                )

        filtros_texto = self._describir_filtros(año, sede_id, nivel_id, grado_id, periodo_sel)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if periodo_sel:
                hojas = [(f"Top10_{periodo_sel.periodo.nombre}", periodo_sel.periodo.nombre, [periodo_sel])]
            else:
                hojas = [("Top10_General", "General (promedio de los períodos calificados)", periodos)]
                hojas += [(f"Top10_{p.periodo.nombre}", p.periodo.nombre, [p]) for p in periodos]

            for nombre_hoja, titulo_periodo, periodos_hoja in hojas:
                ranking = self._ranking(matriculas, promedios, periodos_hoja)
                general = len(periodos_hoja) > 1
                filas_excel = []
                for item in ranking:
                    m = item['matricula']
                    usuario = m.estudiante.usuario
                    fila = {
                        'PUESTO': item['puesto'],
                        'DOCUMENTO': usuario.numero_documento,
                        'ESTUDIANTE': usuario.get_full_name(),
                        'EDAD': usuario.edad,
                        'SEXO': usuario.get_sexo_display() if usuario.sexo else '',
                        'GRADO': m.grado_año_lectivo.grado.nombre,
                        'NIVEL': m.grado_año_lectivo.grado.nivel_escolar.nombre,
                        'SEDE': m.sede.nombre,
                    }
                    if general:
                        for p in periodos_hoja:
                            dato = promedios.get(m.estudiante_id, {}).get(p.id)
                            fila[f'PROM. {p.periodo.nombre.upper()}'] = round(dato[0], 2) if dato else None
                        fila['PERÍODOS CALIFICADOS'] = item['periodos']
                        fila['PROMEDIO GENERAL'] = round(item['promedio'], 2)
                    else:
                        fila['PROMEDIO'] = round(item['promedio'], 2)
                        fila['NOTAS REGISTRADAS'] = item['cantidad']
                    filas_excel.append(fila)

                self._escribir_hoja(writer, nombre_hoja[:31], titulo_periodo, filtros_texto, filas_excel)

        output.seek(0)
        partes = ['top10']
        if nivel_id and nivel_id != 'todos':
            nivel = NivelEscolar.objects.filter(id=nivel_id).first()
            partes.append(nivel.nombre.lower() if nivel else 'nivel')
        partes.append(periodo_sel.periodo.nombre.lower() if periodo_sel else 'general')
        partes.append(datetime.now().strftime('%Y%m%d_%H%M'))
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename={"_".join(partes)}.xlsx'
        return response

    def _ranking(self, matriculas, promedios, periodos_hoja):
        """
        Top 10 por promedio. Con varios períodos se promedian los períodos ya
        calificados, y solo entran los estudiantes con notas en todos ellos
        (así nadie queda arriba por tener nota en un solo período).
        """
        calificados = {p.id for p in periodos_hoja
                       if any(p.id in datos for datos in promedios.values())}
        candidatos = []
        for estudiante_id, matricula in matriculas.items():
            datos = [promedios[estudiante_id][p.id] for p in periodos_hoja
                     if p.id in promedios.get(estudiante_id, {})]
            if not datos or len(datos) < len(calificados):
                continue
            promedio = sum(d[0] for d in datos) / len(datos)
            candidatos.append({
                'matricula': matricula,
                'promedio': promedio,
                'periodos': len(datos),
                'cantidad': sum(d[1] for d in datos),
            })

        candidatos.sort(key=lambda x: (-round(x['promedio'], 2), x['matricula'].estudiante.usuario.get_full_name()))

        # Empates comparten puesto (1, 2, 2, 4...); se incluyen todos los empatados en el puesto 10
        ranking = []
        for posicion, item in enumerate(candidatos, 1):
            if ranking and round(item['promedio'], 2) == round(ranking[-1]['promedio'], 2):
                item['puesto'] = ranking[-1]['puesto']
            else:
                item['puesto'] = posicion
            if item['puesto'] > self.TOP:
                break
            ranking.append(item)
        return ranking

    def _describir_filtros(self, año, sede_id, nivel_id, grado_id, periodo_sel):
        sede = Sede.objects.filter(id=sede_id).first() if sede_id and sede_id != 'todas' else None
        nivel = NivelEscolar.objects.filter(id=nivel_id).first() if nivel_id and nivel_id != 'todos' else None
        grado = Grado.objects.filter(id=grado_id).first() if grado_id and grado_id != 'todos' else None
        return (
            f"Año lectivo: {año.anho}  |  Sede: {sede.nombre if sede else 'Todas'}  |  "
            f"Nivel: {nivel.nombre if nivel else 'Todos (general)'}  |  "
            f"Grado: {grado.nombre if grado else 'Todos'}  |  "
            f"Período: {periodo_sel.periodo.nombre if periodo_sel else 'Todos'}"
        )

    def _escribir_hoja(self, writer, nombre_hoja, titulo_periodo, filtros_texto, filas):
        """Escribe título, filtros aplicados y la tabla (o un aviso si no hay datos)."""
        from openpyxl.styles import Font
        inicio = 4
        if filas:
            pd.DataFrame(filas).to_excel(writer, sheet_name=nombre_hoja, index=False, startrow=inicio)
        else:
            pd.DataFrame({'AVISO': ['No hay estudiantes con notas para estos filtros.']}).to_excel(
                writer, sheet_name=nombre_hoja, index=False, startrow=inicio)

        ws = writer.sheets[nombre_hoja]
        ws['A1'] = f"TOP 10 - {titulo_periodo}"
        ws['A1'].font = Font(bold=True, size=14)
        ws['A2'] = filtros_texto
        ws['A3'] = f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ws['A3'].font = Font(italic=True, color='666666')
        for celda in ws[inicio + 1]:
            celda.font = Font(bold=True)

        # Ancho de columnas según el contenido de la tabla
        for column in ws.iter_cols(min_row=inicio + 1):
            largo = max((len(str(c.value)) for c in column if c.value is not None), default=0)
            ws.column_dimensions[column[0].column_letter].width = min(largo + 2, 50)

class ReporteAsistenciasExcelView(RoleRequiredMixin, View):
    """Reporte Excel de asistencias e inasistencias"""
    allowed_roles = ['Rector']
    
    def get(self, request):
        # Parámetros de filtro
        año_id = request.GET.get('año_id')
        sede_id = request.GET.get('sede_id')
        grado_id = request.GET.get('grado_id')
        fecha_inicio = request.GET.get('fecha_inicio')
        fecha_fin = request.GET.get('fecha_fin')
        
        if not año_id or año_id == 'todos':
            año_actual = AñoLectivo.objects.filter(estado=True).first()
            if año_actual:
                año_id = año_actual.id
            else:
                return HttpResponse("No hay año lectivo activo", status=400)
        
        # Construir filtros
        filtros_asistencias = {
            'periodo_academico__año_lectivo_id': año_id
        }
        
        if sede_id and sede_id != 'todas':
            filtros_asistencias['estudiante__matriculas__sede_id'] = sede_id
        
        if grado_id and grado_id != 'todos':
            filtros_asistencias['estudiante__matriculas__grado_año_lectivo_id'] = grado_id
        
        if fecha_inicio:
            filtros_asistencias['fecha__gte'] = fecha_inicio
        
        if fecha_fin:
            filtros_asistencias['fecha__lte'] = fecha_fin
        
        # Obtener asistencias
        asistencias = Asistencia.objects.filter(**filtros_asistencias).select_related(
            'estudiante__usuario',
            'periodo_academico__periodo'
        ).distinct()
        
        # Agrupar por estudiante
        estudiantes_data = {}
        for asistencia in asistencias:
            estudiante_id = asistencia.estudiante_id
            if estudiante_id not in estudiantes_data:
                estudiantes_data[estudiante_id] = {
                    'estudiante': asistencia.estudiante,
                    'asistencias': 0,
                    'faltas': 0,
                    'justificadas': 0,
                    'total': 0
                }
            
            estudiantes_data[estudiante_id]['total'] += 1
            if asistencia.estado == 'A':
                estudiantes_data[estudiante_id]['asistencias'] += 1
            elif asistencia.estado == 'F':
                estudiantes_data[estudiante_id]['faltas'] += 1
            elif asistencia.estado == 'J':
                estudiantes_data[estudiante_id]['justificadas'] += 1
        
        # Crear DataFrame
        data = []
        for estudiante_id, stats in estudiantes_data.items():
            estudiante = stats['estudiante']
            
            # Obtener matrícula actual
            matricula = estudiante.matricula_actual
            
            if matricula:
                porcentaje_asistencia = (stats['asistencias'] / stats['total'] * 100) if stats['total'] > 0 else 0
                
                row = {
                    'DOCUMENTO': estudiante.usuario.numero_documento,
                    'ESTUDIANTE': estudiante.usuario.get_full_name(),
                    'GRADO': matricula.grado_año_lectivo.grado.nombre,
                    'SEDE': matricula.sede.nombre,
                    'TOTAL REGISTROS': stats['total'],
                    'ASISTENCIAS': stats['asistencias'],
                    'FALTAS': stats['faltas'],
                    'FALTAS JUSTIFICADAS': stats['justificadas'],
                    'PORCENTAJE ASISTENCIA': f"{round(porcentaje_asistencia, 2)}%",
                    'ESTADO ASISTENCIA': 'Aceptable' if porcentaje_asistencia >= 80 else 'Bajo',
                    'AÑO LECTIVO': matricula.año_lectivo.anho,
                }
                data.append(row)
        
        df = pd.DataFrame(data)
        
        # Ordenar por porcentaje de asistencia ascendente (peores primeros)
        if not df.empty:
            df['PORCENTAJE_NUM'] = df['PORCENTAJE ASISTENCIA'].str.replace('%', '').astype(float)
            df = df.sort_values('PORCENTAJE_NUM', ascending=True)
            df = df.drop(columns=['PORCENTAJE_NUM'])
        
        # Crear archivo Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Asistencias', index=False)
            worksheet = writer.sheets['Asistencias']
            
            # Ajustar ancho de columnas
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=reporte_asistencias_{fecha}.xlsx'
        
        return response

class ReporteComportamientoExcelView(RoleRequiredMixin, View):
    """Reporte Excel de comportamiento positivo y negativo"""
    allowed_roles = ['Rector']
    
    def get(self, request):
        # Parámetros de filtro
        año_id = request.GET.get('año_id')
        sede_id = request.GET.get('sede_id')
        grado_id = request.GET.get('grado_id')
        fecha_inicio = request.GET.get('fecha_inicio')
        fecha_fin = request.GET.get('fecha_fin')
        
        if not año_id or año_id == 'todos':
            año_actual = AñoLectivo.objects.filter(estado=True).first()
            if año_actual:
                año_id = año_actual.id
            else:
                return HttpResponse("No hay año lectivo activo", status=400)
        
        # Construir filtros
        filtros_comportamiento = {
            'periodo_academico__año_lectivo_id': año_id
        }
        
        if sede_id and sede_id != 'todas':
            filtros_comportamiento['estudiante__matriculas__sede_id'] = sede_id
        
        if grado_id and grado_id != 'todos':
            filtros_comportamiento['estudiante__matriculas__grado_año_lectivo_id'] = grado_id
        
        if fecha_inicio:
            filtros_comportamiento['fecha__gte'] = fecha_inicio
        
        if fecha_fin:
            filtros_comportamiento['fecha__lte'] = fecha_fin
        
        # Obtener comportamientos
        comportamientos = Comportamiento.objects.filter(**filtros_comportamiento).select_related(
            'estudiante__usuario',
            'periodo_academico__periodo',
            'docente__usuario'
        ).distinct()
        
        # Agrupar por estudiante
        estudiantes_data = {}
        for comportamiento in comportamientos:
            estudiante_id = comportamiento.estudiante_id
            if estudiante_id not in estudiantes_data:
                estudiantes_data[estudiante_id] = {
                    'estudiante': comportamiento.estudiante,
                    'positivos': 0,
                    'negativos': 0,
                    'total': 0,
                    'categorias': {},
                    'ultima_fecha': None
                }
            
            estudiantes_data[estudiante_id]['total'] += 1
            if comportamiento.tipo == 'Positivo':
                estudiantes_data[estudiante_id]['positivos'] += 1
            else:
                estudiantes_data[estudiante_id]['negativos'] += 1
            
            # Contar por categoría
            categoria = comportamiento.categoria
            if categoria not in estudiantes_data[estudiante_id]['categorias']:
                estudiantes_data[estudiante_id]['categorias'][categoria] = {'positivos': 0, 'negativos': 0}
            
            if comportamiento.tipo == 'Positivo':
                estudiantes_data[estudiante_id]['categorias'][categoria]['positivos'] += 1
            else:
                estudiantes_data[estudiante_id]['categorias'][categoria]['negativos'] += 1
            
            # Guardar última fecha
            if not estudiantes_data[estudiante_id]['ultima_fecha'] or comportamiento.fecha > estudiantes_data[estudiante_id]['ultima_fecha']:
                estudiantes_data[estudiante_id]['ultima_fecha'] = comportamiento.fecha
        
        # Crear DataFrame
        data = []
        for estudiante_id, stats in estudiantes_data.items():
            estudiante = stats['estudiante']
            
            # Obtener matrícula actual
            matricula = estudiante.matricula_actual
            
            if matricula:
                # Preparar resumen de categorías
                categorias_resumen = []
                for categoria, cat_stats in stats['categorias'].items():
                    resumen = f"{categoria}: +{cat_stats['positivos']}/-{cat_stats['negativos']}"
                    categorias_resumen.append(resumen)
                
                balance = stats['positivos'] - stats['negativos']
                
                row = {
                    'DOCUMENTO': estudiante.usuario.numero_documento,
                    'ESTUDIANTE': estudiante.usuario.get_full_name(),
                    'GRADO': matricula.grado_año_lectivo.grado.nombre,
                    'SEDE': matricula.sede.nombre,
                    'TOTAL REGISTROS': stats['total'],
                    'COMPORTAMIENTOS POSITIVOS': stats['positivos'],
                    'COMPORTAMIENTOS NEGATIVOS': stats['negativos'],
                    'BALANCE': balance,
                    'ESTADO BALANCE': 'Positivo' if balance > 0 else ('Neutral' if balance == 0 else 'Negativo'),
                    'RESUMEN CATEGORÍAS': "\n".join(categorias_resumen[:3]),  # Máximo 3 categorías
                    'ÚLTIMO REGISTRO': stats['ultima_fecha'].strftime('%d/%m/%Y') if stats['ultima_fecha'] else '',
                    'AÑO LECTIVO': matricula.año_lectivo.anho,
                }
                data.append(row)
        
        df = pd.DataFrame(data)
        
        # Ordenar por balance (peores primero)
        if not df.empty:
            df = df.sort_values('BALANCE', ascending=True)
        
        # Crear archivo Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Comportamiento', index=False)
            worksheet = writer.sheets['Comportamiento']
            
            # Ajustar ancho de columnas
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=reporte_comportamiento_{fecha}.xlsx'
        
        return response

class ReporteConsolidadoExcelView(RoleRequiredMixin, View):
    """Reporte Excel consolidado con múltiples hojas"""
    allowed_roles = ['Rector']
    
    def get(self, request):
        # Parámetros de filtro
        año_id = request.GET.get('año_id')
        sede_id = request.GET.get('sede_id')
        
        if not año_id or año_id == 'todos':
            año_actual = AñoLectivo.objects.filter(estado=True).first()
            if año_actual:
                año_id = año_actual.id
            else:
                return HttpResponse("No hay año lectivo activo", status=400)
        
        # Crear archivo Excel con múltiples hojas
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Hoja 1: Resumen General
            self.crear_hoja_resumen(writer, año_id, sede_id)
            
            # Hoja 2: Estudiantes
            self.crear_hoja_estudiantes(writer, año_id, sede_id)
            
            # Hoja 3: Docentes
            self.crear_hoja_docentes(writer, año_id, sede_id)
            
            # Hoja 4: Promedios por Grado
            self.crear_hoja_promedios_grado(writer, año_id, sede_id)
            
            # Hoja 5: Asistencias
            self.crear_hoja_asistencias(writer, año_id, sede_id)
            
            # Hoja 6: Comportamiento
            self.crear_hoja_comportamiento(writer, año_id, sede_id)
        
        output.seek(0)
        
        fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=reporte_consolidado_{fecha}.xlsx'
        
        return response
    
    def crear_hoja_resumen(self, writer, año_id, sede_id):
        """Crear hoja de resumen general"""
        data = []
        
        # Obtener estadísticas
        total_estudiantes = Matricula.objects.filter(
            año_lectivo_id=año_id,
            estado='ACT'
        )
        
        if sede_id and sede_id != 'todas':
            total_estudiantes = total_estudiantes.filter(sede_id=sede_id)
        
        total_estudiantes = total_estudiantes.count()
        
        total_docentes = Docente.objects.filter(estado=True).count()
        
        # Estadísticas por nivel
        niveles = NivelEscolar.objects.all()
        for nivel in niveles:
            estudiantes_nivel = Matricula.objects.filter(
                año_lectivo_id=año_id,
                estado='ACT',
                grado_año_lectivo__grado__nivel_escolar=nivel
            )
            
            if sede_id and sede_id != 'todas':
                estudiantes_nivel = estudiantes_nivel.filter(sede_id=sede_id)
            
            estudiantes_nivel_count = estudiantes_nivel.count()
            
            row = {
                'NIVEL': nivel.nombre,
                'ESTUDIANTES': estudiantes_nivel_count,
                'PORCENTAJE': round((estudiantes_nivel_count / total_estudiantes * 100) if total_estudiantes > 0 else 0, 2),
                'PROMEDIO GENERAL': 'Calcular'  # Aquí podrías calcular el promedio real
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name='Resumen', index=False)
    
    def crear_hoja_estudiantes(self, writer, año_id, sede_id):
        """Crear hoja de estudiantes (versión simplificada)"""
        matriculas = Matricula.objects.filter(
            año_lectivo_id=año_id,
            estado='ACT'
        ).select_related('estudiante__usuario', 'sede', 'grado_año_lectivo__grado')
        
        if sede_id and sede_id != 'todas':
            matriculas = matriculas.filter(sede_id=sede_id)
        
        data = []
        for matricula in matriculas[:100]:  # Limitar a 100 para el ejemplo
            estudiante = matricula.estudiante
            usuario = estudiante.usuario
            
            row = {
                'DOCUMENTO': usuario.numero_documento,
                'ESTUDIANTE': usuario.get_full_name(),
                'GRADO': matricula.grado_año_lectivo.grado.nombre,
                'SEDE': matricula.sede.nombre,
                'ESTADO': 'Activo' if estudiante.estado else 'Inactivo',
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name='Estudiantes', index=False)
    
    def crear_hoja_docentes(self, writer, año_id, sede_id):
        """Crear hoja de docentes (versión simplificada)"""
        docentes = Docente.objects.filter(estado=True).select_related('usuario')
        
        data = []
        for docente in docentes[:50]:  # Limitar a 50 para el ejemplo
            usuario = docente.usuario
            
            row = {
                'DOCUMENTO': usuario.numero_documento,
                'DOCENTE': usuario.get_full_name(),
                'EMAIL': usuario.email or '',
                'TELÉFONO': usuario.telefono or '',
                'ESTADO': 'Activo' if docente.estado else 'Inactivo',
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name='Docentes', index=False)
    
    def crear_hoja_promedios_grado(self, writer, año_id, sede_id):
        """Crear hoja de promedios por grado"""
        grados = GradoAñoLectivo.objects.filter(
            año_lectivo_id=año_id,
            estado=True
        ).select_related('grado')
        
        data = []
        for grado_año in grados:
            # Obtener promedio del grado
            notas = Nota.objects.filter(
                asignatura_grado_año_lectivo__grado_año_lectivo=grado_año
            ).aggregate(promedio=Avg('calificacion'))
            
            promedio = round(notas['promedio'] or 0, 2)
            
            row = {
                'GRADO': grado_año.grado.nombre,
                'NIVEL': grado_año.grado.nivel_escolar.nombre,
                'PROMEDIO GENERAL': promedio,
                'ESTUDIANTES': Matricula.objects.filter(
                    grado_año_lectivo=grado_año,
                    estado='ACT'
                ).count(),
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name='Promedios_Grado', index=False)
    
    def crear_hoja_asistencias(self, writer, año_id, sede_id):
        """Crear hoja de asistencias (versión simplificada)"""
        # Esta es una versión simplificada
        data = [{
            'GRADO': 'Ejemplo',
            'ASISTENCIA PROMEDIO': '85%',
            'ESTUDIANTES CON BAJA ASISTENCIA': 2,
        }]
        
        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name='Asistencias', index=False)
    
    def crear_hoja_comportamiento(self, writer, año_id, sede_id):
        """Crear hoja de comportamiento (versión simplificada)"""
        # Esta es una versión simplificada
        data = [{
            'GRADO': 'Ejemplo',
            'COMPORTAMIENTO POSITIVO': 15,
            'COMPORTAMIENTO NEGATIVO': 3,
            'BALANCE': '+12',
        }]
        
        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name='Comportamiento', index=False)