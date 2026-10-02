"""Ejercicio 04: estructuras de control con tickets de ejemplo.

Ejecutar:
    docker compose run --rm shell python ejercicios/04_control.py
"""

TICKETS = [
    {"id": 1, "asunto": "No puedo entrar", "prioridad": "alta", "estado": "abierto"},
    {"id": 2, "asunto": "Cambiar email", "prioridad": "baja", "estado": "resuelto"},
    {"id": 3, "asunto": "Caída del servicio", "prioridad": "critica", "estado": "en_progreso"},
    {"id": 4, "asunto": "Factura duplicada", "prioridad": "media", "estado": "abierto"},
]


def condicionales():
    print("--- if / elif / else ---")
    for ticket in TICKETS:
        prioridad = ticket["prioridad"]
        if prioridad == "critica":
            accion = "avisar al equipo YA"
        elif prioridad in ("alta", "media"):
            accion = "encolar"
        else:
            accion = "cuando haya tiempo"
        urgente = "sí" if prioridad in ("alta", "critica") else "no"
        print(f"#{ticket['id']} {prioridad:<8} → {accion} (urgente: {urgente})")

    print("valores falsy:", [v for v in (0, "", [], None, "x", [0]) if not v])


def interpretar(peticion):
    match peticion:
        case {"accion": "crear", "asunto": str(asunto)}:
            return f"crear ticket '{asunto}'"
        case {"accion": "cerrar", "id": int(ticket_id)} if ticket_id > 0:
            return f"cerrar ticket {ticket_id}"
        case ["GET", ruta]:
            return f"leer {ruta}"
        case ["GET" | "DELETE" as metodo, *_]:
            return f"{metodo} con demasiados argumentos"
        case _:
            return "no entiendo la petición"


def coincidencia():
    print("\n--- match ---")
    for peticion in (
        {"accion": "crear", "asunto": "Impresora"},
        {"accion": "cerrar", "id": 7},
        {"accion": "cerrar", "id": -1},
        ["GET", "/tickets/"],
        ["DELETE", "/tickets/", "extra"],
        42,
    ):
        print(f"{peticion!r:45} → {interpretar(peticion)}")


def bucles():
    print("\n--- for / while / break / else ---")
    for indice, ticket in enumerate(TICKETS, start=1):
        if ticket["estado"] == "resuelto":
            continue
        print(indice, ticket["asunto"])

    for buscado in (3, 99):
        for ticket in TICKETS:
            if ticket["id"] == buscado:
                print(f"encontrado #{buscado}: {ticket['asunto']}")
                break
        else:
            print(f"#{buscado} no existe")

    intentos = 0
    while intentos < 3:
        intentos += 1
        print("intento", intentos)


class TransicionInvalida(Exception):
    """Excepción propia del dominio."""


def cerrar(ticket):
    if ticket["estado"] == "cerrado":
        raise TransicionInvalida(f"el ticket {ticket['id']} ya está cerrado")
    ticket["estado"] = "cerrado"


def excepciones():
    print("\n--- try / except / else / finally ---")
    for texto in ("42", "cuarenta"):
        try:
            numero = int(texto)
        except ValueError as error:
            print("ValueError:", error)
        else:
            print("convertido:", numero)
        finally:
            print("  (finally siempre se ejecuta)")

    ticket = {"id": 9, "estado": "abierto"}
    for _ in range(2):
        try:
            cerrar(ticket)
            print("ticket cerrado")
        except TransicionInvalida as error:
            print("TransicionInvalida:", error)


def comprehensions():
    print("\n--- comprehensions ---")
    abiertos = [t["asunto"] for t in TICKETS if t["estado"] == "abierto"]
    por_id = {t["id"]: t["asunto"] for t in TICKETS}
    prioridades = {t["prioridad"] for t in TICKETS}
    cuantos_urgentes = sum(1 for t in TICKETS if t["prioridad"] in ("alta", "critica"))
    print("abiertos:", abiertos)
    print("por id:", por_id)
    print("prioridades:", sorted(prioridades))
    print("urgentes:", cuantos_urgentes)


if __name__ == "__main__":
    condicionales()
    coincidencia()
    bucles()
    excepciones()
    comprehensions()
