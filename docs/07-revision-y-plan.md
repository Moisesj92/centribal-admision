# Revisión de código y plan de mejoras

Revisión de la versión del commit `44b9c05` con criterio de producción: seguridad, integridad de datos, operación y mantenibilidad. Los hallazgos marcados con **✔ verificado** se han reproducido ejecutando el código, no son suposiciones.

**Severidad**: 🔴 alta (riesgo real de seguridad o de datos) · 🟠 media (problema serio al ir a producción o con carga) · 🟡 baja (calidad, mantenimiento).

> **Alcance aplicado.** Es un proyecto de demostración que **no va a producción**. Se corrigió todo lo que afecta al diseño y a la corrección del código (✅, con su commit) y se descartó a propósito lo que solo importa al desplegar (⏭). Descartarlo es una decisión, no un olvido: cada punto ⏭ explica abajo cómo se resolvería.
>
> - **4 (credenciales de demo)**: la contraseña de `ana`/`luis` sigue en el código a propósito, para que quien revise pueda probar la demo sin configurar nada.
> - **Después de la revisión** se retiró todo lo que se había añadido pensando en producción (imagen `prod`, gunicorn, WhiteNoise, configuración por variables de entorno). La configuración es ahora explícitamente de desarrollo, con lo que los hallazgos 2, 12 y parte del 17 dejan de aplicar: no hay entorno de producción que proteger.
> - **16 (parcial)**: el agente pasa a `PROTECT` (no se pierde la asignación sin historial). Reasignar automáticamente al quitar el rol queda fuera de alcance.

---

## Resumen

| # | Hallazgo | Sev. | Dónde | Estado |
|---|---|---|---|---|
| 1 | Condición de carrera: un ticket cerrado puede acabar reabierto | 🔴 | `soporte/models.py` | ✅ `60d715e` |
| 2 | Configuración *fail-open*: sin variables de entorno arranca con DEBUG y una SECRET_KEY pública | 🔴 | `config/settings.py` | ⏭ producción (configuración ahora fija de desarrollo) |
| 3 | Sin límite de peticiones: spam de tickets y fuerza bruta de contraseñas | 🔴 | API, login web, admin | ⏭ producción |
| 4 | Contraseña de agentes en un repositorio público, y el seed se puede ejecutar en producción | 🔴 | `crear_agentes.py` | ⏭ demo (ver nota) |
| 5 | Textos sin límite de tamaño (2 MB por ticket, sin autenticar) | 🟠 | `models.py` | ✅ `4b09912` |
| 6 | En producción los errores 500 no se registran en ningún sitio | 🟠 | `settings.py` (falta `LOGGING`) | ⏭ producción |
| 7 | El rastro de auditoría se puede alterar desde el admin | 🟠 | `admin.py` | ✅ `0792d18` |
| 8 | "Agente" = `is_staff`: todo agente entra al admin y no hay roles | 🟠 | modelo de permisos | ✅ `d22588c` |
| 9 | Tokens de API en claro en la BD y sin caducidad | 🟠 | `rest_framework.authtoken` | ⏭ producción |
| 10 | Sin paginación: los listados devuelven todo | 🟠 | API | ✅ `c0568d5` |
| 11 | Falta configuración HTTPS y cabeceras de seguridad para producción | 🟠 | `settings.py` | ⏭ producción |
| 12 | SQLite con varios workers de gunicorn | 🟠 | `prod` | ⏭ ya no aplica (imagen `prod` retirada) |
| 13 | Sin modelo de usuario propio | 🟠 | estructura | ✅ `d22588c` |
| 14 | Reglas sin respaldo en la base de datos (sin `CheckConstraint`) | 🟡 | `models.py` | ✅ `4b09912` |
| 15 | Código muerto y duplicado | 🟡 | varios | ✅ `4b09912` |
| 16 | Efectos sin historial al borrar o degradar un agente | 🟡 | `models.py` | ✅ `4b09912` (parcial) |
| 17 | Cadena de suministro y Docker: sin lockfile, imagen sin fijar, `prod` con archivos de más | 🟡 | Docker | ⏭ producción |
| 18 | Sin CI, linter ni verificación de tipos | 🟡 | repositorio | ✅ `621c744`, `91cb134` (Ruff + CI; mypy pendiente) |

