# gestioncolegio/templatetags/estudiante_filters.py
from django.db import models
from django import template
import statistics
from django.utils import timezone
from datetime import datetime
from matricula.models import PeriodoAcademico
from decimal import Decimal

register = template.Library()

# ==============================================
# FILTROS PARA CÁLCULO DE NOTAS Y PROMEDIOS
# ==============================================

@register.filter
def calcular_promedio(asignaturas):
    if not asignaturas:
        return 0
    
    notas_con_valor = []
    for a in asignaturas:
        if isinstance(a, dict):
            if a.get('tiene_nota') and a.get('calificacion') is not None:
                calificacion = a['calificacion']
                if isinstance(calificacion, (int, float, Decimal)):
                    notas_con_valor.append(float(calificacion))
        else:
            if getattr(a, 'tiene_nota', False) and getattr(a, 'calificacion', None) is not None:
                calificacion = getattr(a, 'calificacion')
                if isinstance(calificacion, (int, float, Decimal)):
                    notas_con_valor.append(float(calificacion))
    
    if not notas_con_valor:
        return 0
    
    # USAR sum_values EN LUGAR DE sum
    total = sum_values(notas_con_valor)  # ← CAMBIO AQUÍ
    return round(total / len(notas_con_valor), 1)

@register.filter
def calcular_mediana(asignaturas):
    """Calcula la mediana de las calificaciones"""
    notas = []
    for a in asignaturas:
        if isinstance(a, dict):
            if a.get('tiene_nota') and a.get('calificacion'):
                notas.append(a['calificacion'])
        elif getattr(a, 'tiene_nota', False) and getattr(a, 'calificacion', None):
            notas.append(a.calificacion)
    
    if not notas:
        return 0
    
    try:
        return round(statistics.median(notas), 1)
    except statistics.StatisticsError:
        return 0

@register.filter
def calcular_moda(asignaturas):
    """Calcula la moda de las calificaciones"""
    notas = []
    for a in asignaturas:
        if isinstance(a, dict):
            if a.get('tiene_nota') and a.get('calificacion'):
                notas.append(a['calificacion'])
        elif getattr(a, 'tiene_nota', False) and getattr(a, 'calificacion', None):
            notas.append(a.calificacion)
    
    if not notas:
        return 0
    
    try:
        moda = statistics.mode(notas)
        return round(moda, 1)
    except statistics.StatisticsError:
        return 0

# ==============================================
# FILTROS PARA DESEMPEÑO Y COLORES
# ==============================================

@register.filter
def calcular_desempeno_promedio(asignaturas):
    notas_validas = []
    
    for a in asignaturas:
        if isinstance(a, dict):
            if a.get('tiene_nota') and a.get('calificacion') is not None:
                calificacion = a['calificacion']
                if isinstance(calificacion, (int, float)):
                    notas_validas.append(calificacion)
        else:
            if getattr(a, 'tiene_nota', False) and getattr(a, 'calificacion', None) is not None:
                calificacion = getattr(a, 'calificacion')
                if isinstance(calificacion, (int, float)):
                    notas_validas.append(calificacion)
    
    if not notas_validas:
        return "No evaluado"
    
    promedio = sum(notas_validas) / len(notas_validas)
    
    if promedio >= 4.6:
        return "Superior"
    elif promedio >= 4.0:
        return "Alto"
    elif promedio >= 3.0:
        return "Básico"
    else:
        return "Bajo"

@register.filter
def color_desempeno(desempeno):
    """Retorna la clase de color de Bootstrap para un desempeño"""
    colores = {
        'Superior': 'success',
        'Alto': 'info', 
        'Básico': 'warning',
        'Bajo': 'danger',
        'No evaluado': 'secondary'
    }
    return colores.get(desempeno, 'secondary')

@register.filter
def get_color(desempeno, output_format='hex'):
    """Asigna colores a los niveles de desempeño"""
    color_map = {
        'Superior': {
            'hex': '#28a745', 'rgb': 'rgb(40, 167, 69)', 'name': 'verde', 'class': 'success'
        },
        'Alto': {
            'hex': '#17a2b8', 'rgb': 'rgb(23, 162, 184)', 'name': 'azul-claro', 'class': 'info'
        },
        'Básico': {
            'hex': '#ffc107', 'rgb': 'rgb(255, 193, 7)', 'name': 'amarillo', 'class': 'warning'
        },
        'Bajo': {
            'hex': '#dc3545', 'rgb': 'rgb(220, 53, 69)', 'name': 'rojo', 'class': 'danger'
        },
        'No evaluado': {
            'hex': '#6c757d', 'rgb': 'rgb(108, 117, 125)', 'name': 'gris', 'class': 'secondary'
        }
    }
    
    if not desempeno:
        desempeno = 'No evaluado'
    
    nivel = desempeno.capitalize() if isinstance(desempeno, str) else desempeno
    nivel_data = color_map.get(nivel, color_map['No evaluado'])
    
    return nivel_data.get(output_format, nivel_data['hex'])

