# management/commands/check_migracion_completo.py
from django.db.models import Q, Count
from django.core.management.base import BaseCommand
from django.db import connections, transaction
from django.db.models.functions import TruncMonth, TruncYear
from django.utils import timezone

# Importar modelos de cada app
from gestioncolegio.models import *
from usuarios.models import *
from estudiantes.models import *
from academico.models import *
from matricula.models import *
from comportamiento.models import *
from web.models import *

# Importar modelos antiguos
from antigua_bd.models import *

class Command(BaseCommand):
    help = 'Verificación completa de migración con comparación BD antigua vs nueva'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--detallado',
            action='store_true',
            help='Mostrar comparación detallada entre BD antigua y nueva'
        )
        parser.add_argument(
            '--progreso',
            action='store_true',
            help='Mostrar porcentaje de progreso de migración'
        )
        parser.add_argument(
            '--problemas',
            action='store_true',
            help='Mostrar solo problemas encontrados'
        )

    def handle(self, *args, **options):
        self.detallado = options['detallado']
        self.progreso = options['progreso']
        self.solo_problemas = options['problemas']
        
        print("🔍 VERIFICACIÓN COMPLETA DE MIGRACIÓN")
        print("=" * 70)
        
        try:
            # 1. Verificar conexiones
            self.verificar_conexiones()
            
            if not self.solo_problemas:
                print("\n" + "=" * 70)
                
            # 2. Comparación general
            self.comparar_general()
            
            if not self.solo_problemas:
                print("\n" + "=" * 70)
            
            # 3. Verificar estructura del colegio
            self.comparar_colegio()
            
            if not self.solo_problemas:
                print("\n" + "=" * 70)
            
            # 4. Verificar usuarios
            self.comparar_usuarios()
            
            if not self.solo_problemas:
                print("\n" + "=" * 70)
            
            # 5. Verificar estructura académica
            self.comparar_estructura_academica()
            
            if not self.solo_problemas:
                print("\n" + "=" * 70)
            
            # 6. Verificar estudiantes y matrículas
            self.comparar_estudiantes()
            
            if not self.solo_problemas:
                print("\n" + "=" * 70)
            
            # 7. Verificar docentes
            self.comparar_docentes()
            
            if not self.solo_problemas:
                print("\n" + "=" * 70)
            
            # 8. Verificar datos académicos
            self.comparar_datos_academicos()
            
            if not self.solo_problemas:
                print("\n" + "=" * 70)
            
            # 9. Verificar seguimiento
            self.comparar_seguimiento()
            
            if not self.solo_problemas:
                print("\n" + "=" * 70)
            
            # 10. Verificar web
            self.comparar_web()
            
            if not self.solo_problemas:
                print("\n" + "=" * 70)
            
            # 11. Problemas críticos
            self.verificar_problemas_criticos()
            
            # 12. Estadísticas resumen
            self.generar_resumen()
            
            print("\n" + "=" * 70)
            print("✅ VERIFICACIÓN COMPLETADA")
            
        except Exception as e:
            print(f"❌ ERROR en verificación: {e}")
            import traceback
            traceback.print_exc()

    def verificar_conexiones(self):
        """Verificar conexiones a ambas bases de datos"""
        print("\n🔌 VERIFICANDO CONEXIONES")
        
        try:
            # Verificar BD nueva
            connections['default'].ensure_connection()
            print("   ✅ BD nueva (default): Conectada")
            
            # Verificar BD antigua
            connections['antigua'].ensure_connection()
            print("   ✅ BD antigua (antigua): Conectada")
            
        except Exception as e:
            print(f"   ❌ Error en conexión: {e}")

    def comparar_general(self):
        """Comparación general de ambas bases de datos"""
        print("\n📊 COMPARACIÓN GENERAL")
        
        # Tablas principales a comparar
        comparaciones = [
            # (Tabla antigua, Tabla nueva, Nombre, Método)
            ('gestioncolegio_colegio', Colegio, 'Colegios', 'count'),
            ('gestioncolegio_usuario', Usuario, 'Usuarios', 'count'),
            ('gestioncolegio_estudiante', Estudiante, 'Estudiantes', 'count'),
            ('gestioncolegio_docente', Docente, 'Docentes', 'count'),
            ('gestioncolegio_añolectivo', AñoLectivo, 'Años lectivos', 'count'),
            ('gestioncolegio_grado', Grado, 'Grados', 'count'),
            ('gestioncolegio_asignatura', Asignatura, 'Asignaturas', 'count'),
        ]
        
        for tabla_antigua, modelo_nuevo, nombre, metodo in comparaciones:
            try:
                # Obtener conteo antiguo
                with connections['antigua'].cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) FROM {tabla_antigua}")
                    count_antiguo = cursor.fetchone()[0]
                
                # Obtener conteo nuevo
                if metodo == 'count':
                    count_nuevo = modelo_nuevo.objects.count()
                else:
                    count_nuevo = getattr(modelo_nuevo.objects, metodo)()
                
                # Calcular porcentaje
                porcentaje = 0
                if count_antiguo > 0:
                    porcentaje = (count_nuevo / count_antiguo) * 100
                
                # Determinar ícono
                if porcentaje == 100:
                    icono = "✅"
                elif porcentaje >= 80:
                    icono = "🟡"
                elif porcentaje > 0:
                    icono = "🟠"
                else:
                    icono = "❌"
                
                if not self.solo_problemas or porcentaje < 100:
                    print(f"   {icono} {nombre}: Antiguo={count_antiguo} | Nuevo={count_nuevo} ({porcentaje:.1f}%)")
                    
            except Exception as e:
                if not self.solo_problemas:
                    print(f"   ❌ Error comparando {nombre}: {e}")

    def comparar_colegio(self):
        """Comparar datos del colegio"""
        print("\n🏫 COMPARANDO DATOS DEL COLEGIO")
        
        try:
            # Colegio antiguo
            with connections['antigua'].cursor() as cursor:
                cursor.execute("SELECT nombre, direccion, resolucion, dane FROM gestioncolegio_colegio WHERE estado=1")
                colegios_antiguos = cursor.fetchall()
            
            # Colegio nuevo
            colegios_nuevos = Colegio.objects.filter(estado=True).values('nombre', 'direccion', 'resolucion', 'dane')
            
            print(f"   Colegios antiguos activos: {len(colegios_antiguos)}")
            print(f"   Colegios nuevos activos: {len(colegios_nuevos)}")
            
            # Sedes
            sedes_antiguas = 0
            with connections['antigua'].cursor() as cursor:
                # En antiguo no hay tabla de sedes, usar información del colegio
                cursor.execute("SELECT COUNT(*) FROM gestioncolegio_colegio WHERE estado=1")
                sedes_antiguas = cursor.fetchone()[0]
            
            sedes_nuevas = Sede.objects.count()
            print(f"   Sedes nuevas: {sedes_nuevas} (En antiguo: {sedes_antiguas} colegios)")
            
            # Recursos del colegio
            try:
                recursos_antiguos = GestioncolegioRecursoscolegio.objects.using('antigua').count()
                recursos_nuevos = RecursosColegio.objects.count()
                print(f"   Recursos colegio: Antiguo={recursos_antiguos} | Nuevo={recursos_nuevos}")
            except:
                print("   ℹ️ No hay recursos del colegio migrados")
                
        except Exception as e:
            print(f"   ❌ Error comparando colegio: {e}")

    def comparar_usuarios(self):
        """Comparar usuarios"""
        print("\n👤 COMPARANDO USUARIOS")
        
        try:
            # Usuarios antiguos
            with connections['antigua'].cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM gestioncolegio_usuario WHERE estado=1")
                usuarios_antiguos_activos = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM gestioncolegio_usuario")
                usuarios_antiguos_total = cursor.fetchone()[0]
            
            # Usuarios nuevos
            usuarios_nuevos_activos = Usuario.objects.filter(
                estado=True, 
                is_active=True
            ).count()
            
            usuarios_nuevos_total = Usuario.objects.count()
            
            print(f"   Usuarios activos: Antiguo={usuarios_antiguos_activos} | Nuevo={usuarios_nuevos_activos}")
            print(f"   Usuarios totales: Antiguo={usuarios_antiguos_total} | Nuevo={usuarios_nuevos_total}")
            
            # Distribución por tipos
            if self.detallado:
                print("   📊 Distribución por tipo de usuario:")
                
                # Tipos antiguos
                with connections['antigua'].cursor() as cursor:
                    cursor.execute("""
                        SELECT tu.nombre, COUNT(u.id) 
                        FROM gestioncolegio_usuario u
                        LEFT JOIN gestioncolegio_tipousuario tu ON u.tipo_usuario_id = tu.id
                        GROUP BY tu.nombre
                    """)
                    tipos_antiguos = cursor.fetchall()
                    
                    print("     Antiguo:")
                    for tipo, count in tipos_antiguos:
                        print(f"       • {tipo or 'Sin tipo'}: {count}")
                
                # Tipos nuevos
                tipos_nuevos = Usuario.objects.values(
                    'tipo_usuario__nombre'
                ).annotate(
                    total=Count('id')
                ).order_by('tipo_usuario__nombre')
                
                print("     Nuevo:")
                for tipo in tipos_nuevos:
                    nombre = tipo['tipo_usuario__nombre'] or 'Sin tipo'
                    print(f"       • {nombre}: {tipo['total']}")
            
            # Autenticación
            auth_users_antiguos = AuthUser.objects.using('antigua').count()
            print(f"   AuthUser antiguos: {auth_users_antiguos}")
            
        except Exception as e:
            print(f"   ❌ Error comparando usuarios: {e}")

    def comparar_estructura_academica(self):
        """Comparar estructura académica"""
        print("\n📚 COMPARANDO ESTRUCTURA ACADÉMICA")
        
        try:
            # Años lectivos
            años_antiguos = GestioncolegioAolectivo.objects.using('antigua').count()
            años_nuevos = AñoLectivo.objects.count()
            print(f"   Años lectivos: Antiguo={años_antiguos} | Nuevo={años_nuevos}")
            
            # Niveles escolares
            niveles_antiguos = GestioncolegioNivelescolar.objects.using('antigua').count()
            niveles_nuevos = NivelEscolar.objects.count()
            print(f"   Niveles escolares: Antiguo={niveles_antiguos} | Nuevo={niveles_nuevos}")
            
            # Grados
            grados_antiguos = GestioncolegioGrado.objects.using('antigua').count()
            grados_nuevos = Grado.objects.count()
            print(f"   Grados: Antiguo={grados_antiguos} | Nuevo={grados_nuevos}")
            
            # Grados por año
            grados_año_antiguos = GestioncolegioGradoaolectivo.objects.using('antigua').count()
            grados_año_nuevos = GradoAñoLectivo.objects.count()
            print(f"   Grados por año: Antiguo={grados_año_antiguos} | Nuevo={grados_año_nuevos}")
            
            # Áreas
            areas_antiguos = GestioncolegioArea.objects.using('antigua').count()
            areas_nuevos = Area.objects.count()
            print(f"   Áreas: Antiguo={areas_antiguos} | Nuevo={areas_nuevos}")
            
            # Asignaturas
            asignaturas_antiguos = GestioncolegioAsignatura.objects.using('antigua').count()
            asignaturas_nuevos = Asignatura.objects.count()
            print(f"   Asignaturas: Antiguo={asignaturas_antiguos} | Nuevo={asignaturas_nuevos}")
            
            # Periodos
            periodos_antiguos = GestioncolegioPeriodo.objects.using('antigua').count()
            periodos_nuevos = Periodo.objects.count()
            print(f"   Periodos: Antiguo={periodos_antiguos} | Nuevo={periodos_nuevos}")
            
            # Periodos académicos
            periodos_academicos_antiguos = GestioncolegioPeriodoacademico.objects.using('antigua').count()
            periodos_academicos_nuevos = PeriodoAcademico.objects.count()
            print(f"   Periodos académicos: Antiguo={periodos_academicos_antiguos} | Nuevo={periodos_academicos_nuevos}")
            
        except Exception as e:
            print(f"   ❌ Error comparando estructura académica: {e}")

    def comparar_estudiantes(self):
        """Comparar estudiantes y matrículas"""
        print("\n🎓 COMPARANDO ESTUDIANTES")
        
        try:
            # Estudiantes antiguos
            estudiantes_antiguos = GestioncolegioEstudiante.objects.using('antigua').count()
            estudiantes_nuevos = Estudiante.objects.count()
            print(f"   Estudiantes: Antiguo={estudiantes_antiguos} | Nuevo={estudiantes_nuevos}")
            
            # Matrículas antiguas (estudiante + grado_año_lectivo)
            matriculas_antiguas = estudiantes_antiguos  # En antiguo cada estudiante tiene una matrícula implícita
            
            # Matrículas nuevas
            matriculas_nuevas = Matricula.objects.count()
            print(f"   Matrículas: Antiguo={matriculas_antiguas} | Nuevo={matriculas_nuevas}")
            
            # Acudientes
            acudientes_antiguos = GestioncolegioAcudiente.objects.using('antigua').count()
            acudientes_nuevos = Acudiente.objects.count()
            print(f"   Acudientes: Antiguo={acudientes_antiguos} | Nuevo={acudientes_nuevos}")
            
            # Estudiantes sin matrícula
            estudiantes_sin_matricula = Estudiante.objects.filter(matriculas__isnull=True).count()
            if estudiantes_sin_matricula > 0:
                print(f"   ⚠️ Estudiantes sin matrícula: {estudiantes_sin_matricula}")
            
            # Estudiantes activos
            estudiantes_activos_antiguos = GestioncolegioEstudiante.objects.using('antigua').filter(estado=1).count()
            estudiantes_activos_nuevos = Estudiante.objects.filter(estado=True).count()
            print(f"   Estudiantes activos: Antiguo={estudiantes_activos_antiguos} | Nuevo={estudiantes_activos_nuevos}")
            
        except Exception as e:
            print(f"   ❌ Error comparando estudiantes: {e}")

    def comparar_docentes(self):
        """Comparar docentes"""
        print("\n👨‍🏫 COMPARANDO DOCENTES")
        
        try:
            # Docentes antiguos
            docentes_antiguos = GestioncolegioDocente.objects.using('antigua').count()
            docentes_nuevos = Docente.objects.count()
            print(f"   Docentes: Antiguo={docentes_antiguos} | Nuevo={docentes_nuevos}")
            
            # Contactos docentes
            contactos_antiguos = GestioncolegioContactodocente.objects.using('antigua').count()
            contactos_nuevos = ContactoDocente.objects.count()
            print(f"   Contactos docentes: Antiguo={contactos_antiguos} | Nuevo={contactos_nuevos}")
            
            # Docentes por sede
            docentes_sede_nuevos = DocenteSede.objects.count()
            print(f"   Docentes por sede (nuevo): {docentes_sede_nuevos}")
            
            # Asignaturas dictadas
            asignaturas_dictadas_antiguos = GestioncolegioAsignaturagradoaolectivo.objects.using('antigua').filter(
                docente__isnull=False
            ).count()
            
            asignaturas_dictadas_nuevos = AsignaturaGradoAñoLectivo.objects.filter(
                docente__isnull=False
            ).count()
            
            print(f"   Asignaturas dictadas: Antiguo={asignaturas_dictadas_antiguos} | Nuevo={asignaturas_dictadas_nuevos}")
            
        except Exception as e:
            print(f"   ❌ Error comparando docentes: {e}")

    def comparar_datos_academicos(self):
        """Comparar datos académicos"""
        print("\n📊 COMPARANDO DATOS ACADÉMICOS")
        
        try:
            # Asignaturas por grado
            asignaturas_grado_antiguos = GestioncolegioAsignaturagradoaolectivo.objects.using('antigua').count()
            asignaturas_grado_nuevos = AsignaturaGradoAñoLectivo.objects.count()
            print(f"   Asignaturas por grado: Antiguo={asignaturas_grado_antiguos} | Nuevo={asignaturas_grado_nuevos}")
            
            # Logros
            logros_antiguos = GestioncolegioLogro.objects.using('antigua').count()
            logros_nuevos = Logro.objects.count()
            print(f"   Logros: Antiguo={logros_antiguos} | Nuevo={logros_nuevos}")
            
            # Notas
            notas_antiguos = GestioncolegioNota.objects.using('antigua').count()
            notas_nuevos = Nota.objects.count()
            print(f"   Notas: Antiguo={notas_antiguos} | Nuevo={notas_nuevos}")
            
            if notas_nuevos > 0:
                # Estadísticas de notas
                from django.db.models import Avg, Max, Min, StdDev
                stats = Nota.objects.aggregate(
                    avg=Avg('calificacion'),
                    max=Max('calificacion'),
                    min=Min('calificacion'),
                    count=Count('id')
                )
                
                if self.detallado:
                    print(f"   📈 Estadísticas notas (nuevo):")
                    print(f"      • Total: {stats['count']}")
                    print(f"      • Promedio: {stats['avg']:.2f}")
                    print(f"      • Rango: {stats['min']} - {stats['max']}")
            
            # Historial académico
            try:
                historial_antiguos = GestioncolegioHistorialacademicoestudiante.objects.using('antigua').count()
                print(f"   Historial académico (antiguo): {historial_antiguos}")
            except:
                print("   ℹ️ Historial académico (antiguo): No disponible")
            
            # Horarios de clase
            horarios_antiguos = GestioncolegioHorarioclase.objects.using('antigua').count()
            horarios_nuevos = HorarioClase.objects.count()
            print(f"   Horarios: Antiguo={horarios_antiguos} | Nuevo={horarios_nuevos}")
            
            # Planificación de clase
            planificaciones_antiguos = GestioncolegioPlanificacionclase.objects.using('antigua').count()
            print(f"   Planificaciones (antiguo): {planificaciones_antiguos}")
            
            # Material de apoyo
            materiales_antiguos = GestioncolegioMaterialapoyo.objects.using('antigua').count()
            print(f"   Materiales apoyo (antiguo): {materiales_antiguos}")
            
        except Exception as e:
            print(f"   ❌ Error comparando datos académicos: {e}")

    def comparar_seguimiento(self):
        """Comparar seguimiento estudiantil"""
        print("\n📋 COMPARANDO SEGUIMIENTO")
        
        try:
            # Comportamiento
            comportamiento_antiguos = GestioncolegioComportamiento.objects.using('antigua').count()
            comportamiento_nuevos = Comportamiento.objects.count()
            print(f"   Comportamientos: Antiguo={comportamiento_antiguos} | Nuevo={comportamiento_nuevos}")
            
            # Asistencias
            asistencias_antiguos = GestioncolegioAsistencia.objects.using('antigua').count()
            asistencias_nuevos = Asistencia.objects.count()
            print(f"   Asistencias: Antiguo={asistencias_antiguos} | Nuevo={asistencias_nuevos}")
            
            # Inconsistencias
            inconsistencias_antiguos = GestioncolegioInconsistencia.objects.using('antigua').count()
            inconsistencias_nuevos = Inconsistencia.objects.count()
            print(f"   Inconsistencias: Antiguo={inconsistencias_antiguos} | Nuevo={inconsistencias_nuevos}")
            
        except Exception as e:
            print(f"   ❌ Error comparando seguimiento: {e}")

    def comparar_web(self):
        """Comparar datos web"""
        print("\n🌐 COMPARANDO DATOS WEB")
        
        try:
            # Carrusel
            carrusel_antiguos = WebCarrusel.objects.using('antigua').count()
            carrusel_nuevos = Carrusel.objects.count()
            print(f"   Carrusel: Antiguo={carrusel_antiguos} | Nuevo={carrusel_nuevos}")
            
            # Welcome
            welcome_antiguos = WebWelcome.objects.using('antigua').count()
            welcome_nuevos = Welcome.objects.count()
            print(f"   Welcome: Antiguo={welcome_antiguos} | Nuevo={welcome_nuevos}")
            
            # About
            about_antiguos = AboutAbout.objects.using('antigua').count()
            about_nuevos = About.objects.count()
            print(f"   About: Antiguo={about_antiguos} | Nuevo={about_nuevos}")
            
            # Admisión
            admision_antiguos = AdmisionAdmision.objects.using('antigua').count()
            admision_nuevos = Admision.objects.count()
            print(f"   Admisión: Antiguo={admision_antiguos} | Nuevo={admision_nuevos}")
            
            # Redes sociales
            redes_antiguos = SocialRedsocial.objects.using('antigua').count()
            redes_nuevos = RedSocial.objects.count()
            print(f"   Redes sociales: Antiguo={redes_antiguos} | Nuevo={redes_nuevos}")
            
            # Páginas
            paginas_antiguos = PagesPages.objects.using('antigua').count()
            paginas_nuevos = Pagina.objects.count()
            print(f"   Páginas: Antiguo={paginas_antiguos} | Nuevo={paginas_nuevos}")
            
            # Noticias/Proyectos
            proyectos_antiguos = PortfolioProject.objects.using('antigua').count()
            noticias_nuevos = Noticia.objects.count()
            print(f"   Noticias/Proyectos: Antiguo={proyectos_antiguos} | Nuevo={noticias_nuevos}")
            
            # Programas académicos (nuevo)
            programas_nuevos = ProgramaAcademico.objects.count()
            print(f"   Programas académicos (nuevo): {programas_nuevos}")
            
        except Exception as e:
            print(f"   ❌ Error comparando web: {e}")

    def verificar_problemas_criticos(self):
        """Verificar problemas críticos"""
        print("\n🚨 VERIFICANDO PROBLEMAS CRÍTICOS")
        
        problemas = []
        
        try:
            # 1. Usuarios sin autenticación
            usuarios_sin_auth = Usuario.objects.filter(
                Q(username__isnull=True) | Q(username='')
            ).count()
            
            if usuarios_sin_auth > 0:
                problemas.append(f"Usuarios sin username: {usuarios_sin_auth}")
            
            # 2. Estudiantes sin usuario
            estudiantes_sin_usuario = Estudiante.objects.filter(
                usuario__isnull=True
            ).count()
            
            if estudiantes_sin_usuario > 0:
                problemas.append(f"Estudiantes sin usuario: {estudiantes_sin_usuario}")
            
            # 3. Docentes sin usuario
            docentes_sin_usuario = Docente.objects.filter(
                usuario__isnull=True
            ).count()
            
            if docentes_sin_usuario > 0:
                problemas.append(f"Docentes sin usuario: {docentes_sin_usuario}")
            
            # 4. Notas sin relaciones válidas
            notas_invalidas = Nota.objects.filter(
                Q(estudiante__isnull=True) |
                Q(asignatura_grado_año_lectivo__isnull=True) |
                Q(periodo_academico__isnull=True) |
                Q(calificacion__isnull=True)
            ).count()
            
            if notas_invalidas > 0:
                problemas.append(f"Notas con relaciones inválidas: {notas_invalidas}")
            
            # 5. Años lectivos sin sede
            años_sin_sede = AñoLectivo.objects.filter(
                sede__isnull=True
            ).count()
            
            if años_sin_sede > 0:
                problemas.append(f"Años lectivos sin sede: {años_sin_sede}")
            
            # 6. Grados sin nivel escolar
            grados_sin_nivel = Grado.objects.filter(
                nivel_escolar__isnull=True
            ).count()
            
            if grados_sin_nivel > 0:
                problemas.append(f"Grados sin nivel escolar: {grados_sin_nivel}")
            
            # 7. Asignaturas sin área
            asignaturas_sin_area = Asignatura.objects.filter(
                area__isnull=True
            ).count()
            
            if asignaturas_sin_area > 0:
                problemas.append(f"Asignaturas sin área: {asignaturas_sin_area}")
            
            # 8. Fechas inconsistentes
            periodos_inconsistentes = PeriodoAcademico.objects.filter(
                fecha_fin__lt=models.F('fecha_inicio')
            ).count()
            
            if periodos_inconsistentes > 0:
                problemas.append(f"Periodos con fechas inconsistentes: {periodos_inconsistentes}")
            
            # 9. Valores fuera de rango
            notas_fuera_rango = Nota.objects.filter(
                Q(calificacion__lt=0) | Q(calificacion__gt=100)
            ).count()
            
            if notas_fuera_rango > 0:
                problemas.append(f"Notas fuera de rango (0-100): {notas_fuera_rango}")
            
            # 10. Registros duplicados
            try:
                # Estudiantes duplicados por documento
                usuarios_duplicados = Usuario.objects.values('numero_documento').annotate(
                    count=Count('id')
                ).filter(count__gt=1).count()
                
                if usuarios_duplicados > 0:
                    problemas.append(f"Usuarios con documento duplicado: {usuarios_duplicados}")
                    
            except Exception as e:
                problemas.append(f"Error verificando duplicados: {e}")
            
            # Mostrar problemas
            if problemas:
                print("   ❌ PROBLEMAS ENCONTRADOS:")
                for i, problema in enumerate(problemas, 1):
                    print(f"      {i}. {problema}")
            else:
                print("   ✅ No se encontraron problemas críticos")
                
        except Exception as e:
            print(f"   ❌ Error verificando problemas: {e}")

    def generar_resumen(self):
        """Generar resumen de la migración"""
        print("\n📈 RESUMEN DE MIGRACIÓN")
        
        try:
            # Obtener totales de ambas bases
            total_antiguo = 0
            total_nuevo = 0
            
            # Tablas principales
            tablas_principales = [
                ('gestioncolegio_usuario', Usuario),
                ('gestioncolegio_estudiante', Estudiante),
                ('gestioncolegio_docente', Docente),
                ('gestioncolegio_añolectivo', AñoLectivo),
                ('gestioncolegio_asignatura', Asignatura),
                ('gestioncolegio_nota', Nota),
            ]
            
            for tabla_antigua, modelo_nuevo in tablas_principales:
                try:
                    with connections['antigua'].cursor() as cursor:
                        cursor.execute(f"SELECT COUNT(*) FROM {tabla_antigua}")
                        total_antiguo += cursor.fetchone()[0]
                    
                    total_nuevo += modelo_nuevo.objects.count()
                except:
                    continue
            
            # Calcular porcentaje general
            porcentaje = 0
            if total_antiguo > 0:
                porcentaje = (total_nuevo / total_antiguo) * 100
            
            print(f"   📊 Total registros principales:")
            print(f"      • Antiguo: {total_antiguo}")
            print(f"      • Nuevo: {total_nuevo}")
            print(f"      • Migración: {porcentaje:.1f}%")
            
            # Barras de progreso
            if self.progreso:
                bar_length = 40
                filled_length = int(bar_length * porcentaje / 100)
                bar = '█' * filled_length + '░' * (bar_length - filled_length)
                print(f"      [{bar}] {porcentaje:.1f}%")
            
            # Estado por categoría
            print(f"\n   🎯 ESTADO POR CATEGORÍA:")
            
            categorias = [
                ("🏫 Colegio", Colegio, GestioncolegioColegio),
                ("👤 Usuarios", Usuario, 'gestioncolegio_usuario'),
                ("🎓 Estudiantes", Estudiante, GestioncolegioEstudiante),
                ("👨‍🏫 Docentes", Docente, GestioncolegioDocente),
                ("📚 Académico", Asignatura, GestioncolegioAsignatura),
                ("📊 Notas", Nota, GestioncolegioNota),
                ("🌐 Web", Noticia, PortfolioProject),
            ]
            
            for nombre, modelo_nuevo, modelo_antiguo in categorias:
                try:
                    if isinstance(modelo_antiguo, str):
                        with connections['antigua'].cursor() as cursor:
                            cursor.execute(f"SELECT COUNT(*) FROM {modelo_antiguo}")
                            count_antiguo = cursor.fetchone()[0]
                    else:
                        count_antiguo = modelo_antiguo.objects.using('antigua').count()
                    
                    count_nuevo = modelo_nuevo.objects.count()
                    
                    porcentaje_cat = 0
                    if count_antiguo > 0:
                        porcentaje_cat = (count_nuevo / count_antiguo) * 100
                    
                    # Icono según porcentaje
                    if porcentaje_cat == 100:
                        icono = "✅"
                    elif porcentaje_cat >= 80:
                        icono = "🟡"
                    elif porcentaje_cat > 0:
                        icono = "🟠"
                    else:
                        icono = "❌"
                    
                    print(f"      {icono} {nombre}: {porcentaje_cat:.1f}% ({count_nuevo}/{count_antiguo})")
                    
                except Exception as e:
                    print(f"      ⚠️ {nombre}: Error - {e}")
            
            # Recomendaciones
            print(f"\n   💡 RECOMENDACIONES:")
            
            if porcentaje < 100:
                print(f"      • Continuar con la migración de datos faltantes")
            
            problemas = self.verificar_problemas_rapido()
            if problemas:
                print(f"      • Resolver {len(problemas)} problemas identificados")
            else:
                print(f"      • Realizar pruebas de integración")
            
            print(f"      • Realizar backup de ambas bases de datos")
            print(f"      • Verificar permisos y roles de usuarios")
            
        except Exception as e:
            print(f"   ❌ Error generando resumen: {e}")

    def verificar_problemas_rapido(self):
        """Verificación rápida de problemas comunes"""
        problemas = []
        
        try:
            # Usuarios sin tipo
            if Usuario.objects.filter(tipo_usuario__isnull=True).exists():
                problemas.append("Usuarios sin tipo")
            
            # Estudiantes sin matrícula
            if Estudiante.objects.filter(matriculas__isnull=True).exists():
                problemas.append("Estudiantes sin matrícula")
            
            # Docentes sin asignaturas
            if Docente.objects.filter(asignaturas_dictadas__isnull=True).exists():
                problemas.append("Docentes sin asignaturas")
            
            return problemas
            
        except:
            return ["Error en verificación rápida"]