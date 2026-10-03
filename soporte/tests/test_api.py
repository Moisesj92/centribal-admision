from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from soporte.models import Estado, Ticket
from soporte.tests.utils import crear_agente

Usuario = get_user_model()


class TicketApiTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ana = crear_agente("ana")
        cls.luis = crear_agente("luis")
        cls.cliente = Usuario.objects.create_user("cliente", password="x")
        cls.admin_no_agente = Usuario.objects.create_user("admin", password="x", is_staff=True)

    def setUp(self):
        self.client.force_authenticate(self.ana)

    def crear(self, **extra):
        self.client.force_authenticate(None)  # el cliente no necesita cuenta
        respuesta = self.client.post(
            "/api/tickets/", {"asunto": "Impresora", "descripcion": "Atasca papel", **extra}, format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        self.client.force_authenticate(self.ana)
        return respuesta.data

    # --- crear ---

    def test_crear_es_publico_y_tiene_valores_por_defecto(self):
        ticket = self.crear()
        self.assertEqual(
            (ticket["prioridad"], ticket["estado"], ticket["agente"]), ("media", "abierto", None)
        )

    def test_crear_ignora_estado_y_agente(self):
        ticket = self.crear(estado="cerrado", agente="luis")
        self.assertEqual((ticket["estado"], ticket["agente"]), ("abierto", None))

    def test_crear_valida(self):
        self.client.force_authenticate(None)
        casos = [
            {"descripcion": "x"},
            {"asunto": "   ", "descripcion": "x"},
            {"asunto": "a", "descripcion": "x", "prioridad": "urgentisima"},
        ]
        for datos in casos:
            with self.subTest(datos=datos):
                respuesta = self.client.post("/api/tickets/", datos, format="json")
                self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    # --- permisos ---

    def test_solo_agentes_ven_tickets(self):
        ticket = self.crear()
        casos = ((None, 401), (self.cliente, 403), (self.admin_no_agente, 403), (self.ana, 200))
        for usuario, esperado in casos:
            with self.subTest(usuario=usuario):
                self.client.force_authenticate(usuario)
                self.assertEqual(self.client.get("/api/tickets/").status_code, esperado)
                self.assertEqual(self.client.get(f"/api/tickets/{ticket['id']}/").status_code, esperado)

    def test_token(self):
        respuesta = self.client.post("/api/token/", {"username": "ana", "password": "x"})
        self.client.force_authenticate(None)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + respuesta.data["token"])
        self.assertEqual(self.client.get("/api/tickets/").status_code, 200)

    # --- listar ---

    def test_filtros(self):
        self.crear(prioridad="alta")
        self.crear(prioridad="baja")
        self.assertEqual(self.client.get("/api/tickets/").data["count"], 2)
        alta = self.client.get("/api/tickets/", {"prioridad": "alta"}).data["results"]
        self.assertEqual([t["prioridad"] for t in alta], ["alta"])
        self.assertEqual(self.client.get("/api/tickets/", {"estado": "cerrado"}).data["results"], [])

    def test_detalle_inexistente(self):
        self.assertEqual(self.client.get("/api/tickets/999/").status_code, 404)

    # --- estado, asignación, comentarios e historial ---

    def test_flujo_completo(self):
        url = f"/api/tickets/{self.crear(prioridad='alta')['id']}"

        respuesta = self.client.patch(url + "/asignar/", {"agente": "luis"}, format="json")
        self.assertEqual(respuesta.data["agente"], "luis")

        self.client.force_authenticate(self.luis)
        respuesta = self.client.patch(url + "/estado/", {"estado": "en_progreso"}, format="json")
        self.assertEqual(respuesta.data["estado"], "en_progreso")

        respuesta = self.client.post(url + "/comentarios/", {"texto": "Revisando"}, format="json")
        self.assertEqual(respuesta.status_code, 201)
        comentarios = self.client.get(url + "/comentarios/").data["results"]
        self.assertEqual([(c["autor"], c["texto"]) for c in comentarios], [("luis", "Revisando")])

        historial = self.client.get(url + "/historial/").data["results"]
        self.assertEqual(
            [(h["campo"], h["valor_anterior"], h["valor_nuevo"], h["autor"]) for h in historial],
            [("agente", None, "luis", "ana"), ("estado", "abierto", "en_progreso", "luis")],
        )

    def test_cerrado_no_se_reabre_ni_se_reasigna(self):
        url = f"/api/tickets/{self.crear()['id']}"
        self.assertEqual(
            self.client.patch(url + "/estado/", {"estado": "cerrado"}, format="json").status_code, 200
        )
        for ruta, datos in (("/estado/", {"estado": "abierto"}), ("/asignar/", {"agente": "luis"})):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.patch(url + ruta, datos, format="json").status_code, 400)
        self.assertEqual(Ticket.objects.get().estado, Estado.CERRADO)
        self.assertEqual(self.client.get(url + "/historial/").data["count"], 1)

    def test_errores_de_validacion(self):
        url = f"/api/tickets/{self.crear()['id']}"
        casos = [
            ("/estado/", {"estado": "pausado"}),
            ("/estado/", {"estado": "abierto"}),  # mismo estado
            ("/estado/", {}),
            ("/asignar/", {"agente": "cliente"}),  # no es staff
            ("/asignar/", {"agente": "nadie"}),
            ("/asignar/", {"agente": None}),  # ya está sin asignar
        ]
        for ruta, datos in casos:
            with self.subTest(ruta=ruta, datos=datos):
                self.assertEqual(self.client.patch(url + ruta, datos, format="json").status_code, 400)
        respuesta = self.client.post(url + "/comentarios/", {"texto": ""}, format="json")
        self.assertEqual(respuesta.status_code, 400)

    def test_desasignar(self):
        url = f"/api/tickets/{self.crear()['id']}"
        self.client.patch(url + "/asignar/", {"agente": "luis"}, format="json")
        respuesta = self.client.patch(url + "/asignar/", {"agente": None}, format="json")
        self.assertIsNone(respuesta.data["agente"])

    def test_metodo_no_permitido(self):
        url = f"/api/tickets/{self.crear()['id']}/"
        self.assertEqual(self.client.delete(url).status_code, 405)
        self.assertEqual(self.client.put(url, {}, format="json").status_code, 405)

    def test_paginacion(self):
        Ticket.objects.bulk_create(Ticket(asunto=f"t{i}", descripcion="x") for i in range(25))
        primera = self.client.get("/api/tickets/").data
        self.assertEqual((primera["count"], len(primera["results"])), (25, 20))
        self.assertIsNotNone(primera["next"])
        segunda = self.client.get(primera["next"]).data
        self.assertEqual(len(segunda["results"]), 5)
        self.assertIsNone(segunda["next"])
