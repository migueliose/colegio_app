from django.urls import path
from . import views

app_name = 'academico'

urlpatterns = [
    # ============================
    # ACADÉMICO - GRADOS / ASIGNATURAS / HORARIOS / NOTAS
    # ============================
    # Grados
    path('grados/', views.GradosListView.as_view(), name='grados_list'),
    path('grados/nuevo/', views.GradoCreateView.as_view(), name='grado_create'),
    path('grados/<int:pk>/editar/', views.GradoUpdateView.as_view(), name='grado_update'),
    path('grados/<int:pk>/eliminar/', views.GradoDeleteView.as_view(), name='grado_delete'),

    # Asignaturas
    path('asignaturas/', views.AsignaturasListView.as_view(), name='asignaturas_list'),

    # Horarios
    path('horarios/', views.HorariosListView.as_view(), name='horarios_list'),

    # Notas (Admin)
    path('notas/', views.NotasListView.as_view(), name='notas_list'),
    path('notas/nueva/', views.NotaCreateView.as_view(), name='nota_create'),
    path('notas/<int:pk>/editar/', views.NotaUpdateView.as_view(), name='nota_update'),
    path('notas/<int:pk>/eliminar/', views.NotaDeleteView.as_view(), name='nota_delete'),
]