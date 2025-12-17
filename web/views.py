from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, ListView, DetailView
from django.views.generic.edit import FormView
from django.urls import reverse
from django.core.mail import EmailMessage
from .forms import ContactForm
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from .models import *  # Esto importa solo los modelos de la app web

class PerfilView(LoginRequiredMixin, TemplateView):
    template_name = 'web/perfil.html'
    login_url = '/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # AÑADIR PROGRMAS AL CONTEXTO PARA EL NAVBAR
        try:
            context['programas'] = ProgramaAcademico.objects.filter(
                is_active=True
            ).order_by('orden')[:10]
        except Exception as e:
            print(f"Error cargando programas para navbar: {e}")
            context['programas'] = []
        
        # Para superusuarios
        if user.is_superuser:
            context['es_superusuario'] = True
            # Cargar estadísticas para superadmin
            from estudiantes.models import Estudiante, Acudiente
            from usuarios.models import Docente, Usuario
            from gestioncolegio.models import Colegio, AñoLectivo
            
            try:
                context['total_estudiantes'] = Estudiante.objects.filter(estado=True).count()
                context['total_docentes'] = Docente.objects.filter(estado=True).count()
                context['total_usuarios'] = Usuario.objects.filter(estado=True).count()
                context['total_acudientes'] = Acudiente.objects.filter(estado=True).count()
                context['total_superusuarios'] = Usuario.objects.filter(is_superuser=True).count()
                context['colegio_info'] = Colegio.objects.filter(estado=True).first()
                
                # Año lectivo actual
                año_actual = AñoLectivo.objects.filter(estado=True).first()
                if año_actual:
                    context['año_lectivo_actual'] = año_actual
                    
                    # Matrículas del año actual
                    from estudiantes.models import Matricula
                    context['matriculas_año_actual'] = Matricula.objects.filter(
                        año_lectivo=año_actual,
                        estado__in=['ACT', 'PEN']
                    ).count()
                    
            except Exception as e:
                print(f"Error cargando stats superadmin: {e}")
        
        # Obtener datos específicos del usuario y ponerlos directamente en el contexto
        # para que estén disponibles en el template
        user_data = self._get_user_data(user)
        context.update(user_data)
        
        return context
    
    def _get_user_data(self, user):
        """Obtiene datos específicos según el tipo de usuario"""
        data = {}
        
        try:
            # Verificación SEGURA del tipo_usuario
            tipo_nombre = None
            if hasattr(user, 'tipo_usuario'):
                tipo_obj = user.tipo_usuario
                if tipo_obj and hasattr(tipo_obj, 'nombre'):
                    tipo_nombre = tipo_obj.nombre
                    data['tipo_usuario_nombre'] = tipo_nombre  # También ponerlo en data
            
            if not tipo_nombre:
                return data
            
            # Datos comunes a todos los tipos
            data['tipo_nombre'] = tipo_nombre
            
            # Estudiante
            if tipo_nombre == 'Estudiante':
                estudiante_data = self._get_estudiante_data(user)
                data.update(estudiante_data)
            
            # Docente
            elif tipo_nombre == 'Docente':
                docente_data = self._get_docente_data(user)
                data.update(docente_data)
            
            # Administrador
            elif tipo_nombre == 'Administrador':
                admin_data = self._get_administrador_data(user)
                data.update(admin_data)
            
            # Acudiente
            elif tipo_nombre == 'Acudiente':
                acudiente_data = self._get_acudiente_data(user)
                data.update(acudiente_data)
            
            # Rector
            elif tipo_nombre == 'Rector':
                rector_data = self._get_rector_data(user)
                data.update(rector_data)
                
        except Exception as e:
            print(f"Error obteniendo datos de usuario {user.id}: {e}")
        
        return data
    
    def _get_estudiante_data(self, user):
        """Obtiene datos específicos de estudiante"""
        from estudiantes.models import Estudiante, Nota
        from comportamiento.models import Asistencia
        
        data = {}
        try:
            # CORRECCIÓN: Usar get() en lugar de filter().first() para evitar múltiples consultas
            estudiante = Estudiante.objects.get(usuario=user)
            data['estudiante'] = estudiante
            data['matricula_actual'] = estudiante.matricula_actual
            
            if estudiante.matricula_actual:
                data['grado_actual'] = estudiante.grado_actual
                data['sede_actual'] = estudiante.sede_actual
                
                # Notas recientes
                notas = Nota.objects.filter(
                    estudiante=estudiante
                ).select_related(
                    'asignatura_grado_año_lectivo__asignatura'
                ).order_by('-created_at')[:5]
                data['notas_recientes'] = notas
                
                # Asistencia reciente
                asistencias = Asistencia.objects.filter(
                    estudiante=estudiante
                ).order_by('-fecha')[:10]
                data['asistencias_recientes'] = asistencias
                
        except Estudiante.DoesNotExist:
            print(f"No se encontró estudiante para usuario {user.id}")
        except Exception as e:
            print(f"Error obteniendo datos de estudiante: {e}")
        
        return data
    
    def _get_docente_data(self, user):
        """Obtiene datos específicos de docente"""
        from usuarios.models import Docente
        from matricula.models import DocenteSede, AsignaturaGradoAñoLectivo
        
        data = {}
        try:
            docente = Docente.objects.get(usuario=user)
            data['docente'] = docente
            
            # Sedes asignadas
            sedes_asignadas = DocenteSede.objects.filter(
                docente=docente, 
                estado=True
            ).select_related('sede')
            data['sedes_asignadas'] = sedes_asignadas
            
            # Asignaturas asignadas
            asignaturas_docente = AsignaturaGradoAñoLectivo.objects.filter(
                docente=docente
            ).select_related(
                'asignatura',
                'grado_año_lectivo__grado'
            )
            data['asignaturas_docente'] = asignaturas_docente
            
        except Docente.DoesNotExist:
            print(f"No se encontró docente para usuario {user.id}")
        except Exception as e:
            print(f"Error obteniendo datos de docente: {e}")
        
        return data
    
    def _get_acudiente_data(self, user):
        """Obtiene datos específicos de acudiente"""
        from estudiantes.models import Acudiente
        
        data = {}
        try:
            # Obtener todos los estudiantes a cargo
            estudiantes_acargo = Acudiente.objects.filter(
                acudiente=user
            ).select_related(
                'estudiante__usuario'
            ).prefetch_related(
                'estudiante__matriculas__grado_año_lectivo__grado'
            )
            
            data['estudiantes_acargo'] = estudiantes_acargo
            
            # Si hay acudientes, usar el primero para 'acudiente'
            if estudiantes_acargo.exists():
                data['acudiente'] = estudiantes_acargo.first()
                
        except Exception as e:
            print(f"Error obteniendo datos de acudiente: {e}")
        
        return data
    
    def _get_administrador_data(self, user):
        """Obtiene datos específicos de administrador"""
        from estudiantes.models import Estudiante
        from usuarios.models import Docente
        from gestioncolegio.models import Colegio
        
        data = {'es_administrador_sistema': True}
        try:
            data['total_estudiantes'] = Estudiante.objects.filter(estado=True).count()
            data['total_docentes'] = Docente.objects.filter(estado=True).count()
            data['colegio_info'] = Colegio.objects.filter(estado=True).first()
        except Exception as e:
            print(f"Error obteniendo datos de administrador: {e}")
        
        return data
    
    def _get_rector_data(self, user):
        """Obtiene datos específicos de rector"""
        from gestioncolegio.models import Sede
        
        data = {'es_rector': True}
        try:
            sedes_dirigidas = Sede.objects.filter(director=user)
            data['sedes_dirigidas'] = sedes_dirigidas
        except Exception as e:
            print(f"Error obteniendo datos de rector: {e}")
        
        return data
    
