"""Modelo del dominio: tickets de soporte, comentarios e historial.

No sabe nada de HTTP ni de SQL: solo datos y reglas de negocio.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


def ahora() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class ErrorValidacion(Exception):
    """Datos de entrada incorrectos (se traduce a HTTP 400)."""


class TransicionInvalida(ErrorValidacion):
    """Cambio de estado no permitido por el flujo del ticket."""


class Prioridad(StrEnum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class Estado(StrEnum):
    ABIERTO = "abierto"
    EN_PROGRESO = "en_progreso"
    RESUELTO = "resuelto"
    CERRADO = "cerrado"


# Desde cada estado, a cuáles se puede pasar. Un ticket cerrado no se reabre.
TRANSICIONES: dict[Estado, set[Estado]] = {
    Estado.ABIERTO: {Estado.EN_PROGRESO, Estado.RESUELTO, Estado.CERRADO},
    Estado.EN_PROGRESO: {Estado.ABIERTO, Estado.RESUELTO, Estado.CERRADO},
    Estado.RESUELTO: {Estado.ABIERTO, Estado.CERRADO},
    Estado.CERRADO: set(),
}


def parsear_enum[E: StrEnum](tipo: type[E], valor: object, campo: str) -> E:
    try:
        return tipo(valor)
    except ValueError:
        validos = ", ".join(tipo)
        raise ErrorValidacion(f"{campo} inválido: {valor!r}. Valores válidos: {validos}") from None


def texto_obligatorio(valor: object, campo: str, maximo: int | None = None) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ErrorValidacion(f"{campo} es obligatorio y debe ser texto")
    valor = valor.strip()
    if maximo is not None and len(valor) > maximo:
        raise ErrorValidacion(f"{campo} no puede superar {maximo} caracteres")
    return valor


@dataclass
class Historial:
    ticket_id: int
    campo: str
    valor_anterior: str | None
    valor_nuevo: str | None
    autor: str
    fecha: str = field(default_factory=ahora)
    id: int | None = None


@dataclass
class Comentario:
    ticket_id: int
    autor: str
    texto: str
    es_interno: bool = True
    fecha: str = field(default_factory=ahora)
    id: int | None = None

    @classmethod
    def nuevo(cls, ticket_id: int, autor: str, texto: object) -> "Comentario":
        return cls(ticket_id=ticket_id, autor=autor, texto=texto_obligatorio(texto, "texto"))


@dataclass
class Ticket:
    asunto: str
    descripcion: str
    prioridad: Prioridad = Prioridad.MEDIA
    estado: Estado = Estado.ABIERTO
    agente: str | None = None
    creado: str = field(default_factory=ahora)
    actualizado: str = field(default_factory=ahora)
    id: int | None = None

    @classmethod
    def nuevo(cls, datos: dict) -> "Ticket":
        """Crea un ticket validando lo que llega del cliente."""
        if not isinstance(datos, dict):
            raise ErrorValidacion("el cuerpo debe ser un objeto JSON")
        return cls(
            asunto=texto_obligatorio(datos.get("asunto"), "asunto", maximo=200),
            descripcion=texto_obligatorio(datos.get("descripcion"), "descripcion"),
            prioridad=parsear_enum(Prioridad, datos.get("prioridad", Prioridad.MEDIA), "prioridad"),
        )

    def _id(self) -> int:
        if self.id is None:
            raise ValueError("el ticket aún no está guardado")
        return self.id

    def cambiar_estado(self, nuevo: object, autor: str) -> Historial:
        nuevo_estado = parsear_enum(Estado, nuevo, "estado")
        if nuevo_estado == self.estado:
            raise TransicionInvalida(f"el ticket ya está en estado {self.estado}")
        if nuevo_estado not in TRANSICIONES[self.estado]:
            raise TransicionInvalida(f"no se puede pasar de {self.estado} a {nuevo_estado}")
        anterior, self.estado = self.estado, nuevo_estado
        self.actualizado = ahora()
        return Historial(self._id(), "estado", anterior, nuevo_estado, autor)

    def asignar(self, agente: str | None, autor: str) -> Historial:
        if self.estado == Estado.CERRADO:
            raise TransicionInvalida("no se puede reasignar un ticket cerrado")
        if agente == self.agente:
            raise ErrorValidacion(f"el ticket ya está asignado a {agente}")
        anterior, self.agente = self.agente, agente
        self.actualizado = ahora()
        return Historial(self._id(), "agente", anterior, agente, autor)
