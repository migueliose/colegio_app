# management/commands/configurar_passwords.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from usuarios.models import Usuario, TipoUsuario
import csv
from django.utils import timezone
from ._credenciales import env_requerida, superadmin_username

User = get_user_model()

class Command(BaseCommand):
    help = 'Configurar contraseñas según especificaciones y generar reporte'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--solo-reporte',
            action='store_true',
            help='Solo generar reporte sin cambiar contraseñas'
        )
        parser.add_argument(
            '--exportar',
            action='store_true',
            help='Exportar credenciales a archivo CSV'
        )

    def handle(self, *args, **options):
        print("🔐 CONFIGURANDO CONTRASEÑAS SEGÚN ESPECIFICACIONES")
        print("=" * 60)
        
        solo_reporte = options['solo_reporte']
        exportar = options['exportar']
        
        # Configuración de contraseñas según especificaciones
        configuracion_passwords = {
            'SuperAdmin': {
                'username': superadmin_username(),
                'password': env_requerida('SUPERADMIN_PASSWORD'),
                'tipo_buscar': ['Administrador', 'Superusuario'],
                'documento': env_requerida('SUPERADMIN_DOCUMENTO'),
                'nombres': 'Super',
                'apellidos': 'Administrador',
                'email': env_requerida('SUPERADMIN_EMAIL')
            },
            'Administrador': {
                'password': env_requerida('PASSWORD_ADMINISTRADOR'),
                'tipo_buscar': ['Administrador'],
                'excluir_usuario': superadmin_username()
            },
            'Rector': {
                'password': env_requerida('PASSWORD_RECTOR'),
                'tipo_buscar': ['Rector', 'Rector(a)']
            },
            'Docente': {
                'password': env_requerida('PASSWORD_DOCENTE'),
                'tipo_buscar': ['Docente']
            },
            'Estudiante': {
                'password': env_requerida('PASSWORD_ESTUDIANTE'),
                'tipo_buscar': ['Estudiante']
            },
            'Acudiente': {
                'password': env_requerida('PASSWORD_ACUDIENTE'),
                'tipo_buscar': ['Acudiente']
            }
        }
        
        try:
            # 1. Configurar SuperAdmin especial
            print("\n👑 CONFIGURANDO SUPER ADMINISTRADOR")
            superadmin_config = configuracion_passwords['SuperAdmin']
            
            # Verificar si ya existe el usuario mihael
            usuario_superadmin = Usuario.objects.filter(
                username=superadmin_config['username']
            ).first()
            
            if usuario_superadmin:
                print(f"  ⚠ Usuario '{superadmin_config['username']}' ya existe")
                if not solo_reporte:
                    usuario_superadmin.set_password(superadmin_config['password'])
                    usuario_superadmin.is_superuser = True
                    usuario_superadmin.is_staff = True
                    usuario_superadmin.is_active = True
                    usuario_superadmin.save()
                    print(f"  ✅ Contraseña actualizada para SuperAdmin")
            else:
                # Crear nuevo SuperAdmin
                if not solo_reporte:
                    # Buscar tipo Administrador
                    tipo_admin = TipoUsuario.objects.filter(
                        nombre__icontains='Administrador'
                    ).first()
                    
                    if not tipo_admin:
                        # Crear tipo si no existe
                        tipo_admin = TipoUsuario.objects.create(
                            nombre='Administrador',
                            is_deleted=False
                        )
                    
                    # Crear el SuperAdmin
                    usuario_superadmin = Usuario.objects.create_superuser(
                        username=superadmin_config['username'],
                        email=superadmin_config['email'],
                        password=superadmin_config['password'],
                        numero_documento=superadmin_config['documento'],
                        nombres=superadmin_config['nombres'],
                        apellidos=superadmin_config['apellidos'],
                        tipo_usuario=tipo_admin
                    )
                    print(f"  ✅ SuperAdmin creado exitosamente")
            
            # Mostrar credenciales SuperAdmin
            print(f"\n  📋 CREDENCIALES SUPER ADMIN:")
            print(f"     Usuario: {superadmin_config['username']}")
            print(f"     Contraseña: {superadmin_config['password']}")
            print(f"     Documento: {superadmin_config['documento']}")
            print(f"     Nombre: {superadmin_config['nombres']} {superadmin_config['apellidos']}")
            
            # 2. Configurar contraseñas por tipo de usuario
            print("\n🔧 CONFIGURANDO CONTRASEÑAS POR TIPO DE USUARIO")
            print("-" * 50)
            
            resultados = {}
            
            for tipo_nombre, config in configuracion_passwords.items():
                if tipo_nombre == 'SuperAdmin':
                    continue  # Ya lo procesamos
                
                print(f"\n  👥 {tipo_nombre.upper()}S:")
                print(f"     Contraseña asignada: '{config['password']}'")
                
                # Buscar tipos de usuario que coincidan
                tipos_encontrados = []
                for tipo_buscar in config['tipo_buscar']:
                    tipos = TipoUsuario.objects.filter(
                        nombre__icontains=tipo_buscar
                    )
                    tipos_encontrados.extend(tipos)
                
                if not tipos_encontrados:
                    print(f"     ⚠ No se encontró tipo de usuario para '{tipo_nombre}'")
                    resultados[tipo_nombre] = {
                        'password': config['password'],
                        'total': 0,
                        'usuarios': []
                    }
                    continue
                
                # Obtener usuarios de estos tipos
                usuarios_query = Usuario.objects.filter(
                    tipo_usuario__in=tipos_encontrados
                )
                
                # Excluir SuperAdmin si es necesario
                if 'excluir_usuario' in config:
                    usuarios_query = usuarios_query.exclude(
                        username=config['excluir_usuario']
                    )
                
                total_usuarios = usuarios_query.count()
                
                print(f"     Total usuarios: {total_usuarios}")
                
                if total_usuarios > 0:
                    # Actualizar contraseñas
                    if not solo_reporte:
                        usuarios_actualizados = 0
                        for usuario in usuarios_query:
                            usuario.set_password(config['password'])
                            usuario.save()
                            usuarios_actualizados += 1
                        
                        print(f"     ✅ {usuarios_actualizados} contraseñas actualizadas")
                    
                    # Guardar resultados para reporte
                    usuarios_ejemplo = list(usuarios_query.values(
                        'username', 'numero_documento', 'nombres', 'apellidos'
                    )[:5])  # Primeros 5 como ejemplo
                    
                    resultados[tipo_nombre] = {
                        'password': config['password'],
                        'total': total_usuarios,
                        'usuarios': usuarios_ejemplo
                    }
                    
                    # Mostrar ejemplos
                    if usuarios_ejemplo:
                        print(f"     Ejemplos:")
                        for i, usuario in enumerate(usuarios_ejemplo[:3], 1):
                            print(f"       {i}. {usuario['nombres']} {usuario['apellidos']}")
                            print(f"          Usuario: {usuario['username']}")
                            print(f"          Documento: {usuario['numero_documento']}")
                else:
                    print(f"     ℹ️ No hay usuarios de este tipo")
                    resultados[tipo_nombre] = {
                        'password': config['password'],
                        'total': 0,
                        'usuarios': []
                    }
            
            # 3. Generar reporte completo
            print("\n" + "=" * 60)
            print("📊 REPORTE COMPLETO DE CONTRASEÑAS")
            print("=" * 60)
            
            total_general = 0
            for tipo_nombre, datos in resultados.items():
                if tipo_nombre in configuracion_passwords:
                    print(f"\n{tipo_nombre.upper()}:")
                    print(f"  Contraseña: '{datos['password']}'")
                    print(f"  Total usuarios: {datos['total']}")
                    total_general += datos['total']
                    
                    if datos['usuarios']:
                        print(f"  Ejemplos de acceso:")
                        for usuario in datos['usuarios'][:2]:  # Mostrar solo 2
                            print(f"    • Usuario: {usuario['username']}")
                            print(f"      Contraseña: {datos['password']}")
                            print(f"      Nombre: {usuario['nombres']} {usuario['apellidos']}")
            
            # SuperAdmin aparte
            print(f"\nSUPER ADMINISTRADOR (Acceso total):")
            print(f"  Usuario: {superadmin_config['username']}")
            print(f"  Contraseña: {superadmin_config['password']}")
            print(f"  Nombre: {superadmin_config['nombres']} {superadmin_config['apellidos']}")
            
            print(f"\n📈 TOTAL USUARIOS CONFIGURADOS: {total_general}")
            
            # 4. Exportar a CSV si se solicita
            if exportar and not solo_reporte:
                self.exportar_credenciales_csv(resultados, superadmin_config)
            
            # 5. Recomendaciones finales
            print("\n" + "=" * 60)
            print("💡 INSTRUCCIONES Y RECOMENDACIONES:")
            print("=" * 60)
            print("1. 📱 ACCESO AL SISTEMA:")
            print("   • URL: http://localhost:8000/admin/ (para administradores)")
            print("   • URL: http://localhost:8000/ (para usuarios normales)")
            print("\n2. 🔐 CREDENCIALES PRINCIPALES:")
            print("   • Las contraseñas se toman de las variables de entorno del archivo .env")
            print("   • Usuario de cada persona: su número de documento")
            print("\n3. ⚠️ SEGURIDAD:")
            print("   • Cambiar contraseñas en primer acceso")
            print("   • No compartir credenciales")
            print("   • SuperAdmin solo para emergencias")
            print("\n4. 📞 SOPORTE:")
            print("   • Contactar al administrador si hay problemas de acceso")
            print("   • Verificar tipo de usuario asignado")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

    def exportar_credenciales_csv(self, resultados, superadmin_config):
        """Exportar todas las credenciales a archivo CSV"""
        try:
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = f"credenciales_colego_shadai_{timestamp}.csv"
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'Tipo_Usuario', 'Usuario', 'Contraseña', 'Documento',
                    'Nombres', 'Apellidos', 'Email', 'Observaciones'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                
                # Escribir SuperAdmin
                writer.writerow({
                    'Tipo_Usuario': 'SuperAdmin',
                    'Usuario': superadmin_config['username'],
                    'Contraseña': superadmin_config['password'],
                    'Documento': superadmin_config['documento'],
                    'Nombres': superadmin_config['nombres'],
                    'Apellidos': superadmin_config['apellidos'],
                    'Email': superadmin_config['email'],
                    'Observaciones': 'ACCESO COMPLETO AL SISTEMA'
                })
                
                # Escribir usuarios por tipo
                for tipo_nombre, datos in resultados.items():
                    if tipo_nombre in ['Administrador', 'Rector', 'Docente', 'Estudiante', 'Acudiente']:
                        # Buscar todos los usuarios de este tipo
                        tipo_buscar_list = []
                        if tipo_nombre == 'Administrador':
                            tipo_buscar_list = ['Administrador']
                        elif tipo_nombre == 'Rector':
                            tipo_buscar_list = ['Rector', 'Rector(a)']
                        elif tipo_nombre == 'Docente':
                            tipo_buscar_list = ['Docente']
                        elif tipo_nombre == 'Estudiante':
                            tipo_buscar_list = ['Estudiante']
                        elif tipo_nombre == 'Acudiente':
                            tipo_buscar_list = ['Acudiente']
                        
                        tipos_encontrados = []
                        for tipo_buscar in tipo_buscar_list:
                            tipos = TipoUsuario.objects.filter(
                                nombre__icontains=tipo_buscar
                            )
                            tipos_encontrados.extend(tipos)
                        
                        if tipos_encontrados:
                            usuarios = Usuario.objects.filter(
                                tipo_usuario__in=tipos_encontrados
                            ).exclude(
                                username=superadmin_config['username']
                            ).values(
                                'username', 'numero_documento', 
                                'nombres', 'apellidos', 'email'
                            )
                            
                            for usuario in usuarios:
                                writer.writerow({
                                    'Tipo_Usuario': tipo_nombre,
                                    'Usuario': usuario['username'],
                                    'Contraseña': datos['password'],
                                    'Documento': usuario['numero_documento'],
                                    'Nombres': usuario['nombres'],
                                    'Apellidos': usuario['apellidos'],
                                    'Email': usuario['email'] or 'No tiene',
                                    'Observaciones': f'{tipo_nombre} del colegio'
                                })
            
            print(f"\n💾 ARCHIVO EXPORTADO: {filename}")
            print(f"   Total registros exportados: Contiene todas las credenciales")
            
        except Exception as e:
            print(f"\n⚠ Error exportando CSV: {e}")