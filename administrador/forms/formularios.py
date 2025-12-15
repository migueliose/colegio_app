from django import forms
from django.contrib.auth.forms import UserCreationForm
from academico.models import Grado, Area, Asignatura, Periodo, HorarioClase
from gestioncolegio.models import AñoLectivo, Sede
from usuarios.models import Usuario, TipoDocumento, TipoUsuario, Docente
from estudiantes.models import Estudiante, Acudiente, Matricula
from matricula.models import PeriodoAcademico, AsignaturaGradoAñoLectivo, GradoAñoLectivo
from django.core.exceptions import ValidationError

class MatriculaForm(forms.ModelForm):
    """Formulario para crear/editar matrículas con opción de crear estudiante"""
    
    # Opciones para el estudiante
    tipo_estudiante = forms.ChoiceField(
        choices=[
            ('existente', 'Estudiante existente'),
            ('nuevo', 'Crear nuevo estudiante')
        ],
        initial='existente',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label="Tipo de estudiante"
    )
    
    # Campos para nuevo estudiante
    nuevo_tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.all(),
        required=False,
        label="Tipo de Documento"
    )
    nuevo_numero_documento = forms.CharField(
        max_length=50,
        required=False,
        label="Número de Documento"
    )
    nuevo_nombres = forms.CharField(
        max_length=100,
        required=False,
        label="Nombres"
    )
    nuevo_apellidos = forms.CharField(
        max_length=100,
        required=False,
        label="Apellidos"
    )
    nuevo_email = forms.EmailField(
        required=False,
        label="Email"
    )
    nuevo_telefono = forms.CharField(
        max_length=20,
        required=False,
        label="Teléfono"
    )
    nuevo_sexo = forms.ChoiceField(
        choices=Usuario.SEXO_CHOICES,
        required=False,
        label="Sexo"
    )
    nuevo_fecha_nacimiento = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Fecha de Nacimiento"
    )
    nuevo_direccion = forms.CharField(
        max_length=255,
        required=False,
        label="Dirección"
    )
    
    class Meta:
        model = Matricula
        fields = ['año_lectivo', 'sede', 'grado_año_lectivo', 'estado', 'observaciones']
        widgets = {
            'año_lectivo': forms.Select(attrs={'class': 'form-select'}),
            'sede': forms.Select(attrs={'class': 'form-select'}),
            'grado_año_lectivo': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones adicionales...'
            }),
        }
        labels = {
            'año_lectivo': 'Año Lectivo',
            'sede': 'Sede',
            'grado_año_lectivo': 'Grado',
            'estado': 'Estado de Matrícula',
            'observaciones': 'Observaciones'
        }
    
    def __init__(self, *args, **kwargs):
        estudiante_id = kwargs.pop('estudiante_id', None)
        año_lectivo_id = kwargs.pop('año_lectivo_id', None)
        super().__init__(*args, **kwargs)
        
        # Variables para almacenar IDs
        self.estudiante_id_param = estudiante_id
        self.año_lectivo_id_param = año_lectivo_id
        
        # Si viene con estudiante_id, ocultar la opción de tipo y forzar "existente"
        if estudiante_id:
            self.fields['tipo_estudiante'].widget = forms.HiddenInput()
            self.fields['tipo_estudiante'].initial = 'existente'
            
            # Ocultar todos los campos de nuevo estudiante
            for field_name in ['nuevo_tipo_documento', 'nuevo_numero_documento', 'nuevo_nombres', 
                              'nuevo_apellidos', 'nuevo_email', 'nuevo_telefono', 'nuevo_sexo', 
                              'nuevo_fecha_nacimiento', 'nuevo_direccion']:
                self.fields[field_name].widget = forms.HiddenInput()
                self.fields[field_name].required = False
            
            # Mostrar info del estudiante existente
            try:
                estudiante = Estudiante.objects.get(id=estudiante_id)
                self.fields['estudiante_info'] = forms.CharField(
                    initial=f"{estudiante.usuario.get_full_name()} - {estudiante.usuario.numero_documento}",
                    widget=forms.TextInput(attrs={
                        'class': 'form-control',
                        'readonly': 'readonly'
                    }),
                    label="Estudiante",
                    required=False
                )
                
                # Campo hidden para el estudiante
                self.fields['estudiante_hidden'] = forms.IntegerField(
                    initial=estudiante_id,
                    widget=forms.HiddenInput()
                )
            except Estudiante.DoesNotExist:
                pass
        else:
            # Si no viene con estudiante_id, mostrar selector de estudiante existente
            self.fields['estudiante_existente'] = forms.ModelChoiceField(
                queryset=Estudiante.objects.filter().select_related('usuario'),
                required=False,
                widget=forms.Select(attrs={
                    'class': 'form-select',
                    'data-placeholder': 'Buscar estudiante...'
                }),
                label="Seleccionar estudiante existente"
            )
        
        # Si se proporciona un año_lectivo_id, limitar la selección
        if año_lectivo_id:
            self.fields['año_lectivo'].queryset = AñoLectivo.objects.filter(id=año_lectivo_id)
            self.fields['año_lectivo'].initial = año_lectivo_id
            
            # Agregar un texto de ayuda
            año_lectivo = AñoLectivo.objects.filter(id=año_lectivo_id).first()
            if año_lectivo:
                self.fields['año_lectivo'].help_text = f"Año lectivo seleccionado: {año_lectivo.anho}"
        
        # Filtrar grados por año lectivo si está seleccionado
        año_lectivo = None
        
        # Obtener el ID del año lectivo de varias fuentes posibles
        if self.año_lectivo_id_param:
            año_lectivo = self.año_lectivo_id_param
        elif 'año_lectivo' in self.initial and isinstance(self.initial['año_lectivo'], (int, str)):
            año_lectivo = self.initial['año_lectivo']
        elif self.instance and self.instance.año_lectivo:
            año_lectivo = self.instance.año_lectivo.id
        elif 'año_lectivo' in self.data and self.data['año_lectivo']:
            año_lectivo = self.data['año_lectivo']
        
        if año_lectivo:
            self.fields['grado_año_lectivo'].queryset = GradoAñoLectivo.objects.filter(
                año_lectivo_id=año_lectivo
            ).select_related('grado').order_by('grado__nombre')
        else:
            self.fields['grado_año_lectivo'].queryset = GradoAñoLectivo.objects.none()
        
        # Filtrar sedes por año lectivo si está seleccionado
        if año_lectivo:
            self.fields['sede'].queryset = Sede.objects.filter(
                años_lectivos__id=año_lectivo
            ).distinct().order_by('nombre')
        else:
            self.fields['sede'].queryset = Sede.objects.none()
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_estudiante = cleaned_data.get('tipo_estudiante')
        
        if tipo_estudiante == 'existente':
            # Si viene de parámetro, usar ese estudiante
            if self.estudiante_id_param:
                try:
                    estudiante = Estudiante.objects.get(id=self.estudiante_id_param)
                    cleaned_data['estudiante'] = estudiante
                except Estudiante.DoesNotExist:
                    self.add_error(None, 'El estudiante especificado no existe.')
                    return cleaned_data
            else:
                # Si no viene de parámetro, usar el seleccionado
                estudiante_existente = cleaned_data.get('estudiante_existente')
                if not estudiante_existente:
                    self.add_error('estudiante_existente', 'Debe seleccionar un estudiante existente.')
                    return cleaned_data
                cleaned_data['estudiante'] = estudiante_existente
        
        elif tipo_estudiante == 'nuevo':
            # Validar campos para nuevo estudiante
            nuevo_numero_documento = cleaned_data.get('nuevo_numero_documento')
            nuevo_nombres = cleaned_data.get('nuevo_nombres')
            nuevo_apellidos = cleaned_data.get('nuevo_apellidos')
            nuevo_tipo_documento = cleaned_data.get('nuevo_tipo_documento')
            
            # Validar campos obligatorios
            if not nuevo_numero_documento:
                self.add_error('nuevo_numero_documento', 'Este campo es obligatorio para crear un nuevo estudiante.')
            if not nuevo_nombres:
                self.add_error('nuevo_nombres', 'Este campo es obligatorio para crear un nuevo estudiante.')
            if not nuevo_apellidos:
                self.add_error('nuevo_apellidos', 'Este campo es obligatorio para crear un nuevo estudiante.')
            if not nuevo_tipo_documento:
                self.add_error('nuevo_tipo_documento', 'Este campo es obligatorio para crear un nuevo estudiante.')
            
            # Verificar que el documento no exista
            if nuevo_numero_documento and Usuario.objects.filter(numero_documento=nuevo_numero_documento).exists():
                self.add_error('nuevo_numero_documento', 'Este número de documento ya existe en el sistema.')
            
            # Si hay errores, retornar
            if self.errors:
                return cleaned_data
            
            # Crear el estudiante si pasa validaciones
            try:
                # Primero crear/actualizar el usuario
                usuario_existente = Usuario.objects.filter(
                    numero_documento=nuevo_numero_documento
                ).first()
                
                if usuario_existente:
                    # Actualizar usuario existente
                    usuario_existente.nombres = nuevo_nombres
                    usuario_existente.apellidos = nuevo_apellidos
                    usuario_existente.email = cleaned_data.get('nuevo_email')
                    usuario_existente.telefono = cleaned_data.get('nuevo_telefono')
                    usuario_existente.direccion = cleaned_data.get('nuevo_direccion')
                    usuario_existente.sexo = cleaned_data.get('nuevo_sexo')
                    usuario_existente.fecha_nacimiento = cleaned_data.get('nuevo_fecha_nacimiento')
                    usuario_existente.tipo_documento = nuevo_tipo_documento
                    
                    # Establecer tipo de usuario si no lo tiene
                    if not usuario_existente.tipo_usuario:
                        usuario_existente.tipo_usuario = TipoUsuario.objects.get(nombre='Estudiante')
                    
                    usuario_existente.save()
                    usuario = usuario_existente
                else:
                    # Crear nuevo usuario
                    usuario = Usuario.objects.create(
                        username=f"est_{nuevo_numero_documento}",
                        numero_documento=nuevo_numero_documento,
                        tipo_documento=nuevo_tipo_documento,
                        nombres=nuevo_nombres,
                        apellidos=nuevo_apellidos,
                        email=cleaned_data.get('nuevo_email'),
                        telefono=cleaned_data.get('nuevo_telefono'),
                        direccion=cleaned_data.get('nuevo_direccion'),
                        sexo=cleaned_data.get('nuevo_sexo'),
                        fecha_nacimiento=cleaned_data.get('nuevo_fecha_nacimiento'),
                        tipo_usuario=TipoUsuario.objects.get(nombre='Estudiante')
                    )
                    # Contraseña por defecto: número de documento
                    usuario.set_password(nuevo_numero_documento)
                    usuario.save()
                
                # Crear o actualizar perfil de estudiante
                estudiante, created = Estudiante.objects.get_or_create(
                    usuario=usuario,
                    defaults={'estado': True}
                )
                
                if not created and not estudiante.estado:
                    estudiante.estado = True
                    estudiante.save()
                
                cleaned_data['estudiante'] = estudiante
                
            except Exception as e:
                self.add_error(None, f'Error al crear estudiante: {str(e)}')
                return cleaned_data
        
        # Validar año lectivo
        if not cleaned_data.get('año_lectivo') and self.año_lectivo_id_param:
            try:
                año_lectivo = AñoLectivo.objects.get(id=self.año_lectivo_id_param)
                cleaned_data['año_lectivo'] = año_lectivo
            except AñoLectivo.DoesNotExist:
                self.add_error('año_lectivo', 'El año lectivo especificado no existe.')
                return cleaned_data
        
        # Verificar que el estudiante no tenga ya una matrícula en el mismo año
        estudiante = cleaned_data.get('estudiante')
        año_lectivo = cleaned_data.get('año_lectivo')
        
        if estudiante and año_lectivo:
            if self.instance.pk:
                # Si estamos editando, excluir esta matrícula
                existing = Matricula.objects.filter(
                    estudiante=estudiante,
                    año_lectivo=año_lectivo
                ).exclude(pk=self.instance.pk)
            else:
                existing = Matricula.objects.filter(
                    estudiante=estudiante,
                    año_lectivo=año_lectivo
                )
            
            if existing.exists():
                raise ValidationError(
                    f'El estudiante {estudiante.usuario.get_full_name()} ya tiene una matrícula '
                    f'en el año lectivo {año_lectivo.anho}.'
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Asignar el estudiante (creado o existente)
        estudiante = self.cleaned_data.get('estudiante')
        if estudiante:
            instance.estudiante = estudiante
        
        if commit:
            instance.save()
        
        return instance
    
class MatriculaFilterForm(forms.Form):
    """Formulario para filtrar matrículas"""
    ESTADO_CHOICES = [
        ('', 'Todos los estados'),
        ('PRE', 'Pre-matrícula'),
        ('PEN', 'Pendiente'),
        ('ACT', 'Activa'),
        ('INA', 'Inactiva'),
        ('RET', 'Retirada'),
    ]
    
    GRADO_CHOICES = [
        ('', 'Todos los grados'),
        ('preescolar', 'Preescolar'),
        ('primaria', 'Primaria'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nombre, documento...'
        }),
        label="Buscar"
    )
    
    estado = forms.ChoiceField(
        choices=ESTADO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Estado"
    )
    
    grado = forms.ChoiceField(
        choices=GRADO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Nivel Escolar"
    )
    
    año_lectivo = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Año Lectivo"
    )
    
    sede = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Sede"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Obtener años lectivos activos o recientes
        from gestioncolegio.models import AñoLectivo
        self.fields['año_lectivo'].queryset = AñoLectivo.objects.all().order_by('-anho')
        
        # Obtener todas las sedes
        self.fields['sede'].queryset = Sede.objects.filter(estado=True).order_by('nombre')