class HomeView(TemplateView):
    template_name = 'web/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            context['carruseles'] = Carrusel.objects.filter(is_active=True).order_by('order')[:5]
            context['bienvenida'] = Welcome.objects.filter(is_active=True).first()
            context['noticias'] = Noticia.objects.filter(is_published=True).prefetch_related('imagenes')[:6]
            context['redes_sociales'] = RedSocial.objects.filter(is_active=True)
        except Exception as e:
            print(f"Error cargando datos del home: {e}")
                
        return context

class AboutView(TemplateView):
    template_name = 'web/about.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtener toda la información institucional
        try:
            context['historia'] = About.objects.filter(tipo='historia', is_active=True).first()
            context['mision'] = About.objects.filter(tipo='mision', is_active=True).first()
            context['vision'] = About.objects.filter(tipo='vision', is_active=True).first()
            context['valores'] = About.objects.filter(tipo='valores', is_active=True).first()
        except:
            context['historia'] = context['mision'] = context['vision'] = context['valores'] = None
        
        try:
            context['programas'] = ProgramaAcademico.objects.filter(
                is_active=True
            ).order_by('orden')[:10]
        except:
            context['programas'] = []
                
        return context

class ContactView(FormView):
    template_name = 'web/contact.html'
    form_class = ContactForm
    success_url = reverse_lazy('web:contact')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
                
        try:
            context['programas'] = ProgramaAcademico.objects.filter(
                is_active=True
            ).order_by('orden')[:10]
        except:
            context['programas'] = []
                
        return context

    def form_valid(self, form):
        # Capturar los datos
        name = form.cleaned_data.get('name')
        email_sender = form.cleaned_data.get('email')
        phone = form.cleaned_data.get('phone')
        content = form.cleaned_data.get('content')

        # Enviar correo
        email = EmailMessage(
            subject=f'Nuevo mensaje de contacto de {name}',
            body=f"""
Nombre: {name}
Email: {email_sender}
Teléfono: {phone}

Mensaje:
{content}

---
Este mensaje fue enviado desde el formulario de contacto del sitio web.
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.EMAIL_HOST_USER],  # Enviar al mismo email
            reply_to=[email_sender]  # Para que puedan responder directamente
        )
        
        try:
            email.send()
            messages.success(self.request, '¡Mensaje enviado correctamente! Nos pondremos en contacto contigo pronto.')
        except Exception as e:
            messages.error(self.request, f'Error al enviar el mensaje: {str(e)}')
            # También puedes loggear el error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error enviando email de contacto: {e}")

        return super().form_valid(form)
    
class NoticiaListView(ListView):
    model = Noticia
    template_name = 'web/noticias.html'
    context_object_name = 'noticias'
    paginate_by = 6
    
    def get_queryset(self):
        try:
            return Noticia.objects.filter(
                is_published=True
            ).select_related().prefetch_related('imagenes')
        except:
            return Noticia.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            context['programas'] = ProgramaAcademico.objects.filter(
                is_active=True
            ).order_by('orden')[:10]
        except:
            context['programas'] = []
                
        return context

class NoticiaDetailView(DetailView):
    model = Noticia
    template_name = 'web/noticia_detalle.html'
    context_object_name = 'noticia'
    
    def get_queryset(self):
        try:
            return Noticia.objects.prefetch_related('imagenes')
        except:
            return Noticia.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            context['programas'] = ProgramaAcademico.objects.filter(
                is_active=True
            ).order_by('orden')[:10]
        except:
            context['programas'] = []
                
        return context

class PaginaDetailView(DetailView):
    model = Pagina
    template_name = 'web/pagina.html'
    context_object_name = 'pagina'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            context['programas'] = ProgramaAcademico.objects.filter(
                is_active=True
            ).order_by('orden')[:10]
        except:
            context['programas'] = []
                
        return context

class AdmisionView(TemplateView):
    template_name = 'web/admision.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Obtener todos los items activos de una sola consulta
            admisiones_activas = Admision.objects.filter(is_active=True)
            
            # Organizar por tipo para un acceso más fácil
            context['nuevos_estudiantes'] = admisiones_activas.filter(tipo=Admision.NUEVOS).first()
            context['antiguos_estudiantes'] = admisiones_activas.filter(tipo=Admision.ANTIGUOS).first()
            context['proceso_matricula'] = admisiones_activas.filter(tipo=Admision.P_MATRICULA).first()
            context['proceso_admision'] = admisiones_activas.filter(tipo=Admision.P_ADMISION).first()
            
            # También mantener la lista para compatibilidad
            context['admision_items'] = [
                context['nuevos_estudiantes'],
                context['antiguos_estudiantes'], 
                context['proceso_matricula'],
                context['proceso_admision']
            ]
        except:
            context['nuevos_estudiantes'] = None
            context['antiguos_estudiantes'] = None
            context['proceso_matricula'] = None
            context['proceso_admision'] = None
            context['admision_items'] = []
                        
        try:
            context['programas'] = ProgramaAcademico.objects.filter(
                is_active=True
            ).order_by('orden')[:10]
        except:
            context['programas'] = []
                
        return context

class ProgramasView(TemplateView):
    template_name = 'web/programas.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            context['programas'] = ProgramaAcademico.objects.filter(
                is_active=True
            ).prefetch_related('caracteristicas').order_by('orden')
        except:
            context['programas'] = []
                
        return context

class ProgramaDetailView(DetailView):
    model = ProgramaAcademico
    template_name = 'web/programa_detalle.html'
    context_object_name = 'programa'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            context['programas'] = ProgramaAcademico.objects.filter(
                is_active=True
            ).order_by('orden')[:10]
        except:
            context['programas'] = []
                
        return context
    
def custom_404_view(request, exception):
    return render(request, '404.html', status=404)

def custom_500_view(request):
    return render(request, '500.html', status=500)