from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

GRUPO_AGENTES = "Agentes"  # se crea en la migración 0002_grupo_agentes


class UsuarioQuerySet(models.QuerySet):
    def agentes(self):
        return self.filter(is_active=True, groups__name=GRUPO_AGENTES)


class UsuarioManager(UserManager.from_queryset(UsuarioQuerySet)):
    """Manager con nombre propio: las migraciones no pueden serializar uno generado al vuelo."""


class Usuario(AbstractUser):
    """Usuario propio desde el principio, como recomienda Django.

    Permite añadir campos más adelante sin migrar el modelo de usuario con datos reales.
    Ser agente es pertenecer al grupo "Agentes"; is_staff queda solo para quien entra al admin.
    """

    objects = UsuarioManager()

    @property
    def es_agente(self) -> bool:
        return self.is_active and self.groups.filter(name=GRUPO_AGENTES).exists()
