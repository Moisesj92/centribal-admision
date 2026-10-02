# syntax=docker/dockerfile:1
#
# Imagen en varias etapas (multi-stage):
#   base → dependencias de ejecución, compartidas
#   dev  → + herramientas de desarrollo; el código llega por volumen (compose.yaml)
#   prod → código copiado dentro, estáticos recopilados, gunicorn, sin herramientas de desarrollo
#
#   docker build --target dev  -t centribal-admision:dev .
#   docker build --target prod -t centribal-admision:prod .

ARG PYTHON_VERSION=3.13

# ---------------------------------------------------------------- base
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Usuario sin privilegios: si alguien explota la app, no es root dentro del contenedor.
ARG UID=1000
RUN useradd --create-home --uid ${UID} app

# Primero solo requirements.txt: mientras no cambie, Docker reutiliza esta capa
# aunque cambie el código. El cache mount evita volver a descargar paquetes.
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# ---------------------------------------------------------------- dev
FROM base AS dev

COPY requirements-dev.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-dev.txt

USER app
EXPOSE 8000 5678
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---------------------------------------------------------------- prod
FROM base AS prod

# En producción no hace falta escribir .pyc en disco en cada arranque.
ENV PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_DEBUG=0 \
    DJANGO_DB_PATH=/data/db.sqlite3

COPY --chown=app:app . .

# Estáticos (admin, API navegable) a /app/staticfiles; los sirve WhiteNoise.
# La clave es solo para este paso: la real llega por variable de entorno al arrancar.
RUN DJANGO_SECRET_KEY=solo-para-collectstatic python manage.py collectstatic --noinput \
    && mkdir -p /data && chown app:app /data

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/salud/')"

# Migraciones al arrancar y después gunicorn (exec: gunicorn pasa a ser el proceso principal
# y recibe directamente las señales de parada de Docker).
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --access-logfile -"]
