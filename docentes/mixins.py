# docentes/mixins.py
from django.shortcuts import redirect
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib import messages
from usuarios.models import Docente

class DocenteRequiredMixin(UserPassesTestMixin):
    """Mixin para verificar que el usuario es docente"""
    
    def test_func(self):
        # Verificar si el usuario tiene un perfil de docente
        if not self.request.user.is_authenticated:
            return False
        
        try:
            # Importar aquí para evitar problemas de importación circular
            from usuarios.models import Docente
            
            # Verificar si existe un registro de Docente para este usuario
            return Docente.objects.filter(usuario=self.request.user).exists()
            
        except Exception as e:
            print(f"Error verificando perfil docente: {e}")
            return False
    
    def handle_no_permission(self):
        messages.error(self.request, 'No tiene permisos para acceder a esta sección.')
        return redirect('login')


class DocenteContextMixin:
    """Mixin para agregar el objeto Docente al contexto"""
    
    def get_docente(self):
        """Obtener el objeto Docente del usuario actual - MÉTODO SEGURO"""
        if not self.request.user.is_authenticated:
            return None
        
        try:
            from usuarios.models import Docente
            
            # Método SEGURO: Siempre obtener desde el modelo Docente
            docente = Docente.objects.filter(usuario=self.request.user).first()
            return docente
            
        except Exception as e:
            print(f"Error obteniendo docente: {e}")
            return None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['docente_obj'] = self.get_docente()
        return context
    
class DocenteBaseView(DocenteContextMixin):
    """Clase base que ya incluye DocenteContextMixin"""
    
    def get_docente(self):
        """Versión mejorada y segura para obtener docente"""
        if not self.request.user.is_authenticated:
            return None
        
        # Usamos siempre el método seguro
        try:
            return Docente.objects.filter(usuario=self.request.user).first()
        except:
            return None