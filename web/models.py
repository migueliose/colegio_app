from django.db import models
from django.core.exceptions import ValidationError
from django.utils.text import slugify

class Carrusel(models.Model):
    description = models.TextField(verbose_name='Descripción')  
    image = models.ImageField(verbose_name='Imagen', upload_to='home_carrusel')
    alt_text = models.CharField(max_length=255, blank=True, null=True, verbose_name='Texto alternativo')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    order = models.PositiveIntegerField(default=0, verbose_name='Orden')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated = models.DateTimeField(auto_now=True, verbose_name='Fecha de modificación')

    class Meta:
        verbose_name = 'Carrusel'
        verbose_name_plural = 'Carruseles'
        ordering = ['order', '-created']

    def __str__(self):
        return self.description[:50] + "..." if len(self.description) > 50 else self.description

class Welcome(models.Model):
    title = models.CharField(max_length=100, verbose_name='Título')
    description = models.TextField(verbose_name='Descripción')  
    slug = models.SlugField(unique=True, blank=True, null=True, verbose_name='Slug')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated = models.DateTimeField(auto_now=True, verbose_name='Fecha de modificación')

    class Meta:
        verbose_name = 'Bienvenida'
        verbose_name_plural = 'Bienvenidas'
        ordering = ['-created']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class RedSocial(models.Model):
    key = models.SlugField(verbose_name='Nombre clave', max_length=100, unique=True)
    name = models.CharField(verbose_name='Red social', max_length=100)
    link = models.URLField(verbose_name='Enlace', max_length=200, blank=True)
    icon_class = models.CharField(max_length=50, default='bi bi-link', verbose_name='Clase de icono')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated = models.DateTimeField(auto_now=True, verbose_name='Fecha de modificación')

    class Meta:
        verbose_name = 'Red Social'
        verbose_name_plural = 'Redes Sociales'
        ordering = ['name']

    def __str__(self):
        return self.name

class Noticia(models.Model):  # Cambié Project por Noticia para mejor semántica
    title = models.CharField(max_length=100, verbose_name='Título')
    description = models.TextField(verbose_name='Descripción')
    image = models.ImageField(verbose_name='Imagen principal', upload_to='noticias')
    link = models.URLField(null=True, blank=True, verbose_name='Enlace externo')
    is_published = models.BooleanField(default=True, verbose_name='Publicado')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated = models.DateTimeField(auto_now=True, verbose_name='Fecha de modificación')    

    class Meta:
        verbose_name = 'Noticia'
        verbose_name_plural = 'Noticias'
        ordering = ['-created']

    def clean(self):
        if len(self.title) < 5:
            raise ValidationError({'title': 'El título debe tener al menos 5 caracteres'})
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('web:noticia_detalle', kwargs={'pk': self.pk})
    
    def __str__(self):
        return self.title

class NoticiaImagen(models.Model):
    noticia = models.ForeignKey(Noticia, on_delete=models.CASCADE, related_name='imagenes')
    image = models.ImageField(upload_to='noticias/galeria/')
    caption = models.CharField(max_length=255, blank=True, verbose_name='Leyenda')
    order = models.PositiveIntegerField(default=0, verbose_name='Orden')

    class Meta:
        verbose_name = 'Imagen de Noticia'
        verbose_name_plural = 'Imágenes de Noticias'
        ordering = ['order']

    def __str__(self):
        return f"Imagen para {self.noticia.title}"

class Pagina(models.Model):
    TIPO_PAGINA = [
        ('privacidad', 'Política de Privacidad'),
        ('cookies', 'Política de Cookies'),
        ('aviso', 'Aviso Legal'),
    ]
    
    title = models.CharField(verbose_name='Título', max_length=100)
    slug = models.SlugField(unique=True, verbose_name='Slug')
    content = models.TextField(verbose_name='Contenido')
    tipo = models.CharField(max_length=20, choices=TIPO_PAGINA, default='privacidad', verbose_name='Tipo de Página')
    is_published = models.BooleanField(default=True, verbose_name='Publicada')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated = models.DateTimeField(auto_now=True, verbose_name='Fecha de modificación')

    class Meta:
        verbose_name = 'Página Legal'
        verbose_name_plural = 'Páginas Legales'
        ordering = ['tipo', 'title']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.title}"

