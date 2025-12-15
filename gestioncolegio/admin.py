from django.contrib import admin
from .models import *

@admin.register(Colegio)
class ColegioAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'direccion', 'resolucion', 'dane', 'estado']
    list_filter = ['estado']
    search_fields = ['nombre', 'dane']

@admin.register(Sede)  # SOLO UNA VEZ - ELIMINA EL DUPLICADO
class SedeAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'colegio', 'direccion', 'telefono', 'director', 'estado']
    list_filter = ['colegio', 'estado']
    search_fields = ['nombre', 'direccion']
    autocomplete_fields = ['colegio', 'director']

@admin.register(RecursosColegio)
class RecursosColegioAdmin(admin.ModelAdmin):
    list_display = ['colegio', 'sitio_web', 'email', 'telefono']
    autocomplete_fields = ['colegio']

@admin.register(AñoLectivo)
class AñoLectivoAdmin(admin.ModelAdmin):
    list_display = ['anho', 'colegio', 'sede', 'fecha_inicio', 'fecha_fin', 'estado']
    list_filter = ['colegio', 'sede', 'estado']
    search_fields = ['anho']
    autocomplete_fields = ['colegio', 'sede']

@admin.register(ConfiguracionGeneral)
class ConfiguracionGeneralAdmin(admin.ModelAdmin):
    list_display = ['colegio', 'año_lectivo_actual', 'max_estudiantes_por_grupo', 'porcentaje_aprobacion']
    autocomplete_fields = ['colegio', 'año_lectivo_actual']

@admin.register(ParametroSistema)
class ParametroSistemaAdmin(admin.ModelAdmin):
    list_display = ['clave', 'valor', 'tipo', 'descripcion']
    list_filter = ['tipo']
    search_fields = ['clave', 'descripcion']

@admin.register(AuditoriaSistema)
class AuditoriaSistemaAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'accion', 'modelo_afectado', 'created_at', 'ip_address']
    list_filter = ['accion', 'created_at']
    search_fields = ['usuario__username', 'modelo_afectado']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(NotificacionSistema)
class NotificacionSistemaAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'titulo', 'tipo', 'leida', 'created_at']
    list_filter = ['tipo', 'leida', 'created_at']
    search_fields = ['usuario__username', 'titulo']
    readonly_fields = ['created_at', 'updated_at']


# ELIMINA ESTE BLOQUE DUPLICADO - YA ESTÁ REGISTRADO ARRIBA
# @admin.register(Sede)
# class SedeAdmin(admin.ModelAdmin):
#     list_display = ['nombre', 'colegio', 'direccion', 'telefono', 'director', 'estado']
#     list_filter = ['colegio', 'estado']
#     search_fields = ['nombre', 'direccion']
#     autocomplete_fields = ['colegio', 'director']