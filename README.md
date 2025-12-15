# Colegio App

Proyecto Django para la gestión del Colegio Cristiano El Shadai.

## Características

✅ Sistema completo de gestión educativa  
✅ Roles: Administrador, Rector, Docente, Estudiante, Acudiente  
✅ Matrículas, calificaciones, comportamiento, asistencia  
✅ Portal web público con información institucional  
✅ Sistema de notificaciones y reportes  
✅ Modo claro/oscuro  
✅ Responsive design  

## Requisitos

- Python 3.8+
- MySQL 5.7+ (o PostgreSQL)
- Git

## Estructura del Proyecto
colegio_app/
├── settings/ # Configuraciones separadas
│ ├── base.py # Configuración común
│ ├── dev.py # Desarrollo
│ └── prod.py # Producción
├── web/ # Portal web público
├── administrador/ # Panel administrativo
├── academico/ # Módulo académico
├── matricula/ # Gestión de matrículas
├── estudiantes/ # Gestión de estudiantes
├── docentes/ # Panel docente
├── usuarios/ # Sistema de usuarios
├── acudiente/ # Portal acudientes
├── comportamiento/ # Gestión de comportamiento
└── gestioncolegio/ # Configuración del colegio


## Instalación

### 1. Clonar el repositorio
```bash
git clone <url-del-repositorio>
cd colegio-app

python -m venv venv

# En Linux/Mac:
source venv/bin/activate

# En Windows:
venv\Scripts\activate

pip install -r requirements.txt

# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env con tus configuraciones
nano .env  # o usar tu editor favorito

-- Crear base de datos
CREATE DATABASE colegioc_gestion CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Crear usuario (opcional)
CREATE USER 'colegio_user'@'localhost' IDENTIFIED BY 'tu_password';
GRANT ALL PRIVILEGES ON colegioc_gestion.* TO 'colegio_user'@'localhost';
FLUSH PRIVILEGES;

# En desarrollo
python manage.py migrate --settings=colegio_app.settings.dev

# Crear superusuario
python manage.py createsuperuser --settings=colegio_app.settings.dev