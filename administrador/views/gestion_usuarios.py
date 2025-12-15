# views/gestion_usuarios.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.http import JsonResponse
from django.db import IntegrityError
from django.db.models import Q, Count
from django.core.paginator import Paginator

from usuarios.models import Usuario, TipoUsuario, TipoDocumento, Docente, ContactoDocente
from estudiantes.models import Estudiante, Acudiente,Matricula
from gestioncolegio.models import Colegio, Sede
from gestioncolegio.mixins import RoleRequiredMixin
from administrador.forms import *

# ========================
# VISTA PRINCIPAL DE GESTIÓN DE USUARIOS
# ========================

class GestionUsuariosView(RoleRequiredMixin, View):
    """Vista principal de gestión de usuarios"""
    template_name = 'administrador/gestion_usuarios/dashboard.html'
    allowed_roles = ['Administrador', 'Rector']
    
    def get(self, request):
        from django.db.models import Count, Q
        from gestioncolegio.models import AñoLectivo
        
        # Solo usuarios con tipo definido
        usuarios_con_tipo = Usuario.objects.filter(
            tipo_usuario__isnull=False,
            is_deleted=False
        ).select_related('tipo_usuario', 'tipo_documento')
        
        # Para evitar problemas, prefetch los perfiles relacionados
        usuarios_con_tipo = usuarios_con_tipo.prefetch_related(
            'docente_profile',
            'estudiante_profile'
        )
        
        # Estadísticas básicas
        total_usuarios = usuarios_con_tipo.count()
        usuarios_activos = usuarios_con_tipo.filter(estado=True).count()
        usuarios_inactivos = usuarios_con_tipo.filter(estado=False).count()
        
        # Por género
        usuarios_masculino = usuarios_con_tipo.filter(sexo='M').count()
        usuarios_femenino = usuarios_con_tipo.filter(sexo='F').count()
        usuarios_sin_genero = usuarios_con_tipo.filter(Q(sexo__isnull=True) | Q(sexo='')).count()
        
        # Últimos usuarios - solo 10 más recientes
        ultimos_usuarios = usuarios_con_tipo.order_by('-created_at')[:10]
        
        # Tipos de usuario
        tipos_usuario_data = []
        tipo_nombres = ['Administrador', 'Rector', 'Docente', 'Estudiante', 'Acudiente']
        
        for tipo_nombre in tipo_nombres:
            count = usuarios_con_tipo.filter(tipo_usuario__nombre=tipo_nombre).count()
            tipos_usuario_data.append({
                'nombre': tipo_nombre,
                'total_usuarios': count
            })
        
        # Estudiantes por nivel
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        estudiantes_preescolar = 0
        estudiantes_primaria = 0
        
        if año_actual:
            estudiantes_preescolar = Matricula.objects.filter(
                año_lectivo=año_actual,
                estado='ACT',
                grado_año_lectivo__grado__nivel_escolar__nombre='Preescolar'
            ).count()
            
            estudiantes_primaria = Matricula.objects.filter(
                año_lectivo=año_actual,
                estado='ACT',
                grado_año_lectivo__grado__nivel_escolar__nombre='Primaria'
            ).count()
        
        # Docentes con asignaciones
        docentes_con_asignaciones = Docente.objects.filter(
            is_deleted=False,
            asignaturas_dictadas__isnull=False
        ).distinct().count()
        
        # Estudiantes sin acudientes
        estudiantes_sin_acudientes = Estudiante.objects.filter(
            estado=True,
            is_deleted=False,
            acudientes__isnull=True
        ).count()
        
        context = {
            'tipos_usuario': tipos_usuario_data,
            'total_usuarios': total_usuarios,
            'usuarios_activos': usuarios_activos,
            'usuarios_inactivos': usuarios_inactivos,
            'usuarios_masculino': usuarios_masculino,
            'usuarios_femenino': usuarios_femenino,
            'usuarios_sin_genero': usuarios_sin_genero,
            'ultimos_usuarios': ultimos_usuarios,
            'estudiantes_preescolar': estudiantes_preescolar,
            'estudiantes_primaria': estudiantes_primaria,
            'docentes_con_asignaciones': docentes_con_asignaciones,
            'estudiantes_sin_acudientes': estudiantes_sin_acudientes,
            'año_actual': año_actual,
        }
        
        return render(request, self.template_name, context)
    
# ========================
# GESTIÓN DE DOCENTES
# ========================

class DocenteListView(RoleRequiredMixin, ListView):
    model = Docente
    template_name = 'administrador/docentes/docente_list.html'
    context_object_name = 'docentes'
    allowed_roles = ['Administrador', 'Rector']
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Docente.objects.select_related(
            'usuario',
            'usuario__tipo_usuario'
        ).filter(estado=True).order_by('usuario__apellidos', 'usuario__nombres')
        
        # Aplicar filtros
        search = self.request.GET.get('search')
        tipo_usuario = self.request.GET.get('tipo_usuario')
        
        if search:
            queryset = queryset.filter(
                Q(usuario__nombres__icontains=search) |
                Q(usuario__apellidos__icontains=search) |
                Q(usuario__numero_documento__icontains=search) |
                Q(usuario__email__icontains=search)
            )
        
        if tipo_usuario:
            queryset = queryset.filter(usuario__tipo_usuario_id=tipo_usuario)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tipos_usuario'] = TipoUsuario.objects.all()
        
        # Estadísticas
        total_docentes = self.get_queryset().count()
        context['total_docentes'] = total_docentes
        
        # Docentes activos (estado=True en Usuario)
        activos = self.get_queryset().filter(usuario__estado=True).count()
        context['docentes_activos'] = activos
        
        # Docentes por género
        masculino = self.get_queryset().filter(usuario__sexo='M').count()
        femenino = self.get_queryset().filter(usuario__sexo='F').count()
        context['docentes_masculino'] = masculino
        context['docentes_femenino'] = femenino
        
        # Docentes sin email
        sin_email = self.get_queryset().filter(
            Q(usuario__email__isnull=True) | Q(usuario__email='')
        ).count()
        context['docentes_sin_email'] = sin_email
        
        return context

