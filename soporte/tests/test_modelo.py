"""Reglas del modelo, incluida la concurrencia (dos peticiones que leen el mismo ticket a la vez)."""

from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from soporte.models import ConflictoConcurrente, Estado, Ticket
from soporte.tests.utils import crear_agente


class ConcurrenciaTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ana = crear_agente("ana")
        cls.luis = crear_agente("luis")

    def setUp(self):
        self.ticket = Ticket.objects.create(asunto="VPN", descripcion="No conecta")

    def dos_lecturas(self):
        """Simula dos peticiones simultáneas: cada una con su propia copia del ticket."""
        return Ticket.objects.get(pk=self.ticket.pk), Ticket.objects.get(pk=self.ticket.pk)

    def test_un_cerrado_no_se_reabre_aunque_la_peticion_lo_leyera_abierto(self):
        a, b = self.dos_lecturas()
        a.cambiar_estado(Estado.CERRADO, self.ana)
        with self.assertRaises(ConflictoConcurrente):
            b.cambiar_estado(Estado.EN_PROGRESO, self.luis)  # b todavía "ve" abierto
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.estado, Estado.CERRADO)
        self.assertEqual(self.ticket.historial.count(), 1)  # el intento fallido no deja rastro

    def test_no_se_asigna_un_ticket_cerrado_entretanto(self):
        a, b = self.dos_lecturas()
        a.cambiar_estado(Estado.CERRADO, self.ana)
        with self.assertRaises(ConflictoConcurrente):
            b.asignar(self.luis, self.ana)
        self.ticket.refresh_from_db()
        self.assertIsNone(self.ticket.agente)

    def test_dos_asignaciones_a_la_vez_gana_la_primera(self):
        a, b = self.dos_lecturas()
        a.asignar(self.ana, self.ana)
        with self.assertRaises(ConflictoConcurrente):
            b.asignar(self.luis, self.luis)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.agente, self.ana)

    def test_sin_conflicto_actualiza_el_objeto_en_memoria(self):
        self.ticket.cambiar_estado(Estado.EN_PROGRESO, self.ana)
        self.assertEqual(self.ticket.estado, Estado.EN_PROGRESO)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.estado, Estado.EN_PROGRESO)


class ConflictoEnInterfacesTest(TestCase):
    """La API responde 409 y la web muestra un aviso, sin error 500."""

    @classmethod
    def setUpTestData(cls):
        cls.ana = crear_agente("ana")
        cls.ticket = Ticket.objects.create(asunto="VPN", descripcion="No conecta")

    conflicto = mock.patch.object(
        Ticket, "_actualizar_si_no_cambio", side_effect=ConflictoConcurrente("El ticket cambió mientras tanto.")
    )

    def test_api_responde_409(self):
        cliente = APIClient()
        cliente.force_authenticate(self.ana)
        with self.conflicto:
            respuesta = cliente.patch(f"/api/tickets/{self.ticket.pk}/estado/", {"estado": "cerrado"}, format="json")
        self.assertEqual(respuesta.status_code, 409)
        self.assertIn("cambió", respuesta.data["detail"])

    def test_web_muestra_aviso(self):
        self.client.force_login(self.ana)
        with self.conflicto:
            respuesta = self.client.post(f"/tickets/{self.ticket.pk}/estado/", {"estado": "cerrado"}, follow=True)
        self.assertContains(respuesta, "cambió mientras tanto")
        self.assertContains(respuesta, 'class="mensaje error"')