class MatriculaBulkForm(forms.Form):
    """Formulario para matrícula masiva"""
    grado_año_lectivo = forms.ModelChoiceField(
        queryset=GradoAñoLectivo.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Grado",
        required=True
    )
    
    sede = forms.ModelChoiceField(
        queryset=Sede.objects.filter(estado=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Sede",
        required=True
    )
    
    año_lectivo = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Año Lectivo",
        required=True
    )
    
    estado = forms.ChoiceField(
        choices=Matricula.ESTADOS_MATRICULA,
        initial='ACT',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Estado inicial",
        required=True
    )
    
    estudiantes = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 10}),
        label="Estudiantes a matricular",
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        from estudiantes.models import Estudiante
        from gestioncolegio.models import AñoLectivo
        
        # Filtrar estudiantes que no tienen matrícula en el año actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        if año_actual:
            estudiantes_con_matricula = Matricula.objects.filter(
                año_lectivo=año_actual
            ).values_list('estudiante_id', flat=True)
            
            self.fields['estudiantes'].queryset = Estudiante.objects.filter(
                estado=True
            ).exclude(id__in=estudiantes_con_matricula).select_related('usuario')
        else:
            self.fields['estudiantes'].queryset = Estudiante.objects.filter(
                estado=True
            ).select_related('usuario')
        
        # Filtrar años lectivos
        self.fields['año_lectivo'].queryset = AñoLectivo.objects.all().order_by('-anho')
        
        # Si hay año actual, establecerlo por defecto
        if año_actual:
            self.fields['año_lectivo'].initial = año_actual
            # Filtrar grados por año actual
            self.fields['grado_año_lectivo'].queryset = GradoAñoLectivo.objects.filter(
                año_lectivo=año_actual
            ).select_related('grado')

