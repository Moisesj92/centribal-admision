# centribal-admision

API REST de **gestión de solicitudes de soporte** (caso ficticio) para practicar Python y Django.
Se construye en dos fases: primero sin framework (solo librería estándar) y luego con Django + Django REST Framework.

## Caso de uso

Un cliente crea una solicitud con **asunto**, **descripción** y **prioridad**. Cada solicitud tiene un **estado** y puede asignarse a un **agente** interno. Los agentes pueden:

- Cambiar el estado de una solicitud.
- Agregar comentarios internos.
- Revisar el historial de cambios.

## Entorno

Todo corre en Docker (`python:3.13-slim`); no hace falta instalar Python en el ordenador.

```bash
docker compose build                                  # construir la imagen
docker compose run --rm --service-ports shell         # terminal dentro del contenedor (puerto 5678 para debugpy)
docker compose run --rm shell python --version        # comando suelto
docker compose up api-stdlib                          # fase 1 → http://localhost:8000/tickets/
docker compose up api-django                          # fase 2 → API en http://localhost:8001/tickets/ y UI en http://localhost:8001/ui/
docker compose down --rmi local                       # borrar contenedores e imagen y empezar de cero
```

## Estructura

| Carpeta | Contenido |
|---|---|
| `docs/` | Teoría: historia, interpretado vs compilado, tipado, control de flujo, debug |
| `ejercicios/` | Un script por tema: `python ejercicios/02_bytecode.py`, etc. |
| `fase1_sin_framework/` | API con `http.server` + `sqlite3` → [README](fase1_sin_framework/README.md) |
| `fase2_django/` | API con Django + DRF y UI con templates → [README](fase2_django/README.md) (incluye la comparación entre fases) |
| `.vscode/launch.json` | "Attach to Docker" para depurar con VS Code ([docs/05-debug.md](docs/05-debug.md)) |

## API

| Método | Ruta | Acción | Quién |
|---|---|---|---|
| POST | `/tickets/` | Crear solicitud | Cualquiera |
| GET | `/tickets/` | Listar (filtros `?estado=` y `?prioridad=`) | Agente |
| GET | `/tickets/{id}/` | Detalle | Agente |
| PATCH | `/tickets/{id}/estado/` | `{"estado": "en_progreso"}` → queda en el historial | Agente |
| PATCH | `/tickets/{id}/asignar/` | `{"agente": "luis"}` (o `null`) → queda en el historial | Agente |
| POST / GET | `/tickets/{id}/comentarios/` | `{"texto": "..."}` comentarios internos | Agente |
| GET | `/tickets/{id}/historial/` | Cambios de estado y de asignación | Agente |

- **Prioridad**: `baja`, `media` (por defecto), `alta`, `critica`.
- **Estado**: `abierto` → `en_progreso` → `resuelto` → `cerrado`. Se puede volver atrás (reabrir un resuelto, devolver a abierto), pero **un ticket cerrado no se reabre ni se reasigna**.
- **Autenticación de agentes**: en la fase 1, cabecera `X-Agente: ana`; en la fase 2, `Authorization: Token <clave>` o sesión.

## Tests

```bash
docker compose run --rm -w /app/fase1_sin_framework shell python -m unittest discover -s tests -v
docker compose run --rm -w /app/fase2_django shell python manage.py test
```

## Decisiones de diseño

- **Docker en vez de instalar Python**: el Mac no se toca y cualquiera reproduce el mismo entorno. Python 3.13 porque Django 5.2 LTS la soporta de forma oficial.
- **Mismo dominio en las dos fases**: así se puede comparar qué aporta el framework sin que cambien las reglas.
- **El historial se escribe en la misma transacción que el cambio**: si algo falla, no queda un ticket cambiado sin su historial (ni al revés).
- **Estado y agente no se editan en el ticket directamente**: solo por sus endpoints (`/estado/`, `/asignar/`), que validan la transición y dejan historial. Por eso son de solo lectura en el serializer y en el admin.
- **Reglas en el dominio, no en HTTP**: en la fase 1 el dominio no sabe de HTTP ni de SQL y se prueba de forma aislada; en la fase 2 las transiciones viven en el modelo y la validación en los serializers.
- **Reglas en el modelo en la fase 2**: la UI (forms) y la API (serializers) llaman a las mismas validaciones, así no se duplican.
- **Agente = `User` con `is_staff`** en Django: reutiliza el sistema de usuarios, permisos y admin en vez de crear un modelo propio.
- **SQLite** en las dos fases: sin servidor de base de datos extra. Para producción se cambiaría a PostgreSQL solo en `DATABASES`.
- **Simplificaciones conscientes**: la autenticación de la fase 1 es solo una cabecera (no segura); la clave secreta de Django tiene un valor de desarrollo por defecto y se sobrescribe con `DJANGO_SECRET_KEY`.
