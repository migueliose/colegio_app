from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    # ============================
    # USUARIOS (ADMINISTRACIÓN)
    # ============================
    path('', views.GestionUsuariosView.as_view(), name='gestion_usuarios'),

    # --- Estudiantes (CRUD)
    path('estudiantes/', views.EstudiantesListView.as_view(), name='estudiantes_list'),
    path('estudiantes/nuevo/', views.EstudianteCreateView.as_view(), name='estudiante_create'),
    path('estudiantes/<int:pk>/', views.EstudianteDetailView.as_view(), name='estudiante_detail'),
    path('estudiantes/<int:pk>/editar/', views.EstudianteUpdateView.as_view(), name='estudiante_update'),
    path('estudiantes/<int:pk>/eliminar/', views.EstudianteDeleteView.as_view(), name='estudiante_delete'),

    # --- Docentes (CRUD)
    path('docentes/', views.DocentesListView.as_view(), name='docentes_list'),
    path('docentes/nuevo/', views.DocenteCreateView.as_view(), name='docente_create'),
    path('docentes/<int:pk>/', views.DocenteDetailView.as_view(), name='docente_detail'),
    path('docentes/<int:pk>/editar/', views.DocenteUpdateView.as_view(), name='docente_update'),
    path('docentes/<int:pk>/eliminar/', views.DocenteDeleteView.as_view(), name='docente_delete'),

    # --- Administradores
    path('administradores/', views.AdministradoresListView.as_view(), name='administradores_list'),

]
