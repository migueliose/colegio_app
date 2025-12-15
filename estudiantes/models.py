from django.db import models
from usuarios.models import BaseModel, Usuario

class Estudiante(BaseModel):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="estudiante_profile")
    foto = models.ImageField(upload_to='detallecolegio/foto/estudiantes/', null=True, blank=True)
    estado = models.BooleanField(default=True)

    @property
    def matricula_actual(self):
        """Matrícula del año lectivo activo"""
        from gestioncolegio.models import AñoLectivo
        año_lectivo_actual = AñoLectivo.objects.filter(estado=True).first()
        if año_lectivo_actual:
            return self.matriculas.filter(
                año_lectivo=año_lectivo_actual,
                estado__in=['ACT', 'PEN']
            ).select_related(
                'grado_año_lectivo__grado',
                'sede',
                'año_lectivo'
            ).first()
        return None
    
    def tiene_matricula_en_año(self, año_lectivo):
        """Verificar si el estudiante tiene matrícula en un año específico"""
        if año_lectivo:
            return self.matriculas.filter(año_lectivo=año_lectivo).exists()
        return False
    
    def get_matricula_por_año(self, año_lectivo):
        """Obtener matrícula específica por año lectivo"""
        if año_lectivo:
            return self.matriculas.filter(año_lectivo=año_lectivo).first()
        return None
    
    def get_matriculas_por_sede(self, sede):
        """Obtener todas las matrículas de una sede específica"""
        return self.matriculas.filter(sede=sede)
    
    def matriculas_anteriores(self):
        """Todas las matrículas anteriores ordenadas por año"""
        from gestioncolegio.models import AñoLectivo
        
        # Obtener año actual si existe
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        
        # Filtrar matrículas que no sean del año actual
        if año_actual:
            return self.matriculas.filter(
                año_lectivo__anho__lt=año_actual.anho
            ).select_related(
                'grado_año_lectivo__grado',
                'sede',
                'año_lectivo'
            ).order_by('-año_lectivo__anho')
        else:
            return self.matriculas.all().select_related(
                'grado_año_lectivo__grado',
                'sede',
                'año_lectivo'
            ).order_by('-año_lectivo__anho')
    
    def historial_academico_completo(self):
        """Historial académico completo del estudiante - Versión corregida sin HistorialAcademicoEstudiante"""
        # En lugar de usar HistorialAcademicoEstudiante, obtenemos las notas
        from estudiantes.models import Nota
        from comportamiento.models import Comportamiento
        from gestioncolegio.models import AñoLectivo
        
        # Obtener todas las notas del estudiante
        notas = Nota.objects.filter(
            estudiante=self
        ).select_related(
            'asignatura_grado_año_lectivo__asignatura',
            'periodo_academico__periodo',
            'periodo_academico__año_lectivo'
        ).order_by('-periodo_academico__año_lectivo__anho', 'periodo_academico__periodo__nombre')
        
        # También obtenemos comportamientos si son necesarios
        comportamientos = Comportamiento.objects.filter(
            estudiante=self
        ).select_related(
            'periodo_academico__año_lectivo',
            'periodo_academico__periodo'
        ).order_by('-periodo_academico__año_lectivo__anho')
        
        # Podrías necesitar crear una estructura de datos personalizada
        historial = {
            'notas': notas,
            'comportamientos': comportamientos,
            # Agrega otros datos que necesites
        }
        
        return historial
    
    # Método más simple para obtener solo notas
    def get_notas_completas(self):
        """Obtener todas las notas del estudiante ordenadas"""
        from estudiantes.models import Nota
        
        return Nota.objects.filter(
            estudiante=self
        ).select_related(
            'asignatura_grado_año_lectivo__asignatura',
            'asignatura_grado_año_lectivo__grado_año_lectivo__grado',
            'periodo_academico__periodo',
            'periodo_academico__año_lectivo'
        ).order_by(
            '-periodo_academico__año_lectivo__anho',
            'periodo_academico__periodo__nombre',
            'asignatura_grado_año_lectivo__asignatura__nombre'
        )
    
    def get_grado_por_año(self, año):
        """Obtener el grado en un año específico"""
        matricula = self.matriculas.filter(
            año_lectivo__anho=año
        ).select_related(
            'grado_año_lectivo__grado'
        ).first()
        
        return matricula.grado_año_lectivo.grado if matricula else None
    
    @property
    def años_matriculados(self):
        """Lista de años en los que ha estado matriculado"""
        return self.matriculas.values_list(
            'año_lectivo__anho', flat=True
        ).distinct().order_by('-año_lectivo__anho')

    @property
    def grado_actual(self):
        matricula = self.matricula_actual
        return matricula.grado_año_lectivo if matricula else None

    @property
    def sede_actual(self):
        matricula = self.matricula_actual
        return matricula.sede if matricula else None

    def __str__(self):
        return self.usuario.get_full_name()

    class Meta:
        verbose_name = "Estudiante"
        verbose_name_plural = "Estudiantes"

class Matricula(BaseModel):
    """Matrícula de estudiantes"""
    ESTADOS_MATRICULA = [
        ('PRE', 'Pre-matrícula'),
        ('PEN', 'Pendiente'),
        ('ACT', 'Activa'),
        ('INA', 'Inactiva'),
        ('RET', 'Retirada'),
    ]
    
    estudiante = models.ForeignKey('Estudiante', on_delete=models.CASCADE, related_name="matriculas")
    año_lectivo = models.ForeignKey('gestioncolegio.AñoLectivo', on_delete=models.CASCADE, related_name="matriculas")
    sede = models.ForeignKey('gestioncolegio.Sede', on_delete=models.CASCADE, related_name="matriculas")
    grado_año_lectivo = models.ForeignKey('matricula.GradoAñoLectivo', on_delete=models.CASCADE, related_name="matriculas")
    fecha_matricula = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=3, choices=ESTADOS_MATRICULA, default='PRE')
    codigo_matricula = models.CharField(max_length=20, unique=True, blank=True)
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('estudiante', 'año_lectivo')
        verbose_name = "Matrícula"
        verbose_name_plural = "Matrículas"

    def save(self, *args, **kwargs):
        if not self.codigo_matricula:
            self.codigo_matricula = self.generar_codigo_matricula()
        super().save(*args, **kwargs)

    def generar_codigo_matricula(self):
        from django.utils import timezone
        import random
        import string
        
        año = timezone.now().year
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"MAT-{año}-{random_str}"

    def __str__(self):
        return f"{self.estudiante} - {self.grado_año_lectivo} ({self.get_estado_display()})"

class Acudiente(BaseModel):
    """Acudientes de estudiantes"""
    acudiente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="acudiente_profile")
    estudiante = models.ForeignKey('Estudiante', on_delete=models.CASCADE, related_name="acudientes")
    parentesco = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.acudiente.get_full_name()} - {self.estudiante} - {self.parentesco}"

class Nota(BaseModel):
    """Notas de estudiantes"""
    estudiante = models.ForeignKey('Estudiante', on_delete=models.CASCADE, related_name="notas")
    asignatura_grado_año_lectivo = models.ForeignKey('matricula.AsignaturaGradoAñoLectivo', on_delete=models.CASCADE)
    periodo_academico = models.ForeignKey('matricula.PeriodoAcademico', on_delete=models.CASCADE)
    calificacion = models.DecimalField(max_digits=5, decimal_places=2)
    observaciones = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.estudiante} - {self.calificacion}"

    class Meta:
        unique_together = ('estudiante', 'asignatura_grado_año_lectivo', 'periodo_academico')