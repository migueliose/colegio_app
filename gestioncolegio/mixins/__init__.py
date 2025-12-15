# mixins/__init__.py corregido
from .mixins import (
    # Mixins base
    BaseContextMixin,
    DashboardContextMixin,
    PaginationMixin,
    FilterMixin,
    RoleRequiredMixin,
    DocenteAccessMixin,
    ExportMixin,
    NotificationMixin,
    CacheMixin,
    BaseViewMixin,
    
    # Mixins compuestos
    ListViewBaseMixin,      # ← Cambiado de ListViewMixin
    DashboardViewMixin,
    SimpleCRUDMixin,        # ← Cambiado de CRUDViewMixin
)

__all__ = [
    'BaseContextMixin',
    'DashboardContextMixin',
    'PaginationMixin',
    'FilterMixin',
    'RoleRequiredMixin',
    'DocenteAccessMixin',
    'ExportMixin',
    'NotificationMixin',
    'CacheMixin',
    'BaseViewMixin',
    'ListViewBaseMixin',    # ← Cambiado
    'DashboardViewMixin',
    'SimpleCRUDMixin',      # ← Cambiado
]