---

## 🔴 1. Condición de carrera en los cambios de estado — ✔ verificado

**Problema.** `cambiar_estado()` valida contra el estado que tiene **el objeto en memoria**, no contra el de la base de datos. Si dos peticiones llegan a la vez, las dos leen `abierto`, las dos pasan la validación y las dos escriben.

```python
a = Ticket.objects.get(pk=1); b = Ticket.objects.get(pk=1)   # dos peticiones simultáneas
a.cambiar_estado("cerrado", ana)
b.cambiar_estado("en_progreso", ana)                          # b todavía "ve" abierto
# Resultado real: estado = en_progreso
# historial = [abierto→cerrado, abierto→en_progreso]  ← reabrió un cerrado y el historial es incoherente
```

Rompe la regla principal del negocio ("un cerrado no se reabre") y deja un historial imposible. Lo mismo ocurre con `asignar()`.

**Corrección.** Bloquear la fila y volver a validar contra el valor real dentro de la transacción:

```python
@transaction.atomic
def cambiar_estado(self, nuevo, autor):
    actual = Ticket.objects.select_for_update().get(pk=self.pk)   # bloquea la fila hasta el commit
    actual.validar_estado(nuevo)
    ...
```

En SQLite, `select_for_update` no hace nada (bloquea la base de datos entera al escribir), así que la alternativa portable es la **concurrencia optimista**: un `UPDATE … WHERE estado = <anterior>` que solo afecta a la fila si nadie la ha cambiado:

```python
filas = Ticket.objects.filter(pk=self.pk, estado=anterior).update(estado=nuevo, actualizado=now())
if filas == 0:
    raise ValidationError("El ticket cambió mientras tanto; recarga y vuelve a intentarlo.")
```

**Test a añadir.** El mismo escenario de dos instancias "viejas": la segunda debe fallar y el estado tiene que quedar `cerrado`.

---

## 🔴 2. Configuración *fail-open* — ✔ verificado

**Problema.** Si en producción falta una variable de entorno, la aplicación no falla: se vuelve insegura en silencio.

```python
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-solo-para-desarrollo-local')
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'     # por defecto: DEBUG activado
```

Comprobado: con `DJANGO_DEBUG=0` y sin `DJANGO_SECRET_KEY`, arranca sin error usando la clave por defecto.

- La clave está **publicada en el repositorio**. Con ella se pueden falsificar cookies de sesión firmadas, tokens de restablecimiento de contraseña y cualquier dato firmado.
- Si lo que falta es `DJANGO_DEBUG`, producción arranca **en modo debug**: los errores muestran trazas, variables locales y la configuración.

**Corrección.** Seguro por defecto: `DEBUG` vale `False` salvo que se pida lo contrario, y sin clave no se arranca.

```python
DEBUG = os.environ.get("DJANGO_DEBUG") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or (
    "insegura-solo-desarrollo" if DEBUG else _falta("DJANGO_SECRET_KEY")   # ImproperlyConfigured
)
```

El servicio `web` de `compose.yaml` pasaría `DJANGO_DEBUG=1` de forma explícita. Además, el valor por defecto de `DJANGO_SECRET_KEY` en el servicio `prod` de `compose.yaml` debería desaparecer (`${DJANGO_SECRET_KEY:?define la clave}`).

---

## 🔴 3. Sin límite de peticiones (rate limiting) — ✔ verificado

**Problema.**
- `POST /api/tickets/` y `/nuevo/` son **públicos y sin límite**. Un script puede crear miles de tickets por minuto (comprobado: tres tickets de 2 MB seguidos, todos `201`).
- `/api/token/`, `/cuentas/login/`, `/admin/login/` y `/api-auth/login/` aceptan **intentos de contraseña ilimitados**. Comprobado: 15 intentos seguidos, ningún bloqueo. Son cuatro puertas de entrada para un ataque de fuerza bruta.

**Corrección.**
- DRF: `DEFAULT_THROTTLE_CLASSES` + `ScopedRateThrottle`. Por ejemplo, `crear_ticket: 10/hour` por IP y `token: 5/min`. Necesita una caché compartida (Redis) cuando hay varios workers.
- Formularios de login (web y admin): **django-axes**, que bloquea tras N fallos por usuario o IP.
- Formulario público: un *honeypot* o CAPTCHA si hay spam real.
- En producción, además, límites en el proxy o WAF (nginx, Cloudflare, ALB).

