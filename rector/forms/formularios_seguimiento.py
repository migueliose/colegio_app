from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone
from datetime import date

from comportamiento.models import Comportamiento, Asistencia, Inconsistencia
from estudiantes.models import Nota, Estudiante
from usuarios.models import Docente
from matricula.models import PeriodoAcademico, GradoAñoLectivo, AsignaturaGradoAñoLectivo, Asignatura
from gestioncolegio.models import AñoLectivo

# ========== COMPORTAMIENTO ==========
class ComportamientoForm(forms.ModelForm):
    class Meta:
        model = Comportamiento
        fields = ['estudiante', 'periodo_academico', 'tipo', 'categoria', 'descripcion', 'fecha']
        widgets = {
            'estudiante': forms.Select(attrs={'class': 'form-control select2'}),
            'periodo_academico': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción detallada del comportamiento...'
            }),
            'fecha': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'value': timezone.now().strftime('%Y-%m-%d')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar periodos activos
        self.fields['periodo_academico'].queryset = PeriodoAcademico.objects.filter(
            estado=True
        ).select_related('año_lectivo', 'periodo').order_by('-año_lectivo__anho')

class ComportamientoFilterForm(forms.Form):
    TIPO_CHOICES = [('', 'Todos')] + Comportamiento.TIPOS_COMPORTAMIENTO
    CATEGORIA_CHOICES = [('', 'Todas')] + Comportamiento.CATEGORIAS
    
    estudiante = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar estudiante...'
        })
    )
    periodo_academico = forms.ModelChoiceField(
        queryset=PeriodoAcademico.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    categoria = forms.ChoiceField(
        choices=CATEGORIA_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    fecha_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar periodos académicos
        self.fields['periodo_academico'].queryset = PeriodoAcademico.objects.filter(
            estado=True
        ).select_related('año_lectivo', 'periodo').order_by('-año_lectivo__anho')

# ========== ASISTENCIA ==========
class AsistenciaForm(forms.ModelForm):
    class Meta:
        model = Asistencia
        fields = ['estudiante', 'periodo_academico', 'fecha', 'estado', 'justificacion']
        widgets = {
            'estudiante': forms.Select(attrs={'class': 'form-control select2'}),
            'periodo_academico': forms.Select(attrs={'class': 'form-control'}),
            'fecha': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'value': timezone.now().strftime('%Y-%m-%d')
            }),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'justificacion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Justificación de la falta (opcional)...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['periodo_academico'].queryset = PeriodoAcademico.objects.filter(
            estado=True
        ).select_related('año_lectivo', 'periodo').order_by('-año_lectivo__anho')

class AsistenciaBulkForm(forms.Form):
    """Formulario para registro masivo de asistencia"""
    periodo_academico = forms.ModelChoiceField(
        queryset=PeriodoAcademico.objects.filter(estado=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Periodo Académico'
    )
    grado_año_lectivo = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Grado',
        required=False
    )
    fecha = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'value': timezone.now().strftime('%Y-%m-%d')
        }),
        label='Fecha'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar grados activos
        self.fields['grado_año_lectivo'].queryset = self.get_grados_activos()
    
    def get_grados_activos(self):
        from matricula.models import GradoAñoLectivo
        return GradoAñoLectivo.objects.filter(estado=True).select_related(
            'grado', 'año_lectivo'
        ).order_by('grado__nivel_escolar', 'grado__nombre')

class AsistenciaFilterForm(forms.Form):
    ESTADO_CHOICES = [
        ('', 'Todos'),
        ('A', 'Asistió'),
        ('F', 'Faltó'),
        ('J', 'Falta justificada'),
    ]
    
    estudiante = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar estudiante...'
        })
    )
    periodo_academico = forms.ModelChoiceField(
        queryset=PeriodoAcademico.objects.filter(estado=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    grado = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    estado = forms.ChoiceField(
        choices=ESTADO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    fecha_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from matricula.models import GradoAñoLectivo
        self.fields['grado'].queryset = GradoAñoLectivo.objects.filter(
            estado=True
        ).select_related('grado').order_by('grado__nombre')

# ========== INCONSISTENCIAS ==========
class InconsistenciaForm(forms.ModelForm):
    class Meta:
        model = Inconsistencia
        fields = ['estudiante', 'tipo', 'descripcion']
        widgets = {
            'estudiante': forms.Select(attrs={'class': 'form-control select2'}),
            'tipo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tipo de inconsistencia...'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descripción detallada de la inconsistencia...'
            }),
        }

class InconsistenciaFilterForm(forms.Form):
    estudiante = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar estudiante...'
        })
    )
    tipo = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tipo de inconsistencia...'
        })
    )
    fecha_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )

