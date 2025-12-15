"""
Exportación de todas las vistas del sistema - VERSIÓN FINAL
"""
from .dashboard_views import *
from .usuario_views import *

__all__ = [
    # ============================
    # DASHBOARD (TODAS LAS QUE TIENES)
    # ============================
    'DashboardView',
    'DashboardAdministradorView',
    'DashboardDocenteView',
    'DashboardEstudianteView',
    'DashboardAcudienteView',
    'DashboardRectorView',

    # ============================
    # MATRÍCULAS
    # ============================
    'MatriculasListView',
    'MatriculaCreateView',
    'MatriculaUpdateView',
    'MatriculaDeleteView',
    
    # ============================
    # USUARIOS
    # ============================
    'UsuarioListView',
    'UsuarioUpdateView',
    'UsuarioDeleteView',
    'UsuarioCreateView',
    'DocenteListView',
    'EstudianteListView',

]