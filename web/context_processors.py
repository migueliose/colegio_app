from .models import ProgramaAcademico

def programas_context(request):
    try:
        programas = ProgramaAcademico.objects.filter(
            is_active=True
        ).order_by('orden')[:10]
    except:
        programas = []
    
    return {
        'programas_navbar': programas
    }