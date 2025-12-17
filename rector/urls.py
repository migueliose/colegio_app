# rector/urls.py 
from django.urls import path
from . import views

app_name = 'rector'

urlpatterns = [
        
    # ========== GESTIÓN ACADÉMICA ==========
    path('academico/', views.AcademicoDashboardView.as_view(), name='academico_dashboard'),
        
    # ========== ESTUDIANTES ==========
    path('estudiantes/', views.EstudianteListView.as_view(), name='estudiante_list'),
    path('estudiantes/<int:pk>/', views.EstudianteDetailView.as_view(), name='estudiante_detail'),
    path('estudiantes/<int:pk>/editar/', views.EstudianteUpdateView.as_view(), name='estudiante_edit'),
    path('estudiantes/<int:pk>/toggle-estado/', views.EstudianteToggleEstadoView.as_view(), name='estudiante_toggle_estado'),
    path('estudiantes/<int:pk>/editar-informacion/', views.EstudianteEditarInformacionBaseView.as_view(), name='estudiante_editar_informacion'),
    
    # ========== MATRÍCULAS ==========
    path('matriculas/', views.MatriculaListView.as_view(), name='matricula_list'),
    path('matriculas/<int:pk>/', views.MatriculaDetailView.as_view(), name='matricula_detail'),
    path('matriculas/<int:pk>/editar/', views.MatriculaUpdateFromListView.as_view(), name='matricula_edit'),
    path('matriculas/<int:pk>/eliminar/', views.MatriculaDeleteFromListView.as_view(), name='matricula_delete'),
    path('matriculas/exportar/', views.ExportarMatriculasView.as_view(), name='exportar_matriculas'),
    
    # AJAX para matrículas
    path('ajax/matriculas/filtradas/', views.GetMatriculasFiltradasAjaxView.as_view(), name='ajax_matriculas_filtradas'),
    path('matriculas/<int:pk>/matricula/crear/', views.MatriculaCreateView.as_view(), name='matricula_crear'),
    path('matriculas/<int:estudiante_pk>/matricula/<int:matricula_pk>/editar/', views.MatriculaUpdateView.as_view(), name='matricula_editar'),
    path('matriculas/<int:estudiante_pk>/matricula/<int:matricula_pk>/eliminar/',views.MatriculaDeleteView.as_view(), name='matricula_eliminar'),
     # ========== MATRÍCULA RÁPIDA ==========
    path('matricula-rapida/', views.MatriculaRapidaView.as_view(), name='matricula_rapida'),
    
    # AJAX para matrícula rápida
    path('ajax/matricula/buscar-estudiantes/', views.BuscarEstudiantesMatriculaAjaxView.as_view(), name='ajax_buscar_estudiantes_matricula'),
    path('ajax/matricula/verificar-documento/', views.VerificarDocumentoEstudianteAjaxView.as_view(), name='ajax_verificar_documento_estudiante'),
    path('ajax/matricula/crear-estudiante/', views.CrearEstudianteMatriculaAjaxView.as_view(), name='ajax_crear_estudiante_matricula'),
    path('ajax/matricula/matricular-existente/', views.MatricularEstudianteExistenteAjaxView.as_view(), name='ajax_matricular_estudiante_existente'),
    path('ajax/matricula/usar-estudiante-existente/', views.UsarEstudianteExistenteAjaxView.as_view(), name='ajax_usar_estudiante_existente'),
    
    # ========== ACUDIENTES ==========
    path('estudiantes/<int:pk>/acudientes/crear/', views.AcudienteCrearView.as_view(), name='acudiente_crear'),
    path('estudiantes/<int:estudiante_pk>/acudientes/<int:acudiente_pk>/editar-informacion/', views.AcudienteEditarInformacionView.as_view(), name='acudiente_editar_informacion'),
    path('estudiantes/<int:estudiante_pk>/acudientes/<int:acudiente_pk>/eliminar/', views.AcudienteDeleteView.as_view(), name='acudiente_eliminar'),
     
    # ========== DOCENTES ==========
    path('docentes/', views.DocenteListView.as_view(), name='docente_list'),
    path('docentes/crear/', views.DocenteCreateView.as_view(), name='docente_create'),
    path('docentes/<int:pk>/', views.DocenteDetailView.as_view(), name='docente_detail'),
    path('docentes/<int:pk>/editar/', views.DocenteUpdateView.as_view(), name='docente_edit'),
    path('docentes/<int:pk>/toggle-estado/', views.DocenteToggleEstadoView.as_view(), name='docente_toggle_estado'),
    path('docentes/<int:pk>/editar-informacion/', views.DocenteInformacionPersonalView.as_view(), name='docente_informacion_personal'),
    path('docentes/<int:pk>/asignar-asignatura/', views.DocenteAsignarAsignaturaView.as_view(), name='docente_asignar_asignatura'),
    path('docentes/<int:pk>/asignar-sede/', views.DocenteAsignarSedeView.as_view(), name='docente_asignar_sede'),
    
    # Quitar asignaturas y sedes (vistas tradicionales)
    path('docentes/asignatura/<int:pk>/quitar/', views.AsignaturaDocenteDeleteView.as_view(), name='asignatura_quitar'),
    path('docentes/sede/<int:pk>/quitar/', views.DocenteSedeDeleteView.as_view(), name='sede_quitar'),
    path('docentes/sede/<int:pk>/reactivar/', views.DocenteSedeReactivarView.as_view(), name='sede_reactivar'),

    # Grados y niveles
    path('grados/', views.GradoListView.as_view(), name='grado_list'),
    path('grados/<int:pk>/', views.GradoDetailView.as_view(), name='grado_detail'),
    path('grados/niveles/', views.NivelEscolarListView.as_view(), name='nivel_list'),
    path('grados/niveles/<int:pk>/', views.NivelEscolarDetailView.as_view(), name='nivel_detail'),

    # GradoAñoLectivo (asignación de grados)
    path('grados/asignar/', views.GradoAñoLectivoCreateView.as_view(), name='grado_añoelectivo_create'),
    path('grados/modificar/<int:pk>/', views.GradoAñoLectivoUpdateView.as_view(), name='grado_añoelectivo_update'),
    path('grados/eliminar/<int:pk>/', views.GradoAñoLectivoDeleteView.as_view(), name='grado_añoelectivo_delete'),

    # ========== ÁREAS DEL CONOCIMIENTO ==========
    path('areas/', views.AreaListView.as_view(), name='area_list'),
    path('areas/<int:pk>/', views.AreaDetailView.as_view(), name='area_detail'),
    path('areas/crear/', views.AreaCreateView.as_view(), name='area_create'),
    path('areas/<int:pk>/editar/', views.AreaUpdateView.as_view(), name='area_edit'),
    path('areas/<int:pk>/eliminar/', views.AreaDeleteView.as_view(), name='area_delete'),

    # ========== ASIGNATURAS ==========
    path('asignaturas/', views.AsignaturaListView.as_view(), name='asignatura_list'),
    path('asignaturas/<int:pk>/', views.AsignaturaDetailView.as_view(), name='asignatura_detail'),
    path('asignaturas/crear/', views.AsignaturaCreateView.as_view(), name='asignatura_create'),
    path('asignaturas/<int:pk>/editar/', views.AsignaturaUpdateView.as_view(), name='asignatura_edit'),
    path('asignaturas/<int:pk>/eliminar/', views.AsignaturaDeleteView.as_view(), name='asignatura_delete'),
    path('asignaturas/multiples/', views.AsignaturaBulkCreateView.as_view(), name='asignatura_bulk_create'),

    # ========== ASIGNACIÓN ASIGNATURAS A GRADOS ==========
    path('asignaturas-grado/crear/', views.AsignaturaGradoCreateView.as_view(), name='asignatura_grado_create'),
    path('asignaturas-grado/<int:pk>/editar/', views.AsignaturaGradoUpdateView.as_view(), name='asignatura_grado_edit'),
    path('asignaturas-grado/<int:pk>/eliminar/', views.AsignaturaGradoDeleteView.as_view(), name='asignatura_grado_delete'),
    
    # Logros
    path('logros/', views.LogroListView.as_view(), name='logro_list'),
    path('logros/crear/', views.LogroCreateView.as_view(), name='logro_create'),
    path('logros/<int:pk>/', views.LogroDetailView.as_view(), name='logro_detail'),
    path('logros/<int:pk>/editar/', views.LogroUpdateView.as_view(), name='logro_edit'),
    path('logros/<int:pk>/eliminar/', views.LogroDeleteView.as_view(), name='logro_delete'),
    path('logros/por-asignatura/', views.LogrosPorAsignaturaView.as_view(), name='logros_por_asignatura'),
    
    # Horarios
    path('horarios/', views.HorarioListView.as_view(), name='horario_list'),
    path('horarios/crear/', views.HorarioCreateView.as_view(), name='horario_create'),
    path('horarios/<int:pk>/', views.HorarioDetailView.as_view(), name='horario_detail'),
    path('horarios/<int:pk>/editar/', views.HorarioUpdateView.as_view(), name='horario_edit'),
    path('horarios/<int:pk>/eliminar/', views.HorarioDeleteView.as_view(), name='horario_delete'),
    path('horarios/por-grado/', views.HorarioPorGradoView.as_view(), name='horario_por_grado'),
    
    # ========== AJAX ==========
    
    path('ajax/grados-por-filtros/', views.GetGradosByAñoSedeNivelAjaxView.as_view(), name='ajax_grados_por_filtros'),

    path('ajax/estudiante/<int:pk>/toggle-estado/', views.ToggleEstudianteEstadoAjaxView.as_view(), name='ajax_estudiante_toggle_estado'),
    path('ajax/estudiantes-por-grado/', views.GetEstudiantesByGradoView.as_view(), name='ajax_estudiantes_por_grado'),
    
    path('ajax/docente/<int:pk>/toggle-estado/', views.ToggleDocenteEstadoAjaxView.as_view(), name='ajax_docente_toggle_estado'),
    path('ajax/docentes-por-sede/', views.GetDocentesBySedeView.as_view(), name='ajax_docentes_por_sede'),
    
    path('ajax/grados-por-nivel-anho-sede/', views.GetGradosByNivelAñoSedeView.as_view(), name='ajax_grados_nivel_año_sede'),
    
    path('ajax/buscar-acudientes/', views.BuscarAcudientesAjaxView.as_view(), name='ajax_buscar_acudientes'),
    path('ajax/verificar-documento-acudiente/', views.VerificarDocumentoAcudienteAjaxView.as_view(), name='ajax_verificar_documento_acudiente'),
    path('ajax/crear-relacion-acudiente/', views.CrearRelacionAcudienteAjaxView.as_view(), name='ajax_crear_relacion_acudiente'),
    
    # AJAX grados y niveles
    path('ajax/estadisticas-grado/', views.GetEstadisticasGradoAjaxView.as_view(), name='ajax_estadisticas_grado'),
    path('ajax/toggle-grado-anho/', views.ToggleGradoAñoLectivoAjaxView.as_view(), name='ajax_toggle_grado_año'),
    path('ajax/grados-por-nivel-anho/', views.GetGradosByNivelAñoSedeView.as_view(), name='ajax_grados_por_nivel_año'),
    
    # AJAX endpoints para dashboard_academico
    path('ajax/actualizar-estadisticas/', views.ActualizarEstadisticasAjaxView.as_view(), name='ajax_actualizar_estadisticas'),
    path('ajax/dashboard-estadisticas/', views.GetEstadisticasDashboardAjaxView.as_view(), name='ajax_dashboard_estadisticas'),
    
    #AJAX para los filtros asignatura docente
    path('ajax/grados-por-sede-anho/', views.GetGradosBySedeAñoAjaxView.as_view(), name='ajax_grados_sede_año'),
    path('ajax/asignaturas-por-grado-docente/', views.GetAsignaturasByGradoDocenteAjaxView.as_view(), name='ajax_asignaturas_grado_docente'),
    path('ajax/grado-info/<int:grado_id>/', views.GetGradoInfoAjaxView.as_view(), name='ajax_grado_info'),

    # AJAX para docentes (opcionales)
    path('ajax/asignatura/<int:asignatura_id>/quitar-ajax/', views.QuitarAsignaturaDocenteAjaxView.as_view(), name='quitar_asignatura_docente_ajax'),
    path('ajax/sede/<int:sede_id>/quitar-ajax/', views.QuitarSedeDocenteAjaxView.as_view(), name='quitar_sede_docente_ajax'),

    # AJAX para áreas y asignaturas
    path('ajax/area/<int:area_id>/info/', views.GetAreaInfoAjaxView.as_view(), name='ajax_get_area_info'),
    path('ajax/check-asignatura/', views.CheckAsignaturaAjaxView.as_view(), name='ajax_check_asignatura'),

    # AJAX para logros
    path('ajax/grado/<int:grado_id>/info/', views.GetGradoInfoAjaxView.as_view(), name='ajax_get_grado_info'),
    path('ajax/asignaturas-por-grado/', views.GetAsignaturasByGradoAjaxView.as_view(), name='ajax_get_asignaturas_by_grado'),
    
    # ========== AJAX INSTITUCIONAL ==========
    path('ajax/institucional/anhos-por-sede/', views.GetAñosLectivosBySedeAjaxView.as_view(), name='ajax_años_por_sede'),
    path('ajax/institucional/periodos-por-anho/', views.GetPeriodosByAñoLectivoAjaxView.as_view(), name='ajax_periodos_por_año'),
    path('ajax/institucional/estadisticas/', views.GetEstadisticasInstitucionalesAjaxView.as_view(), name='ajax_estadisticas_institucionales'),
    path('ajax/institucional/check-solapamiento/', views.CheckPeriodoSolapamientoAjaxView.as_view(), name='ajax_check_solapamiento'),
    path('ajax/institucional/asignaturas-sin-docente/', views.GetAsignaturasSinDocenteAjaxView.as_view(), name='ajax_asignaturas_sin_docente'),
    path('ajax/institucional/toggle-anho-estado/', views.ToggleAñoLectivoEstadoAjaxView.as_view(), name='ajax_toggle_año_estado'),
    path('ajax/institucional/toggle-periodo-estado/', views.TogglePeriodoEstadoAjaxView.as_view(), name='ajax_toggle_periodo_estado'),
    path('ajax/institucional/sede-info/', views.GetSedeInfoAjaxView.as_view(), name='ajax_sede_info'),

    # ========== GESTIÓN INSTITUCIONAL  ==========
    path('institucional/dashboard/', views.InstitucionalDashboardView.as_view(), name='institucional_dashboard'),
    
    # Años lectivos
    path('institucional/anhos-lectivos/', views.AñoLectivoListView.as_view(), name='año_lectivo_list'),
    path('institucional/anhos-lectivos/crear/', views.AñoLectivoCreateView.as_view(), name='año_lectivo_create'),
    path('institucional/anhos-lectivos/<int:pk>/editar/', views.AñoLectivoUpdateView.as_view(), name='año_lectivo_edit'),
    path('institucional/anhos-lectivos/<int:pk>/eliminar/', views.AñoLectivoDeleteView.as_view(), name='año_lectivo_delete'),
    path('institucional/anhos-lectivos/<int:pk>/establecer-actual/', views.AñoLectivoSetCurrentView.as_view(), name='año_lectivo_set_current'),
    
    # Periodos académicos
    path('institucional/periodos/', views.PeriodoAcademicoListView.as_view(), name='periodo_list'),
    path('institucional/periodos/crear/', views.PeriodoAcademicoCreateView.as_view(), name='periodo_create'),
    path('institucional/periodos/<int:pk>/editar/', views.PeriodoAcademicoUpdateView.as_view(), name='periodo_edit'),
    path('institucional/periodos/<int:pk>/eliminar/', views.PeriodoAcademicoDeleteView.as_view(), name='periodo_delete'),
    
    # Asignación docente
    path('institucional/asignacion-docente/', views.AsignacionDocenteDashboardView.as_view(), name='asignacion_docente_dashboard'),
    path('institucional/asignacion-por-sede/', views.AsignacionPorSedeView.as_view(), name='asignacion_por_sede'),

    # ========== GESTIÓN DE SEDES ==========
    path('sedes/', views.SedesRectorView.as_view(), name='sedes'),
    path('sedes/crear/', views.SedeCreateView.as_view(), name='sede_create'),
    path('sedes/<int:pk>/', views.SedeDetailView.as_view(), name='sede_detail'),
    path('sedes/<int:pk>/editar/', views.SedeUpdateView.as_view(), name='sede_edit'),
    path('sedes/<int:pk>/eliminar/', views.SedeDeleteView.as_view(), name='sede_delete'),
    path('sedes/<int:pk>/reactivar/', views.SedeReactivateView.as_view(), name='sede_reactivate'),
    path('sedes/<int:pk>/cambiar-director/', views.SedeChangeDirectorView.as_view(), name='sede_change_director'),
    
    # ========== MODULO DE SEGUIMIENTO ==========
    path('seguimiento/', views.SeguimientoDashboardView.as_view(), name='seguimiento_dashboard'),
    
    # Comportamiento
    path('seguimiento/comportamiento/', views.ComportamientoListView.as_view(), name='comportamiento_list'),
    path('seguimiento/comportamiento/crear/', views.ComportamientoCreateView.as_view(), name='comportamiento_create'),
    path('seguimiento/comportamiento/<int:pk>/', views.ComportamientoDetailView.as_view(), name='comportamiento_detail'),
    path('seguimiento/comportamiento/<int:pk>/editar/', views.ComportamientoUpdateView.as_view(), name='comportamiento_edit'),
    path('seguimiento/comportamiento/<int:pk>/eliminar/', views.ComportamientoDeleteView.as_view(), name='comportamiento_delete'),
    
    # Asistencia
    path('seguimiento/asistencia/', views.AsistenciaListView.as_view(), name='asistencia_list'),
    path('seguimiento/asistencia/crear/', views.AsistenciaCreateView.as_view(), name='asistencia_create'),
    path('seguimiento/asistencia/masiva/', views.AsistenciaBulkView.as_view(), name='asistencia_bulk'),
    path('seguimiento/asistencia/procesar-masiva/', views.AsistenciaProcesarBulkView.as_view(), name='asistencia_procesar_bulk'),
    path('seguimiento/asistencia/grado/<int:grado_id>/', views.AsistenciaPorGradoView.as_view(), name='asistencia_grado'),
    path('asistencia/<int:pk>/', views.AsistenciaDetailView.as_view(), name='asistencia_detail'),
    path('asistencia/<int:pk>/editar/', views.AsistenciaUpdateView.as_view(), name='asistencia_edit'),
    #path('asistencia/<int:pk>/eliminar/', views.AsistenciaDeleteView.as_view(), name='asistencia_delete'),
    # AJAX para asistencia
    path('ajax/asistencia-detalle/<int:asistencia_id>/', views.AjaxAsistenciaDetalleView.as_view(), name='ajax_asistencia_detalle'),
    path('ajax/actualizar-asistencia/', views.AjaxActualizarAsistenciaIndividualView.as_view(), name='ajax_actualizar_asistencia'),
    path('ajax/estadisticas-asistencia/', views.AjaxObtenerEstadisticasAsistenciaView.as_view(), name='ajax_estadisticas_asistencia'),

    # Inconsistencias
    path('seguimiento/inconsistencias/', views.InconsistenciaListView.as_view(), name='inconsistencia_list'),
    path('seguimiento/inconsistencias/crear/', views.InconsistenciaCreateView.as_view(), name='inconsistencia_create'),
    path('seguimiento/inconsistencias/<int:pk>/', views.InconsistenciaDetailView.as_view(), name='inconsistencia_detail'),
    path('seguimiento/inconsistencias/<int:pk>/editar/', views.InconsistenciaUpdateView.as_view(), name='inconsistencia_edit'),
    path('seguimiento/inconsistencias/<int:pk>/eliminar/', views.InconsistenciaDeleteView.as_view(), name='inconsistencia_delete'),
    
    # AJAX para inconsistencias
    path('ajax/inconsistencias/estadisticas/', views.AjaxEstadisticasInconsistenciasView.as_view(), name='ajax_estadisticas_inconsistencias'),
    path('ajax/inconsistencias/eliminar-multiple/', views.AjaxEliminarInconsistenciasView.as_view(), name='ajax_eliminar_inconsistencias'),
    path('ajax/inconsistencias/marcar-resueltas/', views.AjaxMarcarInconsistenciasResueltasView.as_view(), name='ajax_marcar_inconsistencias_resueltas'),
    path('ajax/inconsistencias/importar/', views.AjaxImportarInconsistenciasView.as_view(), name='ajax_importar_inconsistencias'),
    path('ajax/inconsistencias/tipos/', views.AjaxTiposInconsistenciasView.as_view(), name='ajax_tipos_inconsistencias'),
    path('ajax/inconsistencias/tipos-comunes/', views.AjaxTiposComunesInconsistenciasView.as_view(), name='ajax_tipos_comunes_inconsistencias'),
    path('ajax/inconsistencias/info-estudiante/', views.AjaxInformacionEstudianteView.as_view(), name='ajax_informacion_estudiante'),
    path('ajax/inconsistencias/historial-estudiante/', views.AjaxHistorialInconsistenciasEstudianteView.as_view(), name='ajax_historial_inconsistencias_estudiante'),
    path('ajax/inconsistencias/estadisticas-estudiante/', views.AjaxEstadisticasEstudianteView.as_view(), name='ajax_estadisticas_estudiante'),
    path('ajax/inconsistencias/marcar-resuelta/', views.AjaxMarcarInconsistenciaResueltaView.as_view(), name='ajax_marcar_inconsistencia_resuelta'),
    path('ajax/inconsistencias/marcar-pendiente/', views.AjaxMarcarInconsistenciaPendienteView.as_view(), name='ajax_marcar_inconsistencia_pendiente'),
    path('ajax/inconsistencias/compartir/', views.AjaxCompartirInconsistenciaView.as_view(), name='ajax_compartir_inconsistencia'),
    path('ajax/buscar-estudiantes/', views.AjaxBuscarEstudiantesView.as_view(), name='ajax_buscar_estudiantes'),
    path('ajax/buscar-estudiantes-activos/', views.AjaxBuscarEstudiantesActivosView.as_view(), name='ajax_buscar_estudiantes_activos'),
    
    # Calificaciones
    path('seguimiento/calificaciones/', views.CalificacionListView.as_view(), name='calificacion_list'),
    path('seguimiento/calificaciones/crear/', views.CalificacionCreateView.as_view(), name='calificacion_create'),
    path('seguimiento/calificaciones/masiva/', views.CalificacionBulkView.as_view(), name='calificacion_bulk'),
    path('seguimiento/calificaciones/procesar-masiva/', views.CalificacionProcesarBulkView.as_view(), name='calificacion_procesar_bulk'),
    path('seguimiento/calificaciones/<int:pk>/editar/', views.CalificacionUpdateView.as_view(), name='calificacion_edit'),
    path('seguimiento/calificaciones/<int:pk>/', views.CalificacionDetailView.as_view(), name='calificacion_detail'),
    path('seguimiento/calificaciones/estudiante/<int:pk>/reporte/', views.CalificacionEstudianteReporteView.as_view(), name='calificacion_estudiante_reporte'),
    path('seguimiento/calificaciones/<int:pk>/eliminar/', views.CalificacionDeleteView.as_view(), name='calificacion_delete'),

    # ========== AJAX SEGUIMIENTO ==========
    path('ajax/seguimiento/estadisticas/', views.GetEstadisticasSeguimientoAjaxView.as_view(), name='ajax_estadisticas_seguimiento'),
    path('ajax/seguimiento/estudiantes-por-grado/', views.GetEstudiantesPorGradoAjaxView.as_view(), name='ajax_estudiantes_por_grado'),
    path('ajax/seguimiento/asistencias-estudiante/', views.GetAsistenciasEstudianteAjaxView.as_view(), name='ajax_asistencias_estudiante'),
    path('ajax/seguimiento/calificaciones-estudiante/', views.GetCalificacionesEstudianteAjaxView.as_view(), name='ajax_calificaciones_estudiante'),
    path('ajax/seguimiento/comportamientos-estudiante/', views.GetComportamientosEstudianteAjaxView.as_view(), name='ajax_comportamientos_estudiante'),
    path('ajax/seguimiento/inconsistencias-estudiante/', views.GetInconsistenciasEstudianteAjaxView.as_view(), name='ajax_inconsistencias_estudiante'),
    path('ajax/seguimiento/exportar-reporte/', views.ExportarReporteSeguimientoAjaxView.as_view(), name='ajax_exportar_reporte_seguimiento'),
    
    # Reportes
    path('reportes/', views.ReportesRectorView.as_view(), name='reportes'),
    # Documentos de estudiante
    path('reportes/estudiantes/<int:estudiante_id>/documentos/',  views.DocumentosEstudianteView.as_view(), name='documentos_individual_estudiante'),
    # Redirecciones a documentos (mantienen la misma funcionalidad)
    path('reportes/estudiantes/<int:estudiante_id>/constancia/<int:año_lectivo_id>/', views.RedirigirConstanciaPDFView.as_view(),name='constancia_individual_pdf'),
    path('reportes/estudiantes/<int:estudiante_id>/observador/<int:año_lectivo_id>/', views.RedirigirObservadorPDFView.as_view(),name='observador_individual_pdf'),
    path('reportes/estudiantes/<int:estudiante_id>/boletin/<int:año_lectivo_id>/', views.RedirigirReporteNotasPDFView.as_view(),name='boletin_individual_pdf'),
    
    # ========== REPORTES EXCEL ==========
    path('reportes/estudiantes/excel/', views.ReporteEstudiantesExcelView.as_view(), name='reporte_estudiantes_excel'),
    path('reportes/docentes/excel/', views.ReporteDocentesExcelView.as_view(), name='reporte_docentes_excel'),
    path('reportes/promedios/excel/', views.ReportePromediosExcelView.as_view(), name='reporte_promedios_excel'),
    path('reportes/puestos/excel/', views.ReportePuestosExcelView.as_view(), name='reporte_puestos_excel'),
    path('reportes/mejores10/excel/', views.ReporteMejores10ExcelView.as_view(), name='reporte_mejores10_excel'),
    path('reportes/asistencias/excel/', views.ReporteAsistenciasExcelView.as_view(), name='reporte_asistencias_excel'),
    path('reportes/comportamiento/excel/', views.ReporteComportamientoExcelView.as_view(), name='reporte_comportamiento_excel'),
    path('reportes/consolidado/excel/', views.ReporteConsolidadoExcelView.as_view(), name='reporte_consolidado_excel'),
]