from django.contrib import admin
from .models import *

class CaracteristicaProgramaInline(admin.TabularInline):
    model = CaracteristicaPrograma
    extra = 1

@admin.register(ProgramaAcademico)
class ProgramaAcademicoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'nivel', 'destacado', 'is_active', 'orden']
    list_editable = ['destacado', 'is_active', 'orden']
    list_filter = ['nivel', 'is_active', 'destacado']
    search_fields = ['nombre', 'descripcion_corta']
    prepopulated_fields = {'slug': ['nombre']}
    inlines = [CaracteristicaProgramaInline]

@admin.register(CaracteristicaPrograma)
class CaracteristicaProgramaAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'programa', 'orden']
    list_editable = ['orden']
    list_filter = ['programa']
    search_fields = ['titulo', 'descripcion']
    
@admin.register(Carrusel)
class CarruselAdmin(admin.ModelAdmin):
    list_display = ['description', 'is_active', 'order', 'created']
    list_editable = ['is_active', 'order']
    list_filter = ['is_active', 'created']
    search_fields = ['description']

@admin.register(Welcome)
class WelcomeAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'is_active', 'created']
    list_editable = ['is_active']
    prepopulated_fields = {'slug': ['title']}

@admin.register(RedSocial)
class RedSocialAdmin(admin.ModelAdmin):
    list_display = ['name', 'key', 'link', 'is_active']
    list_editable = ['is_active']

class NoticiaImagenInline(admin.TabularInline):
    model = NoticiaImagen
    extra = 1

@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_published', 'created']
    list_editable = ['is_published']
    list_filter = ['is_published', 'created']
    search_fields = ['title', 'description']
    inlines = [NoticiaImagenInline]

@admin.register(Pagina)
class PaginaAdmin(admin.ModelAdmin):
    list_display = ['title', 'tipo', 'is_published', 'created']
    list_editable = ['is_published']
    list_filter = ['tipo', 'is_published', 'created']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ['title']}

@admin.register(About)
class AboutAdmin(admin.ModelAdmin):
    list_display = ['title', 'tipo', 'is_active', 'created']
    list_editable = ['is_active']
    list_filter = ['tipo', 'is_active', 'created']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ['title']}

@admin.register(Admision)
class AdmisionAdmin(admin.ModelAdmin):
    list_display = ['title', 'tipo', 'is_active', 'created']
    list_editable = ['is_active']
    list_filter = ['tipo', 'is_active', 'created']
    search_fields = ['title', 'description']