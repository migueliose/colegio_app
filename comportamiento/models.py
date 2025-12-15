from django.db import models
from usuarios.models import BaseModel, Docente
from estudiantes.models import Estudiante

class Comportamiento(BaseModel):
    """Registro de comportamiento de estudiantes"""
    POSITIVO = 'Positivo'
    NEGATIVO = 'Negativo'

    TIPOS_COMPORTAMIENTO = [
        (POSITIVO, 'Positivo'),
        (NEGATIVO, 'Negativo'),
    ]
    
    CATEGORIAS = [
        ('Respeto', 'Respeto'),
        ('Responsabilidad', 'Responsabilidad'),
        ('Disciplina', 'Disciplina'),
        ('Solidaridad', 'Solidaridad'),
        ('Academico', 'Académico'),
    ]

    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name="comportamientos")
    periodo_academico = models.ForeignKey('matricula.PeriodoAcademico', on_delete=models.CASCADE, related_name="comportamientos")
    docente = models.ForeignKey(Docente, on_delete=models.SET_NULL, null=True, blank=True, related_name="comportamientos_registrados")
    tipo = models.CharField(max_length=10, choices=TIPOS_COMPORTAMIENTO)
    categoria = models.CharField(max_length=15, choices=CATEGORIAS, default='Academico')
    descripcion = models.TextField()
    fecha = models.DateField()

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.estudiante} - {self.tipo} - {self.categoria} - {self.fecha}"

class Asistencia(BaseModel):
    """Registro de asistencia de estudiantes"""
    ESTADO_CHOICES = [
        ('A', 'Asistió'),
        ('F', 'Faltó'),
        ('J', 'Falta justificada'),
    ]
    
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name="asistencias")
    periodo_academico = models.ForeignKey('matricula.PeriodoAcademico', on_delete=models.CASCADE)
    fecha = models.DateField()
    estado = models.CharField(max_length=1, choices=ESTADO_CHOICES, default='A')
    justificacion = models.TextField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['estudiante', 'fecha'], name='unique_asistencia')
        ]

    def __str__(self):
        return f"{self.estudiante} - {self.fecha} - {self.get_estado_display()}"

class Inconsistencia(BaseModel):
    """Inconsistencias académicas"""
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name="inconsistencias")
    fecha = models.DateField(auto_now=True)
    tipo = models.CharField(max_length=50)
    descripcion = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['estudiante', 'fecha', 'tipo'], name='unique_inconsistencia')
        ]

    def __str__(self):
        return f"{self.estudiante} - {self.tipo} - {self.fecha}"
