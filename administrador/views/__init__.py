from .gestion_academica import *
from .gestion_usuarios import *
from .horarios import *
from .matriculas import *
from .reportes import *
from .calificaciones import *
from .logros import *
from .configuracion import *
from ..forms.formularios import *

__all__ = [
    # ============================
    # GESTION ACADÉMICA
    # ============================
    'GradoListView',
    'GradoCreateView',
    'GradoUpdateView',
    'GradoDeleteView',
    'AreaListView',
    'AreaCreateView',
    'AreaUpdateView',
    'AreaDeleteView',
    'AsignaturaListView',
    'AsignaturaCreateView',
    'AsignaturaUpdateView',
    'AsignaturaDeleteView',
    'AñoLectivoListView',
    'AñoLectivoCreateView',
    'AñoLectivoUpdateView',
    'AñoLectivoDeleteView',
    'AñoLectivoActivarDesactivarView',
    'AñoLectivoPeriodosView',
    'PeriodoAcademicoCreateView',
    'PeriodoAcademicoUpdateView',
    'PeriodoAcademicoDeleteView',
    'AgregarMultiplesPeriodosView',

    # ============================
    # GESTION USUARIOS
    # ============================
    'DocenteListView'
]