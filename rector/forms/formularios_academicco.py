# rector/forms/academico.py
from django import forms
from django.db.models import Count, Avg, Q, Sum, Max, Min
from django.core.exceptions import ValidationError
from estudiantes.models import Matricula, Acudiente, Estudiante
from usuarios.models import TipoDocumento, TipoUsuario, Usuario, Docente  # Importar correctamente
from gestioncolegio.models import AñoLectivo, Sede
from matricula.models import GradoAñoLectivo, AsignaturaGradoAñoLectivo, DocenteSede, PeriodoAcademico
from academico.models import NivelEscolar, Grado, Asignatura, Area, Periodo, Logro


class MatriculaForm(forms.ModelForm):
    """Formulario para crear/editar matrícula"""
    nivel = forms.ModelChoiceField(
        queryset=NivelEscolar.objects.all(),
        required=False,
        label="Nivel Escolar",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'onchange': 'filtrarGrados()'
        })
    )
    
    class Meta:
        model = Matricula
        fields = ['año_lectivo', 'sede', 'grado_año_lectivo', 'estado', 'observaciones']
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'año_lectivo': forms.Select(attrs={'class': 'form-select'}),
            'sede': forms.Select(attrs={'class': 'form-select'}),
            'grado_año_lectivo': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.estudiante = kwargs.pop('estudiante', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar años lectivos activos
        self.fields['año_lectivo'].queryset = AñoLectivo.objects.filter(estado=True)
        
        # Filtrar sedes activas
        self.fields['sede'].queryset = Sede.objects.filter(estado=True)
        
        # Inicialmente mostrar todos los grados activos
        self.fields['grado_año_lectivo'].queryset = GradoAñoLectivo.objects.filter(
            estado=True
        ).select_related('grado__nivel_escolar')
        
        # Ordenar grados por nombre
        self.fields['grado_año_lectivo'].queryset = self.fields['grado_año_lectivo'].queryset.order_by(
            'grado__nivel_escolar__nombre', 'grado__nombre'
        )
        
        # Si estamos editando, establecer el nivel inicial
        if self.instance and self.instance.pk and self.instance.grado_año_lectivo:
            self.fields['nivel'].initial = self.instance.grado_año_lectivo.grado.nivel_escolar
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validar que no exista matrícula para el mismo año
        año_lectivo = cleaned_data.get('año_lectivo')
        if self.estudiante and año_lectivo:
            matricula_existente = Matricula.objects.filter(
                estudiante=self.estudiante,
                año_lectivo=año_lectivo
            ).exclude(pk=self.instance.pk if self.instance else None).exists()
            
            if matricula_existente:
                raise forms.ValidationError({
                    'año_lectivo': 'El estudiante ya tiene matrícula para este año lectivo'
                })
        
        # Validar que el grado pertenezca al año lectivo seleccionado
        grado_año_lectivo = cleaned_data.get('grado_año_lectivo')
        if año_lectivo and grado_año_lectivo:
            if grado_año_lectivo.año_lectivo != año_lectivo:
                raise forms.ValidationError({
                    'grado_año_lectivo': 'El grado seleccionado no pertenece al año lectivo elegido'
                })
        
        return cleaned_data

class EstudianteCreateForm(forms.ModelForm):
    """Formulario para crear un estudiante nuevo"""
    # Campos del usuario
    nombres = forms.CharField(
        max_length=100, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese los nombres'})
    )
    apellidos = forms.CharField(
        max_length=100, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese los apellidos'})
    )
    tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    numero_documento = forms.CharField(
        max_length=50, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese número de documento'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ejemplo@email.com'})
    )
    telefono = forms.CharField(
        max_length=20, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese número telefónico'})
    )
    direccion = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Ingrese dirección completa'}), 
        required=False
    )
    sexo = forms.ChoiceField(
        choices=Usuario.SEXO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    fecha_nacimiento = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    class Meta:
        model = Estudiante
        fields = []  # No usamos campos directos del modelo Estudiante
    
    def clean_numero_documento(self):
        numero_documento = self.cleaned_data['numero_documento']
        
        # Verificar si ya existe un usuario con este documento
        usuario_existente = Usuario.objects.filter(
            numero_documento=numero_documento
        ).exists()
        
        if usuario_existente:
            raise forms.ValidationError('Ya existe un usuario con este número de documento')
        
        return numero_documento
    
    def save(self, commit=True):
        # Crear usuario primero
        tipo_estudiante, _ = TipoUsuario.objects.get_or_create(
            nombre='Estudiante',
            defaults={'nombre': 'Estudiante'}
        )
        
        usuario = Usuario.objects.create_user(
            username=self.cleaned_data['numero_documento'],
            password=self.cleaned_data['numero_documento'],  # Contraseña temporal
            tipo_usuario=tipo_estudiante,
            nombres=self.cleaned_data['nombres'],
            apellidos=self.cleaned_data['apellidos'],
            tipo_documento=self.cleaned_data['tipo_documento'],
            numero_documento=self.cleaned_data['numero_documento'],
            email=self.cleaned_data.get('email'),
            telefono=self.cleaned_data.get('telefono'),
            direccion=self.cleaned_data.get('direccion'),
            sexo=self.cleaned_data.get('sexo'),
            fecha_nacimiento=self.cleaned_data.get('fecha_nacimiento'),
        )
        
        # Crear estudiante
        estudiante = Estudiante.objects.create(
            usuario=usuario,
            estado=True
        )
        
        return estudiante
    
class AcudienteForm(forms.ModelForm):
    """Formulario para crear/editar acudiente"""
    # Campos del usuario
    nombres = forms.CharField(
        max_length=100, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    apellidos = forms.CharField(
        max_length=100, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    numero_documento = forms.CharField(
        max_length=50, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    telefono = forms.CharField(
        max_length=20, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    direccion = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}), 
        required=False
    )
    
    class Meta:
        model = Acudiente
        fields = ['parentesco']
        widgets = {
            'parentesco': forms.TextInput(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        self.estudiante = kwargs.pop('estudiante', None)
        super().__init__(*args, **kwargs)
        
        # Establecer valores iniciales si estamos editando
        if self.instance and self.instance.pk:
            usuario = self.instance.acudiente
            self.fields['nombres'].initial = usuario.nombres
            self.fields['apellidos'].initial = usuario.apellidos
            self.fields['tipo_documento'].initial = usuario.tipo_documento
            self.fields['numero_documento'].initial = usuario.numero_documento
            self.fields['email'].initial = usuario.email
            self.fields['telefono'].initial = usuario.telefono
            self.fields['direccion'].initial = usuario.direccion
    
    def clean_numero_documento(self):
        numero_documento = self.cleaned_data['numero_documento']
        
        # Verificar si ya existe un usuario con este documento
        usuario_existente = Usuario.objects.filter(
            numero_documento=numero_documento,
            tipo_usuario__nombre='Acudiente'
        ).exclude(pk=self.instance.acudiente.pk if self.instance.pk else None).exists()
        
        if usuario_existente:
            raise forms.ValidationError('Ya existe un acudiente con este número de documento')
        
        return numero_documento
    
    def save(self, commit=True):
        acudiente = super().save(commit=False)
        
        # Crear o actualizar usuario
        usuario_data = {
            'nombres': self.cleaned_data['nombres'],
            'apellidos': self.cleaned_data['apellidos'],
            'tipo_documento': self.cleaned_data['tipo_documento'],
            'numero_documento': self.cleaned_data['numero_documento'],
            'email': self.cleaned_data['email'],
            'telefono': self.cleaned_data['telefono'],
            'direccion': self.cleaned_data['direccion'],
        }
        
        if not self.instance.pk:  # Creando nuevo
            # Buscar tipo de usuario "Acudiente"
            tipo_acudiente, _ = TipoUsuario.objects.get_or_create(
                nombre='Acudiente',
                defaults={'nombre': 'Acudiente'}
            )
            
            # Crear nuevo usuario
            usuario = Usuario.objects.create_user(
                username=usuario_data['numero_documento'],
                password=usuario_data['numero_documento'],  # Contraseña temporal
                tipo_usuario=tipo_acudiente,
                **{k: v for k, v in usuario_data.items()}
            )
            acudiente.acudiente = usuario
        else:  # Editando existente
            usuario = acudiente.acudiente
            for key, value in usuario_data.items():
                setattr(usuario, key, value)
            if commit:
                usuario.save()
        
        # Asignar estudiante si es nuevo
        if not acudiente.pk and self.estudiante:
            acudiente.estudiante = self.estudiante
        
        if commit:
            acudiente.save()
        return acudiente
    
class CrearGradoAñoLectivoForm(forms.ModelForm):
    """Formulario para crear nuevo grado año lectivo"""
    copiar_de_año_anterior = forms.BooleanField(
        required=False,
        label='Copiar grados del año anterior',
        help_text='Selecciona para copiar todos los grados del año anterior'
    )
    
    año_anterior = forms.ModelChoiceField(
        queryset=AñoLectivo.objects.none(),
        required=False,
        label='Año anterior a copiar',
        help_text='Selecciona el año del cual copiar los grados'
    )
    
    grados_seleccionados = forms.ModelMultipleChoiceField(
        queryset=Grado.objects.none(),
        required=False,
        label='Grados específicos a copiar',
        widget=forms.CheckboxSelectMultiple,
        help_text='Selecciona grados específicos a copiar (si no se selecciona, se copian todos)'
    )
    
    class Meta:
        model = GradoAñoLectivo
        fields = ['año_lectivo', 'grado']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar años lectivos activos
        self.fields['año_lectivo'].queryset = AñoLectivo.objects.filter(estado=True)
        
        # Obtener años anteriores (excluyendo el actual si existe)
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if año_actual:
            años_anteriores = AñoLectivo.objects.filter(
                colegio=año_actual.colegio,
                sede=año_actual.sede
            ).exclude(id=año_actual.id).order_by('-anho')
            self.fields['año_anterior'].queryset = años_anteriores
            self.fields['grados_seleccionados'].queryset = Grado.objects.filter(
                grados_año_lectivo__año_lectivo__in=años_anteriores
            ).distinct()
        else:
            self.fields['año_anterior'].queryset = AñoLectivo.objects.none()
            self.fields['grados_seleccionados'].queryset = Grado.objects.none()
        
        # Hacer el campo grado opcional si se va a copiar
        self.fields['grado'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        copiar_de_año_anterior = cleaned_data.get('copiar_de_año_anterior')
        año_anterior = cleaned_data.get('año_anterior')
        año_lectivo = cleaned_data.get('año_lectivo')
        grado = cleaned_data.get('grado')
        
        # Validaciones
        if not copiar_de_año_anterior and not grado:
            self.add_error('grado', 'Debe seleccionar un grado o marcar la opción de copiar')
        
        if copiar_de_año_anterior and not año_anterior:
            self.add_error('año_anterior', 'Debe seleccionar un año anterior para copiar')
        
        if año_lectivo and año_anterior and año_lectivo == año_anterior:
            self.add_error('año_anterior', 'No puede copiar del mismo año lectivo')
        
        return cleaned_data

class CrearAsignaturaForm(forms.ModelForm):
    """Formulario para crear nueva asignatura"""
    nivel_escolar = forms.ModelChoiceField(
        queryset=NivelEscolar.objects.all(),
        required=True,
        label="Nivel Escolar",
        help_text="Seleccione el nivel escolar primero"
    )
    
    copiar_de_año_anterior = forms.BooleanField(
        required=False,
        label='Copiar asignaturas del año anterior',
        help_text='Selecciona para copiar asignaturas del año anterior'
    )
    
    año_anterior = forms.ModelChoiceField(
        queryset=AñoLectivo.objects.none(),
        required=False,
        label='Año anterior a copiar'
    )
    
    asignaturas_seleccionadas = forms.ModelMultipleChoiceField(
        queryset=Asignatura.objects.none(),
        required=False,
        label='Asignaturas específicas a copiar',
        widget=forms.CheckboxSelectMultiple
    )
    
    class Meta:
        model = Asignatura
        fields = ['nombre', 'area', 'ih']
        widgets = {
            'ih': forms.Select(choices=[
                ('', 'Seleccione intensidad horaria'),
                ('1', '1 hora'),
                ('2', '2 horas'),
                ('3', '3 horas'),
                ('4', '4 horas'),
                ('5', '5 horas'),
                ('6', '6 horas'),
            ])
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar áreas basadas en el nivel escolar seleccionado
        if 'nivel_escolar' in self.data:
            try:
                nivel_id = int(self.data.get('nivel_escolar'))
                self.fields['area'].queryset = Area.objects.filter(nivel_escolar_id=nivel_id)
            except (ValueError, TypeError):
                self.fields['area'].queryset = Area.objects.none()
        elif self.instance.pk:
            if self.instance.area:
                self.fields['nivel_escolar'].initial = self.instance.area.nivel_escolar
                self.fields['area'].queryset = Area.objects.filter(
                    nivel_escolar=self.instance.area.nivel_escolar
                )
        else:
            self.fields['area'].queryset = Area.objects.none()
        
        # Configurar año anterior para copiar
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if año_actual:
            años_anteriores = AñoLectivo.objects.filter(
                colegio=año_actual.colegio,
                sede=año_actual.sede
            ).exclude(id=año_actual.id).order_by('-anho')
            self.fields['año_anterior'].queryset = años_anteriores
            
            if 'año_anterior' in self.data:
                try:
                    año_id = int(self.data.get('año_anterior'))
                    año_seleccionado = AñoLectivo.objects.get(id=año_id)
                    # Obtener asignaturas del año seleccionado
                    asignaturas_del_año = Asignatura.objects.filter(
                        asignaturas_grado__grado_año_lectivo__año_lectivo=año_seleccionado
                    ).distinct()
                    self.fields['asignaturas_seleccionadas'].queryset = asignaturas_del_año
                except (ValueError, TypeError, AñoLectivo.DoesNotExist):
                    self.fields['asignaturas_seleccionadas'].queryset = Asignatura.objects.none()
            else:
                self.fields['asignaturas_seleccionadas'].queryset = Asignatura.objects.none()
        else:
            self.fields['año_anterior'].queryset = AñoLectivo.objects.none()
            self.fields['asignaturas_seleccionadas'].queryset = Asignatura.objects.none()
    
    def clean(self):
        cleaned_data = super().clean()
        copiar_de_año_anterior = cleaned_data.get('copiar_de_año_anterior')
        año_anterior = cleaned_data.get('año_anterior')
        asignaturas_seleccionadas = cleaned_data.get('asignaturas_seleccionadas')
        
        # Validar que si se marca copiar, se seleccione un año
        if copiar_de_año_anterior and not año_anterior:
            self.add_error('año_anterior', 'Debe seleccionar un año anterior para copiar')
        
        # Validar que si se selecciona año, haya asignaturas para copiar
        if año_anterior and copiar_de_año_anterior:
            if not asignaturas_seleccionadas:
                self.add_error('asignaturas_seleccionadas', 
                              'Seleccione al menos una asignatura para copiar')
        
        return cleaned_data

class AsignaturaGradoForm(forms.ModelForm):
    """Formulario para asignar una asignatura a un grado"""
    class Meta:
        model = AsignaturaGradoAñoLectivo
        fields = ['asignatura', 'grado_año_lectivo', 'sede', 'docente']
        widgets = {
            'asignatura': forms.Select(attrs={'class': 'form-control select2'}),
            'grado_año_lectivo': forms.Select(attrs={'class': 'form-control select2'}),
            'sede': forms.Select(attrs={'class': 'form-control select2'}),
            'docente': forms.Select(attrs={'class': 'form-control select2'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar opciones según el año lectivo actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if año_actual:
            self.fields['grado_año_lectivo'].queryset = GradoAñoLectivo.objects.filter(
                año_lectivo=año_actual,
                estado=True
            )
            self.fields['sede'].queryset = Sede.objects.filter(
                años_lectivos=año_actual
            ).distinct()
            
            # Docentes asignados a sedes en el año actual
            docente_ids = DocenteSede.objects.filter(
                año_lectivo=año_actual,
                estado=True
            ).values_list('docente_id', flat=True)
            
            self.fields['docente'].queryset = Docente.objects.filter(
                id__in=docente_ids,
                estado=True
            )
            
class AsignarAsignaturaGradoForm(forms.ModelForm):
    """Formulario para asignar asignatura a un grado año lectivo"""
    sede = forms.ModelChoiceField(
        queryset=Sede.objects.filter(estado=True),
        required=True,
        label="Sede"
    )
    
    copiar_de_año_anterior = forms.BooleanField(
        required=False,
        label='Copiar asignaciones del año anterior',
        help_text='Copiar las asignaciones de asignaturas a grados del año anterior'
    )
    
    año_anterior = forms.ModelChoiceField(
        queryset=AñoLectivo.objects.none(),
        required=False,
        label='Año anterior a copiar'
    )
    
    class Meta:
        model = AsignaturaGradoAñoLectivo
        fields = ['asignatura', 'grado_año_lectivo', 'docente', 'sede']
    
    def __init__(self, *args, **kwargs):
        año_lectivo = kwargs.pop('año_lectivo', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar grado_año_lectivo por año lectivo
        if año_lectivo:
            self.fields['grado_año_lectivo'].queryset = GradoAñoLectivo.objects.filter(
                año_lectivo=año_lectivo
            )
            
            # Configurar años anteriores para copiar
            años_anteriores = AñoLectivo.objects.filter(
                colegio=año_lectivo.colegio,
                sede=año_lectivo.sede
            ).exclude(id=año_lectivo.id).order_by('-anho')
            self.fields['año_anterior'].queryset = años_anteriores
        
        # Filtrar docentes activos
        self.fields['docente'].queryset = Docente.objects.filter(estado=True)
        
        # Ordenar asignaturas
        self.fields['asignatura'].queryset = Asignatura.objects.all().order_by('nombre')

class GradoAñoLectivoForm(forms.ModelForm):
    class Meta:
        model = GradoAñoLectivo
        fields = ['grado', 'año_lectivo', 'estado']
        widgets = {
            'grado': forms.Select(attrs={'class': 'form-select select2'}),
            'año_lectivo': forms.Select(attrs={'class': 'form-select select2'}),
            'estado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personalizar etiquetas
        self.fields['grado'].label = 'Grado Académico'
        self.fields['año_lectivo'].label = 'Año Lectivo'
        self.fields['estado'].label = 'Activo'
        
        # Ordenar las opciones
        self.fields['grado'].queryset = Grado.objects.all().order_by('nivel_escolar__nombre', 'nombre')
        self.fields['año_lectivo'].queryset = AñoLectivo.objects.all().order_by('-anho')

class GradoAñoLectivoUpdateForm(forms.ModelForm):
    class Meta:
        model = GradoAñoLectivo
        fields = ['estado']
        widgets = {
            'estado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['estado'].label = 'Activo'

class DocenteUpdateForm(forms.ModelForm):
    """Formulario para actualizar perfil docente"""
    class Meta:
        model = Docente
        fields = ['foto', 'hdv', 'estado']
        widgets = {
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'hdv': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'estado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['estado'].label = 'Activo'

class DocenteCreateForm(forms.ModelForm):
    """Formulario para crear un nuevo docente completo"""
    # Campos del usuario
    tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.all(),
        label="Tipo de Documento",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    numero_documento = forms.CharField(
        max_length=50,
        label="Número de Documento",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de documento'})
    )
    nombres = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombres completos'})
    )
    apellidos = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos completos'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'})
    )
    telefono = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono'})
    )
    direccion = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección completa'})
    )
    fecha_nacimiento = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    sexo = forms.ChoiceField(
        choices=Usuario.SEXO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Campos del docente
    foto = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        label="Foto del Docente"
    )
    hdv = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        label="Hoja de Vida"
    )
    
    # Campos de sede inicial (opcional)
    sede_inicial = forms.ModelChoiceField(
        queryset=Sede.objects.filter(estado=True),
        required=False,
        label="Asignar a Sede",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    año_lectivo_sede = forms.ModelChoiceField(
        queryset=AñoLectivo.objects.filter(estado=True),
        required=False,
        label="Año Lectivo para Sede",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Docente
        fields = []  # Todos los campos están definidos arriba
    
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validar que si se selecciona sede, también se seleccione año lectivo
        sede = cleaned_data.get('sede_inicial')
        año_lectivo = cleaned_data.get('año_lectivo_sede')
        
        if sede and not año_lectivo:
            self.add_error('año_lectivo_sede', 'Debe seleccionar un año lectivo cuando asigna una sede.')
        
        if año_lectivo and not sede:
            self.add_error('sede_inicial', 'Debe seleccionar una sede cuando asigna un año lectivo.')
        
        return cleaned_data
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Establecer valores iniciales para año lectivo
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if año_actual:
            self.fields['año_lectivo_sede'].initial = año_actual.id
            self.fields['año_lectivo_sede'].queryset = AñoLectivo.objects.filter(estado=True)
        
    def clean_numero_documento(self):
        numero_documento = self.cleaned_data.get('numero_documento')
        
        # Verificar que el número de documento no exista
        if Usuario.objects.filter(numero_documento=numero_documento).exists():
            raise forms.ValidationError('Este número de documento ya está registrado en el sistema.')
        
        return numero_documento
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        if email:
            # Verificar que el email no exista
            if Usuario.objects.filter(email=email).exists():
                raise forms.ValidationError('Este correo electrónico ya está registrado en el sistema.')
        
        return email
    
    def save(self, commit=True):
        # Primero crear el usuario
        usuario_data = {
            'tipo_documento': self.cleaned_data['tipo_documento'],
            'numero_documento': self.cleaned_data['numero_documento'],
            'nombres': self.cleaned_data['nombres'],
            'apellidos': self.cleaned_data['apellidos'],
            'email': self.cleaned_data['email'],
            'telefono': self.cleaned_data['telefono'],
            'direccion': self.cleaned_data['direccion'],
            'fecha_nacimiento': self.cleaned_data['fecha_nacimiento'],
            'sexo': self.cleaned_data['sexo'],
        }
        
        # Obtener tipo de usuario "Docente"
        try:
            tipo_docente = TipoUsuario.objects.get(nombre='Docente')
        except TipoUsuario.DoesNotExist:
            # Si no existe, crearlo
            tipo_docente = TipoUsuario.objects.create(nombre='Docente')
        
        usuario_data['tipo_usuario'] = tipo_docente
        
        # Generar username automático (puedes personalizar esto)
        username = f"doc_{self.cleaned_data['numero_documento']}"
        usuario_data['username'] = username
        
        # Contraseña temporal (documento)
        usuario_data['password'] = f"{self.cleaned_data['numero_documento']}"
        
        # Crear usuario
        usuario = Usuario.objects.create_user(**usuario_data)
        
        # Ahora crear el docente
        docente = Docente(
            usuario=usuario,
            foto=self.cleaned_data.get('foto'),
            hdv=self.cleaned_data.get('hdv'),
            estado=True  # Por defecto activo
        )
        
        if commit:
            docente.save()
            
            # Asignar sede si se especificó
            sede = self.cleaned_data.get('sede_inicial')
            año_lectivo = self.cleaned_data.get('año_lectivo_sede')
            
            if sede and año_lectivo:
                try:
                    # Verificar que no exista ya la asignación
                    if not DocenteSede.objects.filter(
                        docente=docente,
                        sede=sede,
                        año_lectivo=año_lectivo
                    ).exists():
                        # Crear la asignación con estado activo
                        DocenteSede.objects.create(
                            docente=docente,
                            sede=sede,
                            año_lectivo=año_lectivo,
                            estado=True
                        )
                        print(f"Sede asignada: {sede.nombre} - Año: {año_lectivo.anho}")  # Para debug
                    else:
                        print("La asignación ya existe")  # Para debug
                except Exception as e:
                    print(f"Error al asignar sede: {e}")  # Para debug
        
        return docente
    
class DocenteInformacionPersonalForm(forms.ModelForm):
    """Formulario para editar información personal del docente"""
    class Meta:
        model = Usuario
        fields = [
            'nombres', 'apellidos', 'email', 'telefono', 
            'direccion', 'fecha_nacimiento', 'sexo'
        ]
        widgets = {
            'nombres': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombres'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección'}),
            'fecha_nacimiento': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date', 'placeholder': 'dd/mm/aaaa'}
            ),
            'sexo': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_nacimiento'].required = False

class AsignaturaDocenteForm(forms.ModelForm):
    """Formulario para asignar asignatura a docente con filtros en cascada"""
    grado = forms.ModelChoiceField(
        queryset=Grado.objects.none(),
        label="Grado",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_grado'})
    )
    
    class Meta:
        model = AsignaturaGradoAñoLectivo
        fields = ['grado', 'asignatura', 'sede']
        widgets = {
            'asignatura': forms.Select(attrs={'class': 'form-select', 'id': 'id_asignatura'}),
            'sede': forms.Select(attrs={'class': 'form-select', 'id': 'id_sede'}),
        }
    
    def __init__(self, *args, **kwargs):
        docente_id = kwargs.pop('docente_id', None)
        super().__init__(*args, **kwargs)
        
        self.docente = None
        if docente_id:
            self.docente = Docente.objects.get(id=docente_id)
        
        # Obtener año lectivo actual
        self.año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        if self.año_actual and self.docente:
            # Filtrar sedes donde el docente está asignado en el año actual
            sedes_docente = self.docente.sedes_asignadas.filter(
                año_lectivo=self.año_actual,
                estado=True
            ).values_list('sede_id', flat=True)
            
            self.fields['sede'].queryset = Sede.objects.filter(
                id__in=sedes_docente
            ).order_by('nombre')
            
            # Filtrar grados que estén en el año actual y en las sedes del docente
            grados_disponibles = GradoAñoLectivo.objects.filter(
                año_lectivo=self.año_actual
            ).filter(
                Q(asignaturas_grado__sede__id__in=sedes_docente) |
                Q(matriculas__sede__id__in=sedes_docente)
            ).distinct()
            
            self.fields['grado'].queryset = Grado.objects.filter(
                id__in=grados_disponibles.values_list('grado_id', flat=True)
            ).order_by('nombre')
        
        # Asignaturas vacías inicialmente (se llenarán con AJAX)
        self.fields['asignatura'].queryset = Asignatura.objects.all().order_by('nombre')
        
        # Si estamos editando, cargar datos iniciales
        if self.instance and self.instance.pk:
            if self.instance.grado_año_lectivo:
                self.fields['grado'].initial = self.instance.grado_año_lectivo.grado
                # Cargar asignaturas para el grado seleccionado
                self.fields['asignatura'].queryset = Asignatura.objects.filter(
                    area__nivel_escolar=self.instance.grado_año_lectivo.grado.nivel_escolar
                ).order_by('nombre')
    
    def clean(self):
        cleaned_data = super().clean()
        grado = cleaned_data.get('grado')
        asignatura = cleaned_data.get('asignatura')
        sede = cleaned_data.get('sede')
        
        if grado and asignatura and sede and self.año_actual and self.docente:
            # Verificar que no exista ya esta asignación
            if AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo__grado=grado,
                grado_año_lectivo__año_lectivo=self.año_actual,
                asignatura=asignatura,
                sede=sede,
                docente=self.docente
            ).exists():
                raise forms.ValidationError(
                    'Esta asignatura ya está asignada a este docente para el grado y sede seleccionados.'
                )
            
            # Verificar que la asignatura pertenezca al nivel del grado
            if asignatura.area.nivel_escolar != grado.nivel_escolar:
                raise forms.ValidationError(
                    f'La asignatura "{asignatura.nombre}" no pertenece al nivel escolar "{grado.nivel_escolar.nombre}".'
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        # Obtener o crear el GradoAñoLectivo
        grado = self.cleaned_data['grado']
        sede = self.cleaned_data['sede']
        
        # Buscar el GradoAñoLectivo para el año actual
        grado_año_lectivo, created = GradoAñoLectivo.objects.get_or_create(
            grado=grado,
            año_lectivo=self.año_actual,
            defaults={'estado': True}
        )
        
        # Buscar si ya existe la asignatura para ese grado y sede
        asignatura_grado = AsignaturaGradoAñoLectivo.objects.filter(
            asignatura=self.cleaned_data['asignatura'],
            grado_año_lectivo=grado_año_lectivo,
            sede=sede
        ).first()
        
        if asignatura_grado:
            # Si existe, asignar al docente
            asignatura_grado.docente = self.docente
            instance = asignatura_grado
        else:
            # Si no existe, crear nueva asignación
            self.instance.grado_año_lectivo = grado_año_lectivo
            self.instance.docente = self.docente
            instance = super().save(commit=False)
        
        if commit:
            instance.save()
        
        return instance

class DocenteSedeForm(forms.ModelForm):
    """Formulario para asignar sede a docente"""
    class Meta:
        model = DocenteSede
        fields = ['sede', 'año_lectivo']
        widgets = {
            'sede': forms.Select(attrs={'class': 'form-select'}),
            'año_lectivo': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        docente_id = kwargs.pop('docente_id', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar sedes activas
        self.fields['sede'].queryset = Sede.objects.filter(estado=True).order_by('nombre')
        
        # Filtrar años lectivos activos
        self.fields['año_lectivo'].queryset = AñoLectivo.objects.filter(
            estado=True
        ).order_by('-anho')

class AreaForm(forms.ModelForm):
    """Formulario para crear/editar Áreas"""
    class Meta:
        model = Area
        fields = ['nombre', 'nivel_escolar']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Matemáticas, Ciencias Naturales, Humanidades'
            }),
            'nivel_escolar': forms.Select(attrs={'class': 'form-control select2'})
        }
    
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        nivel_escolar = self.cleaned_data.get('nivel_escolar')
        
        if nombre and nivel_escolar:
            # Verificar si ya existe un área con el mismo nombre en el mismo nivel
            qs = Area.objects.filter(
                nombre__iexact=nombre,
                nivel_escolar=nivel_escolar
            )
            
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                raise ValidationError(
                    f'Ya existe un área con el nombre "{nombre}" en el nivel {nivel_escolar.nombre}'
                )
        
        return nombre

class AsignaturaForm(forms.ModelForm):
    """Formulario para crear/editar Asignaturas"""
    class Meta:
        model = Asignatura
        fields = ['nombre', 'area', 'ih']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Matemáticas Básicas, Ciencias Naturales I'
            }),
            'area': forms.Select(attrs={'class': 'form-control select2'}),
            'ih': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('', 'Seleccione intensidad horaria'),
                ('1', '1 hora semanal'),
                ('2', '2 horas semanales'),
                ('3', '3 horas semanales'),
                ('4', '4 horas semanales'),
                ('5', '5 horas semanales'),
            ])
        }
    
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        area = self.cleaned_data.get('area')
        
        if nombre and area:
            # Verificar si ya existe una asignatura con el mismo nombre en la misma área
            qs = Asignatura.objects.filter(
                nombre__iexact=nombre,
                area=area
            )
            
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                raise ValidationError(
                    f'Ya existe una asignatura con el nombre "{nombre}" en el área {area.nombre}'
                )
        
        return nombre
    
