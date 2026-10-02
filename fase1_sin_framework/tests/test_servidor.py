"""Tests de extremo a extremo: levanta el servidor real en un hilo y le hace peticiones HTTP."""

import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from servidor import crear_servidor


class ServidorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.carpeta = tempfile.TemporaryDirectory()
        cls.servidor = crear_servidor(os.path.join(cls.carpeta.name, "api.sqlite3"), "127.0.0.1", 0)
        cls.base = "http://127.0.0.1:%d" % cls.servidor.server_address[1]
        threading.Thread(target=cls.servidor.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()
        cls.carpeta.cleanup()

    def pedir(self, metodo, ruta, cuerpo=None, agente="ana", crudo=None):
        datos = crudo if crudo is not None else (json.dumps(cuerpo).encode() if cuerpo is not None else None)
        peticion = urllib.request.Request(self.base + ruta, data=datos, method=metodo)
        peticion.add_header("Content-Type", "application/json")
        if agente:
            peticion.add_header("X-Agente", agente)
        try:
            with urllib.request.urlopen(peticion) as respuesta:
                return respuesta.status, json.loads(respuesta.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def crear(self, **extra):
        datos = {"asunto": "Impresora", "descripcion": "Atasca papel", **extra}
        estado, ticket = self.pedir("POST", "/tickets/", datos, agente=None)
        self.assertEqual(estado, 201)
        return ticket

    def test_flujo_completo(self):
        ticket = self.crear(prioridad="alta")
        url = f"/tickets/{ticket['id']}"
        self.assertEqual(ticket["estado"], "abierto")

        self.assertEqual(self.pedir("PATCH", url + "/asignar/", {"agente": "luis"})[0], 200)
        estado, actualizado = self.pedir("PATCH", url + "/estado/", {"estado": "en_progreso"}, agente="luis")
        self.assertEqual((estado, actualizado["estado"], actualizado["agente"]), (200, "en_progreso", "luis"))

        self.assertEqual(self.pedir("POST", url + "/comentarios/", {"texto": "Revisando"})[0], 201)
        _, comentarios = self.pedir("GET", url + "/comentarios/")
        self.assertEqual(comentarios[0]["texto"], "Revisando")

        _, historial = self.pedir("GET", url + "/historial/")
        self.assertEqual([(h["campo"], h["valor_anterior"], h["valor_nuevo"], h["autor"]) for h in historial],
                         [("agente", None, "luis", "ana"), ("estado", "abierto", "en_progreso", "luis")])

    def test_detalle_y_filtros(self):
        ticket = self.crear(prioridad="critica")
        self.assertEqual(self.pedir("GET", f"/tickets/{ticket['id']}")[1]["asunto"], "Impresora")
        _, criticos = self.pedir("GET", "/tickets/?prioridad=critica")
        self.assertTrue(criticos and all(t["prioridad"] == "critica" for t in criticos))

    def test_errores(self):
        ticket = self.crear()
        url = f"/tickets/{ticket['id']}"
        casos = [
            ("crear sin asunto", "POST", "/tickets/", {"descripcion": "x"}, None, 400),
            ("prioridad inválida", "POST", "/tickets/", {"asunto": "a", "descripcion": "b", "prioridad": "x"}, None, 400),
            ("sin cabecera de agente", "GET", "/tickets/", None, None, 401),
            ("agente desconocido", "GET", "/tickets/", None, "mallory", 403),
            ("ticket inexistente", "GET", "/tickets/999/", None, "ana", 404),
            ("ruta inexistente", "GET", "/nada/", None, "ana", 404),
            ("método no permitido", "PATCH", "/tickets/", {}, "ana", 405),
            ("estado inválido", "PATCH", url + "/estado/", {"estado": "pausado"}, "ana", 400),
            ("asignar a no agente", "PATCH", url + "/asignar/", {"agente": "pepe"}, "ana", 400),
            ("comentario vacío", "POST", url + "/comentarios/", {"texto": ""}, "ana", 400),
        ]
        for nombre, metodo, ruta, cuerpo, agente, esperado in casos:
            with self.subTest(nombre):
                estado, respuesta = self.pedir(metodo, ruta, cuerpo, agente=agente)
                self.assertEqual(estado, esperado, respuesta)
                self.assertIn("error", respuesta)

    def test_json_mal_formado(self):
        estado, respuesta = self.pedir("POST", "/tickets/", crudo=b"{no es json")
        self.assertEqual(estado, 400)
        self.assertIn("JSON inválido", respuesta["error"])

    def test_cerrado_no_se_reabre(self):
        url = f"/tickets/{self.crear()['id']}/estado/"
        self.assertEqual(self.pedir("PATCH", url, {"estado": "cerrado"})[0], 200)
        estado, respuesta = self.pedir("PATCH", url, {"estado": "abierto"})
        self.assertEqual(estado, 400)
        self.assertIn("cerrado", respuesta["error"])


if __name__ == "__main__":
    unittest.main()
