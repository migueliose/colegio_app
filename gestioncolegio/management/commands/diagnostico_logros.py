# management/commands/diagnostico_logros.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from usuarios.models import Docente
from academico.models import Logro
from gestioncolegio.models import AñoLectivo
from matricula.models import AsignaturaGradoAñoLectivo
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Diagnóstico de problemas con logros y asignaciones de docentes'
    
    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username del docente')
        parser.add_argument('--logro_id', type=int, help='ID del logro problemático')
    
    def handle(self, *args, **options):
        User = get_user_model()
        
        if options['username']:
            docente = Docente.objects.get(usuario__username=options['username'])
        else:
            # Buscar docentes con problemas
            docentes = Docente.objects.all()
            for docente in docentes:
                self.verificar_docente(docente)
            return
        
        if options['logro_id']:
            self.verificar_logro_especifico(docente, options['logro_id'])
        else:
            self.verificar_docente(docente)
    
    def verificar_docente(self, docente):
        """Verifica todas las asignaciones de un docente"""
        self.stdout.write(f"\n=== DIAGNÓSTICO PARA DOCENTE: {docente.usuario.username} ===")
        
        # 1. Obtener año lectivo actual
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        if not año_actual:
            self.stdout.write(self.style.ERROR("⚠ No hay año lectivo activo"))
            return
        
        self.stdout.write(f"Año lectivo actual: {año_actual}")
        
        # 2. Obtener asignaciones del docente
        asignaciones = AsignaturaGradoAñoLectivo.objects.filter(
            docente=docente,
            grado_año_lectivo__año_lectivo=año_actual
        ).select_related(
            'asignatura',
            'grado_año_lectivo__grado',
            'grado_año_lectivo__año_lectivo',
            'sede'
        )
        
        self.stdout.write(f"\nAsignaciones actuales ({asignaciones.count()}):")
        for a in asignaciones:
            self.stdout.write(f"  - {a.asignatura.nombre} en {a.grado_año_lectivo.grado.nombre} ({a.sede.nombre})")
        
        # 3. Obtener logros relacionados
        logros = Logro.objects.filter(
            asignatura__in=asignaciones.values_list('asignatura', flat=True),
            grado__in=asignaciones.values_list('grado_año_lectivo__grado', flat=True),
            periodo_academico__año_lectivo=año_actual
        )
        
        self.stdout.write(f"\nLogros creados ({logros.count()}):")
        for l in logros[:10]:  # Mostrar primeros 10
            self.stdout.write(f"  - {l.id}: {l.asignatura.nombre} - {l.grado.nombre} - {l.tema[:30]}")
        
        if logros.count() > 10:
            self.stdout.write(f"  ... y {logros.count() - 10} más")
    
    def verificar_logro_especifico(self, docente, logro_id):
        """Verifica un logro específico"""
        try:
            logro = Logro.objects.get(id=logro_id)
            self.stdout.write(f"\n=== VERIFICANDO LOGRO {logro_id} ===")
            self.stdout.write(f"Logro: {logro.asignatura.nombre} - {logro.grado.nombre}")
            self.stdout.write(f"Tema: {logro.tema}")
            self.stdout.write(f"Periodo: {logro.periodo_academico}")
            self.stdout.write(f"Año: {logro.periodo_academico.año_lectivo.anho if logro.periodo_academico else 'N/A'}")
            
            # Verificar asignación del docente
            asignacion = AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente,
                asignatura=logro.asignatura,
                grado_año_lectivo__grado=logro.grado,
                grado_año_lectivo__año_lectivo=logro.periodo_academico.año_lectivo
            ).first()
            
            if asignacion:
                self.stdout.write(self.style.SUCCESS(f"✓ Docente tiene asignación: {asignacion}"))
                self.stdout.write(f"   Sede asignación: {asignacion.sede}")
                self.stdout.write(f"   Sede logro: {logro.periodo_academico.año_lectivo.sede}")
                
                # Verificar sede
                if asignacion.sede != logro.periodo_academico.año_lectivo.sede:
                    self.stdout.write(self.style.WARNING("⚠ Las sedes no coinciden"))
            else:
                self.stdout.write(self.style.ERROR("✗ Docente NO tiene asignación para este logro"))
                
                # Mostrar asignaciones similares
                asignaciones_similares = AsignaturaGradoAñoLectivo.objects.filter(
                    docente=docente,
                    asignatura=logro.asignatura,
                )
                
                if asignaciones_similares.exists():
                    self.stdout.write("Asignaciones similares encontradas:")
                    for a in asignaciones_similares:
                        self.stdout.write(f"  - {a.grado_año_lectivo.grado.nombre} ({a.grado_año_lectivo.año_lectivo.anho})")
                
        except Logro.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Logro {logro_id} no encontrado"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))