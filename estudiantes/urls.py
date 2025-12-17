# urls.py - estudiantes
from django.urls import path
from . import views

app_name = 'estudiantes'

urlpatterns = [

    # ============================
    # PERFIL Y DATOS DEL ESTUDIANTE
    # ============================
    path('perfil/', views.PerfilEstudianteView.as_view(), name='estudiante_perfil'),
    path('<int:estudiante_id>/perfil/', views.PerfilEstudianteView.as_view(), name='estudiante_perfil_admin'),

    # ============================
    # SELECCIÓN DE AÑO LECTIVO
    # ============================
    path('seleccionar-anholectivo/', views.SeleccionarAñoLectivoView.as_view(), name='seleccionar_año_lectivo'),
    path('<int:estudiante_id>/seleccionar-anholectivo/',
         views.SeleccionarAñoLectivoView.as_view(),
         name='seleccionar_año_lectivo_admin'),

    # ============================
    # INFORME ACADÉMICO (VISTA HTML)
    # ============================
    path('informe/', views.InformeAcademicoEstudianteView.as_view(), name='estudiante_informe'),
    path('informe/periodo/<int:periodo_id>/', views.InformeAcademicoEstudianteView.as_view(), name='estudiante_informe_periodo'),

    # Admin/Docente viendo informes del estudiante
    path('<int:estudiante_id>/informe/', views.InformeAcademicoEstudianteView.as_view(), name='estudiante_informe_admin'),
    path('<int:estudiante_id>/informe/periodo/<int:periodo_id>/', views.InformeAcademicoEstudianteView.as_view(), name='estudiante_informe_periodo_admin'),

    # ============================
    # CONSTANCIA DE ESTUDIO
    # ============================
    path('constancia/pdf/', views.ConstanciaEstudioPDFView.as_view(), name='estudiante_constancia_pdf'),
    path('<int:estudiante_id>/constancia/pdf/', views.ConstanciaEstudioPDFView.as_view(), name='estudiante_constancia_pdf_admin'),
    path('estudiante/<int:estudiante_id>/constancia/año/<int:año_lectivo_id>/',
         views.ConstanciaEstudioPDFView.as_view(),
         name='estudiante_constancia_año_admin'),

    # ============================
    # REPORTE DE NOTAS (PDF)
    # ============================
    # Año actual
    path('reporte-notas/pdf/', views.ReporteNotasPDFView.as_view(), name='estudiante_reporte_notas_pdf'),
    path('reporte-notas/pdf/periodo/<int:periodo_id>/', views.ReporteNotasPDFView.as_view(), name='estudiante_reporte_notas_pdf_periodo'),
    path('reporte-notas/pdf/anho/<int:año_lectivo_id>/',
         views.ReporteNotasPDFView.as_view(),
         {'tipo': 'final'},
         name='estudiante_boletin_final_pdf_año'),

    # Admin/Docente
    path('<int:estudiante_id>/reporte-notas/pdf/', views.ReporteNotasPDFView.as_view(), name='estudiante_reporte_notas_pdf_admin'),
    path('<int:estudiante_id>/reporte-notas/pdf/periodo/<int:periodo_id>/',
         views.ReporteNotasPDFView.as_view(),
         name='estudiante_reporte_notas_pdf_periodo_admin'),
    path('<int:estudiante_id>/reporte-notas/año/<int:año_lectivo_id>/',
         views.ReporteNotasPDFView.as_view(),
         {'tipo': 'notas'},
         name='estudiante_reporte_notas_año_admin'),
    path('<int:estudiante_id>/boletin-final/año/<int:año_lectivo_id>/',
         views.ReporteNotasPDFView.as_view(),
         {'tipo': 'final'},
         name='estudiante_boletin_final_año_admin'),

    # ============================
    # OBSERVADOR / COMPORTAMIENTO
    # ============================
    path('observador/pdf/', views.ObservadorEstudiantePDFView.as_view(), name='estudiante_observador_pdf'),
    path('observador/pdf/año/<int:año_lectivo_id>/', views.ObservadorEstudiantePDFView.as_view(), name='estudiante_observador_pdf_año'),
    path('observador-final/pdf/año/<int:año_lectivo_id>/', views.ObservadorEstudiantePDFView.as_view(), name='estudiante_observador_final_pdf'),

    # Admin/Docente
    path('<int:estudiante_id>/observador/pdf/', views.ObservadorEstudiantePDFView.as_view(), name='estudiante_observador_pdf_admin'),
    path('<int:estudiante_id>/observador/año/<int:año_lectivo_id>/',
         views.ObservadorEstudiantePDFView.as_view(),
         name='estudiante_observador_año_admin'),
    path('<int:estudiante_id>/observador-final/año/<int:año_lectivo_id>/',
         views.ObservadorEstudiantePDFView.as_view(),
         {'tipo': 'boletin_final'},
         name='estudiante_observador_final_año_admin'),

    # ============================
    # HORARIO Y ASIGNATURAS
    # ============================
    path('horario/', views.MiHorarioView.as_view(), name='horarios_list'),
    path('asignaturas/', views.MisAsignaturasView.as_view(), name='asignaturas_list'),
    
    
    path('cuenta-inactiva/', views.CuentaInactivaView.as_view(), name='cuenta_inactiva'),
]
