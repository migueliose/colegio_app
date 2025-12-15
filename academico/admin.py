from django.contrib import admin
from .models import *

@admin.register(NivelEscolar)
class NivelEscolarAdmin(admin.ModelAdmin):
    list_display = ['nombre']
    search_fields = ['nombre']

@admin.register(Grado)
class GradoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'nivel_escolar']
    list_filter = ['nivel_escolar']
    search_fields = ['nombre']
    autocomplete_fields = ['nivel_escolar']

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'nivel_escolar']
    list_filter = ['nivel_escolar']
    search_fields = ['nombre']
    autocomplete_fields = ['nivel_escolar']

@admin.register(Asignatura)
class AsignaturaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'area', 'ih']
    list_filter = ['area']
    search_fields = ['nombre']
    autocomplete_fields = ['area']

@admin.register(Periodo)
class PeriodoAdmin(admin.ModelAdmin):
    list_display = ['nombre']
    search_fields = ['nombre']

@admin.register(Logro)
class LogroAdmin(admin.ModelAdmin):
    list_display = ['asignatura', 'periodo_academico', 'grado', 'tema']
    list_filter = ['asignatura', 'grado']
    search_fields = ['tema', 'asignatura__nombre']
    autocomplete_fields = ['asignatura', 'periodo_academico', 'grado']

@admin.register(HorarioClase)
class HorarioClaseAdmin(admin.ModelAdmin):
    list_display = ['asignatura_grado', 'dia_semana', 'hora_inicio', 'hora_fin', 'salon']
    list_filter = ['dia_semana', 'asignatura_grado__sede']
    search_fields = ['asignatura_grado__asignatura__nombre', 'salon']
    autocomplete_fields = ['asignatura_grado']