class PeriodoAcademicoForm(forms.ModelForm):
    # Agrega este campo para capturar el año_lectivo
    año_lectivo_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    
    class Meta:
        model = PeriodoAcademico
        fields = ['periodo', 'fecha_inicio', 'fecha_fin', 'estado']
        widgets = {
            'periodo': forms.Select(attrs={'class': 'form-select'}),
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
        
    def __init__(self, *args, **kwargs):
        año_lectivo = kwargs.pop('año_lectivo', None)
        super().__init__(*args, **kwargs)
        
        if año_lectivo:
            # Guardar el año_lectivo en el formulario
            self.año_lectivo = año_lectivo
            self.fields['año_lectivo_id'].initial = año_lectivo.id
            
            # Filtrar periodos que ya están asignados a este año lectivo
            periodos_asignados = PeriodoAcademico.objects.filter(
                año_lectivo=año_lectivo
            ).values_list('periodo_id', flat=True)
            
            # Excluir periodos ya asignados (solo para creación)
            if not self.instance.pk:  # Si es creación, no edición
                self.fields['periodo'].queryset = Periodo.objects.exclude(
                    id__in=periodos_asignados
                )
    
    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        año_lectivo_id = cleaned_data.get('año_lectivo_id')
        
        # Obtener el año_lectivo desde diferentes fuentes
        año_lectivo = None
        if hasattr(self, 'año_lectivo'):
            año_lectivo = self.año_lectivo
        elif año_lectivo_id:
            from gestioncolegio.models import AñoLectivo
            año_lectivo = AñoLectivo.objects.filter(id=año_lectivo_id).first()
        
        if not año_lectivo:
            raise ValidationError("No se pudo determinar el año lectivo.")
        
        # Validar que fecha fin sea posterior a fecha inicio
        if fecha_inicio and fecha_fin:
            if fecha_fin <= fecha_inicio:
                raise ValidationError({
                    'fecha_fin': 'La fecha fin debe ser posterior a la fecha inicio.'
                })
            
            # Validar que no se solape con otros periodos del mismo año
            if self.instance.pk:
                # Para actualización
                periodos_solapados = PeriodoAcademico.objects.filter(
                    año_lectivo=año_lectivo
                ).exclude(pk=self.instance.pk).filter(
                    fecha_inicio__lt=fecha_fin,
                    fecha_fin__gt=fecha_inicio
                )
            else:
                # Para creación
                periodos_solapados = PeriodoAcademico.objects.filter(
                    año_lectivo=año_lectivo
                ).filter(
                    fecha_inicio__lt=fecha_fin,
                    fecha_fin__gt=fecha_inicio
                )
            
            if periodos_solapados.exists():
                periodos_text = ", ".join([str(p.periodo) for p in periodos_solapados])
                raise ValidationError(
                    f'Este periodo se solapa con otros periodos existentes: {periodos_text}'
                )
        
        return cleaned_data
    
class GradoForm(forms.ModelForm):
    class Meta:
        model = Grado
        fields = ['nombre', 'nivel_escolar']
        widgets = {
            'nombre': forms.Select(attrs={'class': 'form-select'}),
            'nivel_escolar': forms.Select(attrs={'class': 'form-select'}),
        }

class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ['nombre', 'nivel_escolar']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'nivel_escolar': forms.Select(attrs={'class': 'form-select'}),
        }

