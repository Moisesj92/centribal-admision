from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from soporte.models import Estado, Ticket

Usuario = get_user_model()


class UiTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ana = Usuario.objects.create_user("ana", password="x", is_staff=True)
        cls.luis = Usuario.objects.create_user("luis", password="x", is_staff=True)
        cls.cliente = Usuario.objects.create_user("cliente", password="x")
        cls.ticket = Ticket.objects.create(asunto="VPN", descripcion="No conecta", prioridad="alta")

    def setUp(self):
        self.client.force_login(self.ana)

    def url(self, nombre):
        return reverse(f"ui:{nombre}", args=[self.ticket.pk])

    def test_cliente_crea_solicitud_sin_cuenta(self):
        self.client.logout()
        respuesta = self.client.post(
            reverse("ui:nuevo"), {"asunto": "Impresora", "descripcion": "Atasca", "prioridad": "baja"}
        )
        self.assertContains(respuesta, "Solicitud recibida")
        self.assertTrue(Ticket.objects.filter(asunto="Impresora", estado=Estado.ABIERTO).exists())

    def test_formulario_con_errores(self):
        respuesta = self.client.post(reverse("ui:nuevo"), {"asunto": " ", "descripcion": "", "prioridad": "x"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Ticket.objects.count(), 1)
        self.assertContains(respuesta, "errorlist")

    def test_solo_agentes(self):
        for usuario in (None, self.cliente):
            with self.subTest(usuario=usuario):
                self.client.logout()
                if usuario:
                    self.client.force_login(usuario)
                for ruta in (reverse("ui:lista"), self.url("detalle")):
                    respuesta = self.client.get(ruta)
                    self.assertRedirects(respuesta, f"{reverse('login')}?next={ruta}")

    def test_lista_y_filtros(self):
        Ticket.objects.create(asunto="Factura", descripcion="x", prioridad="baja")
        self.assertContains(self.client.get(reverse("ui:lista")), "Factura")
        respuesta = self.client.get(reverse("ui:lista"), {"prioridad": "alta"})
        self.assertContains(respuesta, "VPN")
        self.assertNotContains(respuesta, "Factura")

    def test_flujo_completo(self):
        self.client.post(self.url("asignar"), {"agente": self.luis.pk})
        self.client.post(self.url("estado"), {"estado": "en_progreso"})
        respuesta = self.client.post(self.url("comentar"), {"texto": "Revisando"}, follow=True)
        self.assertContains(respuesta, "Comentario añadido")
        self.ticket.refresh_from_db()
        self.assertEqual((self.ticket.estado, self.ticket.agente), (Estado.EN_PROGRESO, self.luis))
        self.assertEqual(
            list(self.ticket.historial.values_list("campo", "valor_nuevo", "autor__username")),
            [("agente", "luis", "ana"), ("estado", "en_progreso", "ana")],
        )
        self.assertContains(respuesta, "Revisando")

    def test_transicion_invalida_muestra_error(self):
        self.client.post(self.url("estado"), {"estado": "cerrado"})
        respuesta = self.client.post(self.url("estado"), {"estado": "abierto"})
        self.assertEqual(respuesta.status_code, 400)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.estado, Estado.CERRADO)
        self.assertContains(respuesta, "Ticket cerrado", status_code=400)

    def test_solo_ofrece_estados_validos(self):
        respuesta = self.client.get(self.url("detalle"))
        opciones = [valor for valor, _ in respuesta.context["estado_form"].fields["estado"].choices]
        self.assertEqual(opciones, ["en_progreso", "resuelto", "cerrado"])

    def test_acciones_solo_por_post(self):
        self.assertEqual(self.client.get(self.url("estado")).status_code, 405)
