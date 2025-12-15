#modelos gestioncolegio
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from usuarios.models import BaseModel, Usuario

# ================ CONFIGURACIÓN INSTITUCIONAL ==================
class Colegio(BaseModel):
    """Información principal del colegio"""
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255)
    resolucion = models.CharField(max_length=50)
    dane = models.CharField(max_length=50)
    estado = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Colegio"
        verbose_name_plural = "Colegios"


class Sede(BaseModel):
    """Sedes del colegio"""
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name="sedes_gestion") 
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    director = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="sedes_gestion_dirigidas")
    estado = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} - {self.colegio.nombre}"

    class Meta:
        verbose_name = "Sede"
        verbose_name_plural = "Sedes"


class RecursosColegio(BaseModel):
    """Recursos multimedia del colegio"""
    colegio = models.OneToOneField(Colegio, on_delete=models.CASCADE, related_name="recursos")
    escudo = models.ImageField(upload_to='detallecolegio/escudos/', null=True, blank=True)
    bandera = models.ImageField(upload_to='detallecolegio/banderas/', null=True, blank=True)
    sitio_web = models.URLField(max_length=200)
    email = models.EmailField()
    telefono = models.CharField(max_length=20, null=True, blank=True)
    
    def __str__(self):
        return f"Recursos - {self.colegio.nombre}"

    class Meta:
        verbose_name = "Recursos del Colegio"
        verbose_name_plural = "Recursos del Colegio"


class AñoLectivo(BaseModel):
    """Años lectivos del colegio por sede"""
    colegio = models.ForeignKey(Colegio, on_delete=models.CASCADE, related_name="años_lectivos")
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name="años_lectivos")
    anho = models.CharField(max_length=5, verbose_name='Año Lectivo')
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    estado = models.BooleanField(default=True)

    class Meta:
        unique_together = ('colegio', 'sede', 'anho')
        verbose_name = "Año Lectivo"
        verbose_name_plural = "Años Lectivos"

    def __str__(self):
        return f"{self.sede.nombre} - {self.anho}"


class ConfiguracionGeneral(BaseModel):
    """Configuración general del sistema"""
    colegio = models.OneToOneField(Colegio, on_delete=models.CASCADE, related_name="configuracion")
    año_lectivo_actual = models.ForeignKey(AñoLectivo, on_delete=models.SET_NULL, null=True, blank=True)
    max_estudiantes_por_grupo = models.PositiveIntegerField(default=40)
    porcentaje_aprobacion = models.DecimalField(max_digits=5, decimal_places=2, default=60.0)
    habilitar_matricula = models.BooleanField(default=True)
    habilitar_calificaciones = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Configuración - {self.colegio.nombre}"

    class Meta:
        verbose_name = "Configuración General"
        verbose_name_plural = "Configuraciones Generales"


class ParametroSistema(BaseModel):
    """Parámetros configurables del sistema"""
    clave = models.CharField(max_length=100, unique=True)
    valor = models.TextField()
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=50, choices=[
        ('texto', 'Texto'),
        ('numero', 'Número'),
        ('booleano', 'Booleano'),
        ('fecha', 'Fecha'),
    ])
    
    def __str__(self):
        return f"{self.clave} - {self.descripcion}"

    class Meta:
        verbose_name = "Parámetro del Sistema"
        verbose_name_plural = "Parámetros del Sistema"


class AuditoriaSistema(BaseModel):
    """Registro de auditoría del sistema"""
    TIPOS_ACCION = [
        ('creacion', 'Creación'),
        ('modificacion', 'Modificación'),
        ('eliminacion', 'Eliminación'),
        ('login', 'Inicio de Sesión'),
        ('logout', 'Cierre de Sesión'),
    ]
    
    usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True)
    accion = models.CharField(max_length=20, choices=TIPOS_ACCION)
    modelo_afectado = models.CharField(max_length=100)
    objeto_id = models.CharField(max_length=100, blank=True)
    descripcion = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.usuario} - {self.accion} - {self.modelo_afectado}"

    class Meta:
        verbose_name = "Auditoría del Sistema"
        verbose_name_plural = "Auditorías del Sistema"
        ordering = ['-created_at']

class NotificacionSistema(BaseModel):
    """Sistema de notificaciones"""
    TIPOS_NOTIFICACION = [
        ('info', 'Informativa'),
        ('warning', 'Advertencia'),
        ('error', 'Error'),
        ('success', 'Éxito'),
    ]
    
    usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.CASCADE, related_name='notificaciones')
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=10, choices=TIPOS_NOTIFICACION, default='info')
    leida = models.BooleanField(default=False)
    fecha_lectura = models.DateTimeField(null=True, blank=True)
    url_destino = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notificación del Sistema"
        verbose_name_plural = "Notificaciones del Sistema"
    
    def __str__(self):
        return f"{self.usuario} - {self.titulo}"

