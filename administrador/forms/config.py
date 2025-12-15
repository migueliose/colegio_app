# administrador/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from gestioncolegio.models import (
    Colegio, 
    Sede, 
    RecursosColegio, 
    AñoLectivo,
    ConfiguracionGeneral,
    ParametroSistema,
)
from usuarios.models import Usuario
from academico.models import NivelEscolar, Grado

class ColegioForm(forms.ModelForm):
    """Formulario para Colegio"""
    class Meta:
        model = Colegio
        fields = ['nombre', 'direccion', 'resolucion', 'dane', 'estado']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del colegio'
            }),
            'direccion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dirección completa'
            }),
            'resolucion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de resolución'
            }),
            'dane': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código DANE'
            }),
            'estado': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'dane': 'Código DANE',
            'estado': 'Activo',
        }
    
    def clean_dane(self):
        dane = self.cleaned_data.get('dane')
        if dane and not dane.isdigit():
            raise ValidationError(_('El código DANE debe contener solo números'))
        return dane

class SedeForm(forms.ModelForm):
    """Formulario para Sede - VERSIÓN CORREGIDA"""
    class Meta:
        model = Sede
        fields = ['colegio', 'nombre', 'direccion', 'telefono', 'email', 'director', 'estado']
        widgets = {
            'colegio': forms.Select(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la sede'
            }),
            'direccion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dirección de la sede'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono de contacto'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@sede.edu.co'
            }),
            'director': forms.Select(attrs={'class': 'form-control'}),
            'estado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'estado': 'Activa',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # CORRECCIÓN: Buscar todos los posibles nombres para Rector
        # Primero, verificar qué tipos existen en la base de datos
        from usuarios.models import TipoUsuario
        
        # Buscar tipos que contengan "Rector" (case insensitive)
        tipos_rector = TipoUsuario.objects.filter(
            nombre__icontains='rector'
        )
        
        # Si encontramos tipos, obtener los IDs
        if tipos_rector.exists():
            tipo_ids = tipos_rector.values_list('id', flat=True)
            # Filtrar usuarios con esos tipos
            rectores = Usuario.objects.filter(
                tipo_usuario_id__in=tipo_ids,
                estado=True
            ).order_by('nombres', 'apellidos')
        else:
            # Si no encuentra tipos específicos, mostrar todos los usuarios activos
            rectores = Usuario.objects.filter(
                estado=True
            ).order_by('nombres', 'apellidos')
        
        # Aplicar el queryset al campo director
        self.fields['director'].queryset = rectores
        
        # Mejorar la presentación de las opciones
        self.fields['director'].label_from_instance = lambda obj: f"{obj.get_full_name()} ({obj.tipo_usuario.nombre if obj.tipo_usuario else 'Sin rol'})"
        
        # Agregar opción vacía
        self.fields['director'].empty_label = "Seleccionar director..."
        
        # También podemos hacer lo mismo para el colegio
        self.fields['colegio'].empty_label = "Seleccionar colegio..."
        
        # Agregar ayuda contextual
        self.fields['director'].help_text = "Seleccione un usuario con rol de director/rector"
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Normalizar el email
            email = email.lower().strip()
            
            # Verificar si ya existe (excluyendo la instancia actual)
            queryset = Sede.objects.filter(email=email)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise ValidationError('Este correo electrónico ya está registrado en otra sede')
        
        return email
    
    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if telefono:
            # Limpiar caracteres no numéricos (manteniendo + si existe)
            telefono = ''.join(c for c in telefono if c.isdigit() or c == '+')
            
            # Validar longitud mínima
            if len(telefono) < 7:
                raise ValidationError('El teléfono debe tener al menos 7 dígitos')
        
        return telefono
    
    def clean(self):
        cleaned_data = super().clean()
        colegio = cleaned_data.get('colegio')
        nombre = cleaned_data.get('nombre')
        
        # Validar que no haya otra sede con el mismo nombre en el mismo colegio
        if colegio and nombre:
            queryset = Sede.objects.filter(
                colegio=colegio,
                nombre__iexact=nombre.strip()
            )
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                self.add_error('nombre', 'Ya existe una sede con este nombre en el mismo colegio')
        
        return cleaned_data