# ==============================================
# FILTROS PARA CONTEO Y ESTADÍSTICAS
# ==============================================

@register.filter
def count_performance(asignaturas, nivel):
    """Cuenta cuántas asignaturas tienen un nivel de desempeño específico"""
    if not asignaturas:
        return 0
    
    count = 0
    for asignatura in asignaturas:
        desempeno = None
        if isinstance(asignatura, dict):
            desempeno = asignatura.get('desempeno')
            tiene_nota = asignatura.get('tiene_nota')
        else:
            desempeno = getattr(asignatura, 'desempeno', None)
            tiene_nota = getattr(asignatura, 'tiene_nota', False)
        
        if desempeno == nivel and tiene_nota:
            count += 1
    
    return count

@register.filter
def performance_percentage(asignaturas, nivel):
    """Calcula el porcentaje de asignaturas con un nivel de desempeño específico"""
    if not asignaturas:
        return 0
    
    count = count_performance(asignaturas, nivel)
    return round((count / len(asignaturas)) * 100, 1)

@register.filter
def count_evaluated(notas):
    """Cuenta las asignaturas evaluadas"""
    if not notas:
        return 0
    
    count = 0
    for nota in notas:
        if isinstance(nota, dict):
            if nota.get('tiene_nota'):
                count += 1
        elif getattr(nota, 'tiene_nota', False):
            count += 1
    
    return count

@register.filter
def count_pending(notas):
    """Cuenta las asignaturas pendientes"""
    if not notas:
        return 0
    
    total = len(notas)
    evaluadas = count_evaluated(notas)
    return total - evaluadas

# ==============================================
# FILTROS PARA COMPORTAMIENTO
# ==============================================

@register.filter
def filter_by_tipo(comportamientos, tipo):
    """Filtra comportamientos por tipo (Positivo/Negativo)"""
    if not comportamientos:
        return []
    
    return [c for c in comportamientos if getattr(c, 'tipo', '').capitalize() == tipo.capitalize()]

@register.filter
def count_by_tipo(comportamientos, tipo):
    """Cuenta comportamientos por tipo"""
    if not comportamientos:
        return 0
    
    return len(filter_by_tipo(comportamientos, tipo))

@register.filter
def comportamiento_positivo_count(comportamientos):
    """Cuenta solo comportamientos positivos"""
    return count_by_tipo(comportamientos, 'Positivo')

@register.filter
def comportamiento_negativo_count(comportamientos):
    """Cuenta solo comportamientos negativos"""
    return count_by_tipo(comportamientos, 'Negativo')

@register.filter
def comportamiento_porcentaje_positivo(comportamientos):
    """Calcula el porcentaje de comportamientos positivos"""
    if not comportamientos:
        return 0
    
    positivos = comportamiento_positivo_count(comportamientos)
    return round((positivos / len(comportamientos)) * 100, 1)

# ==============================================
# FILTROS PARA MANIPULACIÓN DE DATOS
# ==============================================

@register.filter
def get_item(dictionary, key):
    """Obtiene un elemento de un diccionario por su clave"""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter
def get_attr(obj, attr_name):
    """Obtiene un atributo dinámicamente de un objeto"""
    try:
        if not obj:
            return None
            
        value = obj
        for part in attr_name.split('.'):
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value
    except Exception:
        return None

@register.filter
def extract_attr(items, attr_name):
    """Extrae un atributo específico de cada item"""
    result = []
    for item in items:
        value = get_attr(item, attr_name)
        if value is not None:
            result.append(value)
    return result

@register.filter
def select_by_attr(items, attr_name):
    """Filtra items donde el atributo es verdadero"""
    return [item for item in items if get_attr(item, attr_name)]

@register.filter
def filter_by_attr(items, attr_name, value):
    """Filtra items donde el atributo tiene un valor específico"""
    return [item for item in items if get_attr(item, attr_name) == value]

