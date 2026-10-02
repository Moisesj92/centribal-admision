# Debug en Python

De menos a más potente: `print` → `logging` → `breakpoint()`/`pdb` → debugger visual (VS Code + `debugpy`).

## 1. `print` (rápido y sucio)

```python
print(f"{total=}")          # f-string con '=': imprime 'total=42'
print(repr(texto))          # muestra comillas, espacios y \n ocultos
```

Útil para mirar algo una vez. Hay que acordarse de borrarlo.

## 2. `logging` (prints que se quedan)

```python
import logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)

log.debug("detalle para depurar: %s", valor)
log.info("ticket %s creado", ticket_id)
log.warning("prioridad desconocida")
log.error("fallo al guardar")
log.exception("dentro de un except: incluye el traceback")
```

Niveles: `DEBUG < INFO < WARNING < ERROR < CRITICAL`. Cambiando el nivel se muestran u ocultan mensajes sin tocar el código. Es lo que se usa en producción (Django tiene su propia configuración de `LOGGING`).

## 3. Leer un traceback

Se lee **de abajo arriba**: la última línea dice el tipo de error y el mensaje; encima, la línea exacta donde ocurrió; más arriba, quién llamó a quién.

```
Traceback (most recent call last):
  File "app.py", line 10, in <module>      ← punto de entrada
    main()
  File "app.py", line 6, in main           ← función intermedia
    return 10 / cantidad
ZeroDivisionError: division by zero        ← empieza a leer aquí
```

## 4. `breakpoint()` y `pdb` (debugger en la terminal)

Pones `breakpoint()` en el código y, al llegar ahí, el programa se **pausa** y aparece el prompt `(Pdb)`. Necesita una terminal interactiva: `docker compose run --rm shell` (sin `-T`).

| Comando | Qué hace |
|---|---|
| `l` / `ll` | ver el código alrededor / la función entera |
| `n` | siguiente línea (sin entrar en funciones) |
| `s` | entrar en la función de esta línea |
| `c` | continuar hasta el siguiente breakpoint |
| `r` | seguir hasta que la función actual retorne |
| `p expr` / `pp expr` | imprimir (bonito) una expresión |
| `w` | ver la pila de llamadas; `u` / `d` subir y bajar por ella |
| `b 25` | poner un breakpoint en la línea 25 |
| `display x` | mostrar `x` cada vez que se pare |
| `interact` | abrir un intérprete Python con las variables actuales |
| `q` | salir |

Otras formas:

```bash
python -m pdb script.py           # arranca parado en la primera línea
python -i script.py               # al terminar (o fallar) deja el intérprete abierto
PYTHONBREAKPOINT=0 python app.py  # desactiva todos los breakpoint() sin borrarlos
```

Tras una excepción, dentro de `python -i`: `import pdb; pdb.pm()` abre el debugger en el punto del fallo (*post-mortem*).

## 5. VS Code + `debugpy` (debugger visual dentro de Docker)

`debugpy` es el servidor de depuración que usa la extensión de Python de VS Code. El programa corre **en el contenedor** y VS Code se **conecta** por el puerto 5678.

1. Arrancar el script esperando al debugger (publicando puertos con `--service-ports`):

   ```bash
   docker compose run --rm --service-ports shell \
     python -Xfrozen_modules=off -m debugpy --listen 0.0.0.0:5678 --wait-for-client ejercicios/05_debug.py
   ```

2. En VS Code: poner un punto rojo (breakpoint) en el margen, ir a *Run and Debug* y lanzar **"Attach to Docker"** (definido en `.vscode/launch.json`).
3. El `pathMappings` traduce rutas: la carpeta del proyecto en el Mac es `/app` dentro del contenedor.

Para depurar la aplicación Django es igual, cambiando el script por `manage.py runserver 0.0.0.0:8000 --noreload` y añadiendo `-p 8000:8000` (antes, para el servicio `web` con `docker compose stop web`).

## Práctica

`ejercicios/05_debug.py` tiene un **bug intencional**: el informe de horas por prioridad sale mal. Encuéntralo con `breakpoint()` o con VS Code, sin leer la solución.

```bash
docker compose run --rm shell python ejercicios/05_debug.py
```

<details>
<summary>Solución</summary>

En `horas_por_prioridad` el diccionario `acumulado = {}` se crea **dentro** del `for`, así que se reinicia en cada ticket y solo sobrevive el último. Hay que crearlo antes del bucle. Con `n` y `p acumulado` en pdb se ve cómo se vacía en cada vuelta.

</details>