class AsignaturaBulkForm(forms.Form):
    """Formulario para crear múltiples asignaturas a la vez"""
    area = forms.ModelChoiceField(
        queryset=Area.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        label="Área"
    )
    nombres = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Ingrese los nombres de las asignaturas, uno por línea:\nEj:\nMatemáticas Básicas\nGeometría\nÁlgebra\nCálculo'
        }),
        label="Nombres de asignaturas (una por línea)",
        help_text="Cada línea será una asignatura independiente"
    )
    ih = forms.ChoiceField(
        choices=[
            ('', 'Seleccione intensidad horaria'),
            ('1', '1 hora semanal'),
            ('2', '2 horas semanales'),
            ('3', '3 horas semanales'),
            ('4', '4 horas semanales'),
            ('5', '5 horas semanales'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Intensidad horaria (para todas)"
    )

class LogroForm(forms.ModelForm):
    """Formulario para crear/editar Logros"""
    
    # Cambiar asignatura a un campo que acepte cualquier ID
    asignatura = forms.ModelChoiceField(
        queryset=Asignatura.objects.none(),  # Temporal, se actualizará
        widget=forms.Select(attrs={'class': 'form-control select2-asignatura'}),
        label="Asignatura *"
    )
    
    class Meta:
        model = Logro
        fields = ['grado', 'asignatura', 'periodo_academico', 'tema',
                  'descripcion_superior', 'descripcion_alto', 
                  'descripcion_basico', 'descripcion_bajo']
        widgets = {
            'grado': forms.Select(attrs={'class': 'form-control select2-grado'}),
            'periodo_academico': forms.Select(attrs={'class': 'form-control select2-periodo'}),
            'tema': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Resolución de ecuaciones de primer grado'
            }),
            'descripcion_superior': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe el nivel de desempeño superior...',
                'maxlength': '500'
            }),
            'descripcion_alto': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe el nivel de desempeño alto...',
                'maxlength': '500'
            }),
            'descripcion_basico': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe el nivel de desempeño básico...',
                'maxlength': '500'
            }),
            'descripcion_bajo': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe el nivel de desempeño bajo...',
                'maxlength': '500'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar períodos académicos por año lectivo actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if año_actual:
            self.fields['periodo_academico'].queryset = PeriodoAcademico.objects.filter(
                año_lectivo=año_actual
            )
        
        # En modo edición, establecer el queryset con la asignatura actual
        if self.instance.pk and self.instance.asignatura:
            self.fields['asignatura'].queryset = Asignatura.objects.filter(
                pk=self.instance.asignatura.pk
            )
            self.fields['grado'].initial = self.instance.grado
        else:
            # En modo creación, permitir todas las asignaturas
            # La validación se hará en el método clean()
            self.fields['asignatura'].queryset = Asignatura.objects.all().order_by('nombre')
    
    def clean(self):
        cleaned_data = super().clean()
        grado = cleaned_data.get('grado')
        asignatura = cleaned_data.get('asignatura')
        
        # Validar que la asignatura pertenezca al nivel del grado
        if grado and asignatura:
            if asignatura.area.nivel_escolar != grado.nivel_escolar:
                raise forms.ValidationError({
                    'asignatura': f'La asignatura "{asignatura.nombre}" no pertenece al nivel "{grado.nivel_escolar}". '
                                 f'Pertenece al nivel "{asignatura.area.nivel_escolar}".'
                })
        
        # Validar que al menos una descripción esté completa
        descripciones = ['superior', 'alto', 'basico', 'bajo']
        has_any_description = any(
            cleaned_data.get(f'descripcion_{level}') 
            for level in descripciones
        )
        
        if not has_any_description:
            raise forms.ValidationError("Debe completar al menos un nivel de desempeño.")
        
        return cleaned_data