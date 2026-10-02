"""Crea agentes de prueba (is_staff) con su token: python manage.py crear_agentes"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token

AGENTES = ("ana", "luis")
CLAVE_DESARROLLO = "agente-dev-123"  # solo para el entorno local


class Command(BaseCommand):
    help = "Crea los agentes de prueba ana y luis y muestra sus tokens"

    def handle(self, *args, **opciones):
        Usuario = get_user_model()
        for nombre in AGENTES:
            usuario, creado = Usuario.objects.get_or_create(username=nombre, defaults={"is_staff": True})
            if creado:
                usuario.set_password(CLAVE_DESARROLLO)
                usuario.save()
            token, _ = Token.objects.get_or_create(user=usuario)
            self.stdout.write(f"{nombre:<6} token: {token.key}")
