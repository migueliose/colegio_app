# acudiente/urls.py
from django.urls import path
from . import views
from . import views_pdf

app_name = 'acudiente'

urlpatterns = [
    path('estudiante/<int:pk>/', views.DetalleEstudianteView.as_view(), name='detalle_estudiante'),
    path('estudiante/<int:estudiante_id>/notas/', views.NotasEstudianteView.as_view(), name='notas_estudiante'),
    path('estudiante/<int:estudiante_id>/asistencia/', views.AsistenciaEstudianteView.as_view(), name='asistencia_estudiante'),
    path('estudiante/<int:estudiante_id>/comportamiento/', views.ComportamientoEstudianteView.as_view(), name='comportamiento_estudiante'),
    path('estudiante/<int:estudiante_id>/documentos/', views.DocumentosEstudianteView.as_view(), name='documentos_estudiante'),
    path('estudiante/<int:estudiante_id>/historial/', views.HistorialAcademicoView.as_view(), name='historial_academico'),
    path('estudiante/<int:estudiante_id>/horario/', views.HorarioEstudianteView.as_view(), name='horario_estudiante'),
    
    path('estudiante/<int:estudiante_id>/inconsistencias/', views.InconsistenciasEstudianteView.as_view(), name='inconsistencias_estudiante'),
    path('estudiante/<int:estudiante_id>/comunicacion/', views.ComunicacionEstudianteView.as_view(), name='comunicacion_estudiante'),
    path('estudiante/<int:estudiante_id>/eventos/', views.EventosEstudianteView.as_view(), name='eventos_estudiante'),

    # Documentos PDF - Redirecciones a vistas de estudiantes
    path('estudiante/<int:estudiante_id>/constancia-pdf/<int:año_lectivo_id>/', 
         views_pdf.RedirigirConstanciaPDFView.as_view(), 
         name='constancia_pdf'),
    
    path('estudiante/<int:estudiante_id>/observador-pdf/<int:año_lectivo_id>/', 
         views_pdf.RedirigirObservadorPDFView.as_view(), 
         name='observador_pdf'),
    
    path('estudiante/<int:estudiante_id>/reporte-notas-pdf/<int:año_lectivo_id>/', 
         views_pdf.RedirigirReporteNotasPDFView.as_view(), 
         name='boletin_pdf'),

    # Vista para seleccionar año para documentos históricos
    path('estudiante/<int:estudiante_id>/seleccionar-anio/', 
         views.SeleccionarAñoDocumentosView.as_view(), 
         name='seleccionar_año'),
]

# Compatibilidad con enlaces antiguos que llevaban "ñ" en la ruta ("año").
# Las rutas principales usan "anio" porque algunos servidores (Passenger en
# cPanel) no entregan bien los caracteres no ASCII y Django responde 404.
urlpatterns += [
    path(str(p.pattern).replace('anio/', 'año/'), p.callback, p.default_args)
    for p in list(urlpatterns) if 'anio/' in str(p.pattern)
]
