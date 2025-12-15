# signals.py en la app estudiantes
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Nota
from comportamiento.models import HistorialAcademicoEstudiante

@receiver([post_save, post_delete], sender=Nota)
def actualizar_historial_academico(sender, instance, **kwargs):
    """
    Actualizar HistorialAcademicoEstudiante cuando cambien las notas
    """
    try:
        # Calcular nuevo promedio para esta asignatura, periodo y estudiante
        notas_periodo = Nota.objects.filter(
            estudiante=instance.estudiante,
            periodo_academico=instance.periodo_academico,
            asignatura_grado_año_lectivo__asignatura=instance.asignatura_grado_año_lectivo.asignatura
        )
        
        if notas_periodo.exists():
            promedio = sum(n.calificacion for n in notas_periodo) / notas_periodo.count()
            
            # Actualizar o crear HistorialAcademicoEstudiante
            historial, created = HistorialAcademicoEstudiante.objects.update_or_create(
                estudiante=instance.estudiante,
                año_lectivo=instance.periodo_academico.año_lectivo,
                periodo_academico=instance.periodo_academico,
                asignatura=instance.asignatura_grado_año_lectivo.asignatura,
                defaults={
                    'promedio_periodo': promedio,
                    # Puedes agregar más campos aquí si es necesario
                }
            )
    except Exception as e:
        # Manejar error silenciosamente o loguearlo
        pass