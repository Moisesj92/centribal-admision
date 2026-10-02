# Tipado en Python

Python tiene tipado **dinámico** y **fuerte**. Son dos ejes distintos:

|  | Débil | Fuerte |
|---|---|---|
| **Estático** | C | Java, Go, Rust |
| **Dinámico** | JavaScript, PHP | **Python**, Ruby |

## Dinámico: el tipo va con el valor, no con la variable

Una variable es solo una **etiqueta** que apunta a un objeto. El objeto sabe su tipo; la variable no tiene tipo propio y puede apuntar a otro objeto distinto después.

```python
x = 10          # x apunta a un int
x = "diez"      # ahora apunta a un str: válido
type(x)         # <class 'str'>
```

El tipo se comprueba **al ejecutar**, no antes. Un error de tipos en una rama que nunca se ejecuta no se descubre.

## Fuerte: no hay conversiones implícitas raras

```python
"3" + 4         # TypeError: can only concatenate str (not "int") to str
int("3") + 4    # 7  → la conversión hay que pedirla
```

En JavaScript `"3" + 4` da `"34"`. Python prefiere fallar a adivinar ("Explicit is better than implicit").

Excepciones razonables: `int` y `float` se mezclan (`1 + 2.5 == 3.5`) y cualquier objeto tiene un valor de verdad (`if lista:` es falso si está vacía).

## Duck typing

> "Si camina como un pato y grazna como un pato, es un pato."

No importa la clase de un objeto sino si tiene los métodos que necesitas. `len()` funciona con cualquier cosa que tenga `__len__`; un `for` con cualquier cosa iterable (lista, string, archivo, generador...).

## Mutables e inmutables

- **Inmutables**: `int`, `float`, `str`, `tuple`, `frozenset`, `bool`, `None`. "Modificarlos" crea un objeto nuevo.
- **Mutables**: `list`, `dict`, `set`, objetos de clases propias. Si dos variables apuntan al mismo objeto, un cambio se ve desde ambas.

```python
a = [1, 2]
b = a           # misma lista, no una copia
b.append(3)
a               # [1, 2, 3]
```

Trampa clásica: no uses un mutable como valor por defecto (`def f(x=[])`), se comparte entre llamadas.

## Type hints (anotaciones de tipo)

Desde Python 3.5 se pueden **anotar** tipos. Son documentación que entienden el editor y herramientas como `mypy`, pero **Python no las comprueba al ejecutar**.

```python
def total(precios: list[float], descuento: float = 0.0) -> float:
    return sum(precios) * (1 - descuento)

def buscar(id: int) -> str | None: ...   # puede devolver None
```

- `list[int]`, `dict[str, int]`, `tuple[int, ...]`, `X | None` (antes `Optional[X]`).
- `mypy archivo.py` revisa los tipos sin ejecutar el código (análisis estático).
- En este proyecto las usamos en `dataclasses` y en DRF ayudan a leer el código.

## Herramientas útiles

```python
type(x)                 # tipo exacto
isinstance(x, (int, float))  # ¿es de este tipo (o subclase)?
id(x)                   # identidad del objeto
a is b                  # ¿mismo objeto?   a == b  → ¿mismo valor?
```

## Práctica

```bash
docker compose run --rm shell python ejercicios/03_tipado.py
docker compose run --rm shell mypy ejercicios/03_tipado.py   # verá el error marcado
```

> Ojo: `mypy` solo revisa por defecto las funciones que tienen alguna anotación. Una función sin hints se considera "no tipada" y su cuerpo no se comprueba.
