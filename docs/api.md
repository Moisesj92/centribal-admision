# Referencia de la API

API REST con Django REST Framework, bajo `/api/`. En el navegador, http://localhost:8000/api/ muestra la **API navegable** (hay que entrar como agente).

## Autenticación

Crear un ticket es público. Todo lo demás exige un **agente** (`ana`, `luis` o `sara`; contraseña `agente-dev-123`) con un token:

```bash
curl -X POST http://localhost:8000/api/token/ -d 'username=ana&password=agente-dev-123'
# {"token": "4b81f1bb..."}
```

y se manda en cada petición con la cabecera `Authorization: Token <token>`.

## Endpoints

| Método | Ruta | Acción | Acceso |
|---|---|---|---|
| `POST` | `/api/tickets/` | Crear solicitud | Público |
| `GET` | `/api/tickets/` | Listar (paginado, con filtros) | Agente |
| `GET` | `/api/tickets/{id}/` | Detalle | Agente |
| `PATCH` | `/api/tickets/{id}/estado/` | Cambiar estado (deja historial) | Agente |
| `PATCH` | `/api/tickets/{id}/asignar/` | Asignar o desasignar (deja historial) | Agente |
| `POST` | `/api/tickets/{id}/comentarios/` | Añadir comentario interno | Agente |
| `GET` | `/api/tickets/{id}/comentarios/` | Listar comentarios (paginado) | Agente |
| `GET` | `/api/tickets/{id}/historial/` | Ver historial (paginado) | Agente |
| `POST` | `/api/token/` | Obtener token con `username` y `password` | Público |

**Filtros del listado**: `?estado=abierto`, `?prioridad=alta`, `?agente__username=luis`. Se pueden combinar.

**Paginación**: los listados devuelven 20 elementos por página con este formato; la siguiente página es `?page=2`:

```json
{"count": 42, "next": "http://localhost:8000/api/tickets/?page=2", "previous": null, "results": [ ... ]}
```

## Ejemplos

```bash
B=http://localhost:8000/api
J="Content-Type: application/json"
T="Authorization: Token $(curl -s -X POST $B/token/ -d 'username=ana&password=agente-dev-123' | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"
```

**Crear una solicitud** (público) → `201`

```bash
curl -X POST $B/tickets/ -H "$J" \
  -d '{"asunto": "No puedo entrar", "descripcion": "Error 500 al hacer login", "prioridad": "alta"}'
```

```json
{
  "id": 6,
  "asunto": "No puedo entrar",
  "descripcion": "Error 500 al hacer login",
  "prioridad": "alta",
  "estado": "abierto",
  "agente": null,
  "creado": "2026-10-03T00:48:45.413651Z",
  "actualizado": "2026-10-03T00:48:45.413674Z"
}
```

Si el cliente manda `estado` o `agente`, se ignoran: un ticket siempre nace `abierto` y sin agente.

**Listar con filtros** → `200`

```bash
curl "$B/tickets/?estado=abierto&prioridad=alta" -H "$T"
```

**Asignar** (`null` para desasignar) → `200` con el ticket actualizado

```bash
curl -X PATCH $B/tickets/6/asignar/ -H "$T" -H "$J" -d '{"agente": "luis"}'
```

**Cambiar estado** → `200` con el ticket actualizado

```bash
curl -X PATCH $B/tickets/6/estado/ -H "$T" -H "$J" -d '{"estado": "en_progreso"}'
```

**Comentar** → `201`

```bash
curl -X POST $B/tickets/6/comentarios/ -H "$T" -H "$J" -d '{"texto": "Reproducido en staging"}'
```

```json
{"id": 3, "autor": "ana", "texto": "Reproducido en staging", "fecha": "2026-10-03T00:50:11.467109Z"}
```

**Historial** → `200`

```bash
curl $B/tickets/6/historial/ -H "$T"
```

```json
{"count": 2, "next": null, "previous": null, "results": [
  {"id": 7, "campo": "agente", "valor_anterior": null,      "valor_nuevo": "luis",        "autor": "ana", "fecha": "..."},
  {"id": 8, "campo": "estado", "valor_anterior": "abierto", "valor_nuevo": "en_progreso", "autor": "ana", "fecha": "..."}
]}
```

## Códigos de respuesta

| Código | Cuándo |
|---|---|
| `200` / `201` | Correcto / creado |
| `400` | Datos inválidos o regla incumplida (transición no permitida, ticket cerrado, texto demasiado largo…) |
| `401` | Falta la cabecera `Authorization` |
| `403` | El usuario no es agente |
| `404` | El ticket no existe |
| `405` | Método no permitido (p. ej. `DELETE /api/tickets/1/`) |
| `409` | Otra petición cambió el ticket a la vez: vuelve a pedirlo y reintenta |

Formato de los errores (el de DRF):

```jsonc
{"estado": ["\"pausado\" no es una elección válida."]}                 // error de un campo
{"non_field_errors": ["El ticket ya está asignado a ese agente."]}     // regla de negocio
{"detail": "Las credenciales de autenticación no se proveyeron."}     // autenticación / permisos
```
