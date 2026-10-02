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
docker compose build                              # construir la imagen
docker compose run --rm --service-ports shell     # terminal dentro del contenedor
docker compose run --rm shell python --version    # comando suelto
docker compose down --rmi local                   # borrar todo y empezar de cero
```

## Estructura

| Carpeta | Contenido |
|---|---|
| `docs/` | Teoría: historia, interpretado vs compilado, tipado, control de flujo, debug |
| `ejercicios/` | Scripts para practicar cada tema |
| `fase1_sin_framework/` | API con `http.server` + `sqlite3` |
| `fase2_django/` | API con Django + DRF |
