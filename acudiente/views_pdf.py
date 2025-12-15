# acudiente/views_pdf.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import View
from django.core.exceptions import PermissionDenied
from estudiantes.models import  Acudiente

class AcudientePermissionMixin:
    """Mixin para verificar que el acudiente tiene permiso para ver el estudiante"""
    
    def dispatch(self, request, *args, **kwargs):
        estudiante_id = kwargs.get('estudiante_id')
        
        # Verificar que el usuario es acudiente del estudiante
        if not Acudiente.objects.filter(
            acudiente=request.user,
            estudiante_id=estudiante_id
        ).exists():
            raise PermissionDenied("No tiene permiso para acceder a este estudiante")
        
        return super().dispatch(request, *args, **kwargs)

class RedirigirConstanciaPDFView(AcudientePermissionMixin, View):
    """Redirige a la vista de constancia PDF de estudiantes"""
    
    def get(self, request, *args, **kwargs):
        estudiante_id = kwargs.get('estudiante_id')
        año_lectivo_id = kwargs.get('año_lectivo_id')
        
        return redirect('estudiantes:estudiante_constancia_año_admin', 
                       estudiante_id=estudiante_id, 
                       año_lectivo_id=año_lectivo_id)

class RedirigirObservadorPDFView(AcudientePermissionMixin, View):
    """Redirige a la vista de observador PDF de estudiantes"""
    
    def get(self, request, *args, **kwargs):
        estudiante_id = kwargs.get('estudiante_id')
        año_lectivo_id = kwargs.get('año_lectivo_id')
        
        return redirect('estudiantes:estudiante_observador_año_admin', 
                       estudiante_id=estudiante_id, 
                       año_lectivo_id=año_lectivo_id)

class RedirigirReporteNotasPDFView(AcudientePermissionMixin, View):
    """Redirige a la vista de reporte de notas (boletín) PDF de estudiantes"""
    
    def get(self, request, *args, **kwargs):
        estudiante_id = kwargs.get('estudiante_id')
        año_lectivo_id = kwargs.get('año_lectivo_id')
        
        return redirect('estudiantes:estudiante_boletin_final_año_admin', 
                       estudiante_id=estudiante_id, 
                       año_lectivo_id=año_lectivo_id)

# También puedes mantener un alias por compatibilidad
RedirigirBoletinPDFView = RedirigirReporteNotasPDFView