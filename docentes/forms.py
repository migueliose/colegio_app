# gestioncolegio/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

# Modelos del sistema
from academico.models import Logro, Grado, Asignatura
from estudiantes.models import Estudiante, Nota
from comportamiento.models import Comportamiento
from usuarios.models import Docente
from matricula.models import AsignaturaGradoAñoLectivo, PeriodoAcademico

# En forms.py (o donde tengas tu LogroForm)
from django import forms
from academico.models import Logro, Grado, Asignatura
from matricula.models import PeriodoAcademico, AsignaturaGradoAñoLectivo
from usuarios.models import Docente
from gestioncolegio.models import AñoLectivo

class LogroForm(forms.ModelForm):
    class Meta:
        model = Logro
        fields = [
            'grado', 'asignatura', 'periodo_academico', 'tema',
            'descripcion_superior', 'descripcion_alto',
            'descripcion_basico', 'descripcion_bajo'
        ]
        widgets = {
            'tema': forms.Textarea(attrs={'rows': 3}),
            'descripcion_superior': forms.Textarea(attrs={'rows': 4}),
            'descripcion_alto': forms.Textarea(attrs={'rows': 4}),
            'descripcion_basico': forms.Textarea(attrs={'rows': 4}),
            'descripcion_bajo': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        # Extraer parámetros personalizados
        self.user = kwargs.pop('user', None)
        self.is_editing = kwargs.pop('is_editing', False)  # Agregar este parámetro
        
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.filtrar_choices_por_docente()
        
        # Añadir clases CSS a los campos
        for field_name, field in self.fields.items():
            if field_name != 'tema' and field_name not in ['descripcion_superior', 'descripcion_alto', 'descripcion_basico', 'descripcion_bajo']:
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})
            
            # Marcar campos obligatorios
            if field_name in ['grado', 'asignatura', 'periodo_academico']:
                field.required = True
                field.widget.attrs.update({'required': 'required'})
    
    def filtrar_choices_por_docente(self):
        """Filtra las opciones disponibles para el docente actual"""
        try:
            docente = Docente.objects.get(usuario=self.user)
            
            # Obtener año lectivo actual
            año_actual = AñoLectivo.objects.filter(estado=True).first()
            
            if not año_actual:
                return
            
            # Obtener asignaciones del docente
            asignaciones = AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente,
                grado_año_lectivo__año_lectivo__estado=True
            ).select_related(
                'grado_año_lectivo__grado',
                'asignatura'
            )
            
            # Filtrar grados disponibles
            grados_ids = asignaciones.values_list(
                'grado_año_lectivo__grado_id', flat=True
            ).distinct()
            self.fields['grado'].queryset = Grado.objects.filter(
                id__in=grados_ids
            ).order_by('nombre')
            
            # Filtrar asignaturas disponibles (se llenará dinámicamente con AJAX)
            asignaturas_ids = asignaciones.values_list(
                'asignatura_id', flat=True
            ).distinct()
            self.fields['asignatura'].queryset = Asignatura.objects.filter(
                id__in=asignaturas_ids
            ).order_by('nombre')
            
            # Filtrar periodos disponibles
            if año_actual:
                self.fields['periodo_academico'].queryset = PeriodoAcademico.objects.filter(
                    año_lectivo=año_actual,
                    estado=True
                ).select_related('periodo').order_by('fecha_inicio')
            
        except Docente.DoesNotExist:
            # Si no es docente, vaciar los choices
            self.fields['grado'].queryset = Grado.objects.none()
            self.fields['asignatura'].queryset = Asignatura.objects.none()
            self.fields['periodo_academico'].queryset = PeriodoAcademico.objects.none()
    
    def clean(self):
        """Validación adicional del formulario"""
        cleaned_data = super().clean()
        
        # Verificar que al menos un descriptor esté completado
        descriptores = [
            cleaned_data.get('descripcion_superior'),
            cleaned_data.get('descripcion_alto'),
            cleaned_data.get('descripcion_basico'),
            cleaned_data.get('descripcion_bajo')
        ]
        
        if not any(descriptor for descriptor in descriptores if descriptor):
            raise forms.ValidationError(
                "Debe completar al menos un descriptor de desempeño."
            )
        
        # Si estamos editando y el usuario fue pasado, verificar permisos
        if self.is_editing and self.user and self.instance.pk:
            try:
                docente = Docente.objects.get(usuario=self.user)
                grado = cleaned_data.get('grado')
                asignatura = cleaned_data.get('asignatura')
                
                # Verificar que el docente aún tiene permisos para esta combinación
                tiene_permiso = AsignaturaGradoAñoLectivo.objects.filter(
                    docente=docente,
                    asignatura=asignatura,
                    grado_año_lectivo__grado=grado,
                    grado_año_lectivo__año_lectivo__estado=True
                ).exists()
                
                if not tiene_permiso:
                    raise forms.ValidationError(
                        "No tiene permisos para editar este logro. "
                        "Ya no está asignado a esta asignatura/grado."
                    )
                    
            except Docente.DoesNotExist:
                raise forms.ValidationError("Perfil de docente no encontrado.")
        
        return cleaned_data
    
