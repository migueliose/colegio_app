from django.db import models
from usuarios.models import BaseModel

class NivelEscolar(BaseModel):
    """Niveles escolares (Preescolar, Primaria)"""
    PREESCOLAR = 'Preescolar'
    PRIMARIA = 'Primaria'

    NIVELES = [
        (PREESCOLAR, 'Preescolar'),
        (PRIMARIA, 'Primaria'),
    ]

    nombre = models.CharField(max_length=50, choices=NIVELES, unique=True)

    def __str__(self):
        return self.nombre

class Grado(BaseModel):
    """Grados académicos"""
    PREJARDIN = 'Prejardin'
    JARDIN = 'Jardin'
    TRANSICION = 'Transicion'
    PRIMERO = 'Primero'
    SEGUNDO = 'Segundo'
    TERCERO = 'Tercero'
    CUARTO = 'Cuarto'
    QUINTO = 'Quinto'

    GRADOS = [
        (PREJARDIN, 'Prejardin'), (JARDIN, 'Jardin'), (TRANSICION, 'Transicion'),
        (PRIMERO, 'Primero'), (SEGUNDO, 'Segundo'), (TERCERO, 'Tercero'), 
        (CUARTO, 'Cuarto'), (QUINTO, 'Quinto'),
    ]

    nombre = models.CharField(max_length=50, choices=GRADOS, unique=True)
    nivel_escolar = models.ForeignKey(NivelEscolar, on_delete=models.CASCADE, related_name="grados")

    def __str__(self):
        return self.nombre

class Area(BaseModel):
    """Áreas del conocimiento"""
    nombre = models.CharField(max_length=100)
    nivel_escolar = models.ForeignKey(NivelEscolar, on_delete=models.CASCADE, related_name="areas")

    def __str__(self):
        return self.nombre

class Asignatura(BaseModel):
    """Asignaturas por área"""
    nombre = models.CharField(max_length=100)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="asignaturas")
    ih = models.CharField(max_length=1, verbose_name='Intensidad horaria', blank=True, null=True)

    def __str__(self):
        return self.nombre

class Periodo(BaseModel):
    """Periodos académicos (Primer, Segundo, etc.)"""
    PRIMER = 'Primer'
    SEGUNDO = 'Segundo'
    TERCERO = 'Tercero'
    CUARTO = 'Cuarto'

    PERIODOS = [    
        (PRIMER, 'Primer'), (SEGUNDO, 'Segundo'), 
        (TERCERO, 'Tercero'), (CUARTO, 'Cuarto')
    ]

    nombre = models.CharField(max_length=50, choices=PERIODOS, unique=True)
    
    def __str__(self):
        return self.nombre

class Logro(BaseModel):
    """Logros por asignatura y periodo"""
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE, related_name="logros")
    periodo_academico = models.ForeignKey('matricula.PeriodoAcademico', on_delete=models.CASCADE, related_name="logros")
    grado = models.ForeignKey(Grado, on_delete=models.CASCADE, related_name="logros")
    tema = models.TextField(blank=True, null=True)
    descripcion_superior = models.TextField(null=True, blank=True)
    descripcion_alto = models.TextField(null=True, blank=True)
    descripcion_basico = models.TextField(null=True, blank=True)
    descripcion_bajo = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.asignatura.nombre} - {self.periodo_academico} - {self.tema}"

class HorarioClase(BaseModel):
    """Horarios de clases"""
    asignatura_grado = models.ForeignKey('matricula.AsignaturaGradoAñoLectivo', on_delete=models.CASCADE, related_name="horarios")
    dia_semana = models.CharField(max_length=10, choices=[
        ('LUN', 'Lunes'), ('MAR', 'Martes'), ('MIE', 'Miércoles'),
        ('JUE', 'Jueves'), ('VIE', 'Viernes')
    ])
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    salon = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ('asignatura_grado', 'dia_semana', 'hora_inicio')
        ordering = ['dia_semana', 'hora_inicio']

    def __str__(self):
        return f"{self.asignatura_grado} - {self.get_dia_semana_display()} {self.hora_inicio}"