# rector/forms.py - Agregar estos forms

from django import forms
from gestioncolegio.models import AñoLectivo
from matricula.models import PeriodoAcademico, DocenteSede, AsignaturaGradoAñoLectivo
from gestioncolegio.models import Sede
from usuarios.models import Usuario

class AñoLectivoForm(forms.ModelForm):
    class Meta:
        model = AñoLectivo
        fields = ['colegio', 'sede', 'anho', 'fecha_inicio', 'fecha_fin', 'estado']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }

class PeriodoAcademicoForm(forms.ModelForm):
    class Meta:
        model = PeriodoAcademico
        fields = ['año_lectivo', 'periodo', 'fecha_inicio', 'fecha_fin', 'estado']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }

class SedeForm(forms.ModelForm):
    class Meta:
        model = Sede
        fields = ['colegio', 'nombre', 'direccion', 'telefono', 'email', 'director', 'estado']
        widgets = {
            'direccion': forms.Textarea(attrs={'rows': 3}),
            'telefono': forms.TextInput(attrs={'placeholder': 'Ej: +57 300 123 4567'}),
            'email': forms.EmailInput(attrs={'placeholder': 'ejemplo@colegio.edu.co'}),
        }
        labels = {
            'colegio': 'Colegio al que pertenece',
            'nombre': 'Nombre de la sede',
            'direccion': 'Dirección completa',
            'telefono': 'Teléfono de contacto',
            'email': 'Correo electrónico',
            'director': 'Director asignado',
            'estado': 'Sede activa',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar directores disponibles
        self.fields['director'].queryset = Usuario.objects.filter(
            tipo_usuario__nombre__in=['Rector', 'Administrador']
        )
        # Hacer campos más atractivos
        for field_name, field in self.fields.items():
            if field_name != 'estado':
                field.widget.attrs['class'] = 'form-control'
            if field.required:
                field.widget.attrs['required'] = 'required'
    
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        colegio = self.cleaned_data.get('colegio')
        
        if nombre and colegio:
            # Verificar unicidad
            qs = Sede.objects.filter(
                colegio=colegio,
                nombre__iexact=nombre
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                raise forms.ValidationError(
                    f'Ya existe una sede con el nombre "{nombre}" en este colegio.'
                )
        
        return nombre