---

## 🔴 4. Credenciales en el repositorio y seed sin protección

**Problema.**
- `CLAVE_DESARROLLO = "agente-dev-123"` está en un **repositorio público**.
- `crear_agentes` funciona igual con `DEBUG=0`. Si alguien lo ejecuta en producción, quedan dos cuentas de staff con contraseña conocida.
- `set_password()` no pasa por los validadores de contraseña.
- El comando imprime los tokens en la salida, que puede acabar en los logs del CI o de la plataforma.

**Corrección.**

```python
if not settings.DEBUG:
    raise CommandError("Datos de desarrollo: no se ejecuta con DEBUG=0.")
clave = os.environ.get("AGENTES_DEV_PASSWORD") or raise CommandError(...)
validate_password(clave)
```

Los tokens se mostrarían solo con `--mostrar-tokens`. Los datos que sí deben existir en producción (grupo "Agentes", permisos) irían en una **migración de datos**.

---

## 🟠 5. Textos sin límite de tamaño — ✔ verificado

**Problema.** `descripcion` y `Comentario.texto` son `TextField` sin máximo. Un anónimo puede guardar 2 MB por ticket (el único límite es `DATA_UPLOAD_MAX_MEMORY_SIZE`, 2,5 MB). Combinado con el hallazgo 3, se llena el disco.

**Corrección.** `max_length` en el modelo (por ejemplo, 5 000 caracteres para la descripción y 2 000 para el comentario), que forms y serializers heredan solos. Bajar `DATA_UPLOAD_MAX_MEMORY_SIZE` a unos 100 KB.

---

## 🟠 6. Los errores 500 no se registran en producción — ✔ verificado

**Problema.** No hay configuración de `LOGGING`. La configuración por defecto de Django manda al logger `django` a dos sitios: `console`, que tiene el filtro `require_debug_true` (solo funciona con DEBUG activado), y `mail_admins`, que no está configurado (no hay `ADMINS`). Resultado: **con `DEBUG=0`, una excepción en una vista devuelve 500 y no deja rastro en ningún sitio**. Gunicorn solo ve un 500 en el access log.

**Corrección.** `LOGGING` con salida a consola (stdout) en todos los entornos, mejor en formato JSON en producción, y **Sentry** para agrupar y avisar de errores.

---

## 🟠 7. El rastro de auditoría se puede alterar

**Problema.** El historial es el registro de "quién cambió qué", pero:
- en el admin, `ComentarioInline` permite **editar el texto y el autor** de comentarios ya escritos, y borrarlos;
- `TicketAdmin` permite **borrar un ticket**, y por el `CASCADE` se borran también su historial y sus comentarios.

**Corrección.**
- Inlines de solo lectura y `has_delete_permission → False` para comentarios e historial.
- Prohibir el borrado de tickets, o usar borrado lógico (un campo `archivado`).
- Si la auditoría importa de verdad: tabla de solo inserción, o `django-simple-history` / `django-pghistory`.

---

## 🟠 8. "Agente" = `is_staff`

**Problema.** `is_staff` en Django significa "puede entrar al admin". Al usarlo como "es agente", **todos los agentes pueden entrar en `/admin/`**, y la única forma de dar acceso a la aplicación es dárselo también al panel. Tampoco hay roles: cualquier agente puede reasignar o cerrar cualquier ticket.

**Corrección.**
- Un grupo **"Agentes"**, creado por migración de datos, o un permiso propio (`soporte.atender_ticket`).
- Una clase de permiso de DRF (`EsAgente`) y un decorador equivalente para la web.
- `is_staff` reservado para quien administra.
- Si hace falta, más adelante: rol "Supervisor" (puede reasignar a otros) y permisos por objeto.

---

## 🟠 9. Tokens de API

**Problema.** `rest_framework.authtoken` guarda la clave **en claro** en la base de datos (quien lea la BD o un backup obtiene acceso), **no caduca nunca** y solo admite un token por usuario. Además, el token no se puede revocar desde la interfaz.