# ========== CALIFICACIONES ==========
class NotaForm(forms.ModelForm):
    class Meta:
        model = Nota
        fields = ['estudiante', 'asignatura_grado_año_lectivo', 'periodo_academico', 'calificacion', 'observaciones']
        widgets = {
            'estudiante': forms.Select(attrs={'class': 'form-control'}),
            'asignatura_grado_año_lectivo': forms.Select(attrs={'class': 'form-control'}),
            'periodo_academico': forms.Select(attrs={'class': 'form-control'}),
            'calificacion': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '5',
                'step': '0.1',
                'placeholder': '0.0 - 5.0'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones adicionales (opcional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar opciones relevantes
        self.fields['estudiante'].queryset = Estudiante.objects.filter(
            estado=True  # El modelo Estudiante SÍ tiene campo estado
        ).select_related('usuario').order_by('usuario__nombres')
        
        # CORRECCIÓN: El modelo AsignaturaGradoAñoLectivo NO tiene campo estado
        self.fields['asignatura_grado_año_lectivo'].queryset = AsignaturaGradoAñoLectivo.objects.select_related(
            'asignatura',
            'grado_año_lectivo__grado'
        ).order_by('asignatura__nombre')
        
        # Filtrar periodos académicos activos
        self.fields['periodo_academico'].queryset = PeriodoAcademico.objects.filter(
            estado=True  # El modelo PeriodoAcademico SÍ tiene campo estado
        ).select_related('año_lectivo', 'periodo').order_by('-fecha_inicio')
    
    def clean_calificacion(self):
        calificacion = self.cleaned_data.get('calificacion')
        if calificacion is not None:
            if calificacion < 0 or calificacion > 5:
                raise forms.ValidationError("La calificación debe estar entre 0.0 y 5.0")
        return calificacion
    
class NotaBulkForm(forms.Form):
    """Formulario para registro masivo de calificaciones"""
    periodo_academico = forms.ModelChoiceField(
        queryset=PeriodoAcademico.objects.filter(estado=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Periodo Académico'
    )
    asignatura_grado_año_lectivo = forms.ModelChoiceField(
        queryset=AsignaturaGradoAñoLectivo.objects.filter(grado_año_lectivo__estado=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Asignatura'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Configurar queryset de asignaturas
        self.fields['asignatura_grado_año_lectivo'].queryset = AsignaturaGradoAñoLectivo.objects.filter(
            grado_año_lectivo__estado=True
        ).select_related(
            'asignatura', 
            'grado_año_lectivo__grado',
            'grado_año_lectivo__año_lectivo'
        ).order_by('asignatura__nombre')

class NotaFilterForm(forms.Form):
    estudiante = forms.CharField(
        required=False, 
        label="Estudiante",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre, apellido o documento'
        })
    )
    
    periodo_academico = forms.ModelChoiceField(
        queryset=PeriodoAcademico.objects.select_related('año_lectivo', 'periodo').all(),
        required=False,
        label="Periodo Académico",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # CORRECCIÓN COMPLETA: Cambiar la relación
    asignatura = forms.ModelChoiceField(
        queryset=Asignatura.objects.select_related('area').all().order_by('nombre'),
        required=False,
        label="Asignatura",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    grado = forms.ModelChoiceField(
        queryset=GradoAñoLectivo.objects.select_related(
            'grado', 
            'grado__nivel_escolar'
        ).filter(estado=True),
        required=False,
        label="Grado",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    calificacion_min = forms.DecimalField(
        max_digits=5, 
        decimal_places=2,
        required=False,
        label="Calificación Mínima",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.0',
            'min': '0',
            'max': '5',
            'step': '0.1'
        })
    )
    
    calificacion_max = forms.DecimalField(
        max_digits=5, 
        decimal_places=2,
        required=False,
        label="Calificación Máxima",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '5.0',
            'min': '0',
            'max': '5',
            'step': '0.1'
        })
    )

# ========== DASHBOARD DE SEGUIMIENTO ==========
class SeguimientoFilterForm(forms.Form):
    """Formulario para filtrar el dashboard de seguimiento"""
    periodo_academico = forms.ModelChoiceField(
        queryset=PeriodoAcademico.objects.filter(estado=True),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'id': 'id_periodo_academico',
            'data-placeholder': 'Seleccionar periodo...'
        }),
        label='Periodo Académico',
        empty_label="Todos los periodos"
    )
    
    grado = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'id': 'id_grado',
            'data-placeholder': 'Seleccionar grado...'
        }),
        label='Grado',
        empty_label="Todos los grados"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar grados activos del año actual
        from matricula.models import GradoAñoLectivo
        
        año_actual = None
        from gestioncolegio.models import ConfiguracionGeneral, Colegio
        
        colegio = Colegio.objects.filter(estado=True).first()
        if colegio:
            config = ConfiguracionGeneral.objects.filter(colegio=colegio).first()
            if config and config.año_lectivo_actual:
                año_actual = config.año_lectivo_actual
        
        if año_actual:
            self.fields['grado'].queryset = GradoAñoLectivo.objects.filter(
                año_lectivo=año_actual,
                estado=True
            ).select_related('grado').order_by('grado__nombre')
        else:
            self.fields['grado'].queryset = GradoAñoLectivo.objects.none()
        
        # Configurar periodo académico
        if año_actual:
            self.fields['periodo_academico'].queryset = PeriodoAcademico.objects.filter(
                año_lectivo=año_actual,
                estado=True
            ).select_related('periodo').order_by('periodo__nombre')
        
        # Añadir clases para Select2 si no están en el widget
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'