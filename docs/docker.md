# Docker en detalle

Para usar el proyecto basta con `docker compose up -d` (ver el [README](../README.md)). Esta página explica cómo está montado.

## Imagen: un Dockerfile, dos destinos

[`Dockerfile`](../Dockerfile) es **multi-stage**: varias etapas en un archivo, y cada servicio elige con `target` hasta dónde construir.

```
base  python:3.13-slim + usuario "app" (sin privilegios) + requirements.txt
 ├── dev   + requirements-dev.txt (debugpy, mypy, ruff). El código llega por volumen → recarga en vivo
 └── prod  + código copiado + collectstatic + gunicorn + HEALTHCHECK. DEBUG=0, BD en /data
```

| | `dev` (servicio `web`) | `prod` (servicio `prod`) |
|---|---|---|
| Servidor | `runserver` (recarga al guardar) | gunicorn con 3 workers |
| Código | Volumen `.:/app` (en vivo) | Copiado dentro de la imagen |
| Estáticos | Los sirve Django | `collectstatic` + WhiteNoise |
| `DEBUG` | Activado | Desactivado |
| Base de datos | `db.sqlite3` en la raíz del proyecto | Volumen `datos-prod` (`/data/db.sqlite3`) |
| Datos de demo | Sí (`preparar_demo` al arrancar) | No |
| Tamaño aprox. | ~310 MB | ~200 MB |

Buenas prácticas aplicadas:

- **Usuario sin privilegios** (`app`, UID 1000) en lugar de root.
- **Orden de capas**: primero `requirements.txt`, luego el código. Cambiar código no reinstala dependencias.
- **Cache mount de pip**: al cambiar `requirements.txt` no se vuelve a descargar todo.
- **`.dockerignore`**: ni `.git`, ni `.env`, ni la base de datos entran en la imagen.
- **Healthcheck** contra `/salud/`: `docker compose ps` muestra `healthy` solo si la aplicación responde.
- **`exec gunicorn`**: gunicorn recibe directamente las señales de parada (cierre limpio).

## Servicios ([`compose.yaml`](../compose.yaml))

| Servicio | Puerto | Arranca con | Para qué |
|---|---|---|---|
| `web` | 8000 | `docker compose up -d` | Desarrollo. Al arrancar: migraciones → `preparar_demo` → `runserver` |
| `shell` | 5678 | `docker compose run --rm shell` | Terminal para tests, ejercicios, `manage.py` y depuración |
| `prod` | 8001 | `docker compose --profile prod up -d prod` | La imagen de producción funcionando en local |

`shell` y `prod` están en **perfiles**, así que `docker compose up` solo arranca `web`.

`preparar_demo` es **idempotente**: crea los usuarios si no existen y los tickets de ejemplo solo si la base de datos no tiene ninguno. Reiniciar no duplica nada.

## Dependencias

| Archivo | Contenido | Imagen |
|---|---|---|
| [`requirements.txt`](../requirements.txt) | Django 5.2 LTS, DRF, django-filter, gunicorn, whitenoise | `dev` y `prod` |
| [`requirements-dev.txt`](../requirements-dev.txt) | lo anterior + debugpy, mypy, ruff | solo `dev` |

Las versiones tienen límite superior (`<5.3`, `<4`…), para que una versión mayor nueva no rompa el proyecto sin avisar.

## Variables de entorno

En desarrollo no hace falta ninguna. Para cambiar algo, copia [`.env.example`](../.env.example) a `.env` (Compose lo lee solo y git lo ignora).

| Variable | Por defecto | Para qué |
|---|---|---|
| `DJANGO_DEBUG` | `1` | `0` desactiva el modo debug |
| `DJANGO_SECRET_KEY` | valor de desarrollo | Clave criptográfica |
| `DJANGO_ALLOWED_HOSTS` | `*` con debug | Dominios permitidos cuando `DJANGO_DEBUG=0` |
| `DJANGO_DB_PATH` | `db.sqlite3` (en `prod`: `/data/db.sqlite3`) | Ruta de la base de datos |

## Comandos

```bash
docker compose up -d                                    # arrancar (construye la imagen si hace falta)
docker compose watch                                    # igual, y reconstruye solo al cambiar requirements*.txt
docker compose ps                                       # estado: healthy / unhealthy
docker compose logs -f web                              # logs
docker compose exec web python manage.py shell          # consola de Django con los modelos cargados
docker compose run --rm shell                           # terminal en un contenedor nuevo
docker compose build                                    # reconstruir la imagen de desarrollo
docker compose down                                     # parar

docker compose --profile prod up -d --build prod        # producción en local → http://localhost:8001
docker compose --profile prod exec prod python manage.py check --deploy
docker compose --profile prod down                      # parar todo, incluido prod

docker compose --profile prod down --rmi local -v       # borrar contenedores, imágenes y volúmenes
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
