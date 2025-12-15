from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone

class BaseModel(models.Model):
    """Modelo abstracto base para todos los modelos"""
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class TipoDocumento(BaseModel):
    """Tipos de documento de identidad"""
    RC = 'Registro Civil'
    TI = 'Tarjeta de Identidad'
    CC = 'Cedula de Ciudadania'
    CE = 'Cedula de Extranjeria'
    PA = 'Pasaporte'

    TIPOS = [ 
        (RC, 'Registro Civil'), (TI, 'Tarjeta de Identidad'), (CC, 'Cedula de Ciudadania'),
        (CE, 'Cedula de Extranjeria'), (PA, 'Pasaporte')
    ]

    nombre = models.CharField(max_length=50, choices=TIPOS, unique=True)

    def __str__(self):
        return self.nombre

class TipoUsuario(BaseModel):
    """Tipos de usuario del sistema"""
    ADMINISTRADOR = 'Administrador'
    RECTOR = 'Rector(a)'
    DOCENTE = 'Docente'
    ESTUDIANTE = 'Estudiante'
    ACUDIENTE = 'Acudiente'

    TIPOS = [   
        (ADMINISTRADOR, 'Administrador'), (RECTOR, 'Rector(a)'), 
        (DOCENTE, 'Docente'), (ESTUDIANTE, 'Estudiante'), (ACUDIENTE, 'Acudiente')
    ]

    nombre = models.CharField(max_length=50, choices=TIPOS, unique=True)

    def __str__(self):
        return self.nombre

class Usuario(AbstractUser, BaseModel):
    """Usuario extendido del sistema"""
    SEXO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
    ]

    tipo_documento = models.ForeignKey(TipoDocumento, on_delete=models.SET_NULL, null=True)
    numero_documento = models.CharField(max_length=50, unique=True, db_index=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    estado = models.BooleanField(default=True)
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, blank=True, null=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    tipo_usuario = models.ForeignKey(TipoUsuario, on_delete=models.SET_NULL, null=True)

    @property
    def edad(self):
        if self.fecha_nacimiento:
            today = timezone.now().date()
            return today.year - self.fecha_nacimiento.year - (
                (today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
            )
        return None
    
    def get_full_name(self):
        return f"{self.nombres} {self.apellidos}"
    
    def __str__(self):
        return self.get_full_name()

    class Meta:
        db_table = 'usuarios_usuario'

class Docente(BaseModel):
    """Perfil de docente"""
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="docente_profile")
    foto = models.ImageField(upload_to='detallecolegio/foto/docentes/', null=True, blank=True)    
    hdv = models.FileField(upload_to='detallescolegio/hdv/', blank=True, null=True)
    estado = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.usuario.get_full_name()} - Docente"

class ContactoDocente(BaseModel):
    """Contactos de emergencia para docentes"""
    docente = models.ForeignKey(Docente, on_delete=models.CASCADE, related_name="contactos")
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20)
    email = models.EmailField()
    relacion = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.nombres} {self.apellidos} - {self.docente.usuario.get_full_name()}"