class RecursosColegioForm(forms.ModelForm):
    """Formulario para Recursos del Colegio"""
    class Meta:
        model = RecursosColegio
        fields = ['escudo', 'bandera', 'sitio_web', 'email', 'telefono']
        widgets = {
            'escudo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'bandera': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'sitio_web': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.colegio.edu.co'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'info@colegio.edu.co'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono principal'
            }),
        }
        labels = {
            'sitio_web': 'Sitio Web',
            'email': 'Correo Electrónico Principal',
        }
    
    def clean_sitio_web(self):
        sitio_web = self.cleaned_data.get('sitio_web')
        if sitio_web and not sitio_web.startswith(('http://', 'https://')):
            sitio_web = 'https://' + sitio_web
        return sitio_web

class AñoLectivoForm(forms.ModelForm):
    """Formulario para Año Lectivo"""
    class Meta:
        model = AñoLectivo
        fields = ['colegio', 'sede', 'anho', 'fecha_inicio', 'fecha_fin', 'estado']
        widgets = {
            'colegio': forms.Select(attrs={'class': 'form-control'}),
            'sede': forms.Select(attrs={'class': 'form-control'}),
            'anho': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 2024'
            }),
            'fecha_inicio': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'fecha_fin': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'estado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'anho': 'Año Lectivo',
            'fecha_inicio': 'Fecha de Inicio',
            'fecha_fin': 'Fecha de Finalización',
            'estado': 'Activo',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar sedes activas
        self.fields['sede'].queryset = Sede.objects.filter(estado=True)
    
    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        
        if fecha_inicio and fecha_fin and fecha_inicio >= fecha_fin:
            self.add_error('fecha_fin', _('La fecha de finalización debe ser posterior a la fecha de inicio'))
        
        anho = cleaned_data.get('anho')
        colegio = cleaned_data.get('colegio')
        sede = cleaned_data.get('sede')
        
        if anho and colegio and sede:
            # Validar que no exista año lectivo duplicado
            qs = AñoLectivo.objects.filter(
                colegio=colegio,
                sede=sede,
                anho=anho
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                self.add_error('anho', _('Ya existe un año lectivo con este nombre para esta sede'))
        
        return cleaned_data

class ConfiguracionGeneralForm(forms.ModelForm):
    """Formulario para Configuración General"""
    class Meta:
        model = ConfiguracionGeneral
        fields = [
            'año_lectivo_actual', 
            'max_estudiantes_por_grupo', 
            'porcentaje_aprobacion', 
            'habilitar_matricula', 
            'habilitar_calificaciones'
        ]
        widgets = {
            'año_lectivo_actual': forms.Select(attrs={'class': 'form-control'}),
            'max_estudiantes_por_grupo': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 100
            }),
            'porcentaje_aprobacion': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 100,
                'step': 0.01
            }),
            'habilitar_matricula': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'habilitar_calificaciones': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'año_lectivo_actual': 'Año Lectivo Actual',
            'max_estudiantes_por_grupo': 'Máximo de Estudiantes por Grupo',
            'porcentaje_aprobacion': 'Porcentaje de Aprobación (%)',
            'habilitar_matricula': 'Habilitar Proceso de Matrícula',
            'habilitar_calificaciones': 'Habilitar Registro de Calificaciones',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo años lectivos activos
        self.fields['año_lectivo_actual'].queryset = AñoLectivo.objects.filter(estado=True)
    
    def clean_max_estudiantes_por_grupo(self):
        max_estudiantes = self.cleaned_data.get('max_estudiantes_por_grupo')
        if max_estudiantes < 1:
            raise ValidationError(_('El número debe ser mayor a 0'))
        if max_estudiantes > 100:
            raise ValidationError(_('El número no puede ser mayor a 100'))
        return max_estudiantes
    
    def clean_porcentaje_aprobacion(self):
        porcentaje = self.cleaned_data.get('porcentaje_aprobacion')
        if porcentaje < 0 or porcentaje > 100:
            raise ValidationError(_('El porcentaje debe estar entre 0 y 100'))
        return porcentaje

class ParametroSistemaForm(forms.ModelForm):
    """Formulario para Parámetros del Sistema"""
    class Meta:
        model = ParametroSistema
        fields = ['clave', 'valor', 'descripcion', 'tipo']
        widgets = {
            'clave': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'nombre_parametro'
            }),
            'valor': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Valor del parámetro'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Descripción del parámetro'
            }),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'clave': 'Clave (nombre)',
            'valor': 'Valor',
            'descripcion': 'Descripción',
            'tipo': 'Tipo de Dato',
        }
    
    def clean_clave(self):
        clave = self.cleaned_data.get('clave')
        if clave:
            clave = clave.strip().lower().replace(' ', '_')
            
            # Validar que no exista clave duplicada
            qs = ParametroSistema.objects.filter(clave=clave)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                raise ValidationError(_('Ya existe un parámetro con esta clave'))
        
        return clave