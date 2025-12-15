from django.contrib import admin
from .models import *

@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'estado', 'matricula_actual', 'grado_actual', 'sede_actual']
    list_filter = ['estado']
    search_fields = ['usuario__nombres', 'usuario__apellidos']
    autocomplete_fields = ['usuario']
    
    def matricula_actual(self, obj):
        matricula = obj.matricula_actual
        return matricula.codigo_matricula if matricula else 'Sin matrícula'
    matricula_actual.short_description = 'Matrícula Actual'
    
    def grado_actual(self, obj):
        grado = obj.grado_actual
        return grado.grado.nombre if grado else 'Sin grado'
    grado_actual.short_description = 'Grado Actual'
    
    def sede_actual(self, obj):
        sede = obj.sede_actual
        return sede.nombre if sede else 'Sin sede'
    sede_actual.short_description = 'Sede Actual'

@admin.register(Matricula)
class MatriculaAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'año_lectivo', 'sede', 'grado_año_lectivo', 'estado', 'fecha_matricula']
    list_filter = ['estado', 'año_lectivo', 'sede']
    search_fields = ['estudiante__usuario__nombres', 'codigo_matricula']
    autocomplete_fields = ['estudiante', 'año_lectivo', 'sede', 'grado_año_lectivo']
    readonly_fields = ['codigo_matricula', 'fecha_matricula']

@admin.register(Acudiente)
class AcudienteAdmin(admin.ModelAdmin):
    list_display = ['acudiente', 'estudiante', 'parentesco']
    search_fields = ['acudiente__nombres', 'estudiante__usuario__nombres']
    autocomplete_fields = ['acudiente', 'estudiante']

@admin.register(Nota)
class NotaAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'asignatura_grado_año_lectivo', 'periodo_academico', 'calificacion']
    list_filter = ['periodo_academico', 'asignatura_grado_año_lectivo__sede']
    search_fields = ['estudiante__usuario__nombres', 'asignatura_grado_año_lectivo__asignatura__nombre']
    autocomplete_fields = ['estudiante', 'asignatura_grado_año_lectivo', 'periodo_academico']