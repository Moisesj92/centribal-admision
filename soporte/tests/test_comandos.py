from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from soporte.models import Estado, Ticket


class CrearAgentesTest(TestCase):
    def setUp(self):
        call_command("crear_agentes", stdout=StringIO())
        self.usuarios = {u.username: u for u in get_user_model().objects.all()}

    def test_roles(self):
        self.assertEqual(set(self.usuarios), {"ana", "luis", "sara"})
        self.assertTrue(all(u.es_agente for u in self.usuarios.values()))
        self.assertEqual({n for n, u in self.usuarios.items() if u.is_staff}, {"sara"})
        self.assertFalse(any(u.is_superuser for u in self.usuarios.values()))

    def test_se_puede_ejecutar_varias_veces(self):
        call_command("crear_agentes", stdout=StringIO())
        self.assertEqual(get_user_model().objects.count(), 3)

    def test_sara_usa_el_admin_con_permisos_acotados(self):
        ticket = Ticket.objects.create(asunto="VPN", descripcion="No conecta")
        self.client.force_login(self.usuarios["sara"])
        self.assertEqual(self.client.get("/admin/soporte/ticket/").status_code, 200)
        self.assertEqual(self.client.get(f"/admin/soporte/ticket/{ticket.pk}/change/").status_code, 200)
        self.assertEqual(self.client.get("/admin/soporte/ticket/add/").status_code, 403)  # sin add_ticket
        self.assertEqual(self.client.get("/admin/cuentas/usuario/").status_code, 403)  # no gestiona usuarios

    def test_ana_no_entra_al_admin(self):
        self.client.force_login(self.usuarios["ana"])
        self.assertEqual(self.client.get("/admin/").status_code, 302)


class PrepararDemoTest(TestCase):
    def test_crea_usuarios_y_tickets_con_historial(self):
        call_command("preparar_demo", stdout=StringIO())
        self.assertEqual(get_user_model().objects.count(), 3)
        self.assertEqual(Ticket.objects.count(), 5)
        self.assertTrue(Ticket.objects.filter(estado=Estado.CERRADO).exists())
        caida = Ticket.objects.get(asunto="Caída del servicio")
        self.assertEqual(caida.historial.count(), 2)

    def test_no_duplica_al_repetirse(self):
        call_command("preparar_demo", stdout=StringIO())
        call_command("preparar_demo", stdout=StringIO())
        self.assertEqual(Ticket.objects.count(), 5)
        self.assertEqual(get_user_model().objects.count(), 3)
