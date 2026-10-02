# Estructuras de control

En Python los bloques se marcan con **indentación** (4 espacios por convención), no con llaves. La línea que abre un bloque termina en `:`.

## Condicionales: `if / elif / else`

```python
if prioridad == "critica":
    avisar()
elif prioridad in ("alta", "media"):
    encolar()
else:
    pass            # bloque vacío
```

- Valores "falsy": `False`, `None`, `0`, `0.0`, `""`, `[]`, `{}`, `set()`. Todo lo demás es verdadero.
- Operadores lógicos en palabras: `and`, `or`, `not`. Comparaciones encadenadas: `0 < x <= 10`.
- `x is None` (identidad) en vez de `x == None`.
- Expresión condicional (ternario): `estado = "ok" if valido else "error"`.

## `match` (Python 3.10+)

Coincidencia de **patrones**, más potente que un `switch`: compara valores, desestructura listas/dicts y admite condiciones (`if`).

```python
match peticion:
    case {"accion": "crear", "asunto": str(asunto)}:
        crear(asunto)
    case {"accion": "cerrar", "id": int(id)} if id > 0:
        cerrar(id)
    case ["GET", ruta]:
        leer(ruta)
    case _:
        error()     # comodín: lo que no encaje arriba
```

## Bucles

### `for`: recorre cualquier iterable

```python
for ticket in tickets: ...
for i in range(5): ...                     # 0..4
for i, ticket in enumerate(tickets): ...   # índice + valor
for nombre, edad in zip(nombres, edades): ...
for clave, valor in diccionario.items(): ...
```

No hay `for (i=0; i<n; i++)`: casi nunca hace falta el índice.

### `while`: mientras la condición sea cierta

```python
intentos = 0
while intentos < 3:
    intentos += 1          # no existe i++
```

### `break`, `continue` y el `else` de los bucles

- `break` sale del bucle; `continue` salta a la siguiente vuelta.
- Un bucle puede tener `else`: se ejecuta **solo si no hubo `break`** (útil en búsquedas).

```python
for t in tickets:
    if t.id == buscado:
        break
else:
    print("no encontrado")
```

## Excepciones: `try / except / else / finally`

```python
try:
    numero = int(texto)
except ValueError as error:      # captura solo el error esperado
    print("no es un número:", error)
else:
    print("ok", numero)           # si no hubo excepción
finally:
    print("siempre se ejecuta")   # cerrar recursos, etc.
```

- `raise ValueError("mensaje")` lanza una excepción; podemos crear las nuestras heredando de `Exception`.
- Estilo Python **EAFP** ("es más fácil pedir perdón que permiso"): intentar y capturar, en vez de comprobar todo antes.
- `with open(...) as f:` es un *context manager*: garantiza cerrar el recurso aunque haya errores.

## Comprehensions

Forma corta de construir colecciones a partir de otra:

```python
cuadrados  = [n * n for n in range(10)]
pares      = [n for n in range(10) if n % 2 == 0]
por_id     = {t.id: t for t in tickets}            # dict
estados    = {t.estado for t in tickets}            # set
total      = sum(t.horas for t in tickets)          # generador: no crea lista
```

Si una comprehension no cabe en una línea legible, mejor un `for` normal.

## Práctica

```bash
docker compose run --rm shell python ejercicios/04_control.py
```
