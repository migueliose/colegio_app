from django.db import models
from usuarios.models import BaseModel, Docente
from academico.models import Grado, Asignatura, Periodo

# SOLO estos modelos en matriculas, los demás en gestioncolegio

class GradoAñoLectivo(BaseModel):
    """Relación entre grados y años lectivos"""
    grado = models.ForeignKey(Grado, on_delete=models.CASCADE, related_name="grados_año_lectivo")
    año_lectivo = models.ForeignKey('gestioncolegio.AñoLectivo', on_delete=models.CASCADE, related_name="grados_año_lectivo")
    estado = models.BooleanField(default=True)

    class Meta:
        unique_together = ('grado', 'año_lectivo')

    def __str__(self):
        return f"{self.grado.nombre} - {self.año_lectivo.anho}"

class AsignaturaGradoAñoLectivo(BaseModel):
    """Asignaturas por grado y año lectivo"""
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE, related_name="asignaturas_grado")
    grado_año_lectivo = models.ForeignKey(GradoAñoLectivo, on_delete=models.CASCADE, related_name="asignaturas_grado")
    docente = models.ForeignKey(Docente, on_delete=models.CASCADE, related_name="asignaturas_dictadas", blank=True, null=True)
    sede = models.ForeignKey('gestioncolegio.Sede', on_delete=models.CASCADE, related_name="asignaturas_grado")

    class Meta:
        unique_together = ('asignatura', 'grado_año_lectivo', 'sede')

    def __str__(self):
        return f"{self.asignatura.nombre} - {self.grado_año_lectivo.grado} ({self.sede.nombre})"

class PeriodoAcademico(BaseModel):
    """Periodos académicos dentro de un año lectivo"""
    año_lectivo = models.ForeignKey('gestioncolegio.AñoLectivo', on_delete=models.CASCADE, related_name="periodos_academicos")
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, related_name='periodos')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['año_lectivo', 'periodo'], name='unique_periodo_por_año_lectivo')
        ]

    def __str__(self):
        return f"{self.año_lectivo} - {self.periodo.nombre}"

class DocenteSede(BaseModel):
    """Asignación de docentes a sedes"""
    docente = models.ForeignKey(Docente, on_delete=models.CASCADE, related_name="sedes_asignadas")
    sede = models.ForeignKey('gestioncolegio.Sede', on_delete=models.CASCADE, related_name="docentes_asignados")
    año_lectivo = models.ForeignKey('gestioncolegio.AñoLectivo', on_delete=models.CASCADE, related_name="docentes_sede")
    fecha_asignacion = models.DateField(auto_now_add=True)
    estado = models.BooleanField(default=True)

    class Meta:
        unique_together = ('docente', 'sede', 'año_lectivo')

    def __str__(self):
        return f"{self.docente} - {self.sede} ({self.año_lectivo})"