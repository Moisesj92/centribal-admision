# ¿Interpretado o compilado?

La respuesta corta: **las dos cosas**. Python (en su implementación de referencia, CPython) primero *compila* el código fuente a **bytecode** y después lo *interpreta* con una máquina virtual.

## Lenguajes compilados vs interpretados

| | Compilado (C, Go, Rust) | Interpretado "puro" (shell clásico) |
|---|---|---|
| Cuándo se traduce | Antes de ejecutar, una sola vez | Línea a línea, mientras se ejecuta |
| Resultado | Binario de código máquina para una CPU/SO concretos | No hay archivo intermedio |
| Velocidad | Muy rápida | Lenta |
| Errores | Muchos se detectan al compilar | Aparecen al llegar a esa línea |

Python está en medio: compila a un formato intermedio portable (bytecode) y lo ejecuta una máquina virtual, igual que Java (JVM) o C# (.NET CLR).

## El camino de un `.py`

```
holamundo.py  ──(compilador de CPython)──►  bytecode  ──(PVM)──►  ejecución
 código fuente     análisis léxico           .pyc        bucle que lee
                   → árbol sintáctico (AST)              instrucción a
                   → bytecode                            instrucción
```

1. **Análisis**: el texto se convierte en tokens y luego en un AST (árbol de sintaxis abstracta). Aquí saltan los `SyntaxError`, *antes* de ejecutar nada.
2. **Compilación a bytecode**: instrucciones sencillas para una máquina de pila (`LOAD_FAST`, `BINARY_OP`, `RETURN_VALUE`...). Se puede ver con el módulo `dis`.
3. **Ejecución**: la **PVM** (Python Virtual Machine) es un gran bucle en C que lee cada instrucción del bytecode y la ejecuta.

## `__pycache__` y los `.pyc`

Cuando **importas** un módulo, CPython guarda su bytecode en `__pycache__/modulo.cpython-313.pyc` para no recompilarlo la próxima vez (solo si el `.py` no cambió). El script que lanzas directamente (`python script.py`) se compila en memoria y no deja `.pyc`.

- El `.pyc` **no** es código máquina: sigue necesitando la PVM.
- No hace que el programa corra más rápido, solo que **arranque** más rápido.
- Depende de la versión (`cpython-313`), por eso no se sube a git (está en `.gitignore`).

## Implementaciones de Python

"Python" es el lenguaje; hay varios programas que lo ejecutan:

- **CPython**: la oficial, escrita en C. Es la que usamos en Docker.
- **PyPy**: con compilador **JIT** (traduce a código máquina en caliente las partes que más se repiten); suele ser bastante más rápido.
- **Jython** (JVM), **IronPython** (.NET), **MicroPython** (microcontroladores).
- Desde 3.13, CPython trae un JIT **experimental** y una versión sin GIL (*free-threaded*), ambos desactivados por defecto.

## Consecuencias prácticas

- Los errores de sintaxis aparecen al cargar el archivo; los de tipos o nombres (`TypeError`, `NameError`) solo al **ejecutar** esa línea → importancia de los tests.
- El mismo `.py` corre en Mac, Linux o Windows sin recompilar.
- Para trabajo de CPU intenso Python es lento; por eso librerías como NumPy tienen el núcleo en C.

## Práctica

```bash
docker compose run --rm shell python ejercicios/02_bytecode.py
```
