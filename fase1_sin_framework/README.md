# Fase 1: API sin framework

Solo librería estándar: `http.server` (HTTP), `json`, `sqlite3` (base de datos), `dataclasses` y `enum` (modelo), `unittest` (tests).

## Capas

| Archivo | Responsabilidad | Sabe de... |
|---|---|---|
| `dominio.py` | `Ticket`, `Comentario`, `Historial`, enums y reglas (transiciones, validación) | nada externo |
| `repositorio.py` | Tablas, consultas SQL y transacciones; convierte filas ↔ dataclasses | SQL |
| `servidor.py` | Enrutado por regex, lectura/escritura JSON, cabecera de agente, códigos HTTP | HTTP |

El dominio lanza `ErrorValidacion` / `TransicionInvalida`, el repositorio `NoEncontrado`, y el servidor las traduce a 400 / 404. Así las reglas se prueban sin HTTP ni base de datos.

## Autenticación (simplificada)

Crear un ticket es público (lo hace el cliente). El resto exige la cabecera `X-Agente` con un agente existente (`ana` o `luis`, creados al arrancar): sin cabecera → 401, agente desconocido → 403. Es solo para practicar; en la fase 2 se usa la autenticación real de Django.

## Ejecutar

```bash
docker compose up api-stdlib                                            # http://localhost:8000
docker compose run --rm -w /app/fase1_sin_framework shell python -m unittest discover -s tests -v
```

## Probar con curl

```bash
B=http://localhost:8000
curl -X POST $B/tickets/ -d '{"asunto":"No puedo entrar","descripcion":"Error 500","prioridad":"alta"}'
curl $B/tickets/?estado=abierto -H 'X-Agente: ana'
curl -X PATCH $B/tickets/1/asignar/ -H 'X-Agente: ana'  -d '{"agente":"luis"}'
curl -X PATCH $B/tickets/1/estado/  -H 'X-Agente: luis' -d '{"estado":"en_progreso"}'
curl -X POST  $B/tickets/1/comentarios/ -H 'X-Agente: luis' -d '{"texto":"Reproducido"}'
curl $B/tickets/1/historial/ -H 'X-Agente: ana'
```

## Lo que hubo que hacer a mano

Enrutado y parámetros de URL, parseo y validación del JSON, serialización de respuestas, códigos de error, SQL y migración del esquema, transacciones, autenticación. Todo eso es lo que Django + DRF nos dará hecho en la fase 2.
