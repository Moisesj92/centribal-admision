# Plan: centribal-admision — aprender Python y Django paso a paso

## Contexto
Reto de admisión: una API REST de **solicitudes de soporte** (tickets) con asunto, descripción, prioridad, estado, agente asignado, comentarios internos e historial de cambios. El objetivo doble es (1) aprender Python desde sus fundamentos y (2) entregar el proyecto, primero **sin framework** y luego con **Django + DRF**.

Restricción clave: **no tocar el Python del Mac** (hoy tiene 3.14.2 vía Homebrew). Todo corre en Docker (`docker` 29.3 y `compose` v5 ya instalados), y se puede reiniciar el entorno cuando quieras.

Carpeta de trabajo: `/Users/ajimenez/Downloads/centribal` (vacía). `gh` está autenticado como `Moisesj92` (SSH).

## Decisiones
- Repo **público** `Moisesj92/centribal-admision`.
- Imagen base: `python:3.13-slim` (Debian slim oficial). 3.13 en vez de 3.14 porque Django 5.2 LTS la soporta de forma oficial.
- Sin framework: `http.server` + `json` + `sqlite3` (solo librería estándar).
- Con framework: Django 5.2 LTS + Django REST Framework.
- Teoría en `docs/*.md` + scripts ejecutables en `ejercicios/`.
- Debug: `breakpoint()`/`pdb` en terminal y `debugpy` para conectar VS Code al contenedor.

## Estructura del repo
```
centribal-admision/
├── Dockerfile                 # python:3.13-slim, usuario no-root, WORKDIR /app
├── docker-compose.yml         # servicios: shell, api-stdlib (8000), api-django (8001)
├── requirements.txt           # django, djangorestframework, debugpy, pytest
├── .dockerignore / .gitignore / README.md
├── .vscode/launch.json        # "Attach to Docker" (debugpy en puerto 5678)
├── docs/
│   ├── 01-historia.md         # Guido van Rossum, ABC, 1991, filosofía (Zen of Python), 2→3
│   ├── 02-interpretado-o-compilado.md  # código fuente → bytecode (.pyc) → PVM; CPython
│   ├── 03-tipado.md           # dinámico + fuerte, duck typing, type hints opcionales
│   ├── 04-estructuras-de-control.md    # if/elif, for, while, match, try/except, comprehensions
│   └── 05-debug.md            # print, logging, breakpoint()/pdb, debugpy + VS Code
├── ejercicios/                # un script por tema, se ejecuta dentro del contenedor
│   ├── 02_bytecode.py         # usa `dis` para ver el bytecode
│   ├── 03_tipado.py
│   ├── 04_control.py
│   └── 05_debug.py            # bug intencional para cazar con pdb
├── fase1_sin_framework/
│   ├── dominio.py             # dataclasses Ticket, Comentario, Historial; enums Estado/Prioridad
│   ├── repositorio.py         # sqlite3: crear tablas, CRUD, registrar historial
│   ├── servidor.py            # BaseHTTPRequestHandler + enrutado manual
│   └── tests/test_dominio.py  # unittest (stdlib)
└── fase2_django/
    ├── manage.py, config/     # settings, urls
    └── soporte/               # models, serializers, views (ViewSets), urls, admin, tests
```

## Modelo del dominio (igual en ambas fases)
- **Ticket**: id, asunto, descripcion, prioridad (`baja|media|alta|critica`), estado (`abierto|en_progreso|resuelto|cerrado`), agente (nullable), creado/actualizado.
- **Comentario**: ticket, autor (agente), texto, es_interno=True, fecha.
- **Historial**: ticket, campo, valor_anterior, valor_nuevo, autor, fecha — se escribe automáticamente al cambiar estado o asignación.
- Reglas: transiciones de estado válidas (p. ej. no reabrir un `cerrado`), validación de prioridad.

## Endpoints REST
| Método | Ruta | Acción |
|---|---|---|
| POST | `/tickets/` | Cliente crea solicitud |
| GET | `/tickets/` · `/tickets/{id}/` | Listar / detalle (filtro por estado/prioridad en Django) |
| PATCH | `/tickets/{id}/estado/` | Cambiar estado → historial |
| PATCH | `/tickets/{id}/asignar/` | Asignar agente → historial |
| POST/GET | `/tickets/{id}/comentarios/` | Comentarios internos |
| GET | `/tickets/{id}/historial/` | Historial de cambios |

En Django: agentes = `User` de Django con `is_staff`; autenticación por sesión/token de DRF para endpoints de agente; crear ticket abierto al cliente.

## Pasos (una sesión por paso, explicando el detalle)
1. **Repo + entorno Docker**: `git init`, `.gitignore`, `Dockerfile`, `docker-compose.yml`, README con comandos (`docker compose run --rm shell`, `docker compose down -v` para reiniciar). `gh repo create centribal-admision --public --source . --push`. Comprobar `python --version` dentro del contenedor.
2. **Historia de Python** → `docs/01-historia.md`. Commit.
3. **Interpretado vs compilado** → doc + `ejercicios/02_bytecode.py` (ver `dis`, `__pycache__`).
4. **Tipado** → doc + ejercicio (dinámico/fuerte, type hints, `mypy` opcional).
5. **Estructuras de control** → doc + ejercicio.
6. **Debug** → doc + ejercicio con bug; practicar `breakpoint()` en terminal y attach de VS Code vía debugpy.
7. **Fase 1 sin framework**: dominio → repositorio sqlite → servidor HTTP → tests `unittest`. Probar con `curl`.
8. **Fase 2 Django + DRF**: `startproject`/`startapp`, modelos + migraciones, admin, serializers, ViewSets con `@action` para estado/asignar/comentarios/historial, tests. Comparar con la fase 1 (qué nos ahorra Django).
9. README final con instrucciones de ejecución y decisiones de diseño.

Cada paso termina en un commit y push; pauso al final de cada uno para que preguntes antes de seguir.

## Verificación
- `docker compose run --rm shell python --version` → 3.13.x (y el Mac sigue en 3.14.2 sin cambios).
- `gh repo view Moisesj92/centribal-admision` existe y es público.
- Fase 1: `docker compose up api-stdlib` + `curl` crear ticket → cambiar estado → ver historial; `python -m unittest`.
- Fase 2: `docker compose up api-django`, `python manage.py test`, misma secuencia con `curl` en el puerto 8001 y revisión en `/admin`.
- Debug: un breakpoint en VS Code se detiene dentro del contenedor.
