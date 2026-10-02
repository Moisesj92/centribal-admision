"""Servidor HTTP con la librería estándar: enrutado, JSON y códigos de estado a mano.

Ejecutar:
    docker compose up api-stdlib            # http://localhost:8000/tickets/

Los endpoints de agente piden la cabecera `X-Agente: <nombre>` (agentes: ana, luis).
"""

import json
import logging
import os
import re
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from dominio import ErrorValidacion, Ticket
from repositorio import NoEncontrado, Repositorio

log = logging.getLogger("api")


class ErrorHttp(Exception):
    def __init__(self, estado: HTTPStatus, mensaje: str):
        super().__init__(mensaje)
        self.estado = estado


# (método, patrón de ruta, nombre del método del handler, requiere agente)
RUTAS = [
    ("POST", r"/tickets/", "crear_ticket", False),
    ("GET", r"/tickets/", "listar_tickets", True),
    ("GET", r"/tickets/(?P<id>\d+)/", "detalle_ticket", True),
    ("PATCH", r"/tickets/(?P<id>\d+)/estado/", "cambiar_estado", True),
    ("PATCH", r"/tickets/(?P<id>\d+)/asignar/", "asignar", True),
    ("POST", r"/tickets/(?P<id>\d+)/comentarios/", "crear_comentario", True),
    ("GET", r"/tickets/(?P<id>\d+)/comentarios/", "listar_comentarios", True),
    ("GET", r"/tickets/(?P<id>\d+)/historial/", "listar_historial", True),
]


class Handler(BaseHTTPRequestHandler):
    repo: Repositorio  # se asigna al crear el servidor

    # --- enrutado ---

    def do_GET(self):
        self._despachar("GET")

    def do_POST(self):
        self._despachar("POST")

    def do_PATCH(self):
        self._despachar("PATCH")

    def _despachar(self, metodo: str) -> None:
        url = urlparse(self.path)
        ruta = url.path if url.path.endswith("/") else url.path + "/"
        try:
            metodos_permitidos = []
            for metodo_ruta, patron, accion, requiere_agente in RUTAS:
                coincidencia = re.fullmatch(patron, ruta)
                if not coincidencia:
                    continue
                metodos_permitidos.append(metodo_ruta)
                if metodo_ruta != metodo:
                    continue
                agente = self._autenticar() if requiere_agente else None
                params = {k: int(v) for k, v in coincidencia.groupdict().items()}
                estado, cuerpo = getattr(self, accion)(agente=agente, query=parse_qs(url.query), **params)
                return self._responder(estado, cuerpo)
            if metodos_permitidos:
                raise ErrorHttp(HTTPStatus.METHOD_NOT_ALLOWED, f"método {metodo} no permitido")
            raise ErrorHttp(HTTPStatus.NOT_FOUND, f"ruta no encontrada: {url.path}")
        except ErrorHttp as error:
            self._responder(error.estado, {"error": str(error)})
        except NoEncontrado as error:
            self._responder(HTTPStatus.NOT_FOUND, {"error": str(error)})
        except ErrorValidacion as error:
            self._responder(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except Exception:
            log.exception("error inesperado")
            self._responder(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "error interno"})

    # --- utilidades ---

    def _autenticar(self) -> str:
        agente = self.headers.get("X-Agente")
        if not agente:
            raise ErrorHttp(HTTPStatus.UNAUTHORIZED, "falta la cabecera X-Agente")
        if not self.repo.existe_agente(agente):
            raise ErrorHttp(HTTPStatus.FORBIDDEN, f"{agente} no es un agente")
        return agente

    def _leer_json(self) -> dict:
        longitud = int(self.headers.get("Content-Length") or 0)
        try:
            datos = json.loads(self.rfile.read(longitud) or b"{}")
        except json.JSONDecodeError as error:
            raise ErrorHttp(HTTPStatus.BAD_REQUEST, f"JSON inválido: {error.msg}") from None
        if not isinstance(datos, dict):
            raise ErrorHttp(HTTPStatus.BAD_REQUEST, "el cuerpo debe ser un objeto JSON")
        return datos

    def _responder(self, estado: HTTPStatus, cuerpo) -> None:
        datos = json.dumps(cuerpo, ensure_ascii=False, indent=2).encode()
        self.send_response(estado)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def log_message(self, formato, *args):
        log.info("%s %s", self.address_string(), formato % args)

    # --- acciones ---

    def crear_ticket(self, agente, query):
        ticket = self.repo.crear_ticket(Ticket.nuevo(self._leer_json()))
        return HTTPStatus.CREATED, asdict(ticket)

    def listar_tickets(self, agente, query):
        filtros = {campo: query[campo][0] for campo in ("estado", "prioridad") if campo in query}
        return HTTPStatus.OK, [asdict(t) for t in self.repo.listar_tickets(**filtros)]

    def detalle_ticket(self, agente, query, id):
        return HTTPStatus.OK, asdict(self.repo.obtener_ticket(id))

    def cambiar_estado(self, agente, query, id):
        datos = self._leer_json()
        return HTTPStatus.OK, asdict(self.repo.cambiar_estado(id, datos.get("estado"), autor=agente))

    def asignar(self, agente, query, id):
        datos = self._leer_json()
        if "agente" not in datos:
            raise ErrorValidacion("falta el campo agente (usa null para desasignar)")
        nuevo = datos["agente"]
        if nuevo is not None and not self.repo.existe_agente(nuevo):
            raise ErrorValidacion(f"no existe el agente {nuevo!r}")
        return HTTPStatus.OK, asdict(self.repo.asignar(id, nuevo, autor=agente))

    def crear_comentario(self, agente, query, id):
        comentario = self.repo.agregar_comentario(id, agente, self._leer_json().get("texto"))
        return HTTPStatus.CREATED, asdict(comentario)

    def listar_comentarios(self, agente, query, id):
        return HTTPStatus.OK, [asdict(c) for c in self.repo.listar_comentarios(id)]

    def listar_historial(self, agente, query, id):
        return HTTPStatus.OK, [asdict(h) for h in self.repo.listar_historial(id)]


def crear_servidor(ruta_bd: str, host: str = "0.0.0.0", puerto: int = 8000) -> ThreadingHTTPServer:
    # Subclase con su propio repositorio: varios servidores (p. ej. en tests) no se pisan.
    handler = type("HandlerConRepo", (Handler,), {"repo": Repositorio(ruta_bd)})
    return ThreadingHTTPServer((host, puerto), handler)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    servidor = crear_servidor(os.environ.get("DB_PATH", "soporte.sqlite3"))
    log.info("escuchando en http://%s:%s", *servidor.server_address)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
