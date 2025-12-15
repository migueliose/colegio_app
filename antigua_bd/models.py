# antigua_bd/models.py
from django.db import models

# ============ MODELOS DE GESTIÓN COLEGIO ============
class GestioncolegioColegio(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255)
    resolucion = models.CharField(max_length=50)
    dane = models.CharField(max_length=50)
    estado = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'gestioncolegio_colegio'
        app_label = 'antigua_bd'

class GestioncolegioRecursoscolegio(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    escudo = models.CharField(max_length=100, blank=True, null=True)
    bandera = models.CharField(max_length=100, blank=True, null=True)
    sitio_web = models.CharField(max_length=200)
    email = models.CharField(max_length=254)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    colegio = models.OneToOneField(GestioncolegioColegio, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_recursoscolegio'
        app_label = 'antigua_bd'

class GestioncolegioAolectivo(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    anho = models.CharField(max_length=5, blank=True, null=True)
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)
    estado = models.IntegerField()
    colegio = models.ForeignKey(GestioncolegioColegio, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_añolectivo'
        app_label = 'antigua_bd'

class GestioncolegioNivelescolar(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    nombre = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_nivelescolar'
        app_label = 'antigua_bd'

class GestioncolegioGrado(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    nombre = models.CharField(unique=True, max_length=50)
    nivel_escolar = models.ForeignKey(GestioncolegioNivelescolar, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_grado'
        app_label = 'antigua_bd'

class GestioncolegioGradoaolectivo(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    estado = models.IntegerField()
    año_lectivo = models.ForeignKey(GestioncolegioAolectivo, models.DO_NOTHING)
    grado = models.ForeignKey(GestioncolegioGrado, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_gradoañolectivo'
        unique_together = (('grado', 'año_lectivo'),)
        app_label = 'antigua_bd'

class GestioncolegioArea(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    nombre = models.CharField(max_length=100)
    nivel_escolar = models.ForeignKey(GestioncolegioNivelescolar, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_area'
        app_label = 'antigua_bd'

class GestioncolegioAsignatura(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    nombre = models.CharField(max_length=100)
    ih = models.CharField(max_length=1, blank=True, null=True)
    area = models.ForeignKey(GestioncolegioArea, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_asignatura'
        app_label = 'antigua_bd'

class GestioncolegioTipodocumento(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    nombre = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_tipodocumento'
        app_label = 'antigua_bd'

class GestioncolegioTipousuario(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    nombre = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_tipousuario'
        app_label = 'antigua_bd'

class GestioncolegioUsuario(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    numero_documento = models.CharField(unique=True, max_length=50)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=254, blank=True, null=True)
    estado = models.IntegerField()
    tipo_documento = models.ForeignKey(GestioncolegioTipodocumento, models.DO_NOTHING, blank=True, null=True)
    user = models.OneToOneField('AuthUser', models.DO_NOTHING)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    sexo = models.CharField(max_length=1, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_usuario'
        app_label = 'antigua_bd'

class GestioncolegioDocente(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    foto = models.CharField(max_length=100, blank=True, null=True)
    hdv = models.CharField(max_length=100, blank=True, null=True)
    estado = models.IntegerField()
    año_lectivo = models.ForeignKey(GestioncolegioAolectivo, models.DO_NOTHING, blank=True, null=True)
    usuario = models.ForeignKey(GestioncolegioUsuario, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_docente'
        app_label = 'antigua_bd'

class GestioncolegioEstudiante(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    foto = models.CharField(max_length=100, blank=True, null=True)
    estado = models.IntegerField()
    grado_año_lectivo = models.ForeignKey(GestioncolegioGradoaolectivo, models.DO_NOTHING)
    usuario = models.ForeignKey(GestioncolegioUsuario, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_estudiante'
        unique_together = (('usuario', 'grado_año_lectivo'),)
        app_label = 'antigua_bd'

class GestioncolegioAcudiente(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    parentesco = models.CharField(max_length=50)
    estudiante = models.ForeignKey(GestioncolegioEstudiante, models.DO_NOTHING)
    acudiente = models.ForeignKey(GestioncolegioUsuario, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_acudiente'
        app_label = 'antigua_bd'

class GestioncolegioContactodocente(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20)
    email = models.CharField(max_length=254)
    relacion = models.CharField(max_length=50)
    docente = models.ForeignKey(GestioncolegioDocente, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_contactodocente'
        app_label = 'antigua_bd'

class GestioncolegioPeriodo(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    nombre = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_periodo'
        app_label = 'antigua_bd'

class GestioncolegioPeriodoacademico(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.IntegerField()
    año_lectivo = models.ForeignKey(GestioncolegioAolectivo, models.DO_NOTHING)
    periodo = models.ForeignKey(GestioncolegioPeriodo, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_periodoacademico'
        unique_together = (('año_lectivo', 'periodo'),)
        app_label = 'antigua_bd'

class GestioncolegioAsignaturagradoaolectivo(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    asignatura = models.ForeignKey(GestioncolegioAsignatura, models.DO_NOTHING)
    docente = models.ForeignKey(GestioncolegioDocente, models.DO_NOTHING, blank=True, null=True)
    grado_año_lectivo = models.ForeignKey(GestioncolegioGradoaolectivo, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_asignaturagradoañolectivo'
        unique_together = (('asignatura', 'grado_año_lectivo'),)
        app_label = 'antigua_bd'

class GestioncolegioLogro(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    tema = models.TextField(blank=True, null=True)
    descripcion_superior = models.TextField(blank=True, null=True)
    descripcion_alto = models.TextField(blank=True, null=True)
    descripcion_basico = models.TextField(blank=True, null=True)
    descripcion_bajo = models.TextField(blank=True, null=True)
    asignatura = models.ForeignKey(GestioncolegioAsignatura, models.DO_NOTHING)
    grado = models.ForeignKey(GestioncolegioGrado, models.DO_NOTHING)
    periodo_academico = models.ForeignKey(GestioncolegioPeriodoacademico, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_logro'
        app_label = 'antigua_bd'

class GestioncolegioNota(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    calificacion = models.DecimalField(max_digits=5, decimal_places=2)
    observaciones = models.TextField(blank=True, null=True)
    asignatura_grado_año_lectivo = models.ForeignKey(GestioncolegioAsignaturagradoaolectivo, models.DO_NOTHING)
    estudiante = models.ForeignKey(GestioncolegioEstudiante, models.DO_NOTHING)
    periodo_academico = models.ForeignKey(GestioncolegioPeriodoacademico, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_nota'
        app_label = 'antigua_bd'

class GestioncolegioComportamiento(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    tipo = models.CharField(max_length=10)
    categoria = models.CharField(max_length=15)
    descripcion = models.TextField()
    fecha = models.DateField()
    docente = models.ForeignKey(GestioncolegioDocente, models.DO_NOTHING, blank=True, null=True)
    estudiante = models.ForeignKey(GestioncolegioEstudiante, models.DO_NOTHING)
    periodo_academico = models.ForeignKey(GestioncolegioPeriodoacademico, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_comportamiento'
        app_label = 'antigua_bd'

class GestioncolegioAsistencia(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    fecha = models.DateField()
    estudiante = models.ForeignKey(GestioncolegioEstudiante, models.DO_NOTHING)
    periodo_academico = models.ForeignKey(GestioncolegioPeriodoacademico, models.DO_NOTHING)
    estado = models.CharField(max_length=1)
    justificacion = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_asistencia'
        unique_together = (('estudiante', 'fecha'),)
        app_label = 'antigua_bd'

class GestioncolegioInconsistencia(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    fecha = models.DateField()
    tipo = models.CharField(max_length=50)
    descripcion = models.TextField()
    estudiante = models.ForeignKey(GestioncolegioEstudiante, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_inconsistencia'
        unique_together = (('estudiante', 'fecha', 'tipo'),)
        app_label = 'antigua_bd'

class GestioncolegioHorarioclase(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    dia_semana = models.CharField(max_length=10)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    salon = models.CharField(max_length=20)
    asignatura_grado = models.ForeignKey(GestioncolegioAsignaturagradoaolectivo, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_horarioclase'
        unique_together = (('asignatura_grado', 'dia_semana', 'hora_inicio'),)
        app_label = 'antigua_bd'

class GestioncolegioPlanificacionclase(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    fecha = models.DateField()
    tema = models.CharField(max_length=200)
    actividades = models.TextField()
    recursos = models.TextField()
    estado = models.CharField(max_length=4)
    observaciones = models.TextField()
    horario = models.ForeignKey(GestioncolegioHorarioclase, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_planificacionclase'
        unique_together = (('horario', 'fecha'),)
        app_label = 'antigua_bd'

class GestioncolegioMaterialapoyo(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    nombre = models.CharField(max_length=100)
    archivo = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20)
    planificacion = models.ForeignKey(GestioncolegioPlanificacionclase, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_materialapoyo'
        app_label = 'antigua_bd'

class GestioncolegioHistorialacademicoestudiante(models.Model):
    id = models.BigAutoField(primary_key=True)
    is_deleted = models.IntegerField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    promedio_periodo = models.DecimalField(max_digits=4, decimal_places=2)
    faltas = models.PositiveIntegerField()
    logros = models.TextField()
    asignatura = models.ForeignKey(GestioncolegioAsignatura, models.DO_NOTHING)
    año_lectivo = models.ForeignKey(GestioncolegioAolectivo, models.DO_NOTHING)
    comportamiento = models.ForeignKey(GestioncolegioComportamiento, models.DO_NOTHING, blank=True, null=True)
    estudiante = models.ForeignKey(GestioncolegioEstudiante, models.DO_NOTHING)
    periodo_academico = models.ForeignKey(GestioncolegioPeriodoacademico, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_historialacademicoestudiante'
        unique_together = (('estudiante', 'año_lectivo', 'periodo_academico', 'asignatura'),)
        app_label = 'antigua_bd'

class GestioncolegioHistorialacademicoestudianteNotas(models.Model):
    id = models.BigAutoField(primary_key=True)
    historialacademicoestudiante = models.ForeignKey(GestioncolegioHistorialacademicoestudiante, models.DO_NOTHING)
    nota = models.ForeignKey(GestioncolegioNota, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'gestioncolegio_historialacademicoestudiante_notas'
        unique_together = (('historialacademicoestudiante', 'nota'),)
        app_label = 'antigua_bd'

# ============ MODELOS DE AUTH ============
class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'
        app_label = 'antigua_bd'

class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'
        app_label = 'antigua_bd'

class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)
        app_label = 'antigua_bd'

class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)
        app_label = 'antigua_bd'

class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)
        app_label = 'antigua_bd'

class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)
        app_label = 'antigua_bd'

# ============ MODELOS DE DJANGO ============
class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'
        app_label = 'antigua_bd'

class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)
        app_label = 'antigua_bd'

class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'
        app_label = 'antigua_bd'

class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'
        app_label = 'antigua_bd'

# ============ MODELOS WEB ============
class WebCarrusel(models.Model):
    id = models.BigAutoField(primary_key=True)
    description = models.TextField()
    image = models.CharField(max_length=100)
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    created = models.DateTimeField()
    updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'web_carrusel'
        app_label = 'antigua_bd'

class WebWelcome(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=100)
    description = models.TextField()
    slug = models.CharField(unique=True, max_length=50, blank=True, null=True)
    created = models.DateTimeField()
    updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'web_welcome'
        app_label = 'antigua_bd'

class AboutAbout(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=100)
    description = models.TextField()
    slug = models.CharField(unique=True, max_length=50, blank=True, null=True)
    created = models.DateTimeField()
    updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'about_about'
        app_label = 'antigua_bd'

class AdmisionAdmision(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=100)
    description = models.TextField()
    pdf_document = models.CharField(max_length=100, blank=True, null=True)
    link = models.CharField(max_length=200, blank=True, null=True)
    created = models.DateTimeField()
    updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'admision_admision'
        app_label = 'antigua_bd'

class PortfolioProject(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=100)
    description = models.TextField()
    image = models.CharField(max_length=100)
    link = models.CharField(max_length=200, blank=True, null=True)
    created = models.DateTimeField()
    updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'portfolio_project'
        app_label = 'antigua_bd'

class PortfolioProjectimage(models.Model):
    id = models.BigAutoField(primary_key=True)
    image = models.CharField(max_length=100)
    caption = models.CharField(max_length=255)
    order = models.PositiveIntegerField()
    project = models.ForeignKey(PortfolioProject, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'portfolio_projectimage'
        app_label = 'antigua_bd'

class SocialRedsocial(models.Model):
    id = models.BigAutoField(primary_key=True)
    key = models.CharField(unique=True, max_length=100)
    name = models.CharField(max_length=100)
    link = models.CharField(max_length=200)
    created = models.DateTimeField()
    updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'social_redsocial'
        app_label = 'antigua_bd'

class PagesPages(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=100)
    content = models.TextField()
    created = models.DateTimeField()
    updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'pages_pages'
        app_label = 'antigua_bd'