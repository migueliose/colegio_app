"""
URLs completas para la app gestioncolegio
"""
from django.urls import path
from . import views

app_name = 'gestioncolegio'

urlpatterns = [
    # ========================
    # DASHBOARD
    # ========================
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/administrador/', views.DashboardAdministradorView.as_view(), name='dashboard_administrador'),
    path('dashboard/docente/', views.DashboardDocenteView.as_view(), name='dashboard_docente'),
    path('dashboard/estudiante/', views.DashboardEstudianteView.as_view(), name='dashboard_estudiante'),
    path('dashboard/acudiente/', views.DashboardAcudienteView.as_view(), name='dashboard_acudiente'),
    path('dashboard/rector/', views.DashboardRectorView.as_view(), name='dashboard_rector'),
    
]