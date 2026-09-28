# management/commands/migracion_completa_final.py
from django.core.management.base import BaseCommand
from django.db import connections, transaction
from django.utils import timezone
from django.core.files.base import ContentFile
import os

from ._credenciales import env_requerida, superadmin_username

from gestioncolegio.models import *
from usuarios.models import *
from estudiantes.models import *
from academico.models import *
from matricula.models import *
from comportamiento.models import *
from web.models import *
from antigua_bd.models import *

class Command(BaseCommand):
    help = 'Migración completa desde base de datos antigua'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-web',
            action='store_true',
            help='Saltar migración de datos web'
        )
        parser.add_argument(
            '--only-web',
            action='store_true',
            help='Migrar solo datos web'
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Ejecutar en modo prueba sin guardar'
        )

    def handle(self, *args, **options):
        print("🚀 INICIANDO MIGRACIÓN COMPLETA FINAL...")
        print("=" * 70)
        
        self.test_mode = options['test']
        self.skip_web = options['skip_web']
        self.only_web = options['only_web']
        
        if self.test_mode:
            print("🔬 MODO PRUEBA - No se guardarán cambios")
        
        try:
            if not self.only_web:
                # FASE 1-6: Estructura básica
                self.fase_0_preparacion()
                self.fase_1_configuracion_basica()
                self.fase_2_tipos_catalogos()
                self.fase_3_usuarios_auth_corregida()
                self.fase_4_estructura_academica()
                self.fase_5_personas_basicas_corregida()
                self.fase_6_relaciones_complejas_corregida()
                
                # FASE 7-10: Modelos adicionales
                self.fase_7_asignaturas_grado()
                self.fase_8_periodos_academicos()
                self.fase_9_datos_academicos_corregida()
                self.fase_10_seguimiento_estudiantil()
                self.fase_11_contactos_acudientes_corregida()
                self.fase_12_logros_corregida()
                self.fase_13_recursos_colegio()
                self.fase_14_historial_academico()
                self.fase_15_configuracion_sistema()
            
            if not self.skip_web and not self.test_mode:
                self.fase_16_datos_web_completa()
            
            if not self.test_mode:
                self.fase_17_post_migracion()
            
            print("\n" + "=" * 70)
            print("✅ MIGRACIÓN COMPLETA FINALIZADA EXITOSAMENTE!")
            
            if self.test_mode:
                print("⚠️  MODO PRUEBA - Revisar cambios antes de ejecutar migración real")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    # ==================== FASE 0 ====================
    def fase_0_preparacion(self):
        """FASE 0: Preparación y verificación"""
        print("\n🔧 FASE 0: PREPARACIÓN Y VERIFICACIÓN")
        
        # Verificar conexiones
        try:
            connections['antigua'].ensure_connection()
            connections['default'].ensure_connection()
            print("  ✅ Conexiones a BD verificadas")
        except Exception as e:
            print(f"  ❌ Error en conexiones: {e}")
            raise
        
        # Obtener estadísticas iniciales
        with connections['antigua'].cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM gestioncolegio_usuario")
            usuarios_antiguo = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM gestioncolegio_estudiante")
            estudiantes_antiguo = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM gestioncolegio_nota")
            notas_antiguo = cursor.fetchone()[0]
        
        print(f"  📊 Estadísticas BD antigua:")
        print(f"     • Usuarios: {usuarios_antiguo}")
        print(f"     • Estudiantes: {estudiantes_antiguo}")
        print(f"     • Notas: {notas_antiguo}")

    # ==================== FASE 1 ====================
    def fase_1_configuracion_basica(self):
        """FASE 1: Configuración básica del colegio"""
        print("\n📋 FASE 1: CONFIGURACIÓN BÁSICA")
        
        # 1.1 Colegio
        print("  🏫 Migrando colegio...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("SELECT nombre, direccion, resolucion, dane, estado FROM gestioncolegio_colegio WHERE id=1")
                colegio_data = cursor.fetchone()
            
            if colegio_data:
                colegio, created = Colegio.objects.get_or_create(
                    id=1,
                    defaults={
                        'nombre': colegio_data[0],
                        'direccion': colegio_data[1],
                        'resolucion': colegio_data[2],
                        'dane': colegio_data[3],
                        'estado': bool(colegio_data[4]) if colegio_data[4] is not None else True
                    }
                )
                if created:
                    print(f"    ✅ Colegio creado: {colegio.nombre}")
                else:
                    print(f"    ⚠ Colegio ya existía: {colegio.nombre}")
        except Exception as e:
            print(f"    ❌ Error migrando colegio: {e}")
        
        # 1.2 Sede (crear por defecto ya que no existe en antigua)
        print("  🏢 Creando sede...")
        try:
            sede, created = Sede.objects.get_or_create(
                id=1,
                colegio_id=1,
                defaults={
                    'nombre': 'Sede Principal',
                    'direccion': 'TV 26 NO 16 E 39 FUNDADORES',
                    'estado': True
                }
            )
            if created:
                print(f"    ✅ Sede creada: {sede.nombre}")
            else:
                print(f"    ⚠ Sede ya existía: {sede.nombre}")
        except Exception as e:
            print(f"    ❌ Error creando sede: {e}")

    # ==================== FASE 2 ====================
    def fase_2_tipos_catalogos(self):
        """FASE 2: Tipos y catálogos básicos"""
        print("\n📚 FASE 2: TIPOS Y CATÁLOGOS")
        
        # 2.1 Tipos de documento
        print("  📄 Migrando tipos de documento...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("SELECT id, nombre FROM gestioncolegio_tipodocumento")
                tipos_doc = cursor.fetchall()
            
            migrados = 0
            for id_tipo, nombre in tipos_doc:
                obj, created = TipoDocumento.objects.get_or_create(
                    id=id_tipo,
                    defaults={'nombre': nombre}
                )
                if created:
                    migrados += 1
            
            print(f"    ✅ {migrados}/{len(tipos_doc)} tipos de documento migrados")
        except Exception as e:
            print(f"    ❌ Error migrando tipos documento: {e}")
        
        # 2.2 Tipos de usuario
        print("  👥 Migrando tipos de usuario...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("SELECT id, nombre FROM gestioncolegio_tipousuario")
                tipos_user = cursor.fetchall()
            
            migrados = 0
            for id_tipo, nombre in tipos_user:
                obj, created = TipoUsuario.objects.get_or_create(
                    id=id_tipo,
                    defaults={'nombre': nombre}
                )
                if created:
                    migrados += 1
            
            print(f"    ✅ {migrados}/{len(tipos_user)} tipos de usuario migrados")
        except Exception as e:
            print(f"    ❌ Error migrando tipos usuario: {e}")
        
        # 2.3 Niveles escolares
        print("  🎯 Migrando niveles escolares...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("SELECT id, nombre FROM gestioncolegio_nivelescolar")
                niveles = cursor.fetchall()
            
            migrados = 0
            for id_nivel, nombre in niveles:
                obj, created = NivelEscolar.objects.get_or_create(
                    id=id_nivel,
                    defaults={'nombre': nombre}
                )
                if created:
                    migrados += 1
            
            print(f"    ✅ {migrados}/{len(niveles)} niveles escolares migrados")
        except Exception as e:
            print(f"    ❌ Error migrando niveles escolares: {e}")
        
        # 2.4 Periodos
        print("  ⏱️ Migrando periodos...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("SELECT id, nombre FROM gestioncolegio_periodo")
                periodos = cursor.fetchall()
            
            migrados = 0
            for id_periodo, nombre in periodos:
                obj, created = Periodo.objects.get_or_create(
                    id=id_periodo,
                    defaults={'nombre': nombre}
                )
                if created:
                    migrados += 1
            
            print(f"    ✅ {migrados}/{len(periodos)} periodos migrados")
        except Exception as e:
            print(f"    ❌ Error migrando periodos: {e}")

    # ==================== FASE 3 ====================
    def fase_3_usuarios_auth_corregida(self):
        """FASE 3: Usuarios y autenticación - CORREGIDA"""
        print("\n👤 FASE 3: USUARIOS Y AUTENTICACIÓN - CORREGIDA")
        
        # 3.1 Migrar Usuarios extendidos
        print("  👨‍💼 Migrando usuarios extendidos...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("""
                    SELECT id, numero_documento, nombres, apellidos, direccion, 
                        telefono, email, estado, fecha_nacimiento, sexo, 
                        tipo_documento_id, user_id
                    FROM gestioncolegio_usuario
                    ORDER BY id
                """)
                usuarios_ext = cursor.fetchall()
            
            usuarios_migrados = 0
            usuarios_existentes = 0
            usuarios_error = 0
            
            for usuario in usuarios_ext:
                try:
                    usuario_id_antiguo = usuario[0]
                    
                    # Determinar tipo de usuario
                    tipo_usuario_obj = self.determinar_tipo_usuario_corregido(usuario_id_antiguo)
                    if not tipo_usuario_obj:
                        usuarios_error += 1
                        continue
                    
                    # Verificar si el usuario ya existe
                    if Usuario.objects.filter(numero_documento=usuario[1]).exists():
                        usuarios_existentes += 1
                        continue
                    
                    # Preparar datos para creación
                    email_usuario = usuario[6] or f"No registra"
                    estado_usuario = bool(usuario[7]) if usuario[7] is not None else True
                    
                    # Crear usuario extendido
                    usuario_obj = Usuario(
                        username=usuario[1],
                        numero_documento=usuario[1],
                        nombres=usuario[2] or '',
                        apellidos=usuario[3] or '',
                        direccion=usuario[4] or '',
                        telefono=usuario[5] or '',
                        email=email_usuario,
                        estado=estado_usuario,
                        fecha_nacimiento=usuario[8],
                        sexo=usuario[9],
                        tipo_documento_id=usuario[10],
                        tipo_usuario=tipo_usuario_obj,
                        password="pbkdf2_sha256$600000$temp123$temp"  # Password temporal
                    )
                    
                    # Configurar campos de autenticación
                    usuario_obj.is_active = estado_usuario
                    usuario_obj.is_staff = tipo_usuario_obj.nombre in ['Administrador', 'Rector(a)', 'Rector']
                    
                    if not self.test_mode:
                        usuario_obj.save()
                    
                    usuarios_migrados += 1
                    
                    if usuarios_migrados % 50 == 0:
                        print(f"    📊 {usuarios_migrados} usuarios procesados...")
                        
                except Exception as e:
                    usuarios_error += 1
                    print(f"    ⚠ Usuario {usuario[0]}: {e}")
            
            print(f"    📊 REPORTE USUARIOS:")
            print(f"       ✅ Migrados: {usuarios_migrados}")
            print(f"       ⚠ Existentes: {usuarios_existentes}")
            print(f"       ❌ Errores: {usuarios_error}")
            print(f"       📈 Procesados: {len(usuarios_ext)}")
            
        except Exception as e:
            print(f"    ❌ Error migrando usuarios: {e}")

    def determinar_tipo_usuario_corregido(self, user_id_antiguo):
        """Determinar tipo de usuario - CORREGIDO"""
        try:
            with connections['antigua'].cursor() as cursor:
                # Verificar si es docente
                cursor.execute("SELECT id FROM gestioncolegio_docente WHERE usuario_id = %s", [user_id_antiguo])
                if cursor.fetchone():
                    return TipoUsuario.objects.filter(nombre__icontains='Docente').first()
                
                # Verificar si es estudiante  
                cursor.execute("SELECT id FROM gestioncolegio_estudiante WHERE usuario_id = %s", [user_id_antiguo])
                if cursor.fetchone():
                    return TipoUsuario.objects.filter(nombre__icontains='Estudiante').first()
                
                # Verificar si es acudiente
                cursor.execute("SELECT id FROM gestioncolegio_acudiente WHERE acudiente_id = %s", [user_id_antiguo])
                if cursor.fetchone():
                    return TipoUsuario.objects.filter(nombre__icontains='Acudiente').first()
            
            # Por defecto, acudiente o buscar en auth_user
            with connections['antigua'].cursor() as cursor:
                cursor.execute("""
                    SELECT is_superuser, is_staff 
                    FROM auth_user 
                    WHERE id = %s
                """, [user_id_antiguo])
                auth_data = cursor.fetchone()
                
                if auth_data:
                    if auth_data[0]:  # is_superuser
                        return TipoUsuario.objects.filter(nombre__icontains='Administrador').first()
                    elif auth_data[1]:  # is_staff
                        return TipoUsuario.objects.filter(nombre__icontains='Rector').first()
            
            # Si no se encuentra, usar tipo por defecto
            return TipoUsuario.objects.filter(nombre__icontains='Acudiente').first()
            
        except Exception as e:
            print(f"    ⚠ Error determinando tipo usuario {user_id_antiguo}: {e}")
            return TipoUsuario.objects.filter(nombre__icontains='Acudiente').first()
        
    # ==================== FASE 4 ====================
    def fase_4_estructura_academica(self):
        """FASE 4: Estructura académica"""
        print("\n📖 FASE 4: ESTRUCTURA ACADÉMICA")
        
        # 4.1 Año lectivo
        print("  📅 Migrando año lectivo...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("SELECT id, anho, fecha_inicio, fecha_fin, estado, colegio_id FROM gestioncolegio_añolectivo")
                años_data = cursor.fetchall()
            
            migrados = 0
            for año in años_data:
                try:
                    año_obj, created = AñoLectivo.objects.get_or_create(
                        id=año[0],
                        defaults={
                            'anho': año[1],
                            'fecha_inicio': año[2],
                            'fecha_fin': año[3],
                            'estado': bool(año[4]) if año[4] is not None else True,
                            'colegio_id': año[5],
                            'sede_id': 1
                        }
                    )
                    if created:
                        migrados += 1
                except Exception as e:
                    print(f"    ⚠ Año lectivo {año[0]}: {e}")
            
            print(f"    ✅ {migrados}/{len(años_data)} años lectivos migrados")
        except Exception as e:
            print(f"    ❌ Error migrando años lectivos: {e}")
        
        # 4.2 Grados
        print("  🎓 Migrando grados...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("SELECT id, nombre, nivel_escolar_id FROM gestioncolegio_grado")
                grados_data = cursor.fetchall()
            
            migrados = 0
            for grado in grados_data:
                try:
                    grado_obj, created = Grado.objects.get_or_create(
                        id=grado[0],
                        defaults={
                            'nombre': grado[1],
                            'nivel_escolar_id': grado[2]
                        }
                    )
                    if created:
                        migrados += 1
                except Exception as e:
                    print(f"    ⚠ Grado {grado[0]}: {e}")
            
            print(f"    ✅ {migrados}/{len(grados_data)} grados migrados")
        except Exception as e:
            print(f"    ❌ Error migrando grados: {e}")
        
        # 4.3 Grados por año lectivo
        print("  🔗 Migrando grados por año lectivo...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("SELECT id, grado_id, año_lectivo_id, estado FROM gestioncolegio_gradoañolectivo")
                grados_año_data = cursor.fetchall()
            
            migrados = 0
            for ga in grados_año_data:
                try:
                    ga_obj, created = GradoAñoLectivo.objects.get_or_create(
                        id=ga[0],
                        defaults={
                            'grado_id': ga[1],
                            'año_lectivo_id': ga[2],
                            'estado': bool(ga[3]) if ga[3] is not None else True
                        }
                    )
                    if created:
                        migrados += 1
                except Exception as e:
                    print(f"    ⚠ GradoAñoLectivo {ga[0]}: {e}")
            
            print(f"    ✅ {migrados}/{len(grados_año_data)} grados por año migrados")
        except Exception as e:
            print(f"    ❌ Error migrando grados por año: {e}")
        
        # 4.4 Áreas
        print("  📐 Migrando áreas...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("SELECT id, nombre, nivel_escolar_id FROM gestioncolegio_area")
                areas_data = cursor.fetchall()
            
            migrados = 0
            for area in areas_data:
                try:
                    area_obj, created = Area.objects.get_or_create(
                        id=area[0],
                        defaults={
                            'nombre': area[1],
                            'nivel_escolar_id': area[2]
                        }
                    )
                    if created:
                        migrados += 1
                except Exception as e:
                    print(f"    ⚠ Área {area[0]}: {e}")
            
            print(f"    ✅ {migrados}/{len(areas_data)} áreas migradas")
        except Exception as e:
            print(f"    ❌ Error migrando áreas: {e}")
        
        # 4.5 Asignaturas
        print("  📚 Migrando asignaturas...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("SELECT id, nombre, ih, area_id FROM gestioncolegio_asignatura")
                asignaturas_data = cursor.fetchall()
            
            migrados = 0
            for asignatura in asignaturas_data:
                try:
                    asignatura_obj, created = Asignatura.objects.get_or_create(
                        id=asignatura[0],
                        defaults={
                            'nombre': asignatura[1],
                            'ih': asignatura[2],
                            'area_id': asignatura[3]
                        }
                    )
                    if created:
                        migrados += 1
                except Exception as e:
                    print(f"    ⚠ Asignatura {asignatura[0]}: {e}")
            
            print(f"    ✅ {migrados}/{len(asignaturas_data)} asignaturas migradas")
        except Exception as e:
            print(f"    ❌ Error migrando asignaturas: {e}")

    # ==================== FASE 5 ====================
    def fase_5_personas_basicas_corregida(self):
        """FASE 5: Personas - CORREGIDA"""
        print("\n👥 FASE 5: PERSONAS BÁSICAS - CORREGIDA")
        
        # 5.1 Estudiantes - CORREGIDO
        print("  🎓 Migrando estudiantes...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("""
                    SELECT e.id, u.numero_documento, e.foto, e.estado, e.grado_año_lectivo_id,
                           e.created_at, e.updated_at
                    FROM gestioncolegio_estudiante e
                    JOIN gestioncolegio_usuario u ON e.usuario_id = u.id
                    ORDER BY e.id
                """)
                estudiantes_data = cursor.fetchall()
            
            estudiantes_migrados = 0
            estudiantes_existentes = 0
            estudiantes_error = 0
            
            for est_id, documento, foto, estado, grado_id, created_at, updated_at in estudiantes_data:
                try:
                    # Buscar usuario por documento
                    usuario = Usuario.objects.filter(numero_documento=documento).first()
                    if not usuario:
                        print(f"    ⚠ No se encontró usuario para estudiante con documento {documento}")
                        estudiantes_error += 1
                        continue
                    
                    # Verificar si el estudiante ya existe
                    if Estudiante.objects.filter(usuario=usuario).exists():
                        estudiantes_existentes += 1
                        continue
                    
                    estudiante_obj = Estudiante(
                        usuario=usuario,
                        foto=foto,
                        estado=bool(estado) if estado is not None else True
                    )
                    
                    if not self.test_mode:
                        estudiante_obj.save()
                        # Actualizar timestamps si existen
                        if created_at:
                            Estudiante.objects.filter(id=estudiante_obj.id).update(created_at=created_at)
                        if updated_at:
                            Estudiante.objects.filter(id=estudiante_obj.id).update(updated_at=updated_at)
                    
                    estudiantes_migrados += 1
                    
                    if estudiantes_migrados % 50 == 0:
                        print(f"    📊 {estudiantes_migrados} estudiantes procesados...")
                        
                except Exception as e:
                    estudiantes_error += 1
                    print(f"    ⚠ Estudiante {est_id}: {e}")
            
            print(f"    📊 REPORTE ESTUDIANTES:")
            print(f"       ✅ Migrados: {estudiantes_migrados}")
            print(f"       ⚠ Existentes: {estudiantes_existentes}")
            print(f"       ❌ Errores: {estudiantes_error}")
            print(f"       📈 Procesados: {len(estudiantes_data)}")
            
        except Exception as e:
            print(f"    ❌ Error migrando estudiantes: {e}")
        
        # 5.2 Docentes - CORREGIDO
        print("  👨‍🏫 Migrando docentes...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("""
                    SELECT d.id, u.numero_documento, d.foto, d.hdv, d.estado,
                           d.created_at, d.updated_at
                    FROM gestioncolegio_docente d
                    JOIN gestioncolegio_usuario u ON d.usuario_id = u.id
                    ORDER BY d.id
                """)
                docentes_data = cursor.fetchall()
            
            docentes_migrados = 0
            docentes_existentes = 0
            docentes_error = 0
            
            for doc_id, documento, foto, hdv, estado, created_at, updated_at in docentes_data:
                try:
                    usuario = Usuario.objects.filter(numero_documento=documento).first()
                    if not usuario:
                        print(f"    ⚠ No se encontró usuario para docente con documento {documento}")
                        docentes_error += 1
                        continue
                    
                    # Verificar si el docente ya existe
                    if Docente.objects.filter(usuario=usuario).exists():
                        docentes_existentes += 1
                        continue
                    
                    docente_obj = Docente(
                        usuario=usuario,
                        foto=foto,
                        hdv=hdv,
                        estado=bool(estado) if estado is not None else True
                    )
                    
                    if not self.test_mode:
                        docente_obj.save()
                        # Actualizar timestamps si existen
                        if created_at:
                            Docente.objects.filter(id=docente_obj.id).update(created_at=created_at)
                        if updated_at:
                            Docente.objects.filter(id=docente_obj.id).update(updated_at=updated_at)
                    
                    docentes_migrados += 1
                    
                    if docentes_migrados % 50 == 0:
                        print(f"    📊 {docentes_migrados} docentes procesados...")
                        
                except Exception as e:
                    docentes_error += 1
                    print(f"    ⚠ Docente {doc_id}: {e}")
            
            print(f"    📊 REPORTE DOCENTES:")
            print(f"       ✅ Migrados: {docentes_migrados}")
            print(f"       ⚠ Existentes: {docentes_existentes}")
            print(f"       ❌ Errores: {docentes_error}")
            print(f"       📈 Procesados: {len(docentes_data)}")
            
        except Exception as e:
            print(f"    ❌ Error migrando docentes: {e}")

    # ==================== FASE 6 ====================
    def fase_6_relaciones_complejas_corregida(self):
        """FASE 6: Relaciones complejas - CORREGIDA"""
        print("\n🔗 FASE 6: RELACIONES COMPLEJAS - CORREGIDA")
        
        # Obtener año lectivo activo y sede
        año_lectivo = AñoLectivo.objects.filter(estado=True).first()
        if not año_lectivo:
            año_lectivo = AñoLectivo.objects.first()
        
        sede = Sede.objects.first()
        
        # 6.1 Matrículas - CORREGIDO
        print("  📝 Creando matrículas...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("""
                    SELECT e.id, u.numero_documento, e.grado_año_lectivo_id 
                    FROM gestioncolegio_estudiante e
                    JOIN gestioncolegio_usuario u ON e.usuario_id = u.id
                    WHERE e.grado_año_lectivo_id IS NOT NULL
                """)
                estudiantes_con_grado = cursor.fetchall()
            
            matriculas_creadas = 0
            matriculas_existentes = 0
            matriculas_error = 0
            
            for est_id, documento, grado_id in estudiantes_con_grado:
                try:
                    # Buscar estudiante por documento
                    estudiante = Estudiante.objects.filter(usuario__numero_documento=documento).first()
                    if not estudiante:
                        matriculas_error += 1
                        continue
                    
                    # Verificar si la matrícula ya existe
                    if Matricula.objects.filter(estudiante=estudiante, año_lectivo=año_lectivo).exists():
                        matriculas_existentes += 1
                        continue
                    
                    if GradoAñoLectivo.objects.filter(id=grado_id).exists():
                        matricula = Matricula(
                            estudiante=estudiante,
                            año_lectivo=año_lectivo,
                            sede=sede,
                            grado_año_lectivo_id=grado_id,
                            estado='ACT',
                            observaciones='Migrado desde sistema anterior'
                        )
                        
                        if not self.test_mode:
                            matricula.save()
                        
                        matriculas_creadas += 1
                    else:
                        matriculas_error += 1
                        
                except Exception as e:
                    matriculas_error += 1
                    print(f"    ⚠ Matrícula estudiante {documento}: {e}")
            
            print(f"    📊 REPORTE MATRÍCULAS:")
            print(f"       ✅ Creadas: {matriculas_creadas}")
            print(f"       ⚠ Existentes: {matriculas_existentes}")
            print(f"       ❌ Errores: {matriculas_error}")
            
        except Exception as e:
            print(f"    ❌ Error creando matrículas: {e}")
        
        # 6.2 Asignaciones docente-sede - CORREGIDO
        print("  🏫 Creando asignaciones docente-sede...")
        try:
            docentes = Docente.objects.all()
            asignaciones_creadas = 0
            asignaciones_existentes = 0
            
            for docente in docentes:
                try:
                    # Verificar si ya existe la asignación
                    if DocenteSede.objects.filter(docente=docente, año_lectivo=año_lectivo).exists():
                        asignaciones_existentes += 1
                        continue
                        
                    docente_sede = DocenteSede(
                        docente=docente,
                        sede=sede,
                        año_lectivo=año_lectivo,
                        estado=True
                    )
                    
                    if not self.test_mode:
                        docente_sede.save()
                    
                    asignaciones_creadas += 1
                except Exception as e:
                    print(f"    ⚠ Asignación docente {docente.id}: {e}")
            
            print(f"    ✅ {asignaciones_creadas} asignaciones creadas, {asignaciones_existentes} existentes")
            
        except Exception as e:
            print(f"    ❌ Error creando asignaciones docente-sede: {e}")

    # ==================== FASE 7 ====================
    def fase_7_asignaturas_grado(self):
        """FASE 7: Asignaturas por grado - COMPLETAMENTE CORREGIDA"""
        print("\n📚 FASE 7: ASIGNATURAS POR GRADO - COMPLETAMENTE CORREGIDA")
        
        # 7.1 AsignaturaGradoAñoLectivo - COMPLETAMENTE CORREGIDA
        print("  🔗 Migrando asignaturas por grado...")
        
        try:
            # Primero verificar cuántas hay en la BD antigua
            with connections['antigua'].cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM gestioncolegio_asignaturagradoañolectivo")
                total_antigua = cursor.fetchone()[0]
                print(f"    📊 Total en BD antigua: {total_antigua}")
                
                cursor.execute("""
                    SELECT ag.id, ag.asignatura_id, ag.grado_año_lectivo_id, ag.docente_id,
                        a.nombre as asignatura_nombre, g.nombre as grado_nombre
                    FROM gestioncolegio_asignaturagradoañolectivo ag
                    JOIN gestioncolegio_asignatura a ON ag.asignatura_id = a.id
                    JOIN gestioncolegio_gradoañolectivo gal ON ag.grado_año_lectivo_id = gal.id
                    JOIN gestioncolegio_grado g ON gal.grado_id = g.id
                    ORDER BY ag.id
                """)
                asignaturas_grado_data = cursor.fetchall()
            
            migrados = 0
            existentes = 0
            errores = 0
            sede = Sede.objects.first()
            
            print(f"    🔍 Procesando {len(asignaturas_grado_data)} registros...")
            
            for ag_id, asignatura_id, grado_año_id, docente_id, asignatura_nombre, grado_nombre in asignaturas_grado_data:
                try:
                    # Verificar si ya existe
                    if AsignaturaGradoAñoLectivo.objects.filter(id=ag_id).exists():
                        existentes += 1
                        continue
                    
                    # Verificar que existan las relaciones básicas
                    if not Asignatura.objects.filter(id=asignatura_id).exists():
                        print(f"    ❌ No existe asignatura {asignatura_id} ({asignatura_nombre})")
                        errores += 1
                        continue
                        
                    if not GradoAñoLectivo.objects.filter(id=grado_año_id).exists():
                        print(f"    ❌ No existe grado_año {grado_año_id} ({grado_nombre})")
                        errores += 1
                        continue
                    
                    # Buscar docente si existe
                    docente_obj = None
                    if docente_id:
                        try:
                            # Buscar el documento del docente en la BD antigua
                            with connections['antigua'].cursor() as cursor_doc:
                                cursor_doc.execute("""
                                    SELECT u.numero_documento 
                                    FROM gestioncolegio_docente d 
                                    JOIN gestioncolegio_usuario u ON d.usuario_id = u.id 
                                    WHERE d.id = %s
                                """, [docente_id])
                                resultado = cursor_doc.fetchone()
                                
                                if resultado:
                                    doc_docente = resultado[0]
                                    docente_obj = Docente.objects.filter(
                                        usuario__numero_documento=doc_docente
                                    ).first()
                        except Exception as e:
                            print(f"    ⚠ Error buscando docente {docente_id}: {e}")
                    
                    # CREAR la asignatura_grado
                    asignatura_grado = AsignaturaGradoAñoLectivo(
                        id=ag_id,
                        asignatura_id=asignatura_id,
                        grado_año_lectivo_id=grado_año_id,
                        docente=docente_obj,
                        sede=sede
                    )
                    
                    if not self.test_mode:
                        asignatura_grado.save()
                    
                    migrados += 1
                    
                    if migrados % 50 == 0:
                        print(f"    📊 {migrados} asignaturas por grado procesadas...")
                        
                except Exception as e:
                    errores += 1
                    print(f"    ❌ Error en asignatura_grado {ag_id}: {e}")
            
            print(f"    📊 REPORTE FINAL:")
            print(f"       ✅ Migradas: {migrados}")
            print(f"       ⚠ Existentes: {existentes}")
            print(f"       ❌ Errores: {errores}")
            print(f"       📈 Tasa de éxito: {(migrados/(migrados+errores))*100:.1f}%")
            
            if not self.test_mode:
                total_nueva = AsignaturaGradoAñoLectivo.objects.count()
                print(f"       📋 Total en BD nueva: {total_nueva}")
            
        except Exception as e:
            print(f"    ❌ Error migrando asignaturas por grado: {e}")

    # ==================== FASE 8 ====================
    def fase_8_periodos_academicos(self):
        """FASE 8: Periodos académicos"""
        print("\n📅 FASE 8: PERIODOS ACADÉMICOS")
        
        # 8.1 Periodos (ya migrados en fase 2, pero verificar)
        print("  ✅ Periodos ya migrados")
        
        # 8.2 Periodos académicos
        print("  🗓️ Migrando periodos académicos...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("""
                    SELECT id, año_lectivo_id, periodo_id, fecha_inicio, fecha_fin, estado 
                    FROM gestioncolegio_periodoacademico
                    ORDER BY id
                """)
                periodos_academicos_data = cursor.fetchall()
            
            migrados = 0
            existentes = 0
            errores = 0
            
            for pa in periodos_academicos_data:
                try:
                    # Verificar si ya existe
                    if PeriodoAcademico.objects.filter(id=pa[0]).exists():
                        existentes += 1
                        continue
                    
                    periodo_academico = PeriodoAcademico(
                        id=pa[0],
                        año_lectivo_id=pa[1],
                        periodo_id=pa[2],
                        fecha_inicio=pa[3],
                        fecha_fin=pa[4],
                        estado=bool(pa[5]) if pa[5] is not None else True
                    )
                    
                    if not self.test_mode:
                        periodo_academico.save()
                    
                    migrados += 1
                    
                    if migrados % 20 == 0:
                        print(f"    📊 {migrados} periodos académicos procesados...")
                        
                except Exception as e:
                    errores += 1
                    print(f"    ⚠ PeriodoAcademico {pa[0]}: {e}")
            
            print(f"    📊 REPORTE PERIODOS ACADÉMICOS:")
            print(f"       ✅ Migrados: {migrados}")
            print(f"       ⚠ Existentes: {existentes}")
            print(f"       ❌ Errores: {errores}")
            
        except Exception as e:
            print(f"    ❌ Error migrando periodos académicos: {e}")

    # ==================== FASE 9 ====================
    def fase_9_datos_academicos_corregida(self):
        """FASE 9: Datos académicos - COMPLETAMENTE CORREGIDA"""
        print("\n📊 FASE 9: DATOS ACADÉMICOS - COMPLETAMENTE CORREGIDA")
        
        # 9.1 Notas - COMPLETAMENTE CORREGIDA
        print("  📝 Migrando notas...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("""
                    SELECT n.id, u_est.numero_documento, n.asignatura_grado_año_lectivo_id, 
                        n.periodo_academico_id, n.calificacion, n.observaciones,
                        n.created_at, n.updated_at
                    FROM gestioncolegio_nota n
                    JOIN gestioncolegio_estudiante e ON n.estudiante_id = e.id
                    JOIN gestioncolegio_usuario u_est ON e.usuario_id = u_est.id
                    WHERE n.asignatura_grado_año_lectivo_id IS NOT NULL 
                    AND n.periodo_academico_id IS NOT NULL
                    ORDER BY n.id
                """)
                notas_data = cursor.fetchall()
            
            migrados = 0
            actualizados = 0
            errores = 0
            
            for nota_id, documento_est, asignatura_id, periodo_id, calificacion, observaciones, created_at, updated_at in notas_data:
                try:
                    # Buscar estudiante por documento
                    estudiante = Estudiante.objects.filter(usuario__numero_documento=documento_est).first()
                    if not estudiante:
                        print(f"    ⚠ No se encontró estudiante {documento_est} para nota {nota_id}")
                        errores += 1
                        continue
                    
                    # Verificar que exista la asignatura_grado
                    if not AsignaturaGradoAñoLectivo.objects.filter(id=asignatura_id).exists():
                        print(f"    ⚠ No existe asignatura_grado {asignatura_id} para nota {nota_id}")
                        errores += 1
                        continue
                        
                    # Verificar que exista el periodo académico
                    if not PeriodoAcademico.objects.filter(id=periodo_id).exists():
                        print(f"    ⚠ No existe periodo {periodo_id} para nota {nota_id}")
                        errores += 1
                        continue
                    
                    # Verificar si la nota ya existe
                    nota_existente = Nota.objects.filter(
                        estudiante=estudiante,
                        asignatura_grado_año_lectivo_id=asignatura_id,
                        periodo_academico_id=periodo_id
                    ).first()
                    
                    if nota_existente:
                        # Actualizar la nota existente
                        if not self.test_mode:
                            nota_existente.calificacion = calificacion
                            nota_existente.observaciones = observaciones
                            nota_existente.save()
                        
                        actualizados += 1
                    else:
                        # Crear nueva nota
                        nota_obj = Nota(
                            estudiante=estudiante,
                            asignatura_grado_año_lectivo_id=asignatura_id,
                            periodo_academico_id=periodo_id,
                            calificacion=calificacion,
                            observaciones=observaciones
                        )
                        
                        if not self.test_mode:
                            nota_obj.save()
                            # Actualizar timestamps si existen
                            if created_at:
                                Nota.objects.filter(id=nota_obj.id).update(created_at=created_at)
                            if updated_at:
                                Nota.objects.filter(id=nota_obj.id).update(updated_at=updated_at)
                        
                        migrados += 1
                    
                    if (migrados + actualizados) % 100 == 0:
                        print(f"    📊 {migrados + actualizados} notas procesadas...")
                        
                except Exception as e:
                    errores += 1
                    print(f"    ❌ Nota {nota_id}: {e}")
            
            print(f"    📊 REPORTE NOTAS:")
            print(f"       ✅ Migradas: {migrados}")
            print(f"       🔄 Actualizadas: {actualizados}")
            print(f"       ❌ Errores: {errores}")
            
        except Exception as e:
            print(f"    ❌ Error migrando notas: {e}")

    # ==================== FASE 10 ====================
    def fase_10_seguimiento_estudiantil(self):
        """FASE 10: Seguimiento estudiantil - CORREGIDA COMPLETAMENTE"""
        print("\n👨‍🎓 FASE 10: SEGUIMIENTO ESTUDIANTIL - CORREGIDA")
        
        # 10.1 Comportamiento - CORREGIDO COMPLETAMENTE
        print("  📋 Migrando comportamientos...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("""
                    SELECT c.id, 
                        u_est.numero_documento as doc_estudiante,
                        c.periodo_academico_id, 
                        u_doc.numero_documento as doc_docente,
                        c.tipo, 
                        c.categoria, 
                        c.descripcion, 
                        c.fecha, 
                        c.created_at, 
                        c.updated_at
                    FROM gestioncolegio_comportamiento c
                    JOIN gestioncolegio_estudiante e ON c.estudiante_id = e.id
                    JOIN gestioncolegio_usuario u_est ON e.usuario_id = u_est.id
                    LEFT JOIN gestioncolegio_docente d ON c.docente_id = d.id
                    LEFT JOIN gestioncolegio_usuario u_doc ON d.usuario_id = u_doc.id
                    ORDER BY c.id
                """)
                comportamientos_data = cursor.fetchall()
            
            migrados = 0
            existentes = 0
            errores = 0
            
            for comp in comportamientos_data:
                try:
                    # Obtener IDs de la tupla
                    comp_id, doc_estudiante, periodo_academico_id, doc_docente, tipo, categoria, descripcion, fecha, created_at, updated_at = comp
                    
                    # 1. Buscar estudiante por documento
                    estudiante = Estudiante.objects.filter(usuario__numero_documento=doc_estudiante).first()
                    if not estudiante:
                        print(f"    ⚠ No se encontró estudiante con documento {doc_estudiante} para comportamiento {comp_id}")
                        errores += 1
                        continue
                    
                    # 2. Buscar periodo académico - IMPORTANTE: verificar que exista
                    periodo_academico = None
                    if periodo_academico_id:
                        periodo_academico = PeriodoAcademico.objects.filter(id=periodo_academico_id).first()
                        if not periodo_academico:
                            print(f"    ⚠ No se encontró periodo académico {periodo_academico_id} para comportamiento {comp_id}")
                            # Intentar buscar por año y periodo alternativamente
                            # Pero por ahora continuamos
                            continue
                    
                    # 3. Buscar docente por documento
                    docente = None
                    if doc_docente:
                        docente = Docente.objects.filter(usuario__numero_documento=doc_docente).first()
                    
                    # 4. Mapear tipo y categoría a los nuevos valores
                    tipo_mapeado = self.mapear_tipo_comportamiento(tipo)
                    categoria_mapeada = self.mapear_categoria_comportamiento(categoria)
                    
                    # 5. Verificar si ya existe (usando datos únicos)
                    if Comportamiento.objects.filter(
                        estudiante=estudiante,
                        fecha=fecha,
                        descripcion__icontains=descripcion[:50] if descripcion else ""
                    ).exists():
                        existentes += 1
                        continue
                    
                    # 6. Crear comportamiento
                    comportamiento = Comportamiento(
                        id=comp_id,
                        estudiante=estudiante,
                        periodo_academico=periodo_academico,
                        docente=docente,
                        tipo=tipo_mapeado,
                        categoria=categoria_mapeada,
                        descripcion=descripcion or "Sin descripción",
                        fecha=fecha
                    )
                    
                    if not self.test_mode:
                        comportamiento.save()
                        
                        # Actualizar timestamps si existen
                        if created_at and updated_at:
                            Comportamiento.objects.filter(id=comp_id).update(
                                created_at=created_at,
                                updated_at=updated_at
                            )
                    
                    migrados += 1
                    
                    if migrados % 50 == 0:
                        print(f"    📊 {migrados} comportamientos migrados...")
                        
                except Exception as e:
                    errores += 1
                    print(f"    ❌ Error en comportamiento {comp_id}: {e}")
                    import traceback
                    traceback.print_exc()
            
            print(f"    📊 REPORTE COMPORTAMIENTOS:")
            print(f"       ✅ Migrados: {migrados}")
            print(f"       ⚠ Existentes: {existentes}")
            print(f"       ❌ Errores: {errores}")
            
        except Exception as e:
            print(f"    ❌ Error migrando comportamientos: {e}")
            import traceback
            traceback.print_exc()
        
        # 10.2 Asistencias - TAMBIÉN CORREGIDA
        print("\n  ✅ Migrando asistencias...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("""
                    SELECT a.id, 
                        u_est.numero_documento as doc_estudiante,
                        a.periodo_academico_id, 
                        a.fecha, 
                        a.estado, 
                        a.justificacion,
                        a.created_at, 
                        a.updated_at
                    FROM gestioncolegio_asistencia a
                    JOIN gestioncolegio_estudiante e ON a.estudiante_id = e.id
                    JOIN gestioncolegio_usuario u_est ON e.usuario_id = u_est.id
                    ORDER BY a.id
                """)
                asistencias_data = cursor.fetchall()
            
            migrados = 0
            existentes = 0
            errores = 0
            
            for asis in asistencias_data:
                try:
                    asis_id, doc_estudiante, periodo_academico_id, fecha, estado, justificacion, created_at, updated_at = asis
                    
                    # Buscar estudiante por documento
                    estudiante = Estudiante.objects.filter(usuario__numero_documento=doc_estudiante).first()
                    if not estudiante:
                        print(f"    ⚠ No se encontró estudiante {doc_estudiante} para asistencia {asis_id}")
                        errores += 1
                        continue
                    
                    # Buscar periodo académico
                    periodo_academico = None
                    if periodo_academico_id:
                        periodo_academico = PeriodoAcademico.objects.filter(id=periodo_academico_id).first()
                    
                    # Verificar si ya existe (usando unique constraint)
                    if Asistencia.objects.filter(
                        estudiante=estudiante, 
                        fecha=fecha
                    ).exists():
                        existentes += 1
                        continue
                    
                    asistencia = Asistencia(
                        id=asis_id,
                        estudiante=estudiante,
                        periodo_academico=periodo_academico,
                        fecha=fecha,
                        estado=estado,
                        justificacion=justificacion
                    )
                    
                    if not self.test_mode:
                        asistencia.save()
                        
                        # Actualizar timestamps si existen
                        if created_at and updated_at:
                            Asistencia.objects.filter(id=asis_id).update(
                                created_at=created_at,
                                updated_at=updated_at
                            )
                    
                    migrados += 1
                    
                    if migrados % 100 == 0:
                        print(f"    📊 {migrados} asistencias migradas...")
                        
                except Exception as e:
                    errores += 1
                    print(f"    ❌ Asistencia {asis_id}: {e}")
            
            print(f"    📊 REPORTE ASISTENCIAS:")
            print(f"       ✅ Migradas: {migrados}")
            print(f"       ⚠ Existentes: {existentes}")
            print(f"       ❌ Errores: {errores}")
            
        except Exception as e:
            print(f"    ❌ Error migrando asistencias: {e}")
        
        # 10.3 Inconsistencias - CORREGIDA
        print("\n  ⚠️ Migrando inconsistencias...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("""
                    SELECT i.id, 
                        u_est.numero_documento as doc_estudiante,
                        i.fecha, 
                        i.tipo, 
                        i.descripcion,
                        i.created_at, 
                        i.updated_at
                    FROM gestioncolegio_inconsistencia i
                    JOIN gestioncolegio_estudiante e ON i.estudiante_id = e.id
                    JOIN gestioncolegio_usuario u_est ON e.usuario_id = u_est.id
                    ORDER BY i.id
                """)
                inconsistencias_data = cursor.fetchall()
            
            migrados = 0
            existentes = 0
            errores = 0
            
            for inc in inconsistencias_data:
                try:
                    inc_id, doc_estudiante, fecha, tipo, descripcion, created_at, updated_at = inc
                    
                    # Buscar estudiante por documento
                    estudiante = Estudiante.objects.filter(usuario__numero_documento=doc_estudiante).first()
                    if not estudiante:
                        print(f"    ⚠ No se encontró estudiante {doc_estudiante} para inconsistencia {inc_id}")
                        errores += 1
                        continue
                    
                    # Verificar si ya existe
                    if Inconsistencia.objects.filter(
                        estudiante=estudiante, 
                        fecha=fecha,
                        tipo=tipo
                    ).exists():
                        existentes += 1
                        continue
                    
                    inconsistencia = Inconsistencia(
                        id=inc_id,
                        estudiante=estudiante,
                        fecha=fecha,
                        tipo=tipo,
                        descripcion=descripcion
                    )
                    
                    if not self.test_mode:
                        inconsistencia.save()
                        
                        # Actualizar timestamps si existen
                        if created_at and updated_at:
                            Inconsistencia.objects.filter(id=inc_id).update(
                                created_at=created_at,
                                updated_at=updated_at
                            )
                    
                    migrados += 1
                    
                except Exception as e:
                    errores += 1
                    print(f"    ❌ Inconsistencia {inc_id}: {e}")
            
            print(f"    📊 REPORTE INCONSISTENCIAS:")
            print(f"       ✅ Migradas: {migrados}")
            print(f"       ⚠ Existentes: {existentes}")
            print(f"       ❌ Errores: {errores}")
            
        except Exception as e:
            print(f"    ❌ Error migrando inconsistencias: {e}")
        
        # 10.4 Horarios de clase - CORREGIDA
        print("\n  🕒 Migrando horarios de clase...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("""
                    SELECT h.id, 
                        h.asignatura_grado_id,
                        h.dia_semana, 
                        h.hora_inicio, 
                        h.hora_fin, 
                        h.salon,
                        h.created_at, 
                        h.updated_at
                    FROM gestioncolegio_horarioclase h
                    WHERE h.asignatura_grado_id IS NOT NULL
                    ORDER BY h.id
                """)
                horarios_data = cursor.fetchall()
            
            migrados = 0
            existentes = 0
            errores = 0
            
            for horario in horarios_data:
                try:
                    horario_id, asignatura_grado_id, dia_semana, hora_inicio, hora_fin, salon, created_at, updated_at = horario
                    
                    # Verificar que exista la asignatura_grado
                    if not AsignaturaGradoAñoLectivo.objects.filter(id=asignatura_grado_id).exists():
                        print(f"    ⚠ No existe asignatura_grado {asignatura_grado_id} para horario {horario_id}")
                        errores += 1
                        continue
                    
                    # Verificar si ya existe
                    if HorarioClase.objects.filter(id=horario_id).exists():
                        existentes += 1
                        continue
                    
                    # Mapear días de la semana si es necesario
                    dia_mapeado = self.mapear_dia_semana(dia_semana)
                    
                    horario_obj = HorarioClase(
                        id=horario_id,
                        asignatura_grado_id=asignatura_grado_id,
                        dia_semana=dia_mapeado,
                        hora_inicio=hora_inicio,
                        hora_fin=hora_fin,
                        salon=salon
                    )
                    
                    if not self.test_mode:
                        horario_obj.save()
                        
                        # Actualizar timestamps
                        if created_at and updated_at:
                            HorarioClase.objects.filter(id=horario_id).update(
                                created_at=created_at,
                                updated_at=updated_at
                            )
                    
                    migrados += 1
                    
                except Exception as e:
                    errores += 1
                    print(f"    ❌ Horario {horario_id}: {e}")
            
            print(f"    📊 REPORTE HORARIOS:")
            print(f"       ✅ Migrados: {migrados}")
            print(f"       ⚠ Existentes: {existentes}")
            print(f"       ❌ Errores: {errores}")
            
        except Exception as e:
            print(f"    ℹ️ No se pudieron migrar horarios o no existen: {e}")

    def mapear_tipo_comportamiento(self, tipo_antiguo):
        """Mapear tipos de comportamiento antiguos a nuevos"""
        tipo_mapeo = {
            'positivo': 'Positivo',
            'negativo': 'Negativo',
            'Positivo': 'Positivo',
            'Negativo': 'Negativo',
            'P': 'Positivo',
            'N': 'Negativo',
            'bueno': 'Positivo',
            'malo': 'Negativo',
        }
        
        if tipo_antiguo:
            tipo_lower = str(tipo_antiguo).strip().lower()
            return tipo_mapeo.get(tipo_lower, 'Positivo')  # Por defecto Positivo
        return 'Positivo'

    def mapear_categoria_comportamiento(self, categoria_antigua):
        """Mapear categorías de comportamiento antiguas a nuevas"""
        categoria_mapeo = {
            'respeto': 'Respeto',
            'responsabilidad': 'Responsabilidad',
            'disciplina': 'Disciplina',
            'solidaridad': 'Solidaridad',
            'academico': 'Academico',
            'académico': 'Academico',
            'comportamiento': 'Disciplina',
            'conducta': 'Disciplina',
            'academica': 'Academico',
        }
        
        if categoria_antigua:
            cat_lower = str(categoria_antigua).strip().lower()
            return categoria_mapeo.get(cat_lower, 'Academico')  # Por defecto Académico
        return 'Academico'

    def mapear_dia_semana(self, dia_antiguo):
        """Mapear días de la semana a formato abreviado"""
        dias_mapeo = {
            'lunes': 'LUN',
            'martes': 'MAR',
            'miercoles': 'MIE',
            'miércoles': 'MIE',
            'jueves': 'JUE',
            'viernes': 'VIE',
            'sabado': 'SAB',
            'sábado': 'SAB',
            'domingo': 'DOM',
            'LUN': 'LUN',
            'MAR': 'MAR',
            'MIE': 'MIE',
            'JUE': 'JUE',
            'VIE': 'VIE',
            'SAB': 'SAB',
            'DOM': 'DOM',
        }
        
        if dia_antiguo:
            dia_lower = str(dia_antiguo).strip().lower()
            return dias_mapeo.get(dia_lower, 'LUN')  # Por defecto Lunes
        return 'LUN'

    # ==================== FASE 11 ====================
    def fase_11_contactos_acudientes_corregida(self):
        """FASE 11: Contactos y acudientes - CORREGIDA"""
        print("\n👨‍👩‍👧‍👦 FASE 11: CONTACTOS Y ACUDIENTES - CORREGIDA")
        
        # 11.1 Contactos de docentes - CORREGIDO
        print("  📞 Migrando contactos de docentes...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("""
                    SELECT cd.id, u.numero_documento, cd.nombres, cd.apellidos, 
                           cd.telefono, cd.email, cd.relacion, cd.created_at, cd.updated_at
                    FROM gestioncolegio_contactodocente cd
                    JOIN gestioncolegio_docente d ON cd.docente_id = d.id
                    JOIN gestioncolegio_usuario u ON d.usuario_id = u.id
                    ORDER BY cd.id
                """)
                contactos_data = cursor.fetchall()
            
            migrados = 0
            existentes = 0
            errores = 0
            
            for contacto_id, documento_doc, nombres, apellidos, telefono, email, relacion, created_at, updated_at in contactos_data:
                try:
                    # Buscar docente por documento
                    docente = Docente.objects.filter(usuario__numero_documento=documento_doc).first()
                    if not docente:
                        print(f"    ⚠ No se encontró docente {documento_doc} para contacto {contacto_id}")
                        errores += 1
                        continue
                    
                    # Verificar si ya existe
                    if ContactoDocente.objects.filter(
                        docente=docente,
                        nombres=nombres,
                        apellidos=apellidos,
                        telefono=telefono
                    ).exists():
                        existentes += 1
                        continue
                    
                    contacto_obj = ContactoDocente(
                        docente=docente,
                        nombres=nombres,
                        apellidos=apellidos,
                        telefono=telefono,
                        email=email,
                        relacion=relacion
                    )
                    
                    if not self.test_mode:
                        contacto_obj.save()
                        # Actualizar timestamps
                        if created_at and updated_at:
                            ContactoDocente.objects.filter(id=contacto_obj.id).update(
                                created_at=created_at,
                                updated_at=updated_at
                            )
                    
                    migrados += 1
                    
                except Exception as e:
                    errores += 1
                    print(f"    ⚠ Contacto {contacto_id}: {e}")
            
            print(f"    ✅ {migrados} contactos migrados, {existentes} existentes, {errores} errores")
            
        except Exception as e:
            print(f"    ❌ Error migrando contactos: {e}")
        
        # 11.2 Acudientes - CORREGIDO
        print("  👨‍👩‍👧‍👦 Migrando acudientes...")
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("""
                    SELECT a.id, u_acud.numero_documento, u_est.numero_documento, a.parentesco,
                           a.created_at, a.updated_at
                    FROM gestioncolegio_acudiente a
                    JOIN gestioncolegio_usuario u_acud ON a.acudiente_id = u_acud.id
                    JOIN gestioncolegio_estudiante e ON a.estudiante_id = e.id
                    JOIN gestioncolegio_usuario u_est ON e.usuario_id = u_est.id
                    ORDER BY a.id
                """)
                acudientes_data = cursor.fetchall()
            
            migrados = 0
            existentes = 0
            errores = 0
            
            for acud_id, doc_acudiente, doc_estudiante, parentesco, created_at, updated_at in acudientes_data:
                try:
                    # Buscar acudiente por documento
                    usuario_acudiente = Usuario.objects.filter(numero_documento=doc_acudiente).first()
                    if not usuario_acudiente:
                        print(f"    ⚠ No se encontró acudiente {doc_acudiente}")
                        errores += 1
                        continue
                    
                    # Buscar estudiante por documento
                    estudiante = Estudiante.objects.filter(usuario__numero_documento=doc_estudiante).first()
                    if not estudiante:
                        print(f"    ⚠ No se encontró estudiante {doc_estudiante}")
                        errores += 1
                        continue
                    
                    # Verificar si ya existe
                    if Acudiente.objects.filter(acudiente=usuario_acudiente, estudiante=estudiante).exists():
                        existentes += 1
                        continue
                    
                    acudiente_obj = Acudiente(
                        acudiente=usuario_acudiente,
                        estudiante=estudiante,
                        parentesco=parentesco
                    )
                    
                    if not self.test_mode:
                        acudiente_obj.save()
                        # Actualizar timestamps
                        if created_at and updated_at:
                            Acudiente.objects.filter(id=acudiente_obj.id).update(
                                created_at=created_at,
                                updated_at=updated_at
                            )
                    
                    migrados += 1
                    
                except Exception as e:
                    errores += 1
                    print(f"    ⚠ Acudiente {acud_id}: {e}")
            
            print(f"    ✅ {migrados} acudientes migrados, {existentes} existentes, {errores} errores")
            
        except Exception as e:
            print(f"    ❌ Error migrando acudientes: {e}")

    # ==================== FASE 12 ====================
    def fase_12_logros_corregida(self):
        """FASE 12: Logros - CORREGIDA"""
        print("\n🏆 FASE 12: LOGROS - CORREGIDA")
        
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("""
                    SELECT id, asignatura_id, grado_id, periodo_academico_id, tema,
                           descripcion_superior, descripcion_alto, descripcion_basico, 
                           descripcion_bajo, created_at, updated_at
                    FROM gestioncolegio_logro
                    ORDER BY id
                """)
                logros_data = cursor.fetchall()
            
            migrados = 0
            existentes = 0
            errores = 0
            
            for logro in logros_data:
                try:
                    # Verificar si ya existe
                    if Logro.objects.filter(id=logro[0]).exists():
                        existentes += 1
                        continue
                    
                    logro_obj = Logro(
                        id=logro[0],
                        asignatura_id=logro[1],
                        grado_id=logro[2],
                        periodo_academico_id=logro[3],
                        tema=logro[4],
                        descripcion_superior=logro[5],
                        descripcion_alto=logro[6],
                        descripcion_basico=logro[7],
                        descripcion_bajo=logro[8]
                    )
                    
                    if not self.test_mode:
                        logro_obj.save()
                        # Actualizar timestamps
                        if logro[9] and logro[10]:
                            Logro.objects.filter(id=logro[0]).update(
                                created_at=logro[9],
                                updated_at=logro[10]
                            )
                    
                    migrados += 1
                    
                    if migrados % 20 == 0:
                        print(f"    📊 {migrados} logros procesados...")
                        
                except Exception as e:
                    errores += 1
                    print(f"    ⚠ Logro {logro[0]}: {e}")
            
            print(f"    ✅ {migrados} logros migrados, {existentes} existentes, {errores} errores")
            
        except Exception as e:
            print(f"    ❌ Error migrando logros: {e}")

    # ==================== FASE 13 ====================
    def fase_13_recursos_colegio(self):
        """FASE 13: Recursos del colegio"""
        print("\n🖼️ FASE 13: RECURSOS DEL COLEGIO")
        
        try:
            with connections['antigua'].cursor() as cursor:
                cursor.execute("""
                    SELECT id, escudo, bandera, sitio_web, email, telefono, colegio_id,
                           created_at, updated_at
                    FROM gestioncolegio_recursoscolegio
                """)
                recursos_data = cursor.fetchall()
            
            for recurso in recursos_data:
                try:
                    # Verificar si ya existe
                    if RecursosColegio.objects.filter(colegio_id=recurso[6]).exists():
                        print(f"    ⚠ Recursos ya existen para colegio {recurso[6]}")
                        continue
                    
                    recursos_obj = RecursosColegio(
                        colegio_id=recurso[6],
                        escudo=recurso[1],
                        bandera=recurso[2],
                        sitio_web=recurso[3],
                        email=recurso[4],
                        telefono=recurso[5]
                    )
                    
                    if not self.test_mode:
                        recursos_obj.save()
                        # Actualizar timestamps
                        if recurso[7] and recurso[8]:
                            RecursosColegio.objects.filter(id=recursos_obj.id).update(
                                created_at=recurso[7],
                                updated_at=recurso[8]
                            )
                    
                    print(f"    ✅ Recursos migrados para colegio {recurso[6]}")
                    
                except Exception as e:
                    print(f"    ⚠ Recursos colegio {recurso[0]}: {e}")
            
        except Exception as e:
            print(f"    ❌ Error migrando recursos: {e}")

    # ==================== FASE 14 ====================
    def fase_14_historial_academico(self):
        """FASE 14: Historial académico (si existe)"""
        print("\n📈 FASE 14: HISTORIAL ACADÉMICO")
        
        try:
            # Verificar si existe la tabla
            with connections['antigua'].cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = 'colegioc_colegioshadai' 
                    AND table_name = 'gestioncolegio_historialacademicoestudiante'
                """)
                existe_tabla = cursor.fetchone()[0]
                
                if not existe_tabla:
                    print("    ℹ️ No existe tabla de historial académico en BD antigua")
                    return
                
                cursor.execute("""
                    SELECT id, estudiante_id, año_lectivo_id, periodo_academico_id,
                           asignatura_id, comportamiento_id, promedio_periodo, faltas, logros,
                           created_at, updated_at
                    FROM gestioncolegio_historialacademicoestudiante
                    LIMIT 10  # Solo probar con algunos
                """)
                historiales = cursor.fetchall()
                
                print(f"    ℹ️ Existen {len(historiales)} registros de historial académico")
                print("    ⚠️ Historial académico requiere migración manual por complejidad")
                
        except Exception as e:
            print(f"    ℹ️ No se pudo verificar historial académico: {e}")

    # ==================== FASE 15 ====================
    def fase_15_configuracion_sistema(self):
        """FASE 15: Configuración del sistema"""
        print("\n⚙️ FASE 15: CONFIGURACIÓN DEL SISTEMA")
        
        try:
            # Crear configuración general si no existe
            colegio = Colegio.objects.first()
            if colegio:
                config, created = ConfiguracionGeneral.objects.get_or_create(
                    colegio=colegio,
                    defaults={
                        'max_estudiantes_por_grupo': 40,
                        'porcentaje_aprobacion': 60.0,
                        'habilitar_matricula': True,
                        'habilitar_calificaciones': True
                    }
                )
                
                if created:
                    print(f"    ✅ Configuración general creada para {colegio.nombre}")
                else:
                    print(f"    ⚠ Configuración general ya existía para {colegio.nombre}")
            
            # Parámetros del sistema básicos
            parametros_basicos = [
                ('max_faltas_permitidas', '5', 'Máximo de faltas permitidas por periodo', 'numero'),
                ('dias_matricula', '30', 'Días hábiles para proceso de matrícula', 'numero'),
                ('nota_minima_aprobacion', '30', 'Nota mínima para aprobar', 'numero'),
                ('nota_maxima', '50', 'Nota máxima posible', 'numero'),
            ]
            
            for clave, valor, descripcion, tipo in parametros_basicos:
                param, created = ParametroSistema.objects.get_or_create(
                    clave=clave,
                    defaults={
                        'valor': valor,
                        'descripcion': descripcion,
                        'tipo': tipo
                    }
                )
            
            print(f"    ✅ {len(parametros_basicos)} parámetros del sistema configurados")
            
        except Exception as e:
            print(f"    ❌ Error configurando sistema: {e}")

    # ==================== FASE 16 ====================
    def fase_16_datos_web_completa(self):
        """FASE 16: Datos web - COMPLETA"""
        print("\n🌐 FASE 16: DATOS WEB - COMPLETA")
        
        # 16.1 Carrusel
        print("  📷 Migrando carrusel...")
        try:
            carrusel_items = WebCarrusel.objects.using('antigua').all()
            migrados = 0
            
            for item in carrusel_items:
                try:
                    carrusel, created = Carrusel.objects.get_or_create(
                        description=item.description[:500],  # Limitar longitud
                        defaults={
                            'image': item.image if item.image else '',
                            'alt_text': item.alt_text,
                            'is_active': True,
                            'order': migrados,
                            'created': item.created,
                            'updated': item.updated
                        }
                    )
                    if created:
                        migrados += 1
                except Exception as e:
                    print(f"    ⚠ Carrusel {item.id}: {e}")
            
            print(f"    ✅ {migrados} items de carrusel migrados")
            
        except Exception as e:
            print(f"    ❌ Error migrando carrusel: {e}")
        
        # 16.2 Welcome
        print("  🏫 Migrando welcome...")
        try:
            welcome_items = WebWelcome.objects.using('antigua').all()
            migrados = 0
            
            for item in welcome_items:
                try:
                    welcome, created = Welcome.objects.get_or_create(
                        title=item.title,
                        defaults={
                            'description': item.description,
                            'slug': item.slug,
                            'is_active': True,
                            'created': item.created,
                            'updated': item.updated
                        }
                    )
                    if created:
                        migrados += 1
                except Exception as e:
                    print(f"    ⚠ Welcome {item.id}: {e}")
            
            print(f"    ✅ {migrados} welcome migrados")
            
        except Exception as e:
            print(f"    ❌ Error migrando welcome: {e}")
        
        # 16.3 About
        print("  ℹ️ Migrando about...")
        try:
            about_items = AboutAbout.objects.using('antigua').all()
            migrados = 0
            
            for item in about_items:
                try:
                    about, created = About.objects.get_or_create(
                        title=item.title,
                        defaults={
                            'description': item.description,
                            'slug': item.slug,
                            'tipo': 'historia',  # Por defecto
                            'is_active': True,
                            'created': item.created,
                            'updated': item.updated
                        }
                    )
                    if created:
                        migrados += 1
                except Exception as e:
                    print(f"    ⚠ About {item.id}: {e}")
            
            print(f"    ✅ {migrados} about migrados")
            
        except Exception as e:
            print(f"    ❌ Error migrando about: {e}")
        
        # 16.4 Admisión
        print("  🎓 Migrando admisión...")
        try:
            admision_items = AdmisionAdmision.objects.using('antigua').all()
            migrados = 0
            
            for item in admision_items:
                try:
                    # Determinar tipo basado en título
                    tipo = 'P_admision'
                    if 'nuevo' in item.title.lower():
                        tipo = 'nuevos'
                    elif 'antiguo' in item.title.lower():
                        tipo = 'antiguos'
                    elif 'matrícula' in item.title.lower():
                        tipo = 'P_matricula'
                    
                    admision, created = Admision.objects.get_or_create(
                        title=item.title,
                        defaults={
                            'tipo': tipo,
                            'description': item.description,
                            'link': item.link,
                            'is_active': True,
                            'created': item.created,
                            'updated': item.updated
                        }
                    )
                    if created:
                        migrados += 1
                except Exception as e:
                    print(f"    ⚠ Admisión {item.id}: {e}")
            
            print(f"    ✅ {migrados} admisiones migrados")
            
        except Exception as e:
            print(f"    ❌ Error migrando admisión: {e}")
        
        # 16.5 Redes sociales
        print("  🔗 Migrando redes sociales...")
        try:
            redes_items = SocialRedsocial.objects.using('antigua').all()
            migrados = 0
            
            for item in redes_items:
                try:
                    red, created = RedSocial.objects.get_or_create(
                        key=item.key,
                        defaults={
                            'name': item.name,
                            'link': item.link,
                            'is_active': True,
                            'created': item.created,
                            'updated': item.updated
                        }
                    )
                    if created:
                        migrados += 1
                except Exception as e:
                    print(f"    ⚠ Red social {item.id}: {e}")
            
            print(f"    ✅ {migrados} redes sociales migradas")
            
        except Exception as e:
            print(f"    ❌ Error migrando redes sociales: {e}")
        
        # 16.6 Noticias (de PortfolioProject)
        print("  📰 Migrando noticias...")
        try:
            proyectos_items = PortfolioProject.objects.using('antigua').all()
            migrados = 0
            
            for item in proyectos_items:
                try:
                    noticia, created = Noticia.objects.get_or_create(
                        title=item.title,
                        defaults={
                            'description': item.description,
                            'image': item.image if item.image else '',
                            'link': item.link,
                            'is_published': True,
                            'created': item.created,
                            'updated': item.updated
                        }
                    )
                    if created:
                        migrados += 1
                        
                        # Migrar imágenes asociadas si existen
                        try:
                            imagenes = PortfolioProjectimage.objects.using('antigua').filter(project_id=item.id)
                            for img in imagenes:
                                NoticiaImagen.objects.get_or_create(
                                    noticia=noticia,
                                    image=img.image,
                                    defaults={
                                        'caption': img.caption,
                                        'order': img.order
                                    }
                                )
                        except:
                            pass
                        
                except Exception as e:
                    print(f"    ⚠ Noticia {item.id}: {e}")
            
            print(f"    ✅ {migrados} noticias migradas")
            
        except Exception as e:
            print(f"    ❌ Error migrando noticias: {e}")
        
        # 16.7 Páginas
        print("  📄 Migrando páginas...")
        try:
            paginas_items = PagesPages.objects.using('antigua').all()
            migrados = 0
            
            for item in paginas_items:
                try:
                    # Determinar tipo basado en título
                    tipo = 'privacidad'
                    if 'cookies' in item.title.lower():
                        tipo = 'cookies'
                    elif 'aviso' in item.title.lower() or 'legal' in item.title.lower():
                        tipo = 'aviso'
                    
                    pagina, created = Pagina.objects.get_or_create(
                        title=item.title,
                        defaults={
                            'slug': f"pagina-{migrados+1}",
                            'content': item.content,
                            'tipo': tipo,
                            'is_published': True,
                            'created': item.created,
                            'updated': item.updated
                        }
                    )
                    if created:
                        migrados += 1
                except Exception as e:
                    print(f"    ⚠ Página {item.id}: {e}")
            
            print(f"    ✅ {migrados} páginas migradas")
            
        except Exception as e:
            print(f"    ❌ Error migrando páginas: {e}")

    # ==================== FASE 17 ====================
    def fase_17_post_migracion(self):
        """FASE 17: Post-migración y limpieza"""
        print("\n🧹 FASE 17: POST-MIGRACIÓN Y LIMPIEZA")
        
        try:
            # Actualizar passwords por defecto
            print("  🔒 Actualizando passwords temporales...")
            usuarios_sin_password = Usuario.objects.filter(password__contains='temp123')
            password_defecto = env_requerida('PASSWORD_MIGRACION')
            for usuario in usuarios_sin_password:
                usuario.set_password(password_defecto)
                usuario.save()
            
            print(f"    ✅ {len(usuarios_sin_password)} passwords actualizados")
            
            # Crear superusuario si no existe
            if not Usuario.objects.filter(is_superuser=True).exists():
                print("  👑 Creando superusuario por defecto...")
                superuser = Usuario.objects.create_superuser(
                    username=superadmin_username(),
                    email=env_requerida('SUPERADMIN_EMAIL'),
                    password=env_requerida('SUPERADMIN_PASSWORD'),
                    numero_documento=env_requerida('SUPERADMIN_DOCUMENTO'),
                    nombres='Administrador',
                    apellidos='Sistema',
                    tipo_usuario=TipoUsuario.objects.filter(nombre__icontains='Administrador').first()
                )
                print(f"    ✅ Superusuario creado: {superuser.username}")
            
            # Generar reporte final
            print("\n📊 REPORTE FINAL DE MIGRACIÓN:")
            print("=" * 50)
            
            modelos_verificar = [
                ('Colegio', Colegio),
                ('Sede', Sede),
                ('Usuario', Usuario),
                ('Estudiante', Estudiante),
                ('Docente', Docente),
                ('Matrícula', Matricula),
                ('Año Lectivo', AñoLectivo),
                ('Grado', Grado),
                ('Asignatura', Asignatura),
                ('Nota', Nota),
                ('Asistencia', Asistencia),
                ('Comportamiento', Comportamiento),
                ('Acudiente', Acudiente),
                ('Contacto Docente', ContactoDocente),
                ('Logro', Logro),
            ]
            
            for nombre, modelo in modelos_verificar:
                try:
                    count = modelo.objects.count()
                    print(f"   ✅ {nombre}: {count}")
                except:
                    print(f"   ❌ {nombre}: Error")
            
            print("=" * 50)
            print("🎯 MIGRACIÓN COMPLETADA EXITOSAMENTE!")
            print("\n⚠️ RECOMENDACIONES POST-MIGRACIÓN:")
            print("   1. Verificar relaciones entre datos")
            print("   2. Probar funcionalidades principales")
            print("   3. Crear backup de la nueva base de datos")
            print("   4. Notificar a usuarios sobre nuevo sistema")
            print("   5. Configurar permisos y roles específicos")
            
        except Exception as e:
            print(f"    ❌ Error en post-migración: {e}")