**Corrección.**
- **django-rest-knox**: tokens hasheados, con caducidad y varios por usuario.
- O **JWT** (`djangorestframework-simplejwt`) con vida corta y *refresh*.
- Revocar los tokens al desactivar un usuario.

---

## 🟠 10. Sin paginación

**Problema.** `GET /api/tickets/`, `/comentarios/` e `/historial/` devuelven **todos** los registros. Con miles de tickets hay respuestas enormes, memoria disparada y una vía fácil de denegación de servicio para cualquier agente o token robado. La lista web tiene el mismo problema.

**Corrección.** `DEFAULT_PAGINATION_CLASS` (`PageNumberPagination`, `PAGE_SIZE = 50`) en DRF y `Paginator` en la vista web.

---

## 🟠 11. Producción sin HTTPS ni cabeceras de seguridad

**Problema.** `manage.py check --deploy` devuelve 5 avisos: falta `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HSTS, y la `SECRET_KEY` es débil. Tampoco hay `CSRF_TRUSTED_ORIGINS`, `SECURE_PROXY_SSL_HEADER` (necesario detrás de un balanceador) ni Content-Security-Policy.

**Corrección.** Un bloque `if not DEBUG:` con todo lo anterior, configurable por entorno, y **django-csp** (o el CSP integrado al subir a Django 6.x). Opcionalmente, desactivar la API navegable en producción (`DEFAULT_RENDERER_CLASSES` solo con JSON).

---

## 🟠 12. SQLite con gunicorn

**Problema.** El perfil `prod` arranca 3 workers de gunicorn contra SQLite. SQLite admite **un solo escritor a la vez**; con escrituras concurrentes aparece `database is locked`. Además, el volumen de datos no se puede compartir entre varias máquinas.

**Corrección.** PostgreSQL: un servicio `db` en `compose.yaml` y `DATABASES` desde `DATABASE_URL` (`dj-database-url`). Así también funciona `select_for_update` del hallazgo 1.

---

## 🟠 13. Sin modelo de usuario propio

**Problema.** La documentación de Django recomienda crear un `User` propio **al empezar** cualquier proyecto. Cambiarlo con datos reales obliga a migraciones manuales muy delicadas.

**Corrección.** App `cuentas` con `class Usuario(AbstractUser)` y `AUTH_USER_MODEL = "cuentas.Usuario"`. **Ahora es barato**: no hay datos reales, solo hay que regenerar las migraciones y la base de datos de desarrollo. Cuanto más se espere, más caro sale.

---

## 🟡 14. Reglas sin respaldo en la base de datos

`choices` y `blank=False` solo se comprueban en forms y serializers; `save()` no valida (ver `docs/06`). Con `CheckConstraint` sobre `estado`, `prioridad` y `asunto <> ''`, la base de datos rechaza datos imposibles venga de donde venga (scripts, shell, otro servicio).

## 🟡 15. Código muerto y duplicado

- `Comentario.es_interno` siempre vale `True` y nada lo cambia. O se elimina, o se implementan los comentarios públicos.
- La validación de "asunto no vacío" está **duplicada** en `TicketSerializer.validate_asunto` y `TicketForm.clean_asunto`. Debería vivir en el modelo, como un validador del campo o con el `CheckConstraint`.
- `settings.py` mezcla comillas simples (generadas) y dobles. Se resuelve con un formateador (Ruff).

## 🟡 16. Efectos sin historial

- Borrar un usuario pone `agente = NULL` en sus tickets (`SET_NULL`) **sin entrada en el historial**.
- Si a un agente se le quita el rol, sigue asignado a sus tickets.

Mejor desactivar usuarios (`is_active = False`) en lugar de borrarlos, y reasignar con historial al quitar el rol.

## 🟡 17. Cadena de suministro y Docker

- Hay rangos de versiones pero **no hay lockfile** con hashes. Dos builds en días distintos pueden instalar versiones diferentes, y un paquete comprometido entraría sin aviso. Solución: `uv lock` / `pip-compile --generate-hashes`.
- La imagen base `python:3.13-slim` no está fijada por *digest*.
- La imagen `prod` incluye `docs/`, `ejercicios/`, los tests y `PLAN.md`, que no hacen falta en producción. Se excluyen en `.dockerignore` o con un `COPY` selectivo.
- `pull_policy: build` en el servicio `shell` reconstruye la imagen (con caché) en cada `docker compose run`: lento y con mucha salida por pantalla.
- Falta `pip-audit` o Dependabot para enterarse de las vulnerabilidades en dependencias.

## 🟡 18. Herramientas y CI

No hay CI, ni linter, ni verificación de tipos. Con GitHub Actions se ejecutarían en cada push: `ruff check`, `ruff format --check`, `mypy` (con `django-stubs`), los tests, `makemigrations --check` y `check --deploy`.

---

## Lo que está bien hecho (y hay que mantener)

- Las reglas de negocio están en el modelo, y la API y la web las comparten.
- El historial se escribe en la misma transacción que el cambio.
- Hay listas blancas de campos (`fields`, `read_only_fields`): nada de asignación masiva.
- CSRF activo, escape automático en templates, ORM parametrizado y logout por POST.
- La redirección `next` del login la valida Django (no hay *open redirect*).
- Los endpoints de agente exigen autenticación, con 401 y 403 correctos.
- El contenedor corre con un usuario sin privilegios, la imagen es multi-etapa y tiene healthcheck.
- Hay 20 tests, incluidos los de permisos y transiciones prohibidas.

---

## Plan de mejoras

Ordenado por **riesgo ÷ esfuerzo**. Cada paso se haría en un commit propio, con sus tests.

### Fase 1: seguridad urgente (antes de cualquier despliegue)

| Paso | Hallazgos | Cambio | Test nuevo |
|---|---|---|---|
| 1.1 | 2 | `DEBUG=False` por defecto, `SECRET_KEY` obligatoria fuera de debug, `compose.yaml` sin clave por defecto | Arrancar con `DEBUG=0` sin clave → `ImproperlyConfigured` |
| 1.2 | 4 | `crear_agentes`: contraseña desde `.env`, bloqueado con `DEBUG=0`, validación de contraseña, tokens solo con flag | El comando falla con `DEBUG=0` |
| 1.3 | 1 | Concurrencia optimista en `cambiar_estado` / `asignar` | Dos instancias viejas: la segunda falla y el estado queda `cerrado` |
| 1.4 | 5 | `max_length` en textos + `DATA_UPLOAD_MAX_MEMORY_SIZE` | Descripción demasiado larga → 400 |
| 1.5 | 3 | Throttling en DRF (crear ticket, token) + django-axes en los logins | La petición N+1 → 429; login bloqueado tras N fallos |

### Fase 2: integridad, permisos y operación

| Paso | Hallazgos | Cambio |
|---|---|---|
| 2.1 | 13 | App `cuentas` con `Usuario(AbstractUser)`. **Regenera las migraciones y la BD de desarrollo** (se pierden los tickets de prueba) |
| 2.2 | 8 | Grupo/permiso "Agentes" por migración de datos; `EsAgente` en la API y la web; `is_staff` solo para administración |
| 2.3 | 7 | Admin: comentarios e historial de solo lectura, sin borrado de tickets |
| 2.4 | 6 | `LOGGING` a consola en todos los entornos (+ Sentry opcional) |
| 2.5 | 10 | Paginación en la API y en la lista web |
| 2.6 | 14, 15, 16 | `CheckConstraint`, validación de asunto en el modelo, decidir sobre `es_interno`, reasignación al desactivar |

### Fase 3: listo para producción real

| Paso | Hallazgos | Cambio |
|---|---|---|
| 3.1 | 12 | PostgreSQL en `compose.yaml` + `DATABASE_URL`; `select_for_update` en las transiciones |
| 3.2 | 11 | Settings HTTPS/HSTS/cookies/proxy por entorno + CSP; `check --deploy` sin avisos |
| 3.3 | 9 | Tokens con caducidad y hasheados (knox) o JWT |
| 3.4 | 17 | Lockfile con hashes (uv), imagen base fijada por digest, `.dockerignore` de prod, `pip-audit` |

### Fase 4: calidad continua

| Paso | Hallazgos | Cambio |
|---|---|---|
| 4.1 | 18 | Ruff + mypy/django-stubs + pre-commit |
| 4.2 | 18 | GitHub Actions: lint, tipos, tests, `makemigrations --check`, `check --deploy` |
| 4.3 | — | Cobertura de tests (`coverage`) y tests de admin y de concurrencia |