# ==============================================
# FILTROS MATEMÁTICOS
# ==============================================

@register.filter
def multiply(value, arg):
    """Multiplica value por arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Divide value por arg"""
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def safe_division(dividend, divisor):
    """División segura que evita divisiones por cero"""
    try:
        if float(divisor) == 0:
            return 0
        return float(dividend) / float(divisor)
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """Calcula porcentaje"""
    try:
        if float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError):
        return 0

@register.filter
def subtract(value, arg):
    """Resta arg de value"""
    try:
        # Manejar diferentes tipos de entrada
        if hasattr(value, '__len__'):
            value_len = len(value)
            return value_len - int(arg)
        else:
            return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

# ==============================================
# FILTROS PARA FORMATO Y PRESENTACIÓN
# ==============================================

@register.filter
def format_date(date_obj):
    """Formatea una fecha de manera amigable"""
    if not date_obj:
        return "No definido"
    
    try:
        now = timezone.now()
        if isinstance(date_obj, str):
            date_obj = datetime.strptime(date_obj, '%Y-%m-%d')
        
        diff = now.date() - date_obj.date() if hasattr(date_obj, 'date') else now - date_obj
        
        if diff.days == 0:
            return "Hoy"
        elif diff.days == 1:
            return "Ayer"
        elif diff.days < 7:
            return f"Hace {diff.days} días"
        else:
            return date_obj.strftime("%d/%m/%Y")
    except Exception:
        return "Fecha inválida"

@register.filter
def format_percentage(value):
    """Formatea un valor como porcentaje"""
    try:
        return f"{float(value):.1f}%"
    except (ValueError, TypeError):
        return "0.0%"

@register.filter
def truncate_chars(value, max_length):
    """Trunca un texto a un máximo de caracteres"""
    if not value:
        return ""
    
    if len(value) <= max_length:
        return value
    return value[:max_length] + "..."

@register.filter
def get_initial_icon(nombre):
    """Devuelve la inicial para un avatar"""
    if not nombre:
        return "?"
    
    # Tomar la primera letra del primer nombre
    palabras = str(nombre).strip().split()
    if palabras:
        return palabras[0][0].upper()
    return "?"

@register.filter
def get_status_badge(estado):
    """Devuelve un badge de Bootstrap según el estado"""
    badges = {
        'A': ('success', 'Asistió'),
        'F': ('danger', 'Falta'),
        'J': ('warning', 'Justificada'),
        'R': ('secondary', 'Retardo'),
        'P': ('info', 'Permiso'),
        'V': ('dark', 'Vacaciones'),
    }
    
    color, texto = badges.get(estado, ('secondary', 'Sin registro'))
    return texto  # Solo devuelve el texto, el HTML se generará en la plantilla

# ==============================================
# FILTROS ESPECIALIZADOS PARA ESTUDIANTES
# ==============================================

@register.filter
def calculate_age(fecha_nacimiento):
    """Calcula la edad a partir de la fecha de nacimiento"""
    if not fecha_nacimiento:
        return "No disponible"
    
    try:
        today = datetime.now().date()
        
        if isinstance(fecha_nacimiento, str):
            fecha_nacimiento = datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date()
        
        age = today.year - fecha_nacimiento.year
        if today.month < fecha_nacimiento.month or (today.month == fecha_nacimiento.month and today.day < fecha_nacimiento.day):
            age -= 1
        
        return f"{age} años"
    except Exception:
        return "No disponible"

@register.filter
def get_academic_level(estudiante):
    """Obtiene el nivel académico del estudiante"""
    if hasattr(estudiante, 'grado_actual'):
        nivel = get_attr(estudiante, 'grado_actual.nombre')
        if nivel:
            return nivel
    return "No definido"

@register.filter
def get_periodo_actual(estudiante):
    """Obtiene el período actual del estudiante"""
    try:
        from matricula.models import PeriodoAcademico
        if hasattr(estudiante, 'matricula_actual'):
            matricula = estudiante.matricula_actual
            if matricula and hasattr(matricula, 'año_lectivo'):
                periodo = PeriodoAcademico.objects.filter(
                    año_lectivo=matricula.año_lectivo,
                    estado=True
                ).order_by('-fecha_inicio').first()
                return periodo
    except Exception:
        return None
    return None

# ==============================================
# FILTROS UTILITARIOS
# ==============================================

