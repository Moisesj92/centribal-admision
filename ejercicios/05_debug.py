"""Ejercicio 05: cazar un bug con logging, breakpoint() y VS Code.

Este script tiene un BUG INTENCIONAL. Resultado esperado:
    alta: 7.5 h | baja: 1.0 h | critica: 12.0 h | media: 3.0 h

Ejecutar:
    docker compose run --rm shell python ejercicios/05_debug.py

Con pdb: descomenta el breakpoint() de abajo y usa n, s, p acumulado, c, q.
Con VS Code: ver docs/05-debug.md (debugpy + "Attach to Docker").
(-Xfrozen_modules=off evita un aviso de debugpy con Python 3.13.)
"""

import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(funcName)s: %(message)s")
log = logging.getLogger(__name__)

TICKETS = [
    {"id": 1, "prioridad": "alta", "horas": 5.0},
    {"id": 2, "prioridad": "baja", "horas": 1.0},
    {"id": 3, "prioridad": "critica", "horas": 8.0},
    {"id": 4, "prioridad": "alta", "horas": 2.5},
    {"id": 5, "prioridad": "media", "horas": 3.0},
    {"id": 6, "prioridad": "critica", "horas": 4.0},
]


def horas_por_prioridad(tickets):
    for ticket in tickets:
        acumulado = {}
        # breakpoint()
        prioridad = ticket["prioridad"]
        acumulado[prioridad] = acumulado.get(prioridad, 0) + ticket["horas"]
        log.debug("ticket %s → %s", ticket["id"], acumulado)
    return acumulado


def informe(acumulado):
    return " | ".join(f"{p}: {h} h" for p, h in sorted(acumulado.items()))


if __name__ == "__main__":
    # Cambia INFO por DEBUG arriba para ver cada paso del bucle.
    resultado = horas_por_prioridad(TICKETS)
    log.info("tickets procesados: %d", len(TICKETS))
    print(informe(resultado))
