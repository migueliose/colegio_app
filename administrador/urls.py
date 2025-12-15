from django.urls import path
from . import views

app_name = 'administrador'

urlpatterns = [
     # ========================
     # GESTIÓN ACADÉMICA
     # ========================
     # Grados
     path('gestion-academica/grados/', views.GradoListView.as_view(), name='grado_list'),
     path('gestion-academica/grados/crear/', views.GradoCreateView.as_view(), name='grado_create'),
     path('gestion-academica/grados/<int:pk>/editar/', views.GradoUpdateView.as_view(), name='grado_update'),
     path('gestion-academica/grados/<int:pk>/eliminar/', views.GradoDeleteView.as_view(), name='grado_delete'),

     # Áreas
     path('gestion-academica/areas/', views.AreaListView.as_view(), name='area_list'),
     path('gestion-academica/areas/crear/', views.AreaCreateView.as_view(), name='area_create'),
     path('gestion-academica/areas/<int:pk>/editar/', views.AreaUpdateView.as_view(), name='area_update'),
     path('gestion-academica/areas/<int:pk>/eliminar/', views.AreaDeleteView.as_view(), name='area_delete'),

     # Asignaturas
     path('gestion-academica/asignaturas/', views.AsignaturaListView.as_view(), name='asignatura_list'),
     path('gestion-academica/asignaturas/crear/', views.AsignaturaCreateView.as_view(), name='asignatura_create'),
     path('gestion-academica/asignaturas/<int:pk>/editar/', views.AsignaturaUpdateView.as_view(), name='asignatura_update'),
     path('gestion-academica/asignaturas/<int:pk>/eliminar/', views.AsignaturaDeleteView.as_view(), name='asignatura_delete'),

     # Años Lectivos
     path('gestion-academica/años-lectivos/', views.AñoLectivoListView_Academica.as_view(), name='añolectivo_list'),
     path('gestion-academica/años-lectivos/crear/', views.AñoLectivoCreateView_Academica.as_view(), name='añolectivo_create'),
     path('gestion-academica/años-lectivos/<int:pk>/editar/', views.AñoLectivoUpdateView_Academica.as_view(), name='añolectivo_update'),

     path('gestion-academica/años-lectivos/<int:pk>/eliminar/', views.AñoLectivoDeleteView.as_view(), name='añolectivo_delete'),
     path('gestion-academica/años-lectivos/<int:pk>/activar-desactivar/', views.AñoLectivoActivarDesactivarView.as_view(), name='añolectivo_activar_desactivar'),
     path('gestion-academica/años-lectivos/<int:pk>/cambiar-estado/', views.AñoLectivoActivarDesactivarView.as_view(), name='añolectivo_cambiar_estado'),
     path('gestion-academica/años-lectivos/<int:pk>/periodos/', views.AñoLectivoPeriodosView.as_view(), name='añolectivo_periodos'),

     # Periodos Académicos
     path('gestion-academica/años-lectivos/<int:año_pk>/periodos/crear/', views.PeriodoAcademicoCreateView.as_view(), name='periodo_create'),
     path('gestion-academica/periodos-academicos/<int:pk>/editar/', views.PeriodoAcademicoUpdateView.as_view(), name='periodo_update'),
     path('gestion-academica/periodos-academicos/<int:pk>/eliminar/', views.PeriodoAcademicoDeleteView.as_view(), name='periodo_delete'),
     path('gestion-academica/años-lectivos/<int:pk>/periodos/agregar-multiples/', views.AgregarMultiplesPeriodosView.as_view(), name='periodo_agregar_multiples'),

     # ========================
     # GESTIÓN ACADÉMICA - Grados por Año
     # ========================
    path('gestion-academica/grados-anho/', views.GradoAñoLectivoListView.as_view(), name='grado_anho_list'),
    path('gestion-academica/grados-anho/nuevo/', views.GradoAñoLectivoCreateView.as_view(), name='grado_anho_create'),
    path('gestion-academica/grados-anho/<int:pk>/editar/', views.GradoAñoLectivoUpdateView.as_view(), name='grado_anho_update'),
    path('gestion-academica/grados-anho/<int:pk>/eliminar/', views.GradoAñoLectivoDeleteView.as_view(), name='grado_anho_delete'),

     # ========================
     # GESTIÓN ACADÉMICA - Asignaturas por Grado
     # ========================
    path('gestion-academica/asignaturas-grado/', views.AsignaturaGradoAñoLectivoListView.as_view(), name='asignatura_grado_list'),
    path('gestion-academica/asignaturas-grado/nuevo/', views.AsignaturaGradoAñoLectivoCreateView.as_view(), name='asignatura_grado_create'),
    path('gestion-academica/asignaturas-grado/<int:pk>/editar/', views.AsignaturaGradoAñoLectivoUpdateView.as_view(), name='asignatura_grado_update'),
    path('gestion-academica/asignaturas-grado/<int:pk>/eliminar/', views.AsignaturaGradoAñoLectivoDeleteView.as_view(), name='asignatura_grado_delete'),
         
     path('gestion-academica/asignaturas-grado/masivo/', views.AsignaturaGradoAñoLectivoBulkCreateView.as_view(), name='asignatura_grado_bulk'),
     path('gestion-academica/asignaturas-grado/copiar/', views.AsignaturaGradoAñoLectivoCopyView.as_view(), name='asignatura_grado_copy'),

     # En tu urls.py del administrador
     path('gestion-academica/ajax/', views.GestionAcademicaAjaxView.as_view(), name='gestion_academica_ajax'),
     path('gestion-academica/grado-anho/ajax-info/', views.GestionAcademicaAjaxView.as_view(), name='grado_anho_ajax_info'),
     path('gestion-academica/asignatura/ajax-info/', views.GestionAcademicaAjaxView.as_view(), name='asignatura_ajax_info'),
     path('gestion-academica/asignatura/ajax-stats/',views.GestionAcademicaAjaxView.as_view(), name='asignatura_grado_ajax_stats'),
    
    # ========================
    # GESTIÓN USUARIOS 
    # ========================
    path('gestion-usuarios/', views.GestionUsuariosView.as_view(), name='gestion_usuarios'),

    # Docentes
    path('docentes/', views.DocenteListView.as_view(), name='docente_list'),
    path('docentes/crear/', views.DocenteCreateView.as_view(), name='docente_create'),
    path('docentes/<int:pk>/', views.DocenteDetailView.as_view(), name='docente_detail'),
    path('docentes/<int:pk>/editar/', views.DocenteUpdateView.as_view(), name='docente_update'),
    path('docentes/<int:pk>/eliminar/', views.DocenteDeleteView.as_view(), name='docente_delete'),
   
    # Contactos de docentes
    path('docentes/<int:docente_pk>/contactos/crear/', 
         views.ContactoDocenteCreateView.as_view(), name='contacto_docente_create'),
    path('docentes/contactos/<int:pk>/editar/', 
         views.ContactoDocenteUpdateView.as_view(),name='contacto_docente_update'),
    path('docentes/contactos/<int:pk>/eliminar/', 
         views.ContactoDocenteDeleteView.as_view(),name='contacto_docente_delete'),
    
    # Estudiantes
    path('estudiantes/', views.EstudianteListView.as_view(), name='estudiante_list'),
    path('estudiantes/crear/', views.EstudianteCreateView.as_view(), name='estudiante_create'),
    path('estudiantes/<int:pk>/', views.EstudianteDetailView.as_view(), name='estudiante_detail'),
    path('estudiantes/<int:pk>/editar/', views.EstudianteUpdateView.as_view(), name='estudiante_update'),
    path('estudiantes/<int:pk>/eliminar/', views.EstudianteDeleteView.as_view(), name='estudiante_delete'),
    
    # Documentos de estudiante
    path('estudiantes/<int:estudiante_id>/documentos/', 
         views.DocumentosEstudianteView.as_view(), name='documentos_estudiante'),
    
    # Redirecciones a documentos (mantienen la misma funcionalidad)
    path('estudiantes/<int:estudiante_id>/constancia/<int:año_lectivo_id>/',
         views.RedirigirConstanciaPDFView.as_view(),name='constancia_pdf'),
    
    path('estudiantes/<int:estudiante_id>/observador/<int:año_lectivo_id>/',
         views.RedirigirObservadorPDFView.as_view(),name='observador_pdf'),
    
    path('estudiantes/<int:estudiante_id>/boletin/<int:año_lectivo_id>/',
         views.RedirigirReporteNotasPDFView.as_view(),name='boletin_pdf'),

    # Acudientes
    path('acudientes/', views.AcudienteListView.as_view(), name='acudiente_list'),
    path('acudientes/crear/', views.AcudienteCreateView.as_view(), name='acudiente_create'),
    path('acudientes/<int:pk>/', views.AcudienteDetailView.as_view(), name='acudiente_detail'),
    path('acudientes/<int:pk>/editar/', views.AcudienteUpdateView.as_view(), name='acudiente_update'),
    path('acudientes/<int:pk>/eliminar/', views.AcudienteDeleteView.as_view(), name='acudiente_delete'),
    
    # Administradores/Rectores
    path('administradores/', views.AdministradorListView.as_view(), name='administrador_list'),
    path('administradores/crear/', views.AdministradorCreateView.as_view(), name='administrador_create'),
    path('administradores/<int:pk>/editar/', views.AdministradorUpdateView.as_view(), name='administrador_update'),
    path('administradores/<int:pk>/eliminar/', views.AdministradorDeleteView.as_view(), name='administrador_delete'),
    
    # Ajax Views
    path('ajax/verificar-usuario/', views.VerificarUsuarioView.as_view(), name='verificar_usuario'),
    path('ajax/buscar-usuario/', views.BuscarUsuarioView.as_view(), name='buscar_usuario'),
    path('ajax/buscar-estudiante/', views.BuscarEstudianteView.as_view(), name='buscar_estudiante'),
    path('ajax/estudiante/<int:pk>/status/', views.EstudianteStatusView.as_view(), name='estudiante_status'),
 
    # ========================
    # GESTIÓN DE HORARIOS
    # ========================
    path('horarios/', views.HorarioListView.as_view(), name='horario_list'),
    path('horarios/crear/', views.HorarioCreateView.as_view(), name='horario_create'),
    path('horarios/<int:pk>/editar/', views.HorarioUpdateView.as_view(), name='horario_update'),
    path('horarios/<int:pk>/eliminar/', views.HorarioDeleteView.as_view(), name='horario_delete'),
    path('horarios/eliminar-multiples/', views.HorarioBulkDeleteView.as_view(), name='horario_bulk_delete'),
    
    # Vistas especiales
    path('horarios/calendario/', views.HorarioCalendarioView.as_view(), name='horario_calendario'),
    path('horarios/grado/', views.HorarioGradoView.as_view(), name='horario_grado'),
    path('horarios/grado/<int:grado_id>/', views.HorarioGradoView.as_view(), name='horario_grado_detail'),
    path('horarios/docente/', views.HorarioDocenteView.as_view(), name='horario_docente'),
    path('horarios/docente/<int:docente_id>/', views.HorarioDocenteView.as_view(), name='horario_docente_detail'),
    path('horarios/asignatura/', views.HorarioAsignaturaView.as_view(), name='horario_asignatura'),
    path('horarios/asignatura/<int:asignatura_id>/', views.HorarioAsignaturaView.as_view(), name='horario_asignatura_detail'),
    
    # Generar PDF (opcional)
    path('horarios/pdf/<str:tipo>/', views.HorarioGenerarPDFView.as_view(), name='horario_pdf'),
    path('horarios/pdf/<str:tipo>/<int:id>/', views.HorarioGenerarPDFView.as_view(), name='horario_pdf_detail'),
    
    # Ajax
    path('horarios/ajax/', views.HorarioAjaxView.as_view(), name='horario_ajax'),

    # ========================
    # GESTIÓN DE MATRÍCULAS
    # ========================
    # Lista y filtros
    path('matriculas/', views.MatriculaListView.as_view(), name='matricula_list'),
    
    # Matrículas por estudiante
    path('estudiantes/<int:pk>/matriculas/', views.EstudianteMatriculasView.as_view(), name='estudiante_matriculas'),
    
    # Crear matrícula con año específico
    path('estudiantes/<int:estudiante_id>/matricular/<int:año_lectivo_id>/', views.MatriculaCreateConAñoView.as_view(), name='matricula_create_con_año'),
    
    # CRUD básico
    path('matriculas/nueva/', views.MatriculaCreateView.as_view(), name='matricula_create'),
    path('matriculas/<int:pk>/editar/', views.MatriculaUpdateView.as_view(), name='matricula_update'),
    path('matriculas/<int:pk>/', views.MatriculaDetailView.as_view(), name='matricula_detail'),
    path('matriculas/<int:pk>/eliminar/', views.MatriculaDeleteView.as_view(), name='matricula_delete'),
    
    # Acciones especiales
    path('matriculas/<int:pk>/cambiar-estado/', views.MatriculaChangeStatusView.as_view(), name='matricula_change_status'),
    path('matriculas/masiva/', views.MatriculaBulkCreateView.as_view(), name='matricula_bulk'),
    
    # Reportes y exportaciones
    path('matriculas/reportes/', views.MatriculaReportView.as_view(), name='matricula_reports'),
    path('matriculas/exportar/<str:formato>/', views.MatriculaExportView.as_view(), name='matricula_export'),
    
    # AJAX
    path('matriculas/ajax/', views.MatriculaAjaxView.as_view(), name='matricula_ajax'),
    
    # Acciones desde estudiantes
    path('estudiantes/<int:estudiante_id>/matricular/', views.MatriculaFromEstudianteListView.as_view(), name='matricula_from_estudiante'),

    # ===================== DATOS INSTITUCIONALES =====================
    path('configuracion/colegios/', views.ColegioListView.as_view(), name='colegio_list'),
    path('configuracion/colegios/crear/', views.ColegioCreateView.as_view(), name='colegio_create'),
    path('configuracion/colegios/<int:pk>/editar/', views.ColegioUpdateView.as_view(), name='colegio_update'),
    path('configuracion/colegios/<int:pk>/', views.ColegioDetailView.as_view(), name='colegio_detail'),

    # Sedes
    path('configuracion/sedes/', views.SedeListView.as_view(), name='sede_list'),
    path('configuracion/sedes/crear/', views.SedeCreateView.as_view(), name='sede_create'),
    path('configuracion/sedes/<int:pk>/editar/', views.SedeUpdateView.as_view(), name='sede_update'),

    # Recursos del colegio
    path('configuracion/colegios/<int:colegio_id>/recursos/', views.RecursosColegioUpdateView.as_view(), name='recursos_update'),

    # Años lectivos
    path('configuracion/años-lectivos/', views.AñoLectivoListView.as_view(), name='año_lectivo_list'),
    path('configuracion/años-lectivos/crear/', views.AñoLectivoCreateView.as_view(), name='año_lectivo_create'),
    path('configuracion/años-lectivos/<int:pk>/editar/', views.AñoLectivoUpdateView.as_view(), name='año_lectivo_update'),

    # ===================== AJUSTES DEL SISTEMA =====================
    # Configuración general
    path('configuracion/general/', views.ConfiguracionGeneralUpdateView.as_view(), name='configuracion_general'),

    # Parámetros del sistema
    path('configuracion/parametros/', views.ParametroSistemaListView.as_view(), name='parametro_list'),
    path('configuracion/parametros/crear/', views.ParametroSistemaCreateView.as_view(), name='parametro_create'),
    path('configuracion/parametros/<int:pk>/editar/', views.ParametroSistemaUpdateView.as_view(), name='parametro_update'),

     #vista para el historial académico en matricula.py
     path('estudiantes/<int:pk>/historial-academico/', views.EstudianteHistorialAcademicoView.as_view(), name='estudiante_historial_academico'),

     # Calificaciones
    path('calificaciones/', views.GestionCalificacionesView.as_view(), name='gestion_calificaciones'),
    path('calificaciones/ajax/docentes-por-ano/', views.ObtenerDocentesPorAñoView.as_view(), name='obtener_docentes_por_año'),
    path('calificaciones/ajax/grados-asignaturas-docente/', views.ObtenerGradosAsignaturasDocenteView.as_view(), name='obtener_grados_asignaturas_docente'),
    path('calificaciones/ajax/cargar-estudiantes/', views.CargarEstudiantesCalificacionesView.as_view(), name='cargar_estudiantes_calificaciones'),
    path('calificaciones/ajax/guardar-calificaciones/', views.GuardarCalificacionesView.as_view(), name='guardar_calificaciones'),
    path('calificaciones/ajax/calificaciones/', views.CalificacionesAjaxView.as_view(), name='calificaciones_ajax'),
    path('calificaciones/reporte/<int:periodo_id>/', views.ReporteCalificacionesView.as_view(), name='reporte_calificaciones'),
    path('calificaciones/exportar/', views.ExportarCalificacionesView.as_view(), name='exportar_calificaciones'),
    
    
    # Logros académicos
    path('logros/', views.GestionLogrosView.as_view(), name='gestion_logros'),
    path('logros/ajax/grados-por-ano/', views.ObtenerGradosPorAñoView.as_view(), name='obtener_grados_por_año'),
    path('logros/ajax/asignaturas-por-grado/', views.ObtenerAsignaturasPorGradoView.as_view(), name='obtener_asignaturas_por_grado'),
    path('logros/ajax/cargar-logros/', views.CargarLogrosView.as_view(), name='cargar_logros'),
    path('logros/ajax/guardar-logro/', views.GuardarLogroView.as_view(), name='guardar_logro'),
    path('logros/ajax/eliminar-logro/', views.EliminarLogroView.as_view(), name='eliminar_logro'),
    path('logros/ajax/copiar-logros/', views.CopiarLogrosView.as_view(), name='copiar_logros'),
    path('logros/ajax/logros/', views.LogrosAjaxView.as_view(), name='logros_ajax'),
    path('logros/exportar/', views.ExportarLogrosView.as_view(), name='exportar_logros'),

    
    # Reportes principales
    path('reportes/', views.DashboardReportesView.as_view(), name='dashboard_reportes'),
    path('reportes/estudiantes/', views.ReporteEstudiantesView.as_view(), name='reporte_estudiantes'),
    path('reportes/notas/', views.ReporteNotasView.as_view(), name='reporte_notas'),
    path('reportes/asistencia/', views.ReporteAsistenciaView.as_view(), name='reporte_asistencia'),
    path('reportes/comportamiento/', views.ReporteComportamientoView.as_view(), name='reporte_comportamiento'),
    path('reportes/estadisticas/', views.EstadisticasGeneralesView.as_view(), name='estadisticas_generales'),
    
    # Reportes especializados
    path('reportes/estudiantes-riesgo/', views.ReporteEstudiantesRiesgoView.as_view(), name='reporte_estudiantes_riesgo'),
    path('reportes/logros/', views.ReporteLogrosView.as_view(), name='reporte_logros'),
    
    # Reportes especiales
    path('reportes/cumpleanos/', views.ReporteCumpleañosView.as_view(), name='reporte_cumpleanos'),
    path('reportes/demograficas/', views.EstadisticasDemograficasView.as_view(), name='reporte_demograficas'),
    
    # AJAX endpoints
    path('reportes/ajax/datos/', views.ObtenerDatosReporteView.as_view(), name='obtener_datos_reporte'),
    
    # Exportación
    path('reportes/exportar/', views.ExportarReporteView.as_view(), name='exportar_reporte'),

    
]
