from django.contrib import admin
from .models import GradoAñoLectivo, AsignaturaGradoAñoLectivo, PeriodoAcademico, DocenteSede

@admin.register(GradoAñoLectivo)
class GradoAñoLectivoAdmin(admin.ModelAdmin):
    list_display = ['grado', 'año_lectivo', 'estado']
    list_filter = ['año_lectivo', 'estado']
    search_fields = ['grado__nombre', 'año_lectivo__anho']
    autocomplete_fields = ['grado', 'año_lectivo']

@admin.register(AsignaturaGradoAñoLectivo)
class AsignaturaGradoAñoLectivoAdmin(admin.ModelAdmin):
    list_display = ['asignatura', 'grado_año_lectivo', 'docente', 'sede']
    list_filter = ['sede', 'grado_año_lectivo__año_lectivo']
    search_fields = ['asignatura__nombre', 'docente__usuario__nombres']
    autocomplete_fields = ['asignatura', 'grado_año_lectivo', 'docente', 'sede']

@admin.register(PeriodoAcademico)
class PeriodoAcademicoAdmin(admin.ModelAdmin):
    list_display = ['año_lectivo', 'periodo', 'fecha_inicio', 'fecha_fin', 'estado']
    list_filter = ['año_lectivo', 'estado']
    search_fields = ['año_lectivo__anho']
    autocomplete_fields = ['año_lectivo', 'periodo']

@admin.register(DocenteSede)
class DocenteSedeAdmin(admin.ModelAdmin):
    list_display = ['docente', 'sede', 'año_lectivo', 'fecha_asignacion', 'estado']
    list_filter = ['sede', 'año_lectivo', 'estado']
    search_fields = ['docente__usuario__nombres', 'sede__nombre']
    autocomplete_fields = ['docente', 'sede', 'año_lectivo']