class DocenteDetailView(RoleRequiredMixin, DetailView):
    model = Docente
    template_name = 'administrador/docentes/docente_detail.html'
    context_object_name = 'docente'
    allowed_roles = ['Administrador', 'Rector', 'Docente']
    
    def get_object(self):
        return get_object_or_404(
            Docente.objects.select_related(
                'usuario', 
                'usuario__tipo_documento',
                'usuario__tipo_usuario'
            ),
            pk=self.kwargs['pk']
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        docente = self.object
        
        # Obtener contactos del docente
        context['contactos'] = docente.contactos.all()
        
        # Obtener año lectivo actual
        try:
            config = ConfiguracionGeneral.objects.first()
            año_actual = config.año_lectivo_actual if config else None
        except:
            año_actual = None
        
        # Obtener asignaturas que dicta (filtrado por año actual si existe)
        asignaturas_query = docente.asignaturas_dictadas.all().select_related(
            'asignatura', 
            'grado_año_lectivo__grado',
            'grado_año_lectivo__año_lectivo',
            'sede'
        )
        
        if año_actual:
            asignaturas_query = asignaturas_query.filter(
                grado_año_lectivo__año_lectivo=año_actual
            )
        
        context['asignaturas'] = asignaturas_query
        context['total_horas_semanales'] = self.calcular_horas_semanales(asignaturas_query)
        
        # Obtener sedes asignadas (filtrado por año actual)
        sedes_query = docente.sedes_asignadas.all().select_related(
            'sede', 
            'año_lectivo'
        )
        
        if año_actual:
            sedes_query = sedes_query.filter(año_lectivo=año_actual)
        
        context['sedes_asignadas'] = sedes_query
        
        # Obtener horarios del docente
        context['horarios'] = self.obtener_horarios_docente(docente)
        
        # Obtener comportamientos registrados por el docente
        context['comportamientos_registrados'] = docente.comportamientos_registrados.all()\
            .select_related('estudiante__usuario', 'periodo_academico__periodo')\
            .order_by('-created_at')[:10]
        
        # Obtener estadísticas del docente
        context['estadisticas'] = self.calcular_estadisticas(docente)
        
        # Obtener años lectivos disponibles para filtrar
        context['años_lectivos'] = AñoLectivo.objects.all().order_by('-anho')
        context['año_actual'] = año_actual
        
        # Obtener última asistencia si hay registro
        context['ultima_asistencia'] = self.obtener_ultima_asistencia(docente)
        
        return context
    
    def calcular_horas_semanales(self, asignaturas):
        """Calcular total de horas semanales que dicta el docente"""
        total_horas = 0
        
        for asignatura in asignaturas:
            # Asumimos que cada asignatura tiene una intensidad horaria semanal
            # Puedes ajustar según tu modelo
            try:
                # Si la asignatura tiene campo ih (intensidad horaria)
                if asignatura.asignatura.ih and asignatura.asignatura.ih.isdigit():
                    total_horas += int(asignatura.asignatura.ih)
            except:
                pass
        
        return total_horas
    
    def obtener_horarios_docente(self, docente):
        """Obtener horarios del docente"""
        try:
            from academico.models import HorarioClase
            return HorarioClase.objects.filter(
                asignatura_grado__docente=docente
            ).select_related(
                'asignatura_grado__asignatura',
                'asignatura_grado__grado_año_lectivo__grado',
                'asignatura_grado__sede'
            ).order_by('dia_semana', 'hora_inicio')
        except:
            return []
    
    def calcular_estadisticas(self, docente):
        """Calcular estadísticas del docente"""
        from comportamiento.models import Comportamiento
        from estudiantes.models import Nota
        
        estadisticas = {}
        
        # Total de comportamientos registrados
        estadisticas['total_comportamientos'] = docente.comportamientos_registrados.count()
        estadisticas['comportamientos_positivos'] = docente.comportamientos_registrados.filter(
            tipo='Positivo'
        ).count()
        estadisticas['comportamientos_negativos'] = docente.comportamientos_registrados.filter(
            tipo='Negativo'
        ).count()
        
        # Notas registradas por el docente
        # (Necesitarías un campo que relacione notas con docente)
        
        # Años de experiencia (basado en primera asignación)
        primera_asignacion = docente.sedes_asignadas.order_by('fecha_asignacion').first()
        if primera_asignacion:
            from datetime import date
            hoy = date.today()
            experiencia = hoy.year - primera_asignacion.fecha_asignacion.year
            if (hoy.month, hoy.day) < (primera_asignacion.fecha_asignacion.month, 
                                      primera_asignacion.fecha_asignacion.day):
                experiencia -= 1
            estadisticas['años_experiencia'] = experiencia
        else:
            estadisticas['años_experiencia'] = 0
        
        # Estudiantes bajo su responsabilidad actual
        try:
            estudiantes_actuales = set()
            for asignatura in docente.asignaturas_dictadas.all():
                matriculas = asignatura.grado_año_lectivo.matriculas.filter(estado='ACT')
                for matricula in matriculas:
                    estudiantes_actuales.add(matricula.estudiante.id)
            
            estadisticas['estudiantes_actuales'] = len(estudiantes_actuales)
        except:
            estadisticas['estudiantes_actuales'] = 0
        
        return estadisticas
    
    def obtener_ultima_asistencia(self, docente):
        """Obtener última asistencia registrada"""
        # Esto asume que tienes un modelo de asistencia para docentes
        # Si no, puedes omitir esta función
        try:
            from comportamiento.models import AsistenciaDocente
            return AsistenciaDocente.objects.filter(
                docente=docente
            ).order_by('-fecha').first()
        except:
            return None

class DocenteCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    model = Usuario
    form_class = DocenteForm
    template_name = 'administrador/docentes/docente_form.html'
    success_url = reverse_lazy('administrador:docente_list')
    success_message = "Docente creado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Nuevo Docente'
        context['submit_text'] = 'Crear Docente'
        context['tipos_documento'] = TipoDocumento.objects.all()
        return context
    
    def form_valid(self, form):
        try:
            # Primero crear/obtener el usuario
            numero_documento = form.cleaned_data['numero_documento']
            
            # Verificar si el usuario ya existe
            usuario_existente = Usuario.objects.filter(numero_documento=numero_documento).first()
            
            if usuario_existente:
                # Verificar si ya es docente
                if hasattr(usuario_existente, 'docente_profile'):
                    form.add_error('numero_documento', 'Este usuario ya tiene perfil de docente.')
                    return self.form_invalid(form)
                
                # Actualizar datos del usuario existente
                usuario_existente.tipo_usuario = TipoUsuario.objects.get(nombre='Docente')
                usuario_existente.nombres = form.cleaned_data['nombres']
                usuario_existente.apellidos = form.cleaned_data['apellidos']
                usuario_existente.email = form.cleaned_data['email']
                usuario_existente.telefono = form.cleaned_data['telefono']
                usuario_existente.direccion = form.cleaned_data['direccion']
                usuario_existente.sexo = form.cleaned_data['sexo']
                usuario_existente.fecha_nacimiento = form.cleaned_data['fecha_nacimiento']
                
                # Actualizar contraseña si se proporcionó
                password = form.cleaned_data.get('password')
                if password:
                    usuario_existente.set_password(password)
                
                usuario_existente.save()
                usuario = usuario_existente
            else:
                # Crear nuevo usuario
                usuario = form.save(commit=False)
                usuario.username = form.cleaned_data.get('username', f"doc_{numero_documento}")
                usuario.tipo_usuario = TipoUsuario.objects.get(nombre='Docente')
                usuario.save()
            
            # Crear perfil de docente
            Docente.objects.create(
                usuario=usuario,
                estado=True
            )
            
            return super().form_valid(form)
            
        except Exception as e:
            messages.error(self.request, f'Error al crear docente: {str(e)}')
            return self.form_invalid(form)

class DocenteUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Docente
    form_class = DocenteForm
    template_name = 'administrador/docentes/docente_form.html'
    success_url = reverse_lazy('administrador:docente_list')
    success_message = "Docente actualizado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object.usuario
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Docente'
        context['submit_text'] = 'Actualizar Docente'
        context['tipos_documento'] = TipoDocumento.objects.all()
        return context
    
    def form_valid(self, form):
        try:
            usuario = self.object.usuario
            usuario.nombres = form.cleaned_data['nombres']
            usuario.apellidos = form.cleaned_data['apellidos']
            usuario.email = form.cleaned_data['email']
            usuario.telefono = form.cleaned_data['telefono']
            usuario.direccion = form.cleaned_data['direccion']
            usuario.sexo = form.cleaned_data['sexo']
            usuario.fecha_nacimiento = form.cleaned_data['fecha_nacimiento']
            
            # Actualizar contraseña si se proporcionó
            password = form.cleaned_data.get('password')
            if password:
                usuario.set_password(password)
            
            usuario.save()
            return super().form_valid(form)
            
        except Exception as e:
            messages.error(self.request, f'Error al actualizar docente: {str(e)}')
            return self.form_invalid(form)

class DocenteDeleteView(RoleRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Docente
    template_name = 'administrador/docentes/docente_confirm_delete.html'
    success_url = reverse_lazy('administrador:docente_list')
    success_message = "Docente desactivado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def delete(self, request, *args, **kwargs):
        try:
            docente = self.get_object()
            # Desactivar usuario y docente
            docente.usuario.estado = False
            docente.usuario.save()
            docente.estado = False
            docente.save()
            
            messages.success(self.request, self.success_message)
            return redirect(self.success_url)
        except Exception as e:
            messages.error(request, f'Error al desactivar docente: {str(e)}')
            return redirect(self.success_url)

class ContactoDocenteCreateView(RoleRequiredMixin, CreateView):
    """Crear contacto de emergencia para docente"""
    model = ContactoDocente
    template_name = 'administrador/docentes/contacto_form.html'
    fields = ['nombres', 'apellidos', 'telefono', 'email', 'relacion']
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        docente_id = self.kwargs.get('docente_pk')
        context['docente'] = get_object_or_404(Docente, id=docente_id)
        return context
    
    def form_valid(self, form):
        docente_id = self.kwargs.get('docente_pk')
        docente = get_object_or_404(Docente, id=docente_id)
        form.instance.docente = docente
        messages.success(self.request, 'Contacto agregado exitosamente.')
        return super().form_valid(form)
    
    def get_success_url(self):
        docente_id = self.kwargs.get('docente_pk')
        return reverse_lazy('administrador:docente_detail', kwargs={'pk': docente_id})

class ContactoDocenteUpdateView(RoleRequiredMixin, UpdateView):
    """Editar contacto de emergencia"""
    model = ContactoDocente
    template_name = 'administrador/docentes/contacto_form.html'
    fields = ['nombres', 'apellidos', 'telefono', 'email', 'relacion']
    allowed_roles = ['Administrador', 'Rector']
    
    def get_success_url(self):
        return reverse_lazy('administrador:docente_detail', kwargs={'pk': self.object.docente.pk})

class ContactoDocenteDeleteView(RoleRequiredMixin, DeleteView):
    """Eliminar contacto de emergencia"""
    model = ContactoDocente
    template_name = 'administrador/docentes/contacto_confirm_delete.html'
    allowed_roles = ['Administrador', 'Rector']
    
    def get_success_url(self):
        return reverse_lazy('administrador:docente_detail', kwargs={'pk': self.object.docente.pk})
    
# ========================
# GESTIÓN DE ESTUDIANTES
# ========================

class EstudianteListView(RoleRequiredMixin, ListView):
    model = Estudiante
    template_name = 'administrador/estudiantes/estudiante_list.html'
    context_object_name = 'estudiantes'
    allowed_roles = ['Administrador', 'Rector']
    paginate_by = 15
    
    def get_queryset(self):
        # Incluir todos los estudiantes (activos e inactivos) pero ordenados
        queryset = Estudiante.objects.select_related(
            'usuario',
            'usuario__tipo_usuario',
            'usuario__tipo_documento',
        ).order_by('usuario__apellidos', 'usuario__nombres')
        
        # Aplicar filtros desde la URL
        search = self.request.GET.get('search')
        estado_matricula = self.request.GET.get('estado_matricula')
        tipo_documento = self.request.GET.get('tipo_documento')
        grado = self.request.GET.get('grado')
        genero = self.request.GET.get('genero')
        estado_usuario = self.request.GET.get('estado')
        
        # Filtro por búsqueda general
        if search:
            queryset = queryset.filter(
                Q(usuario__nombres__icontains=search) |
                Q(usuario__apellidos__icontains=search) |
                Q(usuario__numero_documento__icontains=search) |
                Q(usuario__email__icontains=search)
            )
        
        # Filtro por estado de matrícula
        if estado_matricula:
            from gestioncolegio.models import AñoLectivo
            año_actual = AñoLectivo.objects.filter(estado=True).first()
            
            if estado_matricula == 'sin-matricula':
                # Estudiantes SIN matrícula en el año actual
                if año_actual:
                    queryset = queryset.exclude(
                        matriculas__año_lectivo=año_actual
                    )
                else:
                    # Si no hay año actual, mostrar todos
                    queryset = queryset
            elif año_actual:
                if estado_matricula == 'ACT':
                    queryset = queryset.filter(
                        matriculas__año_lectivo=año_actual,
                        matriculas__estado='ACT'
                    )
                elif estado_matricula == 'PEN':
                    queryset = queryset.filter(
                        matriculas__año_lectivo=año_actual,
                        matriculas__estado='PEN'
                    )
                elif estado_matricula == 'INA':
                    queryset = queryset.filter(
                        matriculas__año_lectivo=año_actual,
                        matriculas__estado='INA'
                    )
        
        # Filtro por tipo de documento
        if tipo_documento:
            queryset = queryset.filter(usuario__tipo_documento__nombre__icontains=tipo_documento)
        
        # Filtro por género
        if genero:
            queryset = queryset.filter(usuario__sexo=genero)
        
        # Filtro por grado (nivel escolar)
        if grado:
            from gestioncolegio.models import AñoLectivo
            año_actual = AñoLectivo.objects.filter(estado=True).first()
            
            if año_actual:
                if grado == 'preescolar':
                    queryset = queryset.filter(
                        matriculas__año_lectivo=año_actual,
                        matriculas__grado_año_lectivo__grado__nivel_escolar__nombre='Preescolar'
                    )
                elif grado == 'primaria':
                    queryset = queryset.filter(
                        matriculas__año_lectivo=año_actual,
                        matriculas__grado_año_lectivo__grado__nivel_escolar__nombre='Primaria'
                    )
        
        # Filtro por estado del usuario/estudiante
        if estado_usuario:
            if estado_usuario == 'activo':
                # Estudiantes con usuario Y perfil activos
                queryset = queryset.filter(
                    usuario__estado=True,
                    estado=True
                )
            elif estado_usuario == 'inactivo':
                # Estudiantes con usuario O perfil inactivos
                queryset = queryset.filter(
                    Q(usuario__estado=False) | Q(estado=False)
                ).distinct()
        
        return queryset.distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pasar parámetros de filtro al contexto para mantenerlos en los formularios
        context['filtros'] = {
            'search': self.request.GET.get('search', ''),
            'estado_matricula': self.request.GET.get('estado_matricula', ''),
            'tipo_documento': self.request.GET.get('tipo_documento', ''),
            'grado': self.request.GET.get('grado', ''),
            'genero': self.request.GET.get('genero', ''),
            'estado': self.request.GET.get('estado', ''),
        }
        
        # Obtener año lectivo actual para usarlo en la plantilla
        from gestioncolegio.models import AñoLectivo
        año_actual = AñoLectivo.objects.filter(estado=True).first()
        context['año_lectivo_actual'] = año_actual
        
        # Estadísticas basadas en los filtros aplicados
        queryset = self.get_queryset()
        context['total_estudiantes'] = queryset.count()
        
        # Estudiantes por género
        context['estudiantes_masculino'] = queryset.filter(usuario__sexo='M').count()
        context['estudiantes_femenino'] = queryset.filter(usuario__sexo='F').count()
        
        # Estudiantes matriculados en el año actual
        if año_actual:
            # Estudiantes con matrícula ACTIVA en el año actual
            context['matriculados_actual'] = queryset.filter(
                matriculas__año_lectivo=año_actual,
                matriculas__estado='ACT'
            ).distinct().count()
            
            # Estudiantes sin matrícula en el año actual
            context['sin_matricula_actual'] = queryset.exclude(
                matriculas__año_lectivo=año_actual
            ).count()
            
            # Estudiantes con matrícula pendiente
            context['pendientes_actual'] = queryset.filter(
                matriculas__año_lectivo=año_actual,
                matriculas__estado='PEN'
            ).distinct().count()
        else:
            context['matriculados_actual'] = 0
            context['sin_matricula_actual'] = queryset.count()
            context['pendientes_actual'] = 0
        
        # Estudiantes sin acudientes registrados
        context['sin_acudientes'] = queryset.filter(
            acudientes__isnull=True
        ).count()
        
        # Estudiantes activos vs inactivos
        context['estudiantes_activos'] = queryset.filter(
            usuario__estado=True,
            estado=True
        ).count()
        
        context['estudiantes_inactivos'] = queryset.filter(
            Q(usuario__estado=False) | Q(estado=False)
        ).distinct().count()
        
        # Edad promedio
        from datetime import date
        today = date.today()
        edades = []
        
        for estudiante in queryset:
            if estudiante.usuario.fecha_nacimiento:
                fecha_nac = estudiante.usuario.fecha_nacimiento
                edad = today.year - fecha_nac.year
                if today.month < fecha_nac.month or \
                   (today.month == fecha_nac.month and today.day < fecha_nac.day):
                    edad -= 1
                edades.append(edad)
        
        if edades:
            context['edad_promedio'] = round(sum(edades) / len(edades), 1)
        else:
            context['edad_promedio'] = 0
        
        # Para mostrar en los filtros
        from usuarios.models import TipoDocumento
        context['tipos_documento'] = TipoDocumento.objects.all()
        
        return context
    
class EstudianteDetailView(RoleRequiredMixin, DetailView):
    model = Estudiante
    template_name = 'administrador/estudiantes/estudiante_detail.html'
    context_object_name = 'estudiante'
    allowed_roles = ['Administrador', 'Rector']
    
    def get_object(self):
        return get_object_or_404(
            Estudiante.objects.select_related(
                'usuario', 
                'usuario__tipo_documento',
                'usuario__tipo_usuario'
            ).prefetch_related(
                'acudientes__acudiente',
                'matriculas',
                'notas'
            ),
            pk=self.kwargs['pk']
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante = self.object
        
        # Obtener año lectivo actual
        try:
            config = ConfiguracionGeneral.objects.first()
            if config and config.año_lectivo_actual:
                año_actual = config.año_lectivo_actual
            else:
                # Fallback: buscar el año lectivo activo más reciente
                año_actual = AñoLectivo.objects.filter(estado=True).order_by('-anho').first()
        except:
            año_actual = estudiante.matricula_actual.año_lectivo if estudiante.matricula_actual else None
        
        # === INFORMACIÓN BÁSICA ===
        context['año_actual'] = año_actual
        
        # === ACUDIENTES ===
        context['acudientes'] = estudiante.acudientes.all().select_related(
            'acudiente', 'acudiente__tipo_documento'
        )
        
        # === MATRÍCULAS ===
        context['matricula_actual'] = estudiante.matricula_actual
        context['matriculas_anteriores'] = estudiante.matriculas_anteriores()
        context['matriculas_pendientes'] = estudiante.matriculas.filter(estado='PEN')
        
        # === NOTAS Y RENDIMIENTO ===
        notas = estudiante.get_notas_completas()
        context['notas'] = notas
        context['estadisticas_notas'] = self.calcular_estadisticas_notas(notas)
        context['notas_recientes'] = notas[:10] if notas else []
        
        # === COMPORTAMIENTO ===
        from comportamiento.models import Comportamiento
        context['comportamientos'] = Comportamiento.objects.filter(
            estudiante=estudiante
        ).select_related(
            'periodo_academico__periodo',
            'periodo_academico__año_lectivo',
            'docente__usuario'
        ).order_by('-fecha')[:10]
        
        context['estadisticas_comportamiento'] = self.calcular_estadisticas_comportamiento(estudiante)
        
        # === ASISTENCIAS ===
        from comportamiento.models import Asistencia
        asistencias_query = Asistencia.objects.filter(estudiante=estudiante)
        context['asistencias_recientes'] = asistencias_query.order_by('-fecha')[:10]
        context['estadisticas_asistencia'] = self.calcular_estadisticas_asistencia(asistencias_query)
        
        # === INCONSISTENCIAS Y OBSERVACIONES ===
        from comportamiento.models import Inconsistencia
        context['inconsistencias'] = Inconsistencia.objects.filter(
            estudiante=estudiante
        ).order_by('-fecha')[:5]
        
        # === HISTORIAL ACADÉMICO COMPLETO ===
        context['historial_academico'] = self.obtener_historial_completo(estudiante)
        
        # === HORARIOS ACTUALES ===
        context['horarios'] = self.obtener_horarios(estudiante)
        
        # === LOGROS Y RECONOCIMIENTOS ===
        from academico.models import Logro
        context['logros'] = Logro.objects.filter(
            grado__in=estudiante.matriculas.values_list('grado_año_lectivo__grado', flat=True)
        ).select_related('asignatura', 'grado')[:5]
        
        # === DOCUMENTOS Y ARCHIVOS ===
        context['documentos_estudiante'] = self.obtener_documentos(estudiante)
        
        # === ESTADÍSTICAS AVANZADAS ===
        context['estadisticas_avanzadas'] = self.calcular_estadisticas_avanzadas(estudiante)
        
        # === DATOS PARA GRÁFICOS ===
        context['datos_graficos'] = self.preparar_datos_graficos(estudiante)
        
        # === ACCIONES RÁPIDAS DISPONIBLES ===
        context['acciones_disponibles'] = self.obtener_acciones_disponibles(estudiante)
        
        # === ÚLTIMAS ACTIVIDADES ===
        context['ultimas_actividades'] = self.obtener_ultimas_actividades(estudiante)
        
        return context
    
    def calcular_estadisticas_notas(self, notas):
        """Calcular estadísticas detalladas de notas"""
        if not notas:
            return {
                'promedio_general': 0,
                'total_notas': 0,
                'aprobadas': 0,
                'reprobadas': 0,
                'mejor_nota': 0,
                'peor_nota': 0,
                'desviacion': 0,
                'rendimiento': 'Sin datos'
            }
        
        calificaciones = [float(n.calificacion) for n in notas]
        promedio = sum(calificaciones) / len(calificaciones)
        aprobadas = sum(1 for c in calificaciones if c >= 3.0)
        reprobadas = len(calificaciones) - aprobadas
        
        # Calcular desviación estándar
        import math
        varianza = sum((c - promedio) ** 2 for c in calificaciones) / len(calificaciones)
        desviacion = math.sqrt(varianza)
        
        # Determinar nivel de rendimiento
        if promedio >= 4.0:
            rendimiento = 'Excelente'
            color = 'success'
        elif promedio >= 3.5:
            rendimiento = 'Bueno'
            color = 'info'
        elif promedio >= 3.0:
            rendimiento = 'Regular'
            color = 'warning'
        else:
            rendimiento = 'Bajo'
            color = 'danger'
        
        return {
            'promedio_general': round(promedio, 2),
            'total_notas': len(notas),
            'aprobadas': aprobadas,
            'reprobadas': reprobadas,
            'porcentaje_aprobacion': round((aprobadas / len(notas) * 100), 1),
            'mejor_nota': round(max(calificaciones), 1),
            'peor_nota': round(min(calificaciones), 1),
            'desviacion': round(desviacion, 2),
            'rendimiento': rendimiento,
            'color_rendimiento': color,
        }
    
    def calcular_estadisticas_comportamiento(self, estudiante):
        """Estadísticas detalladas de comportamiento"""
        from comportamiento.models import Comportamiento
        from django.db.models import Count
        
        comportamientos = Comportamiento.objects.filter(estudiante=estudiante)
        
        if not comportamientos.exists():
            return {
                'total': 0,
                'positivos': 0,
                'negativos': 0,
                'ratio': '0/0',
                'tendencia': 'Sin datos'
            }
        
        total = comportamientos.count()
        positivos = comportamientos.filter(tipo='Positivo').count()
        negativos = comportamientos.filter(tipo='Negativo').count()
        
        # Comportamiento por categoría
        por_categoria = comportamientos.values('categoria').annotate(
            total=Count('id'),
            positivos=Count('id', filter=Q(tipo='Positivo')),
            negativos=Count('id', filter=Q(tipo='Negativo'))
        ).order_by('-total')
        
        # Tendencia (últimos 30 días vs anteriores)
        from django.utils import timezone
        from datetime import timedelta
        
        ultimo_mes = timezone.now() - timedelta(days=30)
        comportamientos_recientes = comportamientos.filter(fecha__gte=ultimo_mes)
        comportamientos_anteriores = comportamientos.filter(fecha__lt=ultimo_mes)
        
        ratio_reciente = comportamientos_recientes.filter(tipo='Positivo').count() / max(comportamientos_recientes.count(), 1)
        ratio_anterior = comportamientos_anteriores.filter(tipo='Positivo').count() / max(comportamientos_anteriores.count(), 1)
        
        if ratio_reciente > ratio_anterior + 0.1:
            tendencia = 'Mejorando'
            color_tendencia = 'success'
        elif ratio_reciente < ratio_anterior - 0.1:
            tendencia = 'Empeorando'
            color_tendencia = 'danger'
        else:
            tendencia = 'Estable'
            color_tendencia = 'info'
        
        return {
            'total': total,
            'positivos': positivos,
            'negativos': negativos,
            'ratio_positivos': round((positivos / total * 100), 1),
            'ratio_negativos': round((negativos / total * 100), 1),
            'por_categoria': list(por_categoria),
            'tendencia': tendencia,
            'color_tendencia': color_tendencia,
        }
    
    def calcular_estadisticas_asistencia(self, asistencias_query):
        """Estadísticas avanzadas de asistencia"""
        if not asistencias_query.exists():
            return {
                'total': 0,
                'asistencias': 0,
                'faltas': 0,
                'justificadas': 0,
                'porcentaje': 0,
                'tendencia': 'Sin datos'
            }
        
        total = asistencias_query.count()
        asistencias = asistencias_query.filter(estado='A').count()
        faltas = asistencias_query.filter(estado='F').count()
        justificadas = asistencias_query.filter(estado='J').count()
        
        # Tendencia por mes
        from django.db.models.functions import TruncMonth
        from django.db.models import Count, Case, When, FloatField
        
        tendencia_mensual = asistencias_query.annotate(
            mes=TruncMonth('fecha')
        ).values('mes').annotate(
            total_mes=Count('id'),
            presentes_mes=Count('id', filter=Q(estado='A')),
            porcentaje_mes=Count('id', filter=Q(estado='A')) * 100.0 / Count('id')
        ).order_by('-mes')[:3]
        
        # Determinar tendencia
        if len(tendencia_mensual) >= 2:
            ultimo = tendencia_mensual[0]['porcentaje_mes']
            anterior = tendencia_mensual[1]['porcentaje_mes']
            
            if ultimo > anterior + 5:
                tendencia = 'Mejorando'
                color_tendencia = 'success'
            elif ultimo < anterior - 5:
                tendencia = 'Empeorando'
                color_tendencia = 'danger'
            else:
                tendencia = 'Estable'
                color_tendencia = 'info'
        else:
            tendencia = 'Sin datos suficientes'
            color_tendencia = 'secondary'
        
        return {
            'total': total,
            'asistencias': asistencias,
            'faltas': faltas,
            'justificadas': justificadas,
            'porcentaje': round((asistencias / total * 100), 1),
            'tendencia': tendencia,
            'color_tendencia': color_tendencia,
            'tendencia_mensual': list(tendencia_mensual),
        }
    
    def obtener_historial_completo(self, estudiante):
        """Obtener historial académico completo organizado"""
        historial = {}
        
        # Agrupar por año lectivo
        for matricula in estudiante.matriculas.all().select_related(
            'grado_año_lectivo__grado',
            'año_lectivo'
        ):
            año = matricula.año_lectivo.anho
            grado = matricula.grado_año_lectivo.grado.nombre
            
            if año not in historial:
                historial[año] = {
                    'grado': grado,
                    'matricula': matricula,
                    'notas': [],
                    'comportamientos': [],
                    'asistencias': [],
                }
        
        # Agregar notas a cada año
        notas = estudiante.notas.all().select_related(
            'asignatura_grado_año_lectivo__asignatura',
            'periodo_academico__periodo',
            'periodo_academico__año_lectivo'
        )
        
        for nota in notas:
            año = nota.periodo_academico.año_lectivo.anho
            if año in historial:
                historial[año]['notas'].append(nota)
        
        return historial
    
    def obtener_horarios(self, estudiante):
        """Obtener horarios actuales del estudiante"""
        if not estudiante.matricula_actual:
            return []
        
        from academico.models import HorarioClase
        
        return HorarioClase.objects.filter(
            asignatura_grado__grado_año_lectivo=estudiante.matricula_actual.grado_año_lectivo,
            asignatura_grado__sede=estudiante.matricula_actual.sede
        ).select_related(
            'asignatura_grado__asignatura',
            'asignatura_grado__docente__usuario'
        ).order_by('dia_semana', 'hora_inicio')
    
    def obtener_documentos(self, estudiante):
        """Obtener documentos relacionados con el estudiante"""
        from django.urls import reverse
        documentos = []
        
        # Constancias de años matriculados
        for año_str in estudiante.años_matriculados:
            # Buscar el año lectivo por su año (string)
            año_lectivo = AñoLectivo.objects.filter(anho=año_str).first()
            if año_lectivo:
                documentos.append({
                    'tipo': 'Constancia',
                    'nombre': f'Constancia de Estudio {año_str}',
                    'año': año_str,
                    'url': reverse('administrador:constancia_pdf', 
                                kwargs={
                                    'estudiante_id': estudiante.id,
                                    'año_lectivo_id': año_lectivo.id
                                }),
                    'icono': 'fa-file-certificate',
                    'color': 'primary'
                })

                documentos.append({
                'tipo': 'Boletín',
                'nombre': 'Boletín de Calificaciones',
                'año': año_lectivo.anho,
                'url': reverse('administrador:boletin_pdf',
                            kwargs={
                                'estudiante_id': estudiante.id,
                                'año_lectivo_id': año_lectivo.id
                            }),
                'icono': 'fa-chart-bar',
                'color': 'success'
                }),

                documentos.append({
                'tipo': 'Observador',
                'nombre': f'Observador {año_lectivo.anho}',
                'año': año_lectivo.anho,
                'url': reverse('administrador:observador_pdf',
                            kwargs={
                                'estudiante_id': estudiante.id,
                                'año_lectivo_id': año_lectivo.id
                            }),
                'icono': 'fa-clipboard-list',
                'color': 'warning'
                })
        
        # Observador del año actual
        if estudiante.matricula_actual:
            año_actual = estudiante.matricula_actual.año_lectivo
            documentos.append({
                'tipo': 'Observador',
                'nombre': f'Observador {año_actual.anho}',
                'año': año_actual.anho,
                'url': reverse('administrador:observador_pdf',
                            kwargs={
                                'estudiante_id': estudiante.id,
                                'año_lectivo_id': año_actual.id
                            }),
                'icono': 'fa-clipboard-list',
                'color': 'warning'
            })
        
        # Boletín de notas (año actual)
        if estudiante.matricula_actual:
            año_actual = estudiante.matricula_actual.año_lectivo
            documentos.append({
                'tipo': 'Boletín',
                'nombre': 'Boletín de Calificaciones',
                'año': año_actual.anho,
                'url': reverse('administrador:boletin_pdf',
                            kwargs={
                                'estudiante_id': estudiante.id,
                                'año_lectivo_id': año_actual.id
                            }),
                'icono': 'fa-chart-bar',
                'color': 'success'
            })
        
        return documentos
    
    def calcular_estadisticas_avanzadas(self, estudiante):
        """Calcular estadísticas avanzadas para panel de control"""
        from django.db.models import Avg, Count, Q
        from datetime import datetime
        
        estadisticas = {}
        
        # Edad y años en la institución
        if estudiante.usuario.fecha_nacimiento:
            hoy = datetime.now().date()
            edad = hoy.year - estudiante.usuario.fecha_nacimiento.year
            if (hoy.month, hoy.day) < (estudiante.usuario.fecha_nacimiento.month, 
                                      estudiante.usuario.fecha_nacimiento.day):
                edad -= 1
            estadisticas['edad'] = edad
        
        # Años en la institución
        años_matriculados = estudiante.años_matriculados
        if años_matriculados:
            estadisticas['años_institucion'] = len(años_matriculados)
            estadisticas['primer_año'] = min(años_matriculados)
            estadisticas['ultimo_año'] = max(años_matriculados)
        
        # Promedio histórico
        notas = estudiante.get_notas_completas()
        if notas:
            promedios_por_año = {}
            for nota in notas:
                año = nota.periodo_academico.año_lectivo.anho
                if año not in promedios_por_año:
                    promedios_por_año[año] = {'suma': 0, 'count': 0}
                promedios_por_año[año]['suma'] += float(nota.calificacion)
                promedios_por_año[año]['count'] += 1
            
            # Calcular evolución
            evolucion = []
            for año, datos in sorted(promedios_por_año.items()):
                evolucion.append({
                    'año': año,
                    'promedio': round(datos['suma'] / datos['count'], 2)
                })
            estadisticas['evolucion_academica'] = evolucion
        
        # Riesgo académico
        if notas:
            notas_recientes = notas.filter(
                periodo_academico__año_lectivo__estado=True
            )[:20]  # Últimas 20 notas
            
            if notas_recientes:
                promedio_reciente = notas_recientes.aggregate(
                    promedio=Avg('calificacion')
                )['promedio'] or 0
                
                if promedio_reciente < 3.0:
                    estadisticas['riesgo'] = 'Alto'
                    estadisticas['color_riesgo'] = 'danger'
                elif promedio_reciente < 3.5:
                    estadisticas['riesgo'] = 'Medio'
                    estadisticas['color_riesgo'] = 'warning'
                else:
                    estadisticas['riesgo'] = 'Bajo'
                    estadisticas['color_riesgo'] = 'success'
        
        return estadisticas
    
    def preparar_datos_graficos(self, estudiante):
        """Preparar todos los datos para gráficos"""
        datos = {
            'rendimiento': self.preparar_grafico_rendimiento(estudiante),
            'asistencia': self.preparar_grafico_asistencia(estudiante),
            'comportamiento': self.preparar_grafico_comportamiento(estudiante),
        }
        return datos
    
    def preparar_grafico_rendimiento(self, estudiante):
        """Gráfico de rendimiento académico por periodo"""
        notas = estudiante.get_notas_completas()
        
        if not notas:
            return None
        
        # Agrupar por periodo
        datos_periodo = {}
        for nota in notas:
            key = f"{nota.periodo_academico.periodo.nombre} {nota.periodo_academico.año_lectivo.anho}"
            if key not in datos_periodo:
                datos_periodo[key] = {'suma': 0, 'count': 0}
            datos_periodo[key]['suma'] += float(nota.calificacion)
            datos_periodo[key]['count'] += 1
        
        # Preparar datos
        labels = []
        promedios = []
        
        for periodo, datos in sorted(datos_periodo.items()):
            labels.append(periodo)
            promedio = datos['suma'] / datos['count']
            promedios.append(round(promedio, 2))
        
        return {
            'labels': labels,
            'datasets': [{
                'label': 'Promedio por Periodo',
                'data': promedios,
                'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                'borderColor': 'rgba(54, 162, 235, 1)',
                'borderWidth': 2,
                'tension': 0.1
            }]
        }
    
    def preparar_grafico_asistencia(self, estudiante):
        """Gráfico de asistencia por mes"""
        from comportamiento.models import Asistencia
        from django.db.models.functions import TruncMonth
        
        asistencias = Asistencia.objects.filter(
            estudiante=estudiante
        ).annotate(
            mes=TruncMonth('fecha')
        ).values('mes').annotate(
            total=Count('id'),
            presentes=Count('id', filter=Q(estado='A')),
            porcentaje=Count('id', filter=Q(estado='A')) * 100.0 / Count('id')
        ).order_by('mes')[:12]
        
        if not asistencias:
            return None
        
        labels = []
        porcentajes = []
        
        meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        
        for item in asistencias:
            fecha = item['mes']
            mes_nombre = meses[fecha.month - 1]
            labels.append(f"{mes_nombre} {fecha.year}")
            porcentajes.append(round(item['porcentaje'], 1))
        
        return {
            'labels': labels,
            'datasets': [{
                'label': 'Asistencia %',
                'data': porcentajes,
                'backgroundColor': 'rgba(76, 175, 80, 0.2)',
                'borderColor': 'rgba(76, 175, 80, 1)',
                'borderWidth': 2,
                'fill': True
            }]
        }
    
    def preparar_grafico_comportamiento(self, estudiante):
        """Gráfico de comportamiento por categoría"""
        from comportamiento.models import Comportamiento
        from django.db.models import Count
        
        comportamientos = Comportamiento.objects.filter(
            estudiante=estudiante
        ).values('categoria').annotate(
            positivos=Count('id', filter=Q(tipo='Positivo')),
            negativos=Count('id', filter=Q(tipo='Negativo'))
        ).order_by('categoria')
        
        if not comportamientos:
            return None
        
        labels = []
        datos_positivos = []
        datos_negativos = []
        
        for item in comportamientos:
            labels.append(dict(Comportamiento.CATEGORIAS).get(item['categoria'], item['categoria']))
            datos_positivos.append(item['positivos'])
            datos_negativos.append(item['negativos'])
        
        return {
            'labels': labels,
            'datasets': [
                {
                    'label': 'Positivos',
                    'data': datos_positivos,
                    'backgroundColor': 'rgba(76, 175, 80, 0.5)',
                    'borderColor': 'rgba(76, 175, 80, 1)',
                },
                {
                    'label': 'Negativos',
                    'data': datos_negativos,
                    'backgroundColor': 'rgba(244, 67, 54, 0.5)',
                    'borderColor': 'rgba(244, 67, 54, 1)',
                }
            ]
        }
    
    def obtener_acciones_disponibles(self, estudiante):
        """Obtener lista de acciones administrativas disponibles"""
        acciones = []
        
        # Acciones básicas
        acciones.append({
            'nombre': 'Editar Información',
            'url': reverse_lazy('administrador:estudiante_update', kwargs={'pk': estudiante.pk}),
            'icono': 'fas fa-edit',
            'color': 'warning',
            'descripcion': 'Modificar datos personales'
        })
        
        # Matrículas
        if not estudiante.matricula_actual:
            acciones.append({
                'nombre': 'Crear Matrícula',
                'url': f"{reverse_lazy('administrador:matricula_create')}?estudiante_id={estudiante.pk}",
                'icono': 'fas fa-user-plus',
                'color': 'primary',
                'descripcion': 'Matricular para año actual'
            })
        
        # Acudientes
        acciones.append({
            'nombre': 'Gestionar Acudientes',
            'url': f"{reverse_lazy('administrador:acudiente_create')}?estudiante_id={estudiante.pk}",
            'icono': 'fas fa-user-friends',
            'color': 'info',
            'descripcion': 'Agregar/editar acudientes'
        })
        
        # Documentos
        if estudiante.matricula_actual:
            acciones.append({
                'nombre': 'Generar Documentos',
                'url': reverse_lazy('administrador:documentos_estudiante', kwargs={'estudiante_id': estudiante.pk}),
                'icono': 'fas fa-file-pdf',
                'color': 'danger',
                'descripcion': 'Constancias, boletines, etc.'
            })
        
        # Historial
        acciones.append({
            'nombre': 'Ver Historial Completo',
            'url': reverse_lazy('administrador:estudiante_historial_academico', kwargs={'pk': estudiante.pk}),
            'icono': 'fas fa-history',
            'color': 'secondary',
            'descripcion': 'Historial académico completo'
        })
        # Documentos
        acciones.append({
                'nombre': 'Generar Documentos',
                'url': reverse_lazy('administrador:documentos_estudiante', kwargs={'estudiante_id': estudiante.pk}),
                'icono': 'fas fa-file-pdf',
                'color': 'danger',
                'descripcion': 'Constancias, boletines, etc.'
            })
                
        return acciones
    
    def obtener_ultimas_actividades(self, estudiante):
        """Obtener últimas actividades del estudiante"""
        actividades = []
        
        # Últimas notas
        notas = estudiante.get_notas_completas()[:3]
        for nota in notas:
            actividades.append({
                'fecha': nota.updated_at,
                'tipo': 'nota',
                'descripcion': f'Calificación en {nota.asignatura_grado_año_lectivo.asignatura.nombre}: {nota.calificacion}',
                'icono': 'fas fa-star',
                'color': 'warning'
            })
        
        # Últimos comportamientos
        from comportamiento.models import Comportamiento
        comportamientos = Comportamiento.objects.filter(
            estudiante=estudiante
        ).order_by('-created_at')[:3]
        
        for comp in comportamientos:
            actividades.append({
                'fecha': comp.created_at,
                'tipo': 'comportamiento',
                'descripcion': f'{comp.tipo}: {comp.descripcion[:50]}...',
                'icono': 'fas fa-clipboard-check',
                'color': 'success' if comp.tipo == 'Positivo' else 'danger'
            })
        
        # Ordenar por fecha
        actividades.sort(key=lambda x: x['fecha'], reverse=True)
        
        return actividades[:10]  # Solo las 10 más recientes

class EstudianteCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    model = Usuario
    form_class = EstudianteForm
    template_name = 'administrador/estudiantes/estudiante_form.html'
    success_url = reverse_lazy('administrador:estudiante_list')
    success_message = "Estudiante creado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Nuevo Estudiante'
        context['submit_text'] = 'Crear Estudiante'
        context['tipos_documento'] = TipoDocumento.objects.all()
        return context
    
    def form_valid(self, form):
        try:
            # Primero crear/obtener el usuario
            numero_documento = form.cleaned_data['numero_documento']
            
            # Verificar si el usuario ya existe
            usuario_existente = Usuario.objects.filter(numero_documento=numero_documento).first()
            
            if usuario_existente:
                # Verificar si ya es estudiante
                if hasattr(usuario_existente, 'estudiante_profile'):
                    form.add_error('numero_documento', 'Este usuario ya tiene perfil de estudiante.')
                    return self.form_invalid(form)
                
                # Actualizar datos del usuario existente
                usuario_existente.tipo_usuario = TipoUsuario.objects.get(nombre='Estudiante')
                usuario_existente.nombres = form.cleaned_data['nombres']
                usuario_existente.apellidos = form.cleaned_data['apellidos']
                usuario_existente.email = form.cleaned_data['email']
                usuario_existente.telefono = form.cleaned_data['telefono']
                usuario_existente.direccion = form.cleaned_data['direccion']
                usuario_existente.sexo = form.cleaned_data['sexo']
                usuario_existente.fecha_nacimiento = form.cleaned_data['fecha_nacimiento']
                
                # Actualizar contraseña si se proporcionó
                password = form.cleaned_data.get('password')
                if password:
                    usuario_existente.set_password(password)
                
                usuario_existente.save()
                usuario = usuario_existente
            else:
                # Crear nuevo usuario
                usuario = form.save(commit=False)
                usuario.username = form.cleaned_data.get('username', f"est_{numero_documento}")
                usuario.tipo_usuario = TipoUsuario.objects.get(nombre='Estudiante')
                usuario.save()
            
            # Crear perfil de estudiante
            Estudiante.objects.create(
                usuario=usuario,
                estado=True
            )
            
            return super().form_valid(form)
            
        except Exception as e:
            messages.error(self.request, f'Error al crear estudiante: {str(e)}')
            return self.form_invalid(form)

class EstudianteUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Estudiante
    form_class = EstudianteForm
    template_name = 'administrador/estudiantes/estudiante_form.html'
    success_url = reverse_lazy('administrador:estudiante_list')
    success_message = "Estudiante actualizado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object.usuario
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Estudiante'
        context['submit_text'] = 'Actualizar Estudiante'
        context['tipos_documento'] = TipoDocumento.objects.all()
        return context
    
    def form_valid(self, form):
        try:
            usuario = self.object.usuario
            usuario.nombres = form.cleaned_data['nombres']
            usuario.apellidos = form.cleaned_data['apellidos']
            usuario.email = form.cleaned_data['email']
            usuario.telefono = form.cleaned_data['telefono']
            usuario.direccion = form.cleaned_data['direccion']
            usuario.sexo = form.cleaned_data['sexo']
            usuario.fecha_nacimiento = form.cleaned_data['fecha_nacimiento']
            
            # Actualizar contraseña si se proporcionó
            password = form.cleaned_data.get('password')
            if password:
                usuario.set_password(password)
            
            usuario.save()
            return super().form_valid(form)
            
        except Exception as e:
            messages.error(self.request, f'Error al actualizar estudiante: {str(e)}')
            return self.form_invalid(form)

class EstudianteDeleteView(RoleRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Estudiante
    template_name = 'administrador/estudiantes/estudiante_confirm_delete.html'
    success_url = reverse_lazy('administrador:estudiante_list')
    success_message = "Estudiante desactivado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def delete(self, request, *args, **kwargs):
        try:
            estudiante = self.get_object()
            # Desactivar usuario y estudiante
            estudiante.usuario.estado = False
            estudiante.usuario.save()
            estudiante.estado = False
            estudiante.save()
            
            messages.success(self.request, self.success_message)
            return redirect(self.success_url)
        except Exception as e:
            messages.error(request, f'Error al desactivar estudiante: {str(e)}')
            return redirect(self.success_url)

class EstudianteStatusView(View):
    """Vista AJAX para obtener estado del estudiante"""
    allowed_roles = ['Administrador', 'Rector']
    
    def get(self, request, pk):
        estudiante = get_object_or_404(Estudiante, pk=pk)
        
        data = {
            'status': 'active' if estudiante.usuario.estado else 'inactive',
            'matricula_activa': estudiante.matricula_actual is not None,
            'estudiante_id': estudiante.pk,
            'nombre_completo': estudiante.usuario.get_full_name(),
            'estado_usuario': estudiante.usuario.estado,
            'estado_estudiante': estudiante.estado
        }
        
        return JsonResponse(data)
    
# ========================
# GESTIÓN DE ACUDIENTES
# ========================

class AcudienteListView(RoleRequiredMixin, ListView):
    model = Acudiente
    template_name = 'administrador/acudientes/acudiente_list.html'
    context_object_name = 'acudientes'
    allowed_roles = ['Administrador', 'Rector']
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Acudiente.objects.select_related(
            'acudiente',
            'estudiante',
            'estudiante__usuario'
        ).order_by('acudiente__apellidos', 'acudiente__nombres')
        
        # Aplicar filtros
        search = self.request.GET.get('search')
        parentesco = self.request.GET.get('parentesco')
        
        if search:
            queryset = queryset.filter(
                Q(acudiente__nombres__icontains=search) |
                Q(acudiente__apellidos__icontains=search) |
                Q(acudiente__numero_documento__icontains=search) |
                Q(estudiante__usuario__nombres__icontains=search) |
                Q(estudiante__usuario__apellidos__icontains=search)
            )
        
        if parentesco:
            queryset = queryset.filter(parentesco__icontains=parentesco)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas
        total_acudientes = self.get_queryset().count()
        context['total_acudientes'] = total_acudientes
        
        # Acudientes por parentesco común
        context['padres'] = self.get_queryset().filter(parentesco__icontains='padre').count()
        context['madres'] = self.get_queryset().filter(parentesco__icontains='madre').count()
        context['abuelos'] = self.get_queryset().filter(parentesco__icontains='abuel').count()
        context['tios'] = self.get_queryset().filter(parentesco__icontains='tío').count()
        
        # Estudiantes sin acudientes
        from estudiantes.models import Estudiante
        estudiantes_sin_acudiente = Estudiante.objects.filter(
            estado=True,
            acudientes__isnull=True
        ).count()
        context['estudiantes_sin_acudiente'] = estudiantes_sin_acudiente
        
        return context

class AcudienteDetailView(RoleRequiredMixin, DetailView):
    model = Acudiente
    template_name = 'administrador/acudientes/acudiente_detail.html'
    context_object_name = 'acudiente'
    allowed_roles = ['Administrador', 'Rector']
    
    def get_object(self):
        return get_object_or_404(
            Acudiente.objects.select_related(
                'acudiente',
                'acudiente__tipo_documento',
                'estudiante',
                'estudiante__usuario'
            ),
            pk=self.kwargs['pk']
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener otros estudiantes a cargo (si los tiene)
        context['otros_estudiantes'] = Acudiente.objects.filter(
            acudiente=self.object.acudiente
        ).exclude(pk=self.object.pk).select_related('estudiante', 'estudiante__usuario')
        
        return context

class AcudienteCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    model = Acudiente
    form_class = AcudienteForm
    template_name = 'administrador/acudientes/acudiente_form.html'
    success_url = reverse_lazy('administrador:acudiente_list')
    success_message = "Acudiente creado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Nueva Relación de Acudiente'
        context['submit_text'] = 'Crear Relación'
        context['estudiantes'] = Estudiante.objects.filter(estado=True).select_related('usuario')
        context['tipos_documento'] = TipoDocumento.objects.all()
        return context
    
    def form_valid(self, form):
        try:
            crear_nuevo = form.cleaned_data.get('crear_nuevo_usuario', False)
            
            if crear_nuevo:
                # Crear nuevo usuario acudiente
                nuevo_numero_documento = form.cleaned_data['nuevo_numero_documento']
                
                # Verificar si ya existe
                usuario_existente = Usuario.objects.filter(numero_documento=nuevo_numero_documento).first()
                
                if usuario_existente:
                    # Usar usuario existente
                    usuario = usuario_existente
                    # Actualizar tipo de usuario si es necesario
                    if not usuario.tipo_usuario or usuario.tipo_usuario.nombre != 'Acudiente':
                        usuario.tipo_usuario = TipoUsuario.objects.get(nombre='Acudiente')
                        usuario.save()
                else:
                    # Crear nuevo usuario
                    usuario = Usuario.objects.create(
                        username=f"acu_{nuevo_numero_documento}",
                        numero_documento=nuevo_numero_documento,
                        tipo_documento=form.cleaned_data['nuevo_tipo_documento'],
                        nombres=form.cleaned_data['nuevo_nombres'],
                        apellidos=form.cleaned_data['nuevo_apellidos'],
                        email=form.cleaned_data['nuevo_email'],
                        telefono=form.cleaned_data['nuevo_telefono'],
                        tipo_usuario=TipoUsuario.objects.get(nombre='Acudiente')
                    )
                    
                    # Establecer contraseña
                    password = form.cleaned_data.get('nuevo_password')
                    if password:
                        usuario.set_password(password)
                    else:
                        # Contraseña por defecto: documento
                        usuario.set_password(nuevo_numero_documento)
                    
                    usuario.save()
                
                # Asignar el usuario creado al formulario
                form.instance.acudiente = usuario
            else:
                # Usar usuario existente seleccionado
                usuario = form.cleaned_data['acudiente']
                # Actualizar tipo de usuario si es necesario
                if not usuario.tipo_usuario or usuario.tipo_usuario.nombre != 'Acudiente':
                    usuario.tipo_usuario = TipoUsuario.objects.get(nombre='Acudiente')
                    usuario.save()
            
            return super().form_valid(form)
            
        except Exception as e:
            messages.error(self.request, f'Error al crear acudiente: {str(e)}')
            return self.form_invalid(form)

class AcudienteUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Acudiente
    form_class = AcudienteForm
    template_name = 'administrador/acudientes/acudiente_form.html'
    success_url = reverse_lazy('administrador:acudiente_list')
    success_message = "Acudiente actualizado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Inicializar campos de nuevo usuario como vacíos en modo edición
        kwargs['initial'] = {
            'crear_nuevo_usuario': False
        }
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Relación de Acudiente'
        context['submit_text'] = 'Actualizar Relación'
        context['estudiantes'] = Estudiante.objects.filter(estado=True).select_related('usuario')
        context['tipos_documento'] = TipoDocumento.objects.all()
        return context
    
    def form_valid(self, form):
        try:
            # En modo edición, siempre usamos el usuario existente
            form.instance.acudiente = form.cleaned_data['acudiente']
            
            # Actualizar tipo de usuario si es necesario
            usuario = form.instance.acudiente
            if not usuario.tipo_usuario or usuario.tipo_usuario.nombre != 'Acudiente':
                usuario.tipo_usuario = TipoUsuario.objects.get(nombre='Acudiente')
                usuario.save()
            
            return super().form_valid(form)
            
        except Exception as e:
            messages.error(self.request, f'Error al actualizar acudiente: {str(e)}')
            return self.form_invalid(form)

class AcudienteDeleteView(RoleRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Acudiente
    template_name = 'administrador/acudientes/acudiente_confirm_delete.html'
    success_url = reverse_lazy('administrador:acudiente_list')
    success_message = "Acudiente eliminado exitosamente"
    allowed_roles = ['Administrador', 'Rector']
    
    def delete(self, request, *args, **kwargs):
        try:
            acudiente = self.get_object()
            # Verificar si es el único acudiente del estudiante
            estudiantes_acudientes = Acudiente.objects.filter(
                estudiante=acudiente.estudiante
            ).count()
            
            if estudiantes_acudientes <= 1:
                messages.warning(request, 
                    f"El estudiante {acudiente.estudiante.usuario.get_full_name()} "
                    f"quedará sin acudientes registrados."
                )
            
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            messages.error(request, f'Error al eliminar acudiente: {str(e)}')
            return redirect(self.success_url)

# ========================
# VISTAS AJAX
# ========================

class VerificarUsuarioView(RoleRequiredMixin, View):
    allowed_roles = ['Administrador', 'Rector']
    
    def get(self, request):
        numero_documento = request.GET.get('numero_documento')
        tipo_usuario = request.GET.get('tipo_usuario')
        
        if not numero_documento:
            return JsonResponse({'error': 'Número de documento requerido'}, status=400)
        
        try:
            usuario = Usuario.objects.filter(numero_documento=numero_documento).first()
            
            if usuario:
                # Verificar si ya tiene el tipo de usuario solicitado
                if tipo_usuario == 'Docente' and hasattr(usuario, 'docente_profile'):
                    return JsonResponse({
                        'existe': True,
                        'usuario': {
                            'nombres': usuario.nombres,
                            'apellidos': usuario.apellidos,
                            'email': usuario.email,
                            'telefono': usuario.telefono,
                            'direccion': usuario.direccion,
                            'sexo': usuario.sexo,
                            'fecha_nacimiento': str(usuario.fecha_nacimiento) if usuario.fecha_nacimiento else None,
                            'tipo_documento_id': usuario.tipo_documento_id,
                            'ya_es_tipo': True
                        },
                        'mensaje': 'Este usuario ya tiene perfil de docente.'
                    })
                elif tipo_usuario == 'Estudiante' and hasattr(usuario, 'estudiante_profile'):
                    return JsonResponse({
                        'existe': True,
                        'usuario': {
                            'nombres': usuario.nombres,
                            'apellidos': usuario.apellidos,
                            'email': usuario.email,
                            'telefono': usuario.telefono,
                            'direccion': usuario.direccion,
                            'sexo': usuario.sexo,
                            'fecha_nacimiento': str(usuario.fecha_nacimiento) if usuario.fecha_nacimiento else None,
                            'tipo_documento_id': usuario.tipo_documento_id,
                            'ya_es_tipo': True
                        },
                        'mensaje': 'Este usuario ya tiene perfil de estudiante.'
                    })
                else:
                    # Usuario existe pero no tiene ese perfil específico
                    return JsonResponse({
                        'existe': True,
                        'usuario': {
                            'nombres': usuario.nombres,
                            'apellidos': usuario.apellidos,
                            'email': usuario.email,
                            'telefono': usuario.telefono,
                            'direccion': usuario.direccion,
                            'sexo': usuario.sexo,
                            'fecha_nacimiento': str(usuario.fecha_nacimiento) if usuario.fecha_nacimiento else None,
                            'tipo_documento_id': usuario.tipo_documento_id,
                            'tipo_usuario_actual': usuario.tipo_usuario.nombre if usuario.tipo_usuario else None
                        },
                        'mensaje': 'Usuario encontrado en el sistema.'
                    })
            else:
                return JsonResponse({
                    'existe': False,
                    'mensaje': 'Usuario no encontrado. Puede crear uno nuevo.'
                })
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

class BuscarEstudianteView(RoleRequiredMixin, View):
    allowed_roles = ['Administrador', 'Rector']
    
    def get(self, request):
        query = request.GET.get('q', '')
        
        if not query or len(query) < 2:
            return JsonResponse({'estudiantes': []})
        
        estudiantes = Estudiante.objects.filter(
            estado=True
        ).filter(
            Q(usuario__nombres__icontains=query) |
            Q(usuario__apellidos__icontains=query) |
            Q(usuario__numero_documento__icontains=query)
        ).select_related('usuario')[:10]
        
        data = []
        for estudiante in estudiantes:
            data.append({
                'id': estudiante.pk,
                'text': f"{estudiante.usuario.get_full_name()} - {estudiante.usuario.numero_documento}",
                'nombre_completo': estudiante.usuario.get_full_name(),
                'documento': estudiante.usuario.numero_documento
            })
        
        return JsonResponse({'estudiantes': data})

# ========================
# GESTIÓN DE ADMINISTRADORES/RECTORES
# ========================

class AdministradorListView(RoleRequiredMixin, ListView):
    model = Usuario
    template_name = 'administrador/administradores/administrador_list.html'
    context_object_name = 'administradores'
    allowed_roles = ['Administrador']
    
    def get_queryset(self):
        return Usuario.objects.filter(
            tipo_usuario__nombre__in=['Administrador', 'Rector']
        ).select_related('tipo_usuario').order_by('tipo_usuario__nombre', 'apellidos', 'nombres')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas
        context['total_administradores'] = self.get_queryset().filter(
            tipo_usuario__nombre='Administrador'
        ).count()
        
        context['total_rectores'] = self.get_queryset().filter(
            tipo_usuario__nombre='Rector'
        ).count()
        
        context['total_activos'] = self.get_queryset().filter(estado=True).count()
        
        return context

class AdministradorCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    model = Usuario
    form_class = AdministradorForm
    template_name = 'administrador/administradores/administrador_form.html'
    success_url = reverse_lazy('administrador:administrador_list')
    success_message = "Administrador/Rector creado exitosamente"
    allowed_roles = ['Administrador']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Nuevo Administrador/Rector'
        context['submit_text'] = 'Crear'
        context['tipos_documento'] = TipoDocumento.objects.all()
        return context
    
    def form_valid(self, form):
        try:
            usuario = form.save(commit=False)
            usuario.username = form.cleaned_data.get('username', f"admin_{usuario.numero_documento}")
            usuario.save()
            return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, f'Error al crear administrador: {str(e)}')
            return self.form_invalid(form)

class AdministradorUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Usuario
    form_class = AdministradorForm
    template_name = 'administrador/administradores/administrador_form.html'
    success_url = reverse_lazy('administrador:administrador_list')
    success_message = "Administrador/Rector actualizado exitosamente"
    allowed_roles = ['Administrador']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Administrador/Rector'
        context['submit_text'] = 'Actualizar'
        context['tipos_documento'] = TipoDocumento.objects.all()
        return context
    
    def form_valid(self, form):
        try:
            usuario = form.save(commit=False)
            
            # Actualizar contraseña si se proporcionó
            password = form.cleaned_data.get('password')
            if password:
                usuario.set_password(password)
            
            usuario.save()
            return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, f'Error al actualizar administrador: {str(e)}')
            return self.form_invalid(form)

class AdministradorDeleteView(RoleRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Usuario
    template_name = 'administrador/administradores/administrador_confirm_delete.html'
    success_url = reverse_lazy('administrador:administrador_list')
    success_message = "Administrador/Rector desactivado exitosamente"
    allowed_roles = ['Administrador']
    
    def delete(self, request, *args, **kwargs):
        try:
            usuario = self.get_object()
            
            # No permitir desactivarse a sí mismo
            if usuario == request.user:
                messages.error(request, 'No puede desactivar su propio usuario.')
                return redirect(self.success_url)
            
            usuario.estado = False
            usuario.save()
            
            messages.success(self.request, self.success_message)
            return redirect(self.success_url)
        except Exception as e:
            messages.error(request, f'Error al desactivar administrador: {str(e)}')
            return redirect(self.success_url)
        
class BuscarUsuarioView(RoleRequiredMixin, View):
    """Buscar cualquier usuario (no solo estudiantes)"""
    allowed_roles = ['Administrador', 'Rector']
    
    def get(self, request):
        query = request.GET.get('q', '')
        
        if not query or len(query) < 2:
            return JsonResponse({'usuarios': []})
        
        # Buscar en todos los usuarios
        usuarios = Usuario.objects.filter(
            Q(nombres__icontains=query) |
            Q(apellidos__icontains=query) |
            Q(numero_documento__icontains=query)
        ).select_related('tipo_usuario', 'tipo_documento')[:10]
        
        data = []
        for usuario in usuarios:
            data.append({
                'id': usuario.pk,
                'text': f"{usuario.get_full_name()} - {usuario.numero_documento} ({usuario.tipo_usuario.nombre if usuario.tipo_usuario else 'Sin tipo'})",
                'nombre_completo': usuario.get_full_name(),
                'documento': usuario.numero_documento,
                'tipo_usuario': usuario.tipo_usuario.nombre if usuario.tipo_usuario else None,
                'email': usuario.email,
                'telefono': usuario.telefono
            })
        
        return JsonResponse({'usuarios': data})