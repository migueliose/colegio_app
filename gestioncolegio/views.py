"""
Vistas principales del sistema - IMPORTACIONES CORRECTAS
"""

# =============================================
# IMPORTACIONES DE VISTAS DE DASHBOARD (ESTO ES LO QUE FALTA)
# =============================================

# Dashboard Views
from .views.dashboard_views import (
    DashboardView,
    DashboardAdministradorView,
    DashboardDocenteView,
    DashboardEstudianteView,
    DashboardAcudienteView,
    DashboardRectorView,
)

# Usuario Views
from .views.usuario_views import (
    UsuarioListView,
)

# =============================================
# EXPORTACIÓN DE VISTAS
# =============================================

__all__ = [
    # Dashboard Views (AHORA SÍ IMPORTADAS)
    'DashboardView',
    'DashboardAdministradorView',
    'DashboardDocenteView',
    'DashboardEstudianteView',
    'DashboardAcudienteView',
    'DashboardRectorView',
    
    # Matrícula Views
    'MatriculasListView',
    'MatriculaCreateView',
    
    # Usuario Views
    'UsuarioListView',
    
]