class AsignaturaForm(forms.ModelForm):
    class Meta:
        model = Asignatura
        fields = ['nombre', 'area', 'ih']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'area': forms.Select(attrs={'class': 'form-select'}),
            'ih': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('', 'Seleccione intensidad horaria'),
                ('1', '1 hora'),
                ('2', '2 horas'),
                ('3', '3 horas'),
                ('4', '4 horas'),
                ('5', '5 horas'),
            ]),
        }

class AñoLectivoForm(forms.ModelForm):
    class Meta:
        model = AñoLectivo
        fields = ['colegio', 'sede', 'anho', 'fecha_inicio', 'fecha_fin', 'estado']
        widgets = {
            'colegio': forms.Select(attrs={'class': 'form-select'}),
            'sede': forms.Select(attrs={'class': 'form-select'}),
            'anho': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 2024'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'estado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class DocenteForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Dejar en blanco si no desea cambiar la contraseña"
    )
    
    class Meta:
        model = Usuario
        fields = [
            'tipo_documento', 'numero_documento', 'nombres', 'apellidos',
            'email', 'telefono', 'direccion', 'sexo', 'fecha_nacimiento'
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'sexo': forms.Select(attrs={'class': 'form-control'}),
            'tipo_documento': forms.Select(attrs={'class': 'form-control'}),
        }

# Form para Estudiantes
class EstudianteForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Dejar en blanco si no desea cambiar la contraseña"
    )
    
    class Meta:
        model = Usuario
        fields = [
            'tipo_documento', 'numero_documento', 'nombres', 'apellidos',
            'email', 'telefono', 'direccion', 'sexo', 'fecha_nacimiento'
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'sexo': forms.Select(attrs={'class': 'form-control'}),
            'tipo_documento': forms.Select(attrs={'class': 'form-control'}),
        }

# Form para Acudientes
class AcudienteForm(forms.ModelForm):
    # Campos para crear nuevo usuario si no existe
    crear_nuevo_usuario = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput()
    )
    
    # Campos para nuevo usuario
    nuevo_tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocumento.objects.all(),
        required=False,
        label="Tipo de Documento"
    )
    nuevo_numero_documento = forms.CharField(
        max_length=50,
        required=False,
        label="Número de Documento"
    )
    nuevo_nombres = forms.CharField(
        max_length=100,
        required=False,
        label="Nombres"
    )
    nuevo_apellidos = forms.CharField(
        max_length=100,
        required=False,
        label="Apellidos"
    )
    nuevo_email = forms.EmailField(
        required=False,
        label="Email"
    )
    nuevo_telefono = forms.CharField(
        max_length=20,
        required=False,
        label="Teléfono"
    )
    nuevo_password = forms.CharField(
        widget=forms.PasswordInput(),
        required=False,
        label="Contraseña"
    )
    
    class Meta:
        model = Acudiente
        fields = ['acudiente', 'estudiante', 'parentesco']
        widgets = {
            'acudiente': forms.Select(attrs={'class': 'form-control'}),
            'estudiante': forms.Select(attrs={'class': 'form-control'}),
            'parentesco': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        crear_nuevo = cleaned_data.get('crear_nuevo_usuario')
        
        if crear_nuevo:
            # Validar campos para nuevo usuario
            nuevo_numero_documento = cleaned_data.get('nuevo_numero_documento')
            nuevo_nombres = cleaned_data.get('nuevo_nombres')
            nuevo_apellidos = cleaned_data.get('nuevo_apellidos')
            
            if not nuevo_numero_documento:
                self.add_error('nuevo_numero_documento', 'Este campo es obligatorio')
            if not nuevo_nombres:
                self.add_error('nuevo_nombres', 'Este campo es obligatorio')
            if not nuevo_apellidos:
                self.add_error('nuevo_apellidos', 'Este campo es obligatorio')
                
            # Verificar que el documento no exista
            if nuevo_numero_documento and Usuario.objects.filter(numero_documento=nuevo_numero_documento).exists():
                self.add_error('nuevo_numero_documento', 'Este número de documento ya existe')
        else:
            # Validar que se haya seleccionado un acudiente existente
            acudiente = cleaned_data.get('acudiente')
            if not acudiente:
                self.add_error('acudiente', 'Debe seleccionar un acudiente o crear uno nuevo')
        
        return cleaned_data

# Form para Administradores/Rectores
class AdministradorForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Dejar en blanco si no desea cambiar la contraseña"
    )
    
    class Meta:
        model = Usuario
        fields = [
            'tipo_documento', 'numero_documento', 'nombres', 'apellidos',
            'email', 'telefono', 'direccion', 'sexo', 'fecha_nacimiento',
            'tipo_usuario', 'username'
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'sexo': forms.Select(attrs={'class': 'form-control'}),
            'tipo_documento': forms.Select(attrs={'class': 'form-control'}),
            'tipo_usuario': forms.Select(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

class HorarioClaseForm(forms.ModelForm):
    """Formulario para crear/editar horarios de clase"""
    
    class Meta:
        model = HorarioClase
        fields = ['asignatura_grado', 'dia_semana', 'hora_inicio', 'hora_fin', 'salon']
        widgets = {
            'asignatura_grado': forms.Select(attrs={'class': 'form-select'}),
            'dia_semana': forms.Select(attrs={'class': 'form-select'}),
            'hora_inicio': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'hora_fin': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'salon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Aula 101'
            }),
        }
        labels = {
            'asignatura_grado': 'Asignatura por Grado',
            'dia_semana': 'Día de la semana',
            'hora_inicio': 'Hora de inicio',
            'hora_fin': 'Hora de finalización',
            'salon': 'Salón/Aula'
        }
    
    def __init__(self, *args, **kwargs):
        año_lectivo = kwargs.pop('año_lectivo', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar asignaturas por año lectivo si se proporciona
        if año_lectivo:
            self.fields['asignatura_grado'].queryset = AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo__año_lectivo=año_lectivo
            ).select_related(
                'asignatura',
                'grado_año_lectivo__grado',
                'docente'
            ).order_by('asignatura__nombre')
    
    def clean(self):
        cleaned_data = super().clean()
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_fin = cleaned_data.get('hora_fin')
        dia_semana = cleaned_data.get('dia_semana')
        asignatura_grado = cleaned_data.get('asignatura_grado')
        
        # Validar que hora fin sea posterior a hora inicio
        if hora_inicio and hora_fin:
            if hora_fin <= hora_inicio:
                raise ValidationError({
                    'hora_fin': 'La hora de finalización debe ser posterior a la hora de inicio.'
                })
            
            # Validar que no haya solapamiento con otros horarios del mismo día y asignatura
            if self.instance.pk:
                horarios_solapados = HorarioClase.objects.filter(
                    asignatura_grado=asignatura_grado,
                    dia_semana=dia_semana
                ).exclude(pk=self.instance.pk).filter(
                    hora_inicio__lt=hora_fin,
                    hora_fin__gt=hora_inicio
                )
            else:
                horarios_solapados = HorarioClase.objects.filter(
                    asignatura_grado=asignatura_grado,
                    dia_semana=dia_semana
                ).filter(
                    hora_inicio__lt=hora_fin,
                    hora_fin__gt=hora_inicio
                )
            
            if horarios_solapados.exists():
                raise ValidationError(
                    'Este horario se solapa con otro horario existente para la misma asignatura y día.'
                )
        
        return cleaned_data

class HorarioFilterForm(forms.Form):
    """Formulario para filtrar horarios"""
    TIPO_FILTRO_CHOICES = [
        ('grado', 'Por Grado'),
        ('asignatura', 'Por Asignatura'),
        ('docente', 'Por Docente'),
        ('dia', 'Por Día'),
    ]
    
    tipo_filtro = forms.ChoiceField(
        choices=TIPO_FILTRO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        label="Filtrar por"
    )
    
    grado = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        label="Grado"
    )
    
    asignatura = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        label="Asignatura"
    )
    
    docente = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        label="Docente"
    )
    
    dia_semana = forms.ChoiceField(
        choices=[('', 'Todos los días')] + HorarioClase._meta.get_field('dia_semana').choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        label="Día de la semana"
    )
    
    def __init__(self, *args, **kwargs):
        año_lectivo = kwargs.pop('año_lectivo', None)
        super().__init__(*args, **kwargs)
        
        if año_lectivo:
            # Filtrar grados del año lectivo
            from matricula.models import GradoAñoLectivo
            self.fields['grado'].queryset = GradoAñoLectivo.objects.filter(
                año_lectivo=año_lectivo
            ).select_related('grado').order_by('grado__nombre')
            
            # Filtrar asignaturas del año lectivo (sin DISTINCT ON)
            from academico.models import Asignatura
            asignatura_ids = list(AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo__año_lectivo=año_lectivo
            ).values_list('asignatura_id', flat=True).distinct())
            
            self.fields['asignatura'].queryset = Asignatura.objects.filter(
                id__in=asignatura_ids
            ).order_by('nombre')
            
            # Filtrar docentes del año lectivo
            from usuarios.models import Docente
            docente_ids = list(AsignaturaGradoAñoLectivo.objects.filter(
                grado_año_lectivo__año_lectivo=año_lectivo,
                docente__isnull=False
            ).values_list('docente_id', flat=True).distinct())
            
            self.fields['docente'].queryset = Docente.objects.filter(
                id__in=docente_ids
            ).select_related('usuario').order_by('usuario__apellidos', 'usuario__nombres')

