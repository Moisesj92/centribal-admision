import unittest

from dominio import Estado, ErrorValidacion, Prioridad, Ticket, TransicionInvalida


def ticket_guardado(**cambios) -> Ticket:
    ticket = Ticket.nuevo({"asunto": "No arranca", "descripcion": "Pantalla negra"})
    ticket.id = 1
    for campo, valor in cambios.items():
        setattr(ticket, campo, valor)
    return ticket


class CrearTicketTest(unittest.TestCase):
    def test_valores_por_defecto(self):
        ticket = Ticket.nuevo({"asunto": "  Hola  ", "descripcion": "x"})
        self.assertEqual(ticket.asunto, "Hola")
        self.assertEqual(ticket.prioridad, Prioridad.MEDIA)
        self.assertEqual(ticket.estado, Estado.ABIERTO)
        self.assertIsNone(ticket.agente)

    def test_prioridad_valida(self):
        ticket = Ticket.nuevo({"asunto": "a", "descripcion": "b", "prioridad": "critica"})
        self.assertIs(ticket.prioridad, Prioridad.CRITICA)

    def test_prioridad_invalida(self):
        with self.assertRaisesRegex(ErrorValidacion, "prioridad inválido"):
            Ticket.nuevo({"asunto": "a", "descripcion": "b", "prioridad": "urgentisima"})

    def test_campos_obligatorios(self):
        for datos in ({"descripcion": "b"}, {"asunto": "a"}, {"asunto": "   ", "descripcion": "b"},
                      {"asunto": 3, "descripcion": "b"}):
            with self.subTest(datos=datos), self.assertRaises(ErrorValidacion):
                Ticket.nuevo(datos)

    def test_cuerpo_no_dict(self):
        with self.assertRaises(ErrorValidacion):
            Ticket.nuevo(["no", "es", "dict"])  # type: ignore[arg-type]


class EstadoTest(unittest.TestCase):
    def test_transicion_valida_genera_historial(self):
        ticket = ticket_guardado()
        cambio = ticket.cambiar_estado("en_progreso", autor="ana")
        self.assertEqual(ticket.estado, Estado.EN_PROGRESO)
        self.assertEqual((cambio.campo, cambio.valor_anterior, cambio.valor_nuevo, cambio.autor),
                         ("estado", "abierto", "en_progreso", "ana"))

    def test_resuelto_se_puede_reabrir(self):
        ticket = ticket_guardado(estado=Estado.RESUELTO)
        ticket.cambiar_estado("abierto", autor="ana")
        self.assertEqual(ticket.estado, Estado.ABIERTO)

    def test_cerrado_no_se_reabre(self):
        for destino in ("abierto", "en_progreso", "resuelto"):
            with self.subTest(destino=destino), self.assertRaises(TransicionInvalida):
                ticket_guardado(estado=Estado.CERRADO).cambiar_estado(destino, autor="ana")

    def test_mismo_estado(self):
        with self.assertRaises(TransicionInvalida):
            ticket_guardado().cambiar_estado("abierto", autor="ana")

    def test_estado_desconocido(self):
        with self.assertRaisesRegex(ErrorValidacion, "estado inválido"):
            ticket_guardado().cambiar_estado("pausado", autor="ana")


class AsignarTest(unittest.TestCase):
    def test_asignar_y_desasignar(self):
        ticket = ticket_guardado()
        cambio = ticket.asignar("luis", autor="ana")
        self.assertEqual((cambio.valor_anterior, cambio.valor_nuevo), (None, "luis"))
        ticket.asignar(None, autor="ana")
        self.assertIsNone(ticket.agente)

    def test_mismo_agente(self):
        with self.assertRaises(ErrorValidacion):
            ticket_guardado(agente="luis").asignar("luis", autor="ana")

    def test_cerrado_no_se_reasigna(self):
        with self.assertRaises(TransicionInvalida):
            ticket_guardado(estado=Estado.CERRADO).asignar("luis", autor="ana")


if __name__ == "__main__":
    unittest.main()
