# Fase 2: Django + Django REST Framework

La misma API que la fase 1 (mismos endpoints, mismas reglas) con Django 5.2 LTS, DRF y `django-filter`.

## Piezas

| Archivo | Qué hace |
|---|---|
| `config/settings.py` | Apps instaladas, base de datos, configuración de DRF (autenticación, permisos, filtros) |
| `config/urls.py` | `/admin/`, `/token/`, `/api-auth/` y las rutas de `soporte` |
| `soporte/models.py` | `Ticket`, `Comentario`, `Historial` + `TextChoices` y transiciones. `cambiar_estado()` y `asignar()` escriben el historial dentro de `transaction.atomic` |
| `soporte/serializers.py` | Validación de entrada y JSON de salida. `EstadoSerializer` y `AsignarSerializer` aplican las reglas del negocio |
| `soporte/views.py` | `TicketViewSet` con `@action` para `estado`, `asignar`, `comentarios` e `historial` |
| `soporte/urls.py` | `DefaultRouter`: genera las URLs del ViewSet |
| `soporte/admin.py` | Panel de administración con comentarios e historial dentro del ticket |
| `soporte/management/commands/crear_agentes.py` | Crea los agentes `ana` y `luis` y muestra sus tokens |
| `soporte/forms.py`, `views_ui.py`, `urls_ui.py`, `templates/` | Interfaz HTML con templates de Django (ver abajo) |
| `soporte/tests/` | Tests de la API (`APITestCase`) y de la UI (`TestCase`) |

## Dos interfaces, un mismo modelo

| | UI (`/ui/`) | API (`/tickets/`) |
|---|---|---|
| Para | Personas en el navegador | Programas: frontend JS, app móvil, integraciones |
| Devuelve | HTML generado con templates | JSON |
| Valida con | `forms.py` | `serializers.py` |
| Vistas | `views_ui.py` (funciones) | `views.py` (ViewSet de DRF) |
| Login | Sesión: `/cuentas/login/` | Token o sesión |

Las reglas del negocio (`validar_estado`, `validar_asignacion`) viven en el **modelo**, y los forms y los serializers solo las llaman. Por eso un cambio hecho en la UI aparece en la API y al revés, y una regla nueva se escribe una sola vez.

- `/ui/nuevo/`: formulario público para que el cliente abra una solicitud.
- `/ui/`: lista con filtros (estado, prioridad, asignados a mí, sin asignar). Solo agentes.
- `/ui/tickets/<id>/`: detalle con cambio de estado (solo ofrece las transiciones válidas), asignación, comentarios e historial.

## Agentes y autenticación

Un agente es un `User` con `is_staff=True`. El permiso por defecto (`IsAdminUser`) lo exige en todo menos en `POST /tickets/` (público). Hay dos formas de autenticarse:

- **Token** (curl, otras apps): `Authorization: Token <clave>`. Sin credenciales → 401; con un usuario que no es staff → 403.
- **Sesión** (navegador): entrar en `/api-auth/login/` o en `/admin/` y usar la API navegable de DRF.

## Ejecutar

```bash
docker compose up api-django                                               # aplica migraciones y arranca en :8001
docker compose exec api-django python manage.py crear_agentes              # agentes + tokens
docker compose exec api-django python manage.py createsuperuser            # para entrar a /admin/
docker compose run --rm -w /app/fase2_django shell python manage.py test   # tests
```

## Probar con curl

```bash
B=http://localhost:8001; T="Authorization: Token <token de ana>"; J="Content-Type: application/json"
curl -X POST $B/tickets/ -H "$J" -d '{"asunto":"No puedo entrar","descripcion":"Error 500","prioridad":"alta"}'
curl "$B/tickets/?estado=abierto&prioridad=alta" -H "$T"
curl -X PATCH $B/tickets/1/asignar/ -H "$T" -H "$J" -d '{"agente":"luis"}'
curl -X PATCH $B/tickets/1/estado/  -H "$T" -H "$J" -d '{"estado":"en_progreso"}'
curl -X POST  $B/tickets/1/comentarios/ -H "$T" -H "$J" -d '{"texto":"Reproducido"}'
curl $B/tickets/1/historial/ -H "$T"
```

## Fase 1 vs fase 2: qué nos ahorra Django

| Tarea | Fase 1 (a mano) | Fase 2 (Django + DRF) |
|---|---|---|
| Rutas | Lista de regex + bucle en `_despachar` | `DefaultRouter` + `@action` |
| Esquema de BD | `CREATE TABLE` en un string | Modelos → `makemigrations` / `migrate`, con historial de cambios del esquema |
| Consultas | SQL escrito a mano, filas → dataclasses | ORM: `ticket.historial.create(...)`, `select_related` |
| Validación | Funciones propias (`texto_obligatorio`, `parsear_enum`) | Serializers: tipos, `choices`, obligatorios y longitudes salen del modelo |
| Errores HTTP | `try/except` que traduce cada excepción | DRF devuelve 400/401/403/404/405 con detalle por campo |
| Autenticación | Cabecera `X-Agente` sin contraseña | Usuarios con contraseña, sesiones, tokens, permisos |
| Filtros | `if` que van armando el SQL | `filterset_fields` |
| Panel de gestión | No existe | `/admin/` casi gratis |
| Tests | Levantar el servidor en un hilo y usar `urllib` | `APITestCase`, BD de test automática, `force_authenticate` |

Líneas de código propias aproximadas: fase 1 ≈ 470, fase 2 ≈ 290 haciendo más (auth real, admin, filtros extra).

**Lo que cuesta Django**: más conceptos que aprender (settings, apps, migraciones, serializers, ViewSets), más "magia" que hay que entender para depurar y una dependencia externa que mantener. La fase 1 deja claro qué hace esa magia por debajo.
