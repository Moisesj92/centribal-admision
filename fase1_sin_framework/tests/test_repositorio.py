import os
import tempfile
import unittest

from dominio import Estado, Ticket, TransicionInvalida
from repositorio import NoEncontrado, Repositorio


class RepositorioTest(unittest.TestCase):
    def setUp(self):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        self.repo = Repositorio(os.path.join(carpeta.name, "test.sqlite3"))
        self.ticket = self.repo.crear_ticket(
            Ticket.nuevo({"asunto": "VPN", "descripcion": "No conecta", "prioridad": "alta"})
        )

    def test_crear_y_obtener(self):
        self.assertIsNotNone(self.ticket.id)
        self.assertEqual(self.repo.obtener_ticket(self.ticket.id), self.ticket)

    def test_no_encontrado(self):
        with self.assertRaises(NoEncontrado):
            self.repo.obtener_ticket(999)

    def test_filtros(self):
        self.repo.crear_ticket(Ticket.nuevo({"asunto": "b", "descripcion": "b", "prioridad": "baja"}))
        self.assertEqual(len(self.repo.listar_tickets()), 2)
        self.assertEqual([t.asunto for t in self.repo.listar_tickets(prioridad="alta")], ["VPN"])
        self.assertEqual(self.repo.listar_tickets(estado="cerrado"), [])

    def test_cambios_quedan_en_historial(self):
        self.repo.asignar(self.ticket.id, "luis", autor="ana")
        self.repo.cambiar_estado(self.ticket.id, "en_progreso", autor="luis")
        guardado = self.repo.obtener_ticket(self.ticket.id)
        self.assertEqual((guardado.estado, guardado.agente), (Estado.EN_PROGRESO, "luis"))
        historial = self.repo.listar_historial(self.ticket.id)
        self.assertEqual([(h.campo, h.valor_nuevo, h.autor) for h in historial],
                         [("agente", "luis", "ana"), ("estado", "en_progreso", "luis")])

    def test_transicion_invalida_no_guarda_nada(self):
        self.repo.cambiar_estado(self.ticket.id, "cerrado", autor="ana")
        with self.assertRaises(TransicionInvalida):
            self.repo.cambiar_estado(self.ticket.id, "abierto", autor="ana")
        self.assertEqual(self.repo.obtener_ticket(self.ticket.id).estado, Estado.CERRADO)
        self.assertEqual(len(self.repo.listar_historial(self.ticket.id)), 1)

    def test_comentarios(self):
        self.repo.agregar_comentario(self.ticket.id, "ana", "Llamé al cliente")
        comentarios = self.repo.listar_comentarios(self.ticket.id)
        self.assertEqual([(c.autor, c.texto, c.es_interno) for c in comentarios],
                         [("ana", "Llamé al cliente", True)])

    def test_agentes(self):
        self.assertTrue(self.repo.existe_agente("ana"))
        self.assertFalse(self.repo.existe_agente("mallory"))


if __name__ == "__main__":
    unittest.main()