@register.filter
def get_range(value):
    """Crea un rango de números"""
    try:
        return range(int(value))
    except (ValueError, TypeError):
        return range(0)

@register.filter
def split(value, separator):
    """Divide un string por un separador y retorna una lista"""
    if not value:
        return []
    return str(value).split(separator)

@register.filter
def index(sequence, position):
    """Obtiene un elemento de una secuencia por índice"""
    try:
        return sequence[int(position)]
    except (IndexError, ValueError, TypeError):
        return None

@register.filter
def sum_values(items):
    """Suma todos los valores de una lista/diccionario/queryset"""
    try:
        if isinstance(items, dict):
            return sum(items.values())
        elif hasattr(items, '__iter__'):
            return sum(float(item) for item in items if str(item).replace('.', '').isdigit())
        else:
            return float(items) if str(items).replace('.', '').isdigit() else 0
    except (ValueError, TypeError):
        return 0

@register.filter
def sum_attr(items, attr_name):
    """Suma un atributo específico de una lista de objetos/diccionarios"""
    total = 0
    for item in items:
        value = get_attr(item, attr_name)
        if isinstance(value, (int, float)):
            total += value
    return total

# ==============================================
# FILTROS DE MAPEO (similar a Python map)
# ==============================================

@register.filter(name='map')
def map_filter(items, attr_name):
    """
    Filtro que funciona como map para obtener atributos de objetos.
    Se registra con name='map' para poder usarlo como {{ items|map:'atributo' }}
    """
    return extract_attr(items, attr_name)

@register.filter
def map_attr(items, attr_name):
    """Alias para extract_attr"""
    return extract_attr(items, attr_name)

@register.filter
def map_key(dict_items, key_name):
    """Obtiene valores de diccionarios por clave"""
    if not dict_items:
        return []
    return [item.get(key_name) for item in dict_items]

# ==============================================
# FILTROS PARA TENDENCIAS Y PROGRESO
# ==============================================

@register.filter
def calcular_tendencia(periodos_comparativos):
    """Calcula la tendencia del rendimiento a través de períodos"""
    if not periodos_comparativos or len(periodos_comparativos) < 2:
        return "estable"
    
    try:
        promedios = []
        for periodo_data in periodos_comparativos:
            if periodo_data.get('notas'):
                prom = calcular_promedio(periodo_data['notas'])
                if prom > 0:
                    promedios.append(prom)
        
        if len(promedios) < 2:
            return "estable"
        
        # Calcular tendencia
        diferencia = promedios[-1] - promedios[0]
        if diferencia > 0.3:
            return "mejorando"
        elif diferencia < -0.3:
            return "bajando"
        else:
            return "estable"
    except Exception:
        return "estable"

@register.filter
def calcular_progreso(notas_actuales, notas_anteriores):
    """Calcula el progreso entre dos conjuntos de notas"""
    if not notas_actuales or not notas_anteriores:
        return 0
    
    try:
        prom_actual = calcular_promedio(notas_actuales)
        prom_anterior = calcular_promedio(notas_anteriores)
        
        if prom_anterior == 0:
            return 100
        
        progreso = ((prom_actual - prom_anterior) / prom_anterior) * 100
        return round(progreso, 1)
    except Exception:
        return 0

# ==============================================
# FILTROS PARA CALIFICACIONES
# ==============================================

@register.filter
def calificacion_color(value):
    """Determina el color basado en la calificación"""
    try:
        valor = float(value)
        if valor >= 4.6:
            return 'success'
        elif valor >= 4.0:
            return 'info'
        elif valor >= 3.0:
            return 'warning'
        else:
            return 'danger'
    except (ValueError, TypeError):
        return 'secondary'

@register.filter
def desempeno_texto(value):
    """Determina el texto de desempeño basado en la calificación"""
    try:
        valor = float(value)
        if valor >= 4.6:
            return 'Superior'
        elif valor >= 4.0:
            return 'Alto'
        elif valor >= 3.0:
            return 'Básico'
        else:
            return 'Bajo'
    except (ValueError, TypeError):
        return 'No evaluado'
    
@register.filter
def filter_activos(años_lectivos):
    """Cuenta cuántos años están activos"""
    if not años_lectivos:
        return 0
    
    count = 0
    for año in años_lectivos:
        # Verifica si es un diccionario
        if isinstance(año, dict):
            if año.get('es_año_activo_sistema'):
                count += 1
        # Verifica si es un objeto con atributo
        elif hasattr(año, 'es_año_activo_sistema'):
            if año.es_año_activo_sistema:
                count += 1
        # Verifica si es un objeto con método get
        elif hasattr(año, 'get'):
            if año.get('es_año_activo_sistema'):
                count += 1
    
    return count

