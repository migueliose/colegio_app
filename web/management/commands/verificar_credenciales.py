# management/commands/verificar_credenciales.py
from django.core.management.base import BaseCommand
from django.contrib.auth import authenticate
from usuarios.models import Usuario
from ._credenciales import env_requerida, superadmin_username

class Command(BaseCommand):
    help = 'Verificar que las credenciales funcionen correctamente'
    
    def handle(self, *args, **options):
        print("🔍 VERIFICANDO CREDENCIALES DEL SISTEMA")
        print("=" * 60)
        
        # Credenciales a verificar
        credenciales_prueba = [
            {
                'tipo': 'SuperAdmin',
                'username': superadmin_username(),
                'password': env_requerida('SUPERADMIN_PASSWORD'),
                'descripcion': 'Acceso completo al sistema'
            },
            {
                'tipo': 'Administrador Ejemplo',
                'username': '',  # Se buscará uno real
                'password': env_requerida('PASSWORD_ADMINISTRADOR'),
                'descripcion': 'Acceso administrativo'
            },
            {
                'tipo': 'Docente Ejemplo',
                'username': '',  # Se buscará uno real
                'password': env_requerida('PASSWORD_DOCENTE'),
                'descripcion': 'Acceso docente'
            },
            {
                'tipo': 'Estudiante Ejemplo',
                'username': '',  # Se buscará uno real
                'password': env_requerida('PASSWORD_ESTUDIANTE'),
                'descripcion': 'Acceso estudiante'
            }
        ]
        
        # Buscar usuarios reales para prueba
        try:
            # Buscar un administrador
            admin = Usuario.objects.filter(
                tipo_usuario__nombre__icontains='Administrador'
            ).exclude(username=superadmin_username()).first()
            
            if admin:
                credenciales_prueba[1]['username'] = admin.username
            
            # Buscar un docente
            docente = Usuario.objects.filter(
                tipo_usuario__nombre__icontains='Docente'
            ).first()
            
            if docente:
                credenciales_prueba[2]['username'] = docente.username
            
            # Buscar un estudiante
            estudiante = Usuario.objects.filter(
                tipo_usuario__nombre__icontains='Estudiante'
            ).first()
            
            if estudiante:
                credenciales_prueba[3]['username'] = estudiante.username
            
        except Exception as e:
            print(f"⚠ Error buscando usuarios: {e}")
        
        # Probar cada credencial
        print("\n🧪 PROBANDO ACCESO AL SISTEMA:")
        print("-" * 50)
        
        for cred in credenciales_prueba:
            if not cred['username']:
                print(f"\n❌ {cred['tipo']}: No hay usuario disponible para prueba")
                continue
            
            print(f"\n🔑 {cred['tipo']}:")
            print(f"   Usuario: {cred['username']}")
            
            # Intentar autenticar
            user = authenticate(username=cred['username'], password=cred['password'])
            
            if user is not None:
                print(f"   ✅ AUTENTICACIÓN EXITOSA")
                print(f"   📋 Información del usuario:")
                print(f"      • Nombre: {user.get_full_name()}")
                print(f"      • Email: {user.email}")
                print(f"      • Activo: {'Sí' if user.is_active else 'No'}")
                print(f"      • Staff: {'Sí' if user.is_staff else 'No'}")
                print(f"      • Superusuario: {'Sí' if user.is_superuser else 'No'}")
                print(f"      • Tipo: {user.tipo_usuario.nombre if user.tipo_usuario else 'No asignado'}")
            else:
                print(f"   ❌ FALLÓ LA AUTENTICACIÓN")
                print(f"   ⚠ Posibles problemas:")
                print(f"      • Usuario no existe")
                print(f"      • Contraseña incorrecta")
                print(f"      • Usuario inactivo")
        
        # Verificación adicional
        print("\n" + "=" * 60)
        print("📊 ESTADÍSTICAS DEL SISTEMA:")
        print("-" * 50)
        
        try:
            total_usuarios = Usuario.objects.count()
            usuarios_activos = Usuario.objects.filter(is_active=True).count()
            usuarios_staff = Usuario.objects.filter(is_staff=True).count()
            superusuarios = Usuario.objects.filter(is_superuser=True).count()
            
            print(f"   Total usuarios: {total_usuarios}")
            print(f"   Usuarios activos: {usuarios_activos}")
            print(f"   Usuarios staff: {usuarios_staff}")
            print(f"   Superusuarios: {superusuarios}")
            
            # Contar por tipo
            print(f"\n   👥 DISTRIBUCIÓN POR TIPO:")
            from usuarios.models import TipoUsuario
            
            tipos = TipoUsuario.objects.all()
            for tipo in tipos:
                count = Usuario.objects.filter(tipo_usuario=tipo).count()
                print(f"      • {tipo.nombre}: {count}")
            
        except Exception as e:
            print(f"   ⚠ Error obteniendo estadísticas: {e}")
        
        print("\n" + "=" * 60)
        print("✅ VERIFICACIÓN COMPLETADA")