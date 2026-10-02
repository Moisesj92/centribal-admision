"""Ejercicio 03: tipado dinámico y fuerte, duck typing y type hints.

Ejecutar:
    docker compose run --rm shell python ejercicios/03_tipado.py
    docker compose run --rm shell mypy ejercicios/03_tipado.py
"""


def dinamico():
    print("--- Dinámico: la variable cambia de tipo ---")
    x = 10
    print(x, type(x))
    x = "diez"
    print(x, type(x))
    x = [1, 0]
    print(x, type(x))


def fuerte():
    print("\n--- Fuerte: sin conversiones implícitas ---")
    try:
        print("3" + 4)
    except TypeError as error:
        print("TypeError:", error)
    print('int("3") + 4 =', int("3") + 4)
    print('"3" + str(4) =', "3" + str(4))
    print("1 + 2.5 =", 1 + 2.5, "(int y float sí se mezclan)")


class Pato:
    def hablar(self):
        return "Cuac"


class Robot:
    def hablar(self):
        return "Bip bup"


def duck_typing():
    print("\n--- Duck typing: solo importa que tenga .hablar() ---")
    for cosa in (Pato(), Robot()):
        print(type(cosa).__name__, "dice", cosa.hablar())

    print("len() con distintos tipos:", len("hola"), len([1, 2]), len({"a": 1}))


def mutables():
    print("\n--- Mutables e inmutables ---")
    a = [1, 2]
    b = a
    b.append(3)
    print("a tras modificar b:", a, "| a is b:", a is b)

    texto = "hola"
    otro = texto
    otro += " mundo"  # crea un str nuevo
    print("texto:", repr(texto), "| otro:", repr(otro))

    def agregar_mal(item, lista=[]):
        lista.append(item)
        return lista

    print("default mutable compartido:", agregar_mal(1), agregar_mal(2))


def precio_final(precios: list[float], descuento: float = 0.0) -> float:
    return sum(precios) * (1 - descuento)


def saludar(nombre: str) -> str:
    return f"Hola, {nombre}"


def type_hints() -> None:  # anotada para que mypy revise su cuerpo
    print("\n--- Type hints: no se comprueban al ejecutar ---")
    print("bien:", precio_final([10.0, 20.0], 0.1))
    # mypy marca esta línea como error (int no es str), pero Python la ejecuta igual:
    print("mal pero funciona:", saludar(42))
    print("anotaciones:", precio_final.__annotations__)


if __name__ == "__main__":
    dinamico()
    fuerte()
    duck_typing()
    mutables()
    type_hints()
