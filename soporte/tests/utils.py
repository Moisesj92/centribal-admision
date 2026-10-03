from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from cuentas.models import GRUPO_AGENTES


def crear_agente(nombre: str):
    """Usuario del grupo "Agentes" (el grupo lo crea la migración de datos de cuentas)."""
    usuario = get_user_model().objects.create_user(nombre, password="x")
    usuario.groups.add(Group.objects.get(name=GRUPO_AGENTES))
    return usuario