class MatriculaCreateForm(MatriculaForm):
    """Formulario específico para crear matrícula con años disponibles"""
    
    def __init__(self, *args, **kwargs):
        estudiante_id = kwargs.pop('estudiante_id', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar años lectivos disponibles para el estudiante
        if estudiante_id:
            from estudiantes.models import Estudiante
            from gestioncolegio.models import AñoLectivo
            
            estudiante = Estudiante.objects.get(id=estudiante_id)
            # Obtener años en los que ya está matriculado
            años_matriculados = estudiante.matriculas.values_list('año_lectivo_id', flat=True)
            # Filtrar años disponibles (no matriculados aún)
            self.fields['año_lectivo'].queryset = AñoLectivo.objects.exclude(
                id__in=años_matriculados
            ).order_by('-anho')
            
            # También mostrar años en los que ya está matriculado para referencia
            self.años_matriculados = estudiante.matriculas.select_related(
                'año_lectivo', 'grado_año_lectivo__grado', 'sede'
            ).order_by('-año_lectivo__anho')

# ================================================
# FORMULARIOS PARA GESTIÓN ACADÉMICA - GRADOS POR AÑO
# ================================================

class GradoAñoLectivoForm(forms.ModelForm):
    """Formulario para crear/editar relación entre grados y años lectivos"""
    
    class Meta:
        model = GradoAñoLectivo
        fields = ['grado', 'año_lectivo', 'estado']
        widgets = {
            'grado': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'Seleccione un grado'
            }),
            'año_lectivo': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'Seleccione un año lectivo'
            }),
            'estado': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'checked': 'checked'
            }),
        }
        labels = {
            'grado': 'Grado Académico',
            'año_lectivo': 'Año Lectivo',
            'estado': 'Activo'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Ordenar grados por nombre
        self.fields['grado'].queryset = Grado.objects.all().order_by('nombre')
        
        # Filtrar años lectivos activos o recientes
        self.fields['año_lectivo'].queryset = AñoLectivo.objects.filter(
            estado=True
        ).order_by('-anho')
    
    def clean(self):
        cleaned_data = super().clean()
        grado = cleaned_data.get('grado')
        año_lectivo = cleaned_data.get('año_lectivo')
        
        # Verificar que no exista ya esta relación
        if grado and año_lectivo:
            existing = GradoAñoLectivo.objects.filter(
                grado=grado,
                año_lectivo=año_lectivo
            )
            
            # Si estamos editando, excluir esta instancia
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError(
                    f'Ya existe una relación entre el grado {grado} y el año lectivo {año_lectivo}.'
                )
        
        return cleaned_data

class GradoAñoLectivoFilterForm(forms.Form):
    """Formulario para filtrar grados por año lectivo"""
    año_lectivo = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Año Lectivo"
    )
    
    sede = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Sede"
    )
    
    nivel_escolar = forms.ChoiceField(
        choices=[
            ('', 'Todos los niveles'),
            ('Preescolar', 'Preescolar'),
            ('Primaria', 'Primaria'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Nivel Escolar"
    )
    
    estado = forms.ChoiceField(
        choices=[
            ('', 'Todos'),
            ('1', 'Activos'),
            ('0', 'Inactivos'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Estado"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Años lectivos ordenados descendentemente
        self.fields['año_lectivo'].queryset = AñoLectivo.objects.all().order_by('-anho')
        
        # Sedes activas
        self.fields['sede'].queryset = Sede.objects.filter(estado=True).order_by('nombre')

# ================================================
# FORMULARIOS PARA ASIGNATURAS POR GRADO Y AÑO
# ================================================

class AsignaturaGradoAñoLectivoForm(forms.ModelForm):
    """Formulario para crear/editar asignaturas por grado y año lectivo"""
    
    class Meta:
        model = AsignaturaGradoAñoLectivo
        fields = ['asignatura', 'grado_año_lectivo', 'docente', 'sede']
        widgets = {
            'asignatura': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'Seleccione una asignatura'
            }),
            'grado_año_lectivo': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'Seleccione grado y año'
            }),
            'docente': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'Asignar docente (opcional)'
            }),
            'sede': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'Seleccione una sede'
            }),
        }
        labels = {
            'asignatura': 'Asignatura',
            'grado_año_lectivo': 'Grado y Año Lectivo',
            'docente': 'Docente Responsable',
            'sede': 'Sede'
        }
    
    def __init__(self, *args, **kwargs):
        año_lectivo_id = kwargs.pop('año_lectivo_id', None)
        sede_id = kwargs.pop('sede_id', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar asignaturas por nivel escolar del grado si ya está seleccionado
        if self.instance.pk and self.instance.grado_año_lectivo:
            # Obtener nivel escolar del grado
            nivel_escolar = self.instance.grado_año_lectivo.grado.nivel_escolar
            # Filtrar asignaturas por ese nivel escolar
            self.fields['asignatura'].queryset = Asignatura.objects.filter(
                area__nivel_escolar=nivel_escolar
            ).order_by('nombre')
        else:
            # Todas las asignaturas inicialmente
            self.fields['asignatura'].queryset = Asignatura.objects.all().order_by('nombre')
        
        # Filtrar grados por año lectivo si se proporciona
        if año_lectivo_id:
            self.fields['grado_año_lectivo'].queryset = GradoAñoLectivo.objects.filter(
                año_lectivo_id=año_lectivo_id
            ).select_related('grado').order_by('grado__nombre')
        else:
            # Todos los grados-año inicialmente
            self.fields['grado_año_lectivo'].queryset = GradoAñoLectivo.objects.all().select_related(
                'grado', 'año_lectivo'
            ).order_by('año_lectivo__anho', 'grado__nombre')
        
        # Filtrar docentes activos
        self.fields['docente'].queryset = Docente.objects.filter(
            estado=True
        ).select_related('usuario').order_by('usuario__apellidos', 'usuario__nombres')
        
        # Filtrar sedes si se proporciona
        if sede_id:
            self.fields['sede'].queryset = Sede.objects.filter(id=sede_id)
        else:
            self.fields['sede'].queryset = Sede.objects.filter(estado=True).order_by('nombre')
    
    def clean(self):
        cleaned_data = super().clean()
        asignatura = cleaned_data.get('asignatura')
        grado_año_lectivo = cleaned_data.get('grado_año_lectivo')
        sede = cleaned_data.get('sede')
        
        # Verificar que no exista ya esta combinación
        if asignatura and grado_año_lectivo and sede:
            existing = AsignaturaGradoAñoLectivo.objects.filter(
                asignatura=asignatura,
                grado_año_lectivo=grado_año_lectivo,
                sede=sede
            )
            
            # Si estamos editando, excluir esta instancia
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError(
                    f'Esta asignatura ya está asignada al grado {grado_año_lectivo.grado} '
                    f'en la sede {sede} para el año {grado_año_lectivo.año_lectivo.anho}.'
                )
        
        # Validar que la asignatura sea del mismo nivel escolar que el grado
        if asignatura and grado_año_lectivo:
            nivel_asignatura = asignatura.area.nivel_escolar
            nivel_grado = grado_año_lectivo.grado.nivel_escolar
            
            if nivel_asignatura != nivel_grado:
                raise ValidationError(
                    f'La asignatura "{asignatura.nombre}" pertenece al nivel {nivel_asignatura}, '
                    f'pero el grado seleccionado es de nivel {nivel_grado}. '
                    f'Por favor seleccione una asignatura del nivel correcto.'
                )
        
        return cleaned_data

class AsignaturaGradoAñoLectivoFilterForm(forms.Form):
    """Formulario para filtrar asignaturas por grado y año"""
    año_lectivo = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Año Lectivo"
    )
    
    grado = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Grado"
    )
    
    sede = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Sede"
    )
    
    docente = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Docente"
    )
    
    asignada_docente = forms.ChoiceField(
        choices=[
            ('', 'Todas'),
            ('con_docente', 'Con docente asignado'),
            ('sin_docente', 'Sin docente asignado'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Estado de asignación"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Años lectivos ordenados descendentemente
        self.fields['año_lectivo'].queryset = AñoLectivo.objects.all().order_by('-anho')
        
        # Todos los grados
        self.fields['grado'].queryset = Grado.objects.all().order_by('nombre')
        
        # Sedes activas
        self.fields['sede'].queryset = Sede.objects.filter(estado=True).order_by('nombre')
        
        # Docentes activos
        self.fields['docente'].queryset = Docente.objects.filter(
            estado=True
        ).select_related('usuario').order_by('usuario__apellidos', 'usuario__nombres')

# ================================================
# FORMULARIOS PARA ASIGNACIÓN MASIVA
# ================================================

class AsignaturaGradoBulkForm(forms.Form):
    """Formulario para asignación masiva de asignaturas a grados"""
    
    # Año lectivo para la asignación
    año_lectivo = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Año Lectivo",
        required=True
    )
    
    # Grados a los que asignar
    grados = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 6}),
        label="Grados",
        help_text="Seleccione los grados a los que asignar las asignaturas",
        required=True
    )
    
    # Asignaturas a asignar
    asignaturas = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 8}),
        label="Asignaturas",
        help_text="Seleccione las asignaturas a asignar",
        required=True
    )
    
    # Sedes
    sedes = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 4}),
        label="Sedes",
        help_text="Seleccione las sedes donde se asignarán las asignaturas",
        required=True
    )
    
    # Opciones adicionales
    asignar_docente_automaticamente = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Asignar docente automáticamente (si hay disponible)"
    )
    
    sobrescribir_existentes = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Sobrescribir asignaciones existentes",
        help_text="Si está marcado, eliminará asignaturas existentes y creará nuevas"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar años lectivos activos
        self.fields['año_lectivo'].queryset = AñoLectivo.objects.filter(
            estado=True
        ).order_by('-anho')
        
        # Si hay año actual, establecerlo por defecto
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if año_actual:
            self.fields['año_lectivo'].initial = año_actual
        
        # Todos los grados
        self.fields['grados'].queryset = Grado.objects.all().order_by('nombre')
        
        # Todas las asignaturas
        self.fields['asignaturas'].queryset = Asignatura.objects.all().order_by('nombre')
        
        # Sedes activas
        self.fields['sedes'].queryset = Sede.objects.filter(estado=True).order_by('nombre')
    
    def clean(self):
        cleaned_data = super().clean()
        año_lectivo = cleaned_data.get('año_lectivo')
        grados = cleaned_data.get('grados')
        sedes = cleaned_data.get('sedes')
        asignaturas = cleaned_data.get('asignaturas')
        sobrescribir = cleaned_data.get('sobrescribir_existentes')
        
        # Verificar que los grados existan en el año lectivo seleccionado
        if año_lectivo and grados:
            grados_faltantes = []
            for grado in grados:
                if not GradoAñoLectivo.objects.filter(
                    grado=grado,
                    año_lectivo=año_lectivo
                ).exists():
                    grados_faltantes.append(str(grado))
            
            if grados_faltantes:
                raise ValidationError(
                    f'Los siguientes grados no están registrados en el año lectivo {año_lectivo.anho}: '
                    f'{", ".join(grados_faltantes)}. '
                    f'Primero debe crear la relación grado-año lectivo.'
                )
        
        # Si no se va a sobrescribir, verificar cuántas asignaturas ya existen
        if not sobrescribir and año_lectivo and grados and sedes and asignaturas:
            contador_existentes = 0
            detalles_existentes = []
            
            for grado in grados:
                grado_año = GradoAñoLectivo.objects.get(
                    grado=grado,
                    año_lectivo=año_lectivo
                )
                
                for sede in sedes:
                    for asignatura in asignaturas:
                        existe = AsignaturaGradoAñoLectivo.objects.filter(
                            asignatura=asignatura,
                            grado_año_lectivo=grado_año,
                            sede=sede
                        ).exists()
                        
                        if existe:
                            contador_existentes += 1
                            detalles_existentes.append(
                                f'{asignatura.nombre} en {grado.nombre} ({sede.nombre})'
                            )
            
            if contador_existentes > 0:
                self.add_error(
                    'sobrescribir_existentes',
                    f'Existen {contador_existentes} asignaciones previas. '
                    f'Marque "Sobrescribir asignaciones existentes" para reemplazarlas.'
                )
        
        return cleaned_data

