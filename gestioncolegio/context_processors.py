# gestioncolegio/context_processors.py
from gestioncolegio.models import Colegio, ConfiguracionGeneral, AñoLectivo
from estudiantes.models import Acudiente, Estudiante, Matricula
from matricula.models import PeriodoAcademico
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

def informacion_colegio(request):
    """Context processor para información general del colegio"""
    try:
        colegio = Colegio.objects.filter(estado=True).first()
        configuracion = ConfiguracionGeneral.objects.filter(colegio=colegio).first() if colegio else None
    except:
        colegio = None
        configuracion = None
    
    return {
        'colegio': colegio,
        'configuracion_general': configuracion,
    }

def menu_sistema(request):
    """Context processor para menús del sistema por tipo de usuario"""
    menus = []
    if request.user.is_authenticated:
        try:
            from gestioncolegio.models import MenuSistema
            tipo_usuario = getattr(request.user, 'tipo_usuario', None)
            if tipo_usuario and hasattr(tipo_usuario, 'nombre'):
                tipo_usuario_str = tipo_usuario.nombre.lower()
                menus = MenuSistema.objects.filter(
                    tipo_usuario=tipo_usuario_str,
                    activo=True,
                    padre__isnull=True
                ).order_by('orden').prefetch_related('hijos')
        except:
            menus = []
    
    return {
        'menus_sistema': menus,
    }

def periodo_actual_processor(request):
    """Añade periodo_actual al contexto de todas las vistas - VERSIÓN MEJORADA"""
    periodo_actual = None
    
    try:
        # Solo para usuarios autenticados
        if request.user.is_authenticated:
            # Si es estudiante, obtener su período actual basado en su matrícula
            if hasattr(request.user, 'tipo_usuario') and request.user.tipo_usuario:
                tipo_nombre = getattr(request.user.tipo_usuario, 'nombre', '')
                
                if tipo_nombre == 'Estudiante':
                    try:
                        estudiante = Estudiante.objects.get(usuario=request.user)
                        matricula_actual = estudiante.matricula_actual
                        
                        if matricula_actual and matricula_actual.grado_año_lectivo:
                            año_lectivo = matricula_actual.grado_año_lectivo.año_lectivo
                            hoy = timezone.now().date()
                            
                            # Buscar período actual
                            periodo_actual = PeriodoAcademico.objects.filter(
                                año_lectivo=año_lectivo,
                                fecha_inicio__lte=hoy,
                                fecha_fin__gte=hoy,
                                estado=True
                            ).first()
                            
                            if not periodo_actual:
                                # Buscar último período
                                periodo_actual = PeriodoAcademico.objects.filter(
                                    año_lectivo=año_lectivo,
                                    estado=True
                                ).order_by('periodo__nombre').last()
                    
                    except Estudiante.DoesNotExist:
                        logger.debug(f"Estudiante no encontrado para usuario: {request.user}")
                    except Exception as e:
                        logger.debug(f"Error obteniendo periodo para estudiante: {e}")
                
                # Para otros tipos de usuario (incluyendo acudientes, docentes, admin)
                else:
                    # Usar año lectivo actual del sistema
                    año_actual = AñoLectivo.objects.filter(estado=True).first()
                    if año_actual:
                        hoy = timezone.now().date()
                        
                        # Buscar período actual
                        periodo_actual = PeriodoAcademico.objects.filter(
                            año_lectivo=año_actual,
                            fecha_inicio__lte=hoy,
                            fecha_fin__gte=hoy,
                            estado=True
                        ).first()
                        
                        if not periodo_actual:
                            # Buscar último período del año
                            periodo_actual = PeriodoAcademico.objects.filter(
                                año_lectivo=año_actual,
                                estado=True
                            ).order_by('periodo__nombre').last()
    
    except Exception as e:
        logger.debug(f"Error en periodo_actual_processor: {e}")
        periodo_actual = None
    
    return {
        'periodo_actual': periodo_actual,
    }

def acudiente_menu(request):
    """Context processor ultra-seguro que nunca falla"""
    context = {
        'user_acudientes': [],
        'matriculas_activas': {},
        'año_lectivo_actual': None,
        'es_acudiente': False
    }
    
    try:
        # Solo para usuarios autenticados
        if not request.user.is_authenticated:
            return context
        
        # Verificar tipo de usuario
        if not hasattr(request.user, 'tipo_usuario'):
            return context
        
        tipo_usuario = getattr(request.user.tipo_usuario, 'nombre', '')
        if tipo_usuario != 'Acudiente':
            return context
        
        # Marcar como acudiente
        context['es_acudiente'] = True
        
        # Obtener acudientes relacionados
        acudientes = Acudiente.objects.filter(
            acudiente=request.user
        ).select_related('estudiante__usuario')
        
        if acudientes.exists():
            context['user_acudientes'] = list(acudientes)
            
            # Obtener año lectivo actual
            año_lectivo_actual = AñoLectivo.objects.filter(estado=True).first()
            if año_lectivo_actual:
                context['año_lectivo_actual'] = año_lectivo_actual
                
                # Obtener matrículas activas
                for acudiente in acudientes:
                    try:
                        matricula = Matricula.objects.filter(
                            estudiante=acudiente.estudiante,
                            año_lectivo=año_lectivo_actual,
                            estado__in=['ACT', 'PEN']
                        ).select_related('grado_año_lectivo__grado').first()
                        
                        if matricula and matricula.grado_año_lectivo and matricula.grado_año_lectivo.grado:
                            context['matriculas_activas'][acudiente.estudiante.id] = matricula.grado_año_lectivo.grado.nombre
                    except Exception as e:
                        logger.debug(f"Error obteniendo matrícula: {e}")
                        continue
    
    except Exception as e:
        logger.debug(f"Error en acudiente_menu: {e}")
    
    return context

def año_lectivo_admin_context(request):
    """
    Context processor específico para el panel de administración
    Solo funciona en rutas que comienzan con /administrador/
    """
    try:
        # Verificar si estamos en una ruta de administración
        path = request.path
        if not path.startswith('/administrador/'):
            return {}
        
        # Verificar si el usuario está autenticado
        if not request.user.is_authenticated:
            return {}
        
        # Verificar si el usuario es administrador o rector
        tipo_usuario = getattr(request.user, 'tipo_usuario', None)
        if not tipo_usuario:
            return {}
        
        tipo_nombre = getattr(tipo_usuario, 'nombre', '')
        
        # Solo para administradores y rectores
        if tipo_nombre not in ['Administrador', 'Rector(a)', 'Rector']:
            return {}
        
        # Obtener año lectivo actual
        año_lectivo_actual = AñoLectivo.objects.filter(estado=True).first()
        
        return {
            'año_lectivo_actual': año_lectivo_actual,
        }
        
    except Exception as e:
        # En caso de error, devolver vacío
        import sys
        if 'runserver' in sys.argv:
            print(f"Error en año_lectivo_admin_context: {e}")
        return {}