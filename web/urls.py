from django.urls import path
from . import views

app_name = 'web'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('noticias/', views.NoticiaListView.as_view(), name='noticias'),
    path('noticias/<int:pk>/', views.NoticiaDetailView.as_view(), name='noticia_detalle'),
    path('pagina/<slug:slug>/', views.PaginaDetailView.as_view(), name='pagina_detalle'),
    path('admision/', views.AdmisionView.as_view(), name='admision'),
    path('perfil/', views.PerfilView.as_view(), name='perfil'),
    path('programas/', views.ProgramasView.as_view(), name='programas'),
    path('programas/<slug:slug>/', views.ProgramaDetailView.as_view(), name='programa_detalle'),
]
