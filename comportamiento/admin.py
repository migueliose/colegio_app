from django.contrib import admin
from .models import *

@admin.register(Comportamiento)
class ComportamientoAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'periodo_academico', 'tipo', 'categoria', 'fecha', 'docente']
    list_filter = ['tipo', 'categoria', 'fecha', 'periodo_academico']
    search_fields = ['estudiante__usuario__nombres', 'descripcion']
    autocomplete_fields = ['estudiante', 'periodo_academico', 'docente']
    date_hierarchy = 'fecha'

@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'periodo_academico', 'fecha', 'estado', 'justificacion']
    list_filter = ['estado', 'fecha', 'periodo_academico']
    search_fields = ['estudiante__usuario__nombres']
    autocomplete_fields = ['estudiante', 'periodo_academico']
    date_hierarchy = 'fecha'

@admin.register(Inconsistencia)
class InconsistenciaAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'tipo', 'fecha', 'descripcion']
    list_filter = ['tipo', 'fecha']
    search_fields = ['estudiante__usuario__nombres', 'tipo', 'descripcion']
    autocomplete_fields = ['estudiante']
    date_hierarchy = 'fecha'