class About(models.Model):
    TIPO_ABOUT = [
        ('historia', 'Reseña Histórica'),
        ('vision', 'Visión Institucional'),
        ('mision', 'Misión Institucional'),
        ('valores','Valores Institucionales'),
    ]
    
    title = models.CharField(max_length=100, verbose_name='Título')
    description = models.TextField(verbose_name='Descripción')  
    slug = models.SlugField(unique=True, verbose_name='Slug')
    tipo = models.CharField(max_length=20, choices=TIPO_ABOUT, default='historia', verbose_name='Tipo de Información')
    image = models.ImageField(upload_to='about/', blank=True, null=True, verbose_name='Imagen')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated = models.DateTimeField(auto_now=True, verbose_name='Fecha de modificación')

    class Meta:
        verbose_name = 'Información Institucional'
        verbose_name_plural = 'Información Institucional'
        ordering = ['tipo']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.get_tipo_display()}-{self.title}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.title}"
    
class Admision(models.Model):
    NUEVOS = 'nuevos'
    ANTIGUOS = 'antiguos'
    P_MATRICULA = 'P_matricula'
    P_ADMISION = 'P_admision'

    TIPO_CHOICES = [
        (NUEVOS, 'Nuevos Estudiantes'),
        (ANTIGUOS, 'Antiguos Estudiantes'),
        (P_MATRICULA, 'Proceso de Matrícula'),
        (P_ADMISION, 'Proceso de Admisión'),
    ]

    title = models.CharField(max_length=100, verbose_name='Título')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name='Tipo')
    description = models.TextField(verbose_name='Descripción')
    link = models.URLField(null=True, blank=True, verbose_name='Enlace')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    slug = models.SlugField(unique=True, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_description_as_list(self):
        """Convierte la descripción en una lista de líneas"""
        if not self.description:
            return []
        return [line.strip() for line in self.description.splitlines() if line.strip()]

    class Meta:
        verbose_name = 'Admisión'
        verbose_name_plural = 'Admisiones'
        ordering = ['-created']

    def __str__(self):
        return self.title
    
class ProgramaAcademico(models.Model):
    NIVEL_CHOICES = [
        ('preescolar', 'Preescolar'),
        ('primaria', 'Primaria'),
        ('bachillerato', 'Bachillerato'),
    ]
    
    nombre = models.CharField(max_length=100, verbose_name='Nombre del Programa')
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, verbose_name='Nivel')
    descripcion_corta = models.TextField(verbose_name='Descripción Corta', max_length=200)
    descripcion_completa = models.TextField(verbose_name='Descripción Completa')
    imagen_principal = models.ImageField(upload_to='programas/', verbose_name='Imagen Principal')
    edad_minima = models.IntegerField(verbose_name='Edad Mínima', blank=True, null=True)
    edad_maxima = models.IntegerField(verbose_name='Edad Máxima', blank=True, null=True)
    grados = models.CharField(max_length=100, verbose_name='Grados Ofrecidos', 
                             help_text='Ej: Prejardín a Transición')
    horario = models.CharField(max_length=100, verbose_name='Horario', 
                              default='7:00 AM - 12:00 PM')
    costo_matricula = models.DecimalField(max_digits=10, decimal_places=2, 
                                         verbose_name='Costo Matrícula', blank=True, null=True)
    costo_pension = models.DecimalField(max_digits=10, decimal_places=2, 
                                       verbose_name='Costo Pensión', blank=True, null=True)
    
    # Campos de gestión
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    destacado = models.BooleanField(default=False, verbose_name='Destacado en Home')
    orden = models.PositiveIntegerField(default=0, verbose_name='Orden')
    slug = models.SlugField(unique=True, blank=True, verbose_name='Slug')
    
    created = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated = models.DateTimeField(auto_now=True, verbose_name='Fecha de modificación')

    class Meta:
        verbose_name = 'Programa Académico'
        verbose_name_plural = 'Programas Académicos'
        ordering = ['orden', 'nivel']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.nivel}-{self.nombre}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_nivel_display()} - {self.nombre}"

class CaracteristicaPrograma(models.Model):
    programa = models.ForeignKey(ProgramaAcademico, on_delete=models.CASCADE, 
                               related_name='caracteristicas')
    titulo = models.CharField(max_length=100, verbose_name='Título')
    descripcion = models.TextField(verbose_name='Descripción')
    icono = models.CharField(max_length=50, default='bi-check-circle', 
                           verbose_name='Clase de Icono')
    orden = models.PositiveIntegerField(default=0, verbose_name='Orden')

    class Meta:
        verbose_name = 'Característica de Programa'
        verbose_name_plural = 'Características de Programas'
        ordering = ['orden']

    def __str__(self):
        return f"{self.programa.nombre} - {self.titulo}"