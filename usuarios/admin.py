from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ['username', 'email', 'get_full_name', 'tipo_usuario', 'estado', 'is_active']
    list_filter = ['tipo_usuario', 'estado', 'is_active', 'is_staff']
    search_fields = ['username', 'email', 'nombres', 'apellidos', 'numero_documento']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Información Personal', {
            'fields': (
                'tipo_documento', 'numero_documento', 'nombres', 'apellidos',
                'direccion', 'telefono', 'sexo', 'fecha_nacimiento', 'tipo_usuario'
            )
        }),
        ('Estado del Sistema', {
            'fields': ('estado',)
        }),
    )
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Nombre Completo'

@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
    list_display = ['nombre']
    search_fields = ['nombre']

@admin.register(TipoUsuario)
class TipoUsuarioAdmin(admin.ModelAdmin):
    list_display = ['nombre']
    search_fields = ['nombre']

@admin.register(Docente)
class DocenteAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'estado', 'created_at']
    list_filter = ['estado']
    search_fields = ['usuario__nombres', 'usuario__apellidos']
    autocomplete_fields = ['usuario']

@admin.register(ContactoDocente)
class ContactoDocenteAdmin(admin.ModelAdmin):
    list_display = ['nombres', 'apellidos', 'docente', 'telefono', 'relacion']
    search_fields = ['nombres', 'apellidos', 'docente__usuario__nombres']
    autocomplete_fields = ['docente']