"""Deja la demo lista: usuarios de prueba y, si no hay tickets, unos de ejemplo.

Se ejecuta en cada arranque del servicio web (compose.yaml) y se puede repetir sin duplicar nada:
los usuarios se crean con get_or_create y los tickets solo si la base de datos no tiene ninguno.
"""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from soporte.models import Estado, Prioridad, Ticket

TICKETS_EJEMPLO = [
    ("No puedo entrar al portal", "Al hacer login aparece un error 500.", Prioridad.ALTA),
    ("Factura duplicada", "Me han cobrado dos veces la cuota de septiembre.", Prioridad.MEDIA),
    ("Caída del servicio", "La API no responde desde las 10:00.", Prioridad.CRITICA),
    ("Cambiar el email de la cuenta", "Quiero usar otra dirección de correo.", Prioridad.BAJA),
    ("Exportar datos a CSV", "¿Se pueden descargar los informes en CSV?", Prioridad.BAJA),
]


class Command(BaseCommand):
    help = "Crea los usuarios de prueba y, si no hay tickets, tickets de ejemplo con historial"

    def handle(self, *args, **opciones):
        call_command("crear_agentes", stdout=self.stdout)
        if Ticket.objects.exists():
            self.stdout.write("Ya hay tickets: no se crean los de ejemplo.")
            return
        self._crear_tickets()
        self.stdout.write(f"Creados {len(TICKETS_EJEMPLO)} tickets de ejemplo.")

    @transaction.atomic
    def _crear_tickets(self):
        usuarios = get_user_model().objects.in_bulk(["ana", "luis", "sara"], field_name="username")
        ana, luis, sara = usuarios["ana"], usuarios["luis"], usuarios["sara"]
        portal, factura, caida, email, _ = (
            Ticket.objects.create(asunto=asunto, descripcion=descripcion, prioridad=prioridad)
            for asunto, descripcion, prioridad in TICKETS_EJEMPLO
        )
        # Los cambios pasan por los métodos del modelo, así queda historial real.
        caida.asignar(luis, autor=sara)
        caida.cambiar_estado(Estado.EN_PROGRESO, autor=luis)
        caida.comentarios.create(autor=luis, texto="Escalado a infraestructura.")
        portal.asignar(ana, autor=sara)
        factura.asignar(ana, autor=ana)
        factura.cambiar_estado(Estado.RESUELTO, autor=ana)
        factura.comentarios.create(autor=ana, texto="Devuelto el cargo duplicado.")
        email.cambiar_estado(Estado.CERRADO, autor=luis)
