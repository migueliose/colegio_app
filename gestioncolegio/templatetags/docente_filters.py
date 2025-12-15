#gestioncolegio/templatetags/docente_filters.py
from django import template
from estudiantes.models import Estudiante
from gestioncolegio.models import AñoLectivo

register = template.Library()

@register.filter
def count_estudiantes_asignatura(asignatura_grado):
    """Cuenta estudiantes en una asignatura - CORREGIDO"""
    try:
        # Obtener año lectivo actual
        from gestioncolegio.models import AñoLectivo
        año_lectivo_actual = AñoLectivo.objects.filter(estado=True).first()
        if not año_lectivo_actual:
            return 0
            
        # Contar estudiantes a través de matrículas
        from estudiantes.models import Matricula
        count = Matricula.objects.filter(
            grado_año_lectivo=asignatura_grado.grado_año_lectivo,
            año_lectivo=año_lectivo_actual,
            estado__in=['ACT', 'PEN']
        ).distinct().count()
        
        return count
    except Exception as e:
        print(f"Error en count_estudiantes_asignatura: {e}")
        return 0

@register.filter
def horas_semana(asignatura_grado):
    """Calcula horas semanales de una asignatura - VERSIÓN MEJORADA"""
    try:
        from academico.models import HorarioClase
        # Calcular horas totales sumando duración de cada horario
        horarios = HorarioClase.objects.filter(asignatura_grado=asignatura_grado)
        
        total_horas = 0
        for horario in horarios:
            # Calcular duración en horas
            duracion = horario.hora_fin.hour - horario.hora_inicio.hour
            duracion += (horario.hora_fin.minute - horario.hora_inicio.minute) / 60
            total_horas += duracion
        
        # Si no hay horarios, usar la intensidad horaria de la asignatura
        if total_horas == 0:
            return asignatura_grado.asignatura.ih or "3"
        
        return round(total_horas, 1)
    except Exception as e:
        print(f"Error en horas_semana: {e}")
        return asignatura_grado.asignatura.ih or "3"

@register.filter
def format_hora_clase(horario):
    """Formatea la hora de la clase"""
    try:
        return f"{horario.hora_inicio.strftime('%H:%M')} - {horario.hora_fin.strftime('%H:%M')}"
    except:
        return "Horario no disponible"

@register.filter
def dia_semana_espanol(dia):
    """Convierte día de la semana a español"""
    dias = {
        'MON': 'Lunes',
        'TUE': 'Martes', 
        'WED': 'Miércoles',
        'THU': 'Jueves',
        'FRI': 'Viernes',
        'SAT': 'Sábado',
        'SUN': 'Domingo',
        'LUN': 'Lunes',
        'MAR': 'Martes',
        'MIE': 'Miércoles',
        'JUE': 'Jueves',
        'VIE': 'Viernes'
    }
    return dias.get(dia, dia)