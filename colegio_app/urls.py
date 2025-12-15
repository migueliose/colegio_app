from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from web.views import custom_404_view, custom_500_view

urlpatterns = [
    # web inicio
    path('', include('web.urls')),
    
    # sistema de gestión académica
    path('gestion/', include('gestioncolegio.urls')),

    # sistema de usuarios
    path('usuarios/', include('usuarios.urls')),

    # Académico
    path('academico/', include('academico.urls')),

    # sistema de Estudiantes
    path('estudiantes/', include('estudiantes.urls')),

    # sistema de Docentes
    path('docentes/', include('docentes.urls')),

    # Acudientes
    path('acudiente/', include('acudiente.urls')),

    # Administrador
    path('administrador/', include('administrador.urls')),

    # admin
    path('admin/', admin.site.urls),

    # URLs de autenticación personalizadas
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(
        template_name='registration/logged_out.html',
        next_page='/'
    ), name='logout'),

    path('accounts/', include('django.contrib.auth.urls')), 
]

# Handlers de errores
handler404 = custom_404_view
handler500 = custom_500_view

# Servir archivos multimedia en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)