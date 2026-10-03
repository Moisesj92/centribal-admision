"""Migración de datos: el grupo "Agentes" debe existir en cualquier base de datos (también en la de tests)."""

from django.db import migrations

GRUPO_AGENTES = "Agentes"  # copia literal: las migraciones no deben importar código que pueda cambiar


def crear_grupo(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name=GRUPO_AGENTES)


def borrar_grupo(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name=GRUPO_AGENTES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cuentas", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(crear_grupo, borrar_grupo)]
