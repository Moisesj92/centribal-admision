"""Crea los usuarios de prueba con su token: python manage.py crear_agentes

- ana, luis: agentes (web y API).
- sara: agente y además staff (supervisora): entra al admin con permisos acotados.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token

from cuentas.models import GRUPO_AGENTES

CLAVE_DESARROLLO = "agente-dev-123"  # proyecto de demostración: credencial conocida a propósito

# nombre → es staff
USUARIOS = {"ana": False, "luis": False, "sara": True}

# is_staff solo deja ENTRAR al admin; lo que ve y puede hacer depende de estos permisos.
PERMISOS_SUPERVISION = [
    "soporte.view_ticket",
    "soporte.change_ticket",  # asunto, descripción y prioridad (estado y agente son de solo lectura)
    "soporte.view_comentario",
    "soporte.view_historial",
]


class Command(BaseCommand):
    help = "Crea los agentes de prueba (ana, luis) y la supervisora (sara, staff) y muestra sus tokens"

    def handle(self, *args, **opciones):
        Usuario = get_user_model()
        agentes = Group.objects.get(name=GRUPO_AGENTES)
        supervision = [
            Permission.objects.get(content_type__app_label=app, codename=codigo)
            for app, codigo in (permiso.split(".") for permiso in PERMISOS_SUPERVISION)
        ]
        for nombre, es_staff in USUARIOS.items():
            usuario, creado = Usuario.objects.get_or_create(username=nombre)
            if creado:
                usuario.set_password(CLAVE_DESARROLLO)
            usuario.is_staff = es_staff
            usuario.save()
            usuario.groups.add(agentes)
            if es_staff:
                usuario.user_permissions.add(*supervision)
            token, _ = Token.objects.get_or_create(user=usuario)
            rol = "agente + staff" if es_staff else "agente"
            self.stdout.write(f"{nombre:<6} {rol:<15} token: {token.key}")