class AsignaturaGradoCopyForm(forms.Form):
    """Formulario para copiar asignaturas entre años/grados"""
    
    año_origen = forms.ModelChoiceField(
        queryset=AñoLectivo.objects.filter(estado=True),
        label="Año Lectivo Origen",
        required=True,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_año_origen'})
    )
    
    año_destino = forms.ModelChoiceField(
        queryset=AñoLectivo.objects.filter(estado=True),
        label="Año Lectivo Destino",
        required=True,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_año_destino'})
    )
    
    grados_origen = forms.ModelMultipleChoiceField(
        queryset=Grado.objects.all(),
        label="Grados Origen",
        required=True,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'id': 'id_grados_origen'})
    )
    
    grados_destino = forms.ModelMultipleChoiceField(
        queryset=Grado.objects.all(),
        label="Grados Destino",
        required=True,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'id': 'id_grados_destino'})
    )
    
    sedes = forms.ModelMultipleChoiceField(
        queryset=Sede.objects.filter(estado=True),
        label="Sedes",
        required=True,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'id': 'id_sedes'})
    )
    
    incluir_docentes = forms.BooleanField(
        label="Incluir asignación de docentes",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_incluir_docentes'})
    )
    
    sobrescribir_existentes = forms.BooleanField(
        label="Sobrescribir asignaturas existentes en destino",
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_sobrescribir_existentes'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ordenar los querysets
        self.fields['año_origen'].queryset = AñoLectivo.objects.filter().order_by('-anho')
        self.fields['año_destino'].queryset = AñoLectivo.objects.filter(estado=True).order_by('-anho')
        self.fields['grados_origen'].queryset = Grado.objects.all().order_by('nivel_escolar__nombre', 'nombre')
        self.fields['grados_destino'].queryset = Grado.objects.all().order_by('nivel_escolar__nombre', 'nombre')
        self.fields['sedes'].queryset = Sede.objects.filter(estado=True).order_by('nombre')
    
    def clean(self):
        cleaned_data = super().clean()
        año_origen = cleaned_data.get('año_origen')
        año_destino = cleaned_data.get('año_destino')
        grados_origen = cleaned_data.get('grados_origen')
        grados_destino = cleaned_data.get('grados_destino')
        
        if año_origen and año_destino and año_origen == año_destino:
            raise forms.ValidationError(
                "El año origen y destino no pueden ser el mismo."
            )
        
        if grados_origen and grados_destino:
            if len(grados_origen) != len(grados_destino):
                raise forms.ValidationError(
                    "El número de grados en origen y destino debe ser igual."
                )
            
            # Verificar que los niveles escolares coincidan
            for grado_origen, grado_destino in zip(grados_origen, grados_destino):
                if grado_origen.nivel_escolar != grado_destino.nivel_escolar:
                    raise forms.ValidationError(
                        f"Los grados {grado_origen.nombre} y {grado_destino.nombre} "
                        f"pertenecen a niveles escolares diferentes."
                    )
        
        return cleaned_data
    
class AsignarDocenteAsignaturaForm(forms.ModelForm):
    """Formulario para asignar docente a una asignatura específica"""
    
    class Meta:
        model = AsignaturaGradoAñoLectivo
        fields = ['docente']
        widgets = {
            'docente': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'Seleccione un docente'
            }),
        }
        labels = {
            'docente': 'Docente Responsable'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar docentes activos
        self.fields['docente'].queryset = Docente.objects.filter(
            estado=True
        ).select_related('usuario').order_by('usuario__apellidos', 'usuario__nombres')