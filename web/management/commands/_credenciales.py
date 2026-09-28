# management/commands/_credenciales.py
"""
Lectura de credenciales desde variables de entorno (.env).
Las contraseñas NUNCA deben escribirse en el código fuente.
"""
from decouple import config
from django.core.management.base import CommandError


def env_requerida(nombre):
    """Devuelve el valor de la variable de entorno o detiene el comando."""
    valor = config(nombre, default='')
    if not valor:
        raise CommandError(
            f"Falta la variable de entorno '{nombre}'. Defínala en el archivo .env "
            f"(vea .env.example)."
        )
    return valor


def superadmin_username():
    return config('SUPERADMIN_USERNAME', default='admin')
