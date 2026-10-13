# app/templatetags/schedule_filters.py
from django import template
from datetime import datetime, time

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Obtener elemento de un diccionario"""
    if dictionary and key in dictionary:
        return dictionary[key]
    return None

@register.filter
def split(value, delimiter=','):
    """Dividir string por delimitador"""
    return value.split(delimiter)

@register.filter
def calculate_total_classes(horarios_organizados):
    """Calcular total de clases en la semana"""
    total = 0
    for dia in horarios_organizados.values():
        for hora, horario in dia.items():
            if horario:
                total += 1
    return total

@register.filter
def calculate_total_hours(horarios_organizados):
    """Calcular total de horas semanales"""
    total_hours = 0
    for dia in horarios_organizados.values():
        for hora, horario in dia.items():
            if horario:
                # Calcular duración en horas
                inicio = horario.hora_inicio
                fin = horario.hora_fin
                diff = datetime.combine(datetime.today(), fin) - datetime.combine(datetime.today(), inicio)
                total_hours += diff.total_seconds() / 3600
    return total_hours

@register.filter
def get_assigned_teachers(horarios_organizados):
    """Obtener lista de docentes asignados"""
    teachers = set()
    for dia in horarios_organizados.values():
        for hora, horario in dia.items():
            if horario and horario.asignatura_grado.docente:
                teachers.add(horario.asignatura_grado.docente.usuario.get_full_name())
    return list(teachers)

@register.filter
def get_used_rooms(horarios_organizados):
    """Obtener lista de salones utilizados"""
    rooms = set()
    for dia in horarios_organizados.values():
        for hora, horario in dia.items():
            if horario and horario.salon:
                rooms.add(horario.salon)
    return list(rooms)


@register.filter
def calculate_duration(horario):
    """Calcular duración de una clase en minutos"""
    if not horario:
        return 0
    
    inicio = horario.hora_inicio
    fin = horario.hora_fin
    
    # Calcular diferencia en minutos
    diff = datetime.combine(datetime.today(), fin) - datetime.combine(datetime.today(), inicio)
    return int(diff.total_seconds() / 60)