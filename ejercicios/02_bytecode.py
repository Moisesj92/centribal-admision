"""Ejercicio 02: ver cómo Python compila a bytecode.

Ejecutar:
    docker compose run --rm shell python ejercicios/02_bytecode.py
"""

import dis
import importlib.util
import pathlib
import py_compile
import sys


def sumar(a, b):
    total = a + b
    return total


def main():
    print(f"Implementación: {sys.implementation.name}  versión: {sys.version.split()[0]}")

    # 1. El bytecode de una función: instrucciones para la máquina de pila.
    print("\n--- dis.dis(sumar) ---")
    dis.dis(sumar)

    # 2. El objeto código que guarda ese bytecode.
    codigo = sumar.__code__
    print("\n--- sumar.__code__ ---")
    print("variables locales:", codigo.co_varnames)
    print("bytes crudos:", codigo.co_code[:16], "...")

    # 3. compile() hace a mano lo que Python hace al cargar un archivo.
    print("\n--- compile() de un texto ---")
    fuente = "x = 2\ny = x * 21\nprint('resultado:', y)"
    objeto = compile(fuente, "<texto>", "exec")
    dis.dis(objeto)
    exec(objeto)

    # 4. Un SyntaxError aparece al compilar, antes de ejecutar nada.
    print("\n--- SyntaxError en compilación ---")
    try:
        compile("print('hola'", "<roto>", "exec")
    except SyntaxError as error:
        print("SyntaxError detectado sin ejecutar:", error.msg)

    # 5. Generar un .pyc en __pycache__ (lo que pasa al importar un módulo).
    print("\n--- __pycache__ ---")
    este_archivo = pathlib.Path(__file__)
    ruta_pyc = py_compile.compile(str(este_archivo))
    print("pyc generado en:", ruta_pyc)
    print("tag de la versión:", sys.implementation.cache_tag)
    print("cabecera (magic number):", importlib.util.MAGIC_NUMBER)


if __name__ == "__main__":
    main()
