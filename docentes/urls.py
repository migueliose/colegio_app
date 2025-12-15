# urls.py - docentes
from django.urls import path
from . import views

app_name = 'docentes'

urlpatterns = [

    # ===========DEBUG============= #
    path('debug/', views.debug_docente, name='logros_debug'),

    # ========================
    # DOCENTES - LOGROS
    # ========================
    path('logros/', views.ListaLogrosView.as_view(), name='lista_logros'),
    path('logros/filtrados/', views.ListaLogrosFiltradosView.as_view(), name='logros_filtrados'),
    path('logros/crear/', views.CrearLogroView.as_view(), name='crear_logro'),
    path('logros/<int:pk>/', views.DetalleLogroView.as_view(), name='detalle_logro'),
    path('logros/<int:pk>/editar/', views.EditarLogroView.as_view(), name='editar_logro'),
    path('logros/<int:pk>/eliminar/', views.EliminarLogroView.as_view(), name='eliminar_logro'),
    
    # ========================
    # DOCENTES - CALIFICACIONES
    # ========================
    path('calificar/', views.CalificarNotasView.as_view(), name='calificar_notas'),
    path('notas/', views.ListaNotasDocenteView.as_view(), name='lista_notas_docente'),
    path('notas/<int:pk>/editar/', views.EditarNotaView.as_view(), name='editar_nota'),
    path('notas/<int:pk>/eliminar/', views.EliminarNotaView.as_view(), name='eliminar_nota'),
    
    # ========================
    # DOCENTES - COMPORTAMIENTO
    # ========================
    path('comportamiento/', views.ListaComportamientosView.as_view(), name='lista_comportamientos'),
    path('comportamiento/crear/', views.CrearComportamientoView.as_view(), name='crear_comportamiento'),
    path('comportamiento/<int:pk>/', views.DetalleComportamientoView.as_view(), name='detalle_comportamiento'),
    path('comportamiento/<int:pk>/editar/', views.EditarComportamientoView.as_view(), name='editar_comportamiento'),
    path('comportamiento/<int:pk>/eliminar/', views.EliminarComportamientoView.as_view(), name='eliminar_comportamiento'),
    
    # ========================
    # DOCENTES - ESTUDIANTES
    # ========================
    path('estudiantes/', views.ListaEstudiantesView.as_view(), name='lista_estudiantes'),
    path('estudiantes/exportar-excel/', views.ExportarEstudiantesExcelView.as_view(), name='exportar_estudiantes_excel'),
    path('estudiantes/<int:pk>/', views.DetalleEstudianteView.as_view(), name='detalle_estudiante'),
    
    # ========================
    # DOCENTES - REPORTES
    # ========================
    path('reportes/notas-asignatura/', views.ReporteNotasAsignaturaView.as_view(), name='reporte_notas_asignatura'),
    path('reportes/estadisticas-comportamiento/', views.ReporteEstadisticasComportamientoView.as_view(), name='reporte_estadisticas_comportamiento'),
    
    # ========================
    # ACADÉMICO
    # ========================
    path('academico/asignaturas/', views.AsignaturasListView.as_view(), name='asignaturas_list'),
    path('academico/horarios/', views.HorariosListView.as_view(), name='horarios_list'),
    path('academico/grados/', views.GradosListView.as_view(), name='grados_list'),

    # ==================== ASISTENCIA ====================
    path('asistencia/', views.asistencia_principal, name='asistencia_principal'),
    path('asistencia/registrar/', views.registrar_asistencia, name='registrar_asistencia'),
    path('asistencia/registrar-masivo/', views.registrar_asistencia_masiva, name='registrar_asistencia_masiva'),
    path('asistencia/calendario/<int:curso_id>/<int:periodo_id>/', views.asistencia_calendario, name='asistencia_calendario'),
    path('asistencia/historico/<int:estudiante_id>/', views.asistencia_historico, name='asistencia_historico'),
    path('asistencia/reporte/<int:curso_id>/<int:periodo_id>/', views.reporte_asistencia_curso, name='reporte_asistencia_curso'),
    path('asistencia/justificar/', views.justificar_asistencia, name='justificar_asistencia'),
    
    # ========================
    # AJAX endpoints
    # ========================
    # AJAX para logros
    path('ajax/asignaturas-por-grado/', views.AjaxObtenerAsignaturasPorGradoView.as_view(), name='ajax_obtener_asignaturas_por_grado'),
    path('ajax/periodos/', views.AjaxObtenerPeriodosView.as_view(), name='ajax_obtener_periodos'),

    # Calificaciones
    path('ajax/obtener-asignaturas-', views.obtener_asignaturas_docente, name='obtener_asignaturas_docente'),
    path('ajax/obtener-periodos-', views.obtener_periodos_docente, name='obtener_periodos_docente'),
    path('ajax/obtener-notas-estudiantes/', views.obtener_notas_estudiantes, name='obtener_notas_estudiantes'),
    path('ajax/guardar-notas/', views.guardar_notas, name='guardar_notas'),
    
    # Generales
    path('ajax/asignaturas-por-grado/', views.obtener_asignaturas_por_grado, name='obtener_asignaturas'),
    path('ajax/estudiantes-por-grado/', views.obtener_estudiantes_por_grado, name='obtener_estudiantes'),
    path('ajax/guardar-nota/', views.guardar_nota_individual, name='guardar_nota'),
    
    # ==================== AJAX ENDPOINTS ====================
    path('ajax/obtener-estudiantes-curso/', views.ajax_obtener_estudiantes_curso, name='ajax_obtener_estudiantes_curso'),
    path('ajax/obtener-asistencia-dia/', views.ajax_obtener_asistencia_dia, name='ajax_obtener_asistencia_dia'),
    path('ajax/obtener-dias-semana/', views.ajax_obtener_dias_semana, name='ajax_obtener_dias_semana'),

    # AJAX para comportamiento
    path('ajax/estudiantes-por-periodo/', views.AjaxObtenerEstudiantesPorPeriodoView.as_view(), name='ajax_estudiantes_por_periodo'),
    path('ajax/resumen-comportamiento/', views.AjaxResumenComportamientoEstudianteView.as_view(), name='ajax_resumen_comportamiento'),

]