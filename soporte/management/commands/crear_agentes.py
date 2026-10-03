"""Crea agentes de prueba (grupo "Agentes") con su token: python manage.py crear_agentes"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token

from cuentas.models import GRUPO_AGENTES

NOMBRES = ("ana", "luis")
CLAVE_DESARROLLO = "agente-dev-123"  # proyecto de demostración: credencial conocida a propósito


class Command(BaseCommand):
    help = "Crea los agentes de prueba ana y luis y muestra sus tokens"

    def handle(self, *args, **opciones):
        Usuario = get_user_model()
        agentes = Group.objects.get(name=GRUPO_AGENTES)
        for nombre in NOMBRES:
            usuario, creado = Usuario.objects.get_or_create(username=nombre)
            if creado:
                usuario.set_password(CLAVE_DESARROLLO)
                usuario.save()
            usuario.groups.add(agentes)
            token, _ = Token.objects.get_or_create(user=usuario)
            self.stdout.write(f"{nombre:<6} token: {token.key}")
