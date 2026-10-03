# syntax=docker/dockerfile:1
# Imagen de desarrollo: el código llega por volumen (compose.yaml) y runserver recarga al guardar.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Usuario sin privilegios en lugar de root.
ARG UID=1000
RUN useradd --create-home --uid ${UID} app

# Primero solo requirements.txt: mientras no cambie, Docker reutiliza esta capa aunque cambie
# el código. El cache mount evita volver a descargar los paquetes al reconstruir.
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

USER app
EXPOSE 8000 5678
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