@register.filter
def contar_inactivos(años_lectivos):
    """Cuenta cuántos años están inactivos"""
    if not años_lectivos:
        return 0
    
    total = len(años_lectivos)
    activos = filter_activos(años_lectivos)
    return total - activos

@register.filter
def count_evaluadas(asignaturas):
    """Cuenta cuántas asignaturas tienen calificación"""
    if not asignaturas:
        return 0
    
    count = 0
    for asignatura in asignaturas:
        # Manejo para diccionarios
        if isinstance(asignatura, dict):
            if asignatura.get('tiene_nota'):
                count += 1
        # Manejo para objetos
        elif hasattr(asignatura, 'tiene_nota'):
            if asignatura.tiene_nota:
                count += 1
    
    return count

@register.filter
def get_matricula_info(estudiante, año_str):
    """Obtiene información de matrícula por año específico"""
    try:
        # Buscar la matrícula para el año específico
        matricula = estudiante.matriculas.filter(
            año_lectivo__anho=año_str
        ).select_related(
            'año_lectivo',
            'grado_año_lectivo__grado'
        ).first()
        
        if matricula:
            return {
                'año_id': matricula.año_lectivo.id,
                'año': matricula.año_lectivo.anho,
                'grado': matricula.grado_año_lectivo.grado.nombre if matricula.grado_año_lectivo else None,
                'estado': matricula.estado,
                'matricula_obj': matricula,
                'tiene_notas': matricula.estudiante.notas.filter(
                    periodo_academico__año_lectivo=matricula.año_lectivo
                ).exists(),
            }
        return None
    except Exception as e:
        print(f"Error obteniendo información de matrícula: {e}")
        return None

@register.filter
def average(values):
    """Calcula el promedio de una lista numérica."""
    if not values:
        return 0
    try:
        numeric_values = [float(v) for v in values if v is not None]
        if not numeric_values:
            return 0
        return round(sum(numeric_values) / len(numeric_values), 2)
    except:
        return 0
    
@register.filter
def multiply(value, arg):
    """Multiplica el valor por el argumento"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def calculate_average(queryset, field_name):
    """Calcula el promedio de un campo en un queryset"""
    if not queryset:
        return 0
    
    total = 0
    count = 0
    
    for obj in queryset:
        value = getattr(obj, field_name, None)
        if value is not None:
            try:
                total += float(value)
                count += 1
            except (ValueError, TypeError):
                pass
    
    return round(total / count, 2) if count > 0 else 0

@register.filter
def sum(queryset, field_name):
    """Suma los valores de un campo en un queryset"""
    if not queryset:
        return 0
    
    total = 0
    for obj in queryset:
        value = getattr(obj, field_name, 0)
        if value is not None:
            try:
                total += float(value)
            except (ValueError, TypeError):
                pass
    
    return total

@register.filter
def get_average_color(value):
    """Devuelve la clase CSS según el promedio"""
    if value is None:
        return "text-muted"
    try:
        num = float(value)
        if num >= 3.5:
            return "text-success"
        elif num >= 3.0:
            return "text-warning"
        else:
            return "text-danger"
    except (ValueError, TypeError):
        return "text-muted"
    
@register.filter
def filter_by_nivel(queryset, nivel_nombre):
    """Filtra áreas por el nombre del nivel escolar"""
    if queryset is None:
        return []
    return queryset.filter(nivel_escolar__nombre=nivel_nombre)

@register.filter
def get_area_name(areas, area_id):
    try:
        return areas.get(id=area_id).nombre
    except:
        return "Desconocido"
    
@register.filter
def get_nivel_name(niveles, nivel_id):
    try:
        return niveles.get(id=nivel_id).nombre
    except:
        return "Desconocido"
    
@register.filter
def get_matricula_grado(estudiante, año_lectivo):
    """Obtener grado de matrícula para un año específico"""
    matricula = estudiante.get_matricula_por_año(año_lectivo)
    if matricula:
        return matricula.grado_año_lectivo.grado.nombre
    return "No matriculado"

@property
def matricula_actual(self):
    return self.matriculas.filter(activa=True).first()
