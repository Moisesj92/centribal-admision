from django.contrib.auth import get_user_model
from django.test import TestCase

from soporte.models import Ticket
from soporte.tests.utils import crear_agente


class AdminAuditoriaTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser("admin", password="x")
        agente = crear_agente("ana")
        cls.ticket = Ticket.objects.create(asunto="VPN", descripcion="No conecta")
        cls.ticket.cambiar_estado("en_progreso", agente)
        cls.comentario = cls.ticket.comentarios.create(autor=agente, texto="original")

    def setUp(self):
        self.client.force_login(self.admin)

    def test_no_se_borran_tickets(self):
        self.assertEqual(self.client.get(f"/admin/soporte/ticket/{self.ticket.pk}/delete/").status_code, 403)

    def test_comentarios_e_historial_no_editables(self):
        respuesta = self.client.get(f"/admin/soporte/ticket/{self.ticket.pk}/change/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "original")
        self.assertNotContains(respuesta, 'name="comentarios-0-texto"')  # sin campo editable
        self.assertNotContains(respuesta, 'name="historial-0-DELETE"')   # sin casilla de borrar

    def test_agente_sin_is_staff_no_entra_al_admin(self):
        self.client.force_login(crear_agente("luis"))
        self.assertEqual(self.client.get("/admin/").status_code, 302)  # redirige al login del admin