class ComportamientoForm(forms.ModelForm):
    """Formulario para registrar observaciones de comportamiento"""
    
    # Campo adicional para filtrar por grado (no se guarda en el modelo)
    grado_filtro = forms.ModelChoiceField(
        queryset=Grado.objects.none(),
        required=False,
        label="Filtrar por Grado",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_grado_filtro'
        })
    )
    
    class Meta:
        model = Comportamiento
        fields = [
            'estudiante',
            'periodo_academico', 
            'tipo',
            'categoria',
            'descripcion',
            'fecha'
        ]
        widgets = {
            'estudiante': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_estudiante',
                'disabled': True
            }),
            'periodo_academico': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_periodo'
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_tipo'
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_categoria'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describa detalladamente el comportamiento observado...',
                'data-min-length': '10',
                'data-max-length': '500'
            }),
            'fecha': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'max': timezone.now().date().isoformat()
            }),
        }
        labels = {
            'estudiante': 'Estudiante',
            'periodo_academico': 'Período Académico',
            'tipo': 'Tipo de Observación',
            'categoria': 'Categoría del Comportamiento',
            'descripcion': 'Descripción Detallada',
            'fecha': 'Fecha del Comportamiento'
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Configurar fecha actual por defecto
        if not self.instance.pk:
            self.fields['fecha'].initial = timezone.now().date()
        
        # Configurar períodos académicos
        self.fields['periodo_academico'].queryset = PeriodoAcademico.objects.filter(
            año_lectivo__estado=True
        ).select_related('periodo', 'año_lectivo').order_by('-fecha_inicio')
        
        # Configurar opciones para tipo y categoría
        self.configure_choice_fields()
        
        # Configurar campos según el docente
        if self.user:
            docente = self.get_docente()
            if docente:
                self.configure_grade_filter(docente)
                self.configure_student_field(docente)
        
        # Si es una edición, habilitar campos y cargar datos existentes
        if self.instance and self.instance.pk:
            self.fields['estudiante'].disabled = False
            # Si hay un estudiante seleccionado, cargar su grado en el filtro
            if self.instance.estudiante and self.instance.estudiante.grado_actual:
                self.fields['grado_filtro'].initial = self.instance.estudiante.grado_actual.grado

    def configure_choice_fields(self):
        """Configura los campos de selección con opciones mejoradas"""
        self.fields['tipo'].choices = [
            ('', '--------- Seleccione el tipo ---------'),
            ('Positivo', '✅ Comportamiento Positivo'),
            ('Negativo', '❌ Comportamiento a Mejorar')
        ]
        
        self.fields['categoria'].choices = [
            ('', '--------- Seleccione la categoría ---------'),
            ('Académico', '📚 Desempeño Académico'),
            ('Comportamiento', '👥 Comportamiento en Clase'),
            ('Disciplina', '⚖️ Disciplina y Normas'),
            ('Responsabilidad', '✅ Responsabilidad'),
            ('Respeto', '🙏 Respeto y Valores'),
            ('Social', '🤝 Relaciones Sociales'),
            ('Otro', '🔍 Otro Comportamiento')
        ]

    def get_docente(self):
        """Obtiene el objeto docente del usuario actual"""
        try:
            return Docente.objects.select_related('usuario').get(usuario=self.user)
        except (Docente.DoesNotExist, AttributeError):
            return None

    def configure_grade_filter(self, docente):
        """Configura el filtro de grado"""
        grados_ids = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__año_lectivo__estado=True
        ).values_list('grado_año_lectivo__grado_id', flat=True).distinct()
        
        # CORRECCIÓN: Solo ordenar por nombre (no existe 'orden' en Grado)
        self.fields['grado_filtro'].queryset = Grado.objects.filter(
            id__in=grados_ids
        ).select_related('nivel_escolar').order_by('nombre')  # Solo 'nombre'

    def configure_student_field(self, docente):
        """Configura el campo de estudiante"""
        self.fields['estudiante'].queryset = Estudiante.objects.none()
        
        # Si hay un grado seleccionado en el filtro, cargar estudiantes
        grado_filtro = self.data.get('grado_filtro') if self.data else None
        if grado_filtro:
            self.fields['estudiante'].queryset = self.get_available_students(docente, grado_filtro)
            self.fields['estudiante'].disabled = False
        
        # Si estamos editando, cargar estudiantes del grado del estudiante
        elif self.instance and self.instance.pk and self.instance.estudiante:
            grado = self.instance.estudiante.grado_actual.grado
            self.fields['estudiante'].queryset = self.get_available_students(docente, grado.id)
            self.fields['estudiante'].disabled = False

    def get_available_students(self, docente, grado_id):
        """Obtiene estudiantes disponibles para el docente en el grado"""
        return Estudiante.objects.filter(
            grado_actual__grado_id=grado_id,
            grado_actual__año_lectivo__estado=True,
            estado=True
        ).select_related('usuario').order_by('usuario__apellidos', 'usuario__nombres')

    def clean(self):
        cleaned_data = super().clean()
        estudiante = cleaned_data.get('estudiante')
        fecha = cleaned_data.get('fecha')
        descripcion = cleaned_data.get('descripcion')
        
        self.validate_date(fecha)
        self.validate_duplicate_behavior(estudiante, fecha, descripcion)
        
        return cleaned_data

    def validate_date(self, fecha):
        """Valida la fecha del comportamiento"""
        if fecha:
            hoy = timezone.now().date()
            
            if fecha > hoy:
                raise ValidationError({
                    'fecha': "La fecha no puede ser futura."
                })
            
            if fecha < hoy - timedelta(days=30):
                raise ValidationError({
                    'fecha': "No puede registrar comportamientos con más de 30 días de antigüedad."
                })

    def validate_duplicate_behavior(self, estudiante, fecha, descripcion):
        """Valida que no exista un registro duplicado"""
        if estudiante and fecha and descripcion:
            existing = Comportamiento.objects.filter(
                estudiante=estudiante,
                fecha=fecha,
                descripcion__iexact=descripcion.strip()
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing.exists():
                raise ValidationError({
                    'descripcion': "Ya existe un registro similar para este estudiante en la fecha seleccionada."
                })

    def clean_descripcion(self):
        descripcion = self.cleaned_data.get('descripcion', '').strip()
        
        if not descripcion:
            raise ValidationError("La descripción del comportamiento es obligatoria.")
        
        if len(descripcion) < 10:
            raise ValidationError("La descripción debe tener al menos 10 caracteres.")
        
        if len(descripcion) > 500:
            raise ValidationError("La descripción no puede exceder los 500 caracteres.")
        
        return descripcion

    def save(self, commit=True):
        comportamiento = super().save(commit=False)
        
        # Asignar automáticamente el docente
        if self.user and not comportamiento.docente:
            docente = self.get_docente()
            if docente:
                comportamiento.docente = docente
        
        if commit:
            comportamiento.save()
        
        return comportamiento
    
class NotaForm(forms.ModelForm):
    """Formulario para registrar calificaciones individuales"""
    
    class Meta:
        model = Nota
        fields = ['calificacion', 'observaciones']
        widgets = {
            'calificacion': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '5',
                'step': '0.1',
                'placeholder': '0.0 - 5.0'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observaciones adicionales...'
            }),
        }
        labels = {
            'calificacion': 'Calificación',
            'observaciones': 'Observaciones'
        }

    def clean_calificacion(self):
        calificacion = self.cleaned_data.get('calificacion')
        
        if calificacion is not None:
            if calificacion < 0 or calificacion > 5:
                raise ValidationError("La calificación debe estar entre 0.0 y 5.0")
            
            # Redondear a un decimal
            calificacion = round(calificacion, 1)
        
        return calificacion