# Docker en detalle

Para usar el proyecto basta con `docker compose up -d` (ver el [README](../README.md)). Esta página explica cómo está montado.

## Imagen ([`Dockerfile`](../Dockerfile))

Una imagen de desarrollo:

- `python:3.13-slim` con las dependencias de [`requirements.txt`](../requirements.txt): Django 5.2 LTS, DRF, django-filter y las herramientas de desarrollo (debugpy, mypy, ruff).
- **El código no se copia dentro**: llega por un volumen (`.:/app`), así que los cambios se ven al instante y `runserver` se recarga solo.
- **Usuario sin privilegios** (`app`, UID 1000) en lugar de root.
- **Orden de capas**: primero `requirements.txt`, después nada más. Cambiar código no obliga a reconstruir; cambiar dependencias sí.
- **Cache mount de pip**: al reconstruir no se vuelven a descargar todos los paquetes.
- **`.dockerignore`**: ni `.git` ni la base de datos se envían a Docker al construir.

Las versiones de `requirements.txt` tienen límite superior (`<5.3`, `<4`…), para que una versión mayor nueva no rompa el proyecto sin avisar.

## Servicios ([`compose.yaml`](../compose.yaml))

| Servicio | Puerto | Arranca con | Para qué |
|---|---|---|---|
| `web` | 8000 | `docker compose up -d` | La aplicación. Al arrancar: migraciones → `preparar_demo` → `runserver` |
| `shell` | 5678 | `docker compose run --rm shell` | Terminal para tests, ejercicios, `manage.py` y depuración |

- `shell` está en un **perfil** (`tools`), así que `docker compose up` solo arranca `web`.
- `preparar_demo` es **idempotente**: crea los usuarios si no existen y los tickets de ejemplo solo si la base de datos no tiene ninguno. Reiniciar no duplica nada.
- `web` tiene un **healthcheck** contra `/salud/`: `docker compose ps` muestra `healthy` cuando la aplicación ya responde.
- La base de datos es `db.sqlite3`, en la raíz del proyecto (git la ignora).

## Comandos

```bash
docker compose up -d                                    # arrancar (construye la imagen si hace falta)
docker compose watch                                    # igual, y reconstruye solo al cambiar requirements.txt
docker compose ps                                       # estado: healthy / unhealthy
docker compose logs -f web                              # logs
docker compose exec web python manage.py shell          # consola de Django con los modelos cargados
docker compose run --rm shell                           # terminal en un contenedor nuevo
docker compose build                                    # reconstruir la imagen
docker compose down                                     # parar
docker compose down --rmi local                         # parar y borrar también la imagen
```

## Depurar con VS Code

Para el servicio web y arranca el servidor esperando al debugger. Después conecta con **"Attach to Docker"** ([`.vscode/launch.json`](../.vscode/launch.json)):

```bash
docker compose stop web
docker compose run --rm --service-ports -p 8000:8000 shell \
  python -Xfrozen_modules=off -m debugpy --listen 0.0.0.0:5678 --wait-for-client \
  manage.py runserver 0.0.0.0:8000 --noreload
```

Más sobre depuración (pdb, `breakpoint()`, logging): [05-debug.md](05-debug.md).
