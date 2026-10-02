"""Persistencia con sqlite3: traduce entre filas de la base de datos y objetos del dominio."""

import sqlite3
from contextlib import contextmanager
from dataclasses import asdict

from dominio import Comentario, Estado, Historial, Prioridad, Ticket, ahora

ESQUEMA = """
CREATE TABLE IF NOT EXISTS agentes (
    nombre TEXT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    asunto      TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    prioridad   TEXT NOT NULL,
    estado      TEXT NOT NULL,
    agente      TEXT REFERENCES agentes(nombre),
    creado      TEXT NOT NULL,
    actualizado TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS comentarios (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id  INTEGER NOT NULL REFERENCES tickets(id),
    autor      TEXT NOT NULL REFERENCES agentes(nombre),
    texto      TEXT NOT NULL,
    es_interno INTEGER NOT NULL DEFAULT 1,
    fecha      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS historial (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id      INTEGER NOT NULL REFERENCES tickets(id),
    campo          TEXT NOT NULL,
    valor_anterior TEXT,
    valor_nuevo    TEXT,
    autor          TEXT NOT NULL,
    fecha          TEXT NOT NULL
);
"""

AGENTES_INICIALES = ("ana", "luis")


class NoEncontrado(Exception):
    """El recurso pedido no existe (se traduce a HTTP 404)."""


class Repositorio:
    def __init__(self, ruta: str):
        self.ruta = ruta
        with self._conexion() as con:
            con.executescript(ESQUEMA)
            con.executemany(
                "INSERT OR IGNORE INTO agentes (nombre) VALUES (?)",
                [(nombre,) for nombre in AGENTES_INICIALES],
            )

    @contextmanager
    def _conexion(self):
        """Una conexión por operación: commit si todo va bien, rollback si hay excepción."""
        con = sqlite3.connect(self.ruta)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        try:
            with con:  # transacción
                yield con
        finally:
            con.close()

    # --- agentes ---

    def existe_agente(self, nombre: str | None) -> bool:
        with self._conexion() as con:
            fila = con.execute("SELECT 1 FROM agentes WHERE nombre = ?", (nombre,)).fetchone()
        return fila is not None

    # --- tickets ---

    @staticmethod
    def _a_ticket(fila: sqlite3.Row) -> Ticket:
        datos = dict(fila)
        datos["prioridad"] = Prioridad(datos["prioridad"])
        datos["estado"] = Estado(datos["estado"])
        return Ticket(**datos)

    def crear_ticket(self, ticket: Ticket) -> Ticket:
        datos = asdict(ticket)
        del datos["id"]
        with self._conexion() as con:
            cursor = con.execute(
                "INSERT INTO tickets (asunto, descripcion, prioridad, estado, agente, creado, actualizado)"
                " VALUES (:asunto, :descripcion, :prioridad, :estado, :agente, :creado, :actualizado)",
                datos,
            )
        ticket.id = cursor.lastrowid
        return ticket

    def obtener_ticket(self, ticket_id: int) -> Ticket:
        with self._conexion() as con:
            fila = con.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if fila is None:
            raise NoEncontrado(f"no existe el ticket {ticket_id}")
        return self._a_ticket(fila)

    def listar_tickets(self, estado: str | None = None, prioridad: str | None = None) -> list[Ticket]:
        consulta, parametros = "SELECT * FROM tickets WHERE 1 = 1", []
        if estado:
            consulta += " AND estado = ?"
            parametros.append(estado)
        if prioridad:
            consulta += " AND prioridad = ?"
            parametros.append(prioridad)
        with self._conexion() as con:
            filas = con.execute(consulta + " ORDER BY id", parametros).fetchall()
        return [self._a_ticket(fila) for fila in filas]

    def _guardar_cambio(self, ticket: Ticket, cambio: Historial) -> None:
        """Actualiza el ticket y escribe su historial en la MISMA transacción."""
        with self._conexion() as con:
            con.execute(
                "UPDATE tickets SET estado = ?, agente = ?, actualizado = ? WHERE id = ?",
                (ticket.estado, ticket.agente, ticket.actualizado, ticket.id),
            )
            con.execute(
                "INSERT INTO historial (ticket_id, campo, valor_anterior, valor_nuevo, autor, fecha)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (cambio.ticket_id, cambio.campo, cambio.valor_anterior, cambio.valor_nuevo,
                 cambio.autor, cambio.fecha),
            )

    def cambiar_estado(self, ticket_id: int, nuevo: object, autor: str) -> Ticket:
        ticket = self.obtener_ticket(ticket_id)
        self._guardar_cambio(ticket, ticket.cambiar_estado(nuevo, autor))
        return ticket

    def asignar(self, ticket_id: int, agente: str | None, autor: str) -> Ticket:
        ticket = self.obtener_ticket(ticket_id)
        self._guardar_cambio(ticket, ticket.asignar(agente, autor))
        return ticket

    # --- comentarios ---

    def agregar_comentario(self, ticket_id: int, autor: str, texto: object) -> Comentario:
        self.obtener_ticket(ticket_id)  # 404 si no existe
        comentario = Comentario.nuevo(ticket_id, autor, texto)
        with self._conexion() as con:
            cursor = con.execute(
                "INSERT INTO comentarios (ticket_id, autor, texto, es_interno, fecha) VALUES (?, ?, ?, ?, ?)",
                (comentario.ticket_id, comentario.autor, comentario.texto, comentario.es_interno,
                 comentario.fecha),
            )
            con.execute("UPDATE tickets SET actualizado = ? WHERE id = ?", (ahora(), ticket_id))
        comentario.id = cursor.lastrowid
        return comentario

    def listar_comentarios(self, ticket_id: int) -> list[Comentario]:
        self.obtener_ticket(ticket_id)
        with self._conexion() as con:
            filas = con.execute(
                "SELECT * FROM comentarios WHERE ticket_id = ? ORDER BY id", (ticket_id,)
            ).fetchall()
        return [Comentario(**{**dict(f), "es_interno": bool(f["es_interno"])}) for f in filas]

    # --- historial ---

    def listar_historial(self, ticket_id: int) -> list[Historial]:
        self.obtener_ticket(ticket_id)
        with self._conexion() as con:
            filas = con.execute(
                "SELECT * FROM historial WHERE ticket_id = ? ORDER BY id", (ticket_id,)
            ).fetchall()
        return [Historial(**dict(f)) for f in filas]
