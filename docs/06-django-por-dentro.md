# Django por dentro

Cómo funciona Django de verdad, explicado con el código de este proyecto. Se puede leer de arriba abajo: sigue el recorrido de una petición.

---

## 1. Vocabulario: proyecto, app, MTV

- **Proyecto** (`config/`): la configuración global (`settings.py`) y la tabla de rutas raíz (`urls.py`). Hay uno.
- **App** (`soporte/`): un módulo reutilizable con sus modelos, vistas, URLs, templates y migraciones. Un proyecto tiene varias: las nuestras y las que trae Django (`auth`, `admin`, `sessions`…) o terceros (`rest_framework`).

Django no habla de MVC sino de **MTV**:

| MVC clásico | Django (MTV) | En este proyecto |
|---|---|---|
| Model | **Model** | `models.py` |
| View (lo que se ve) | **Template** | `templates/soporte/*.html` |
| Controller | **View** | `views_ui.py`, `views.py` |
| (enrutado del controller) | **URLconf** + el propio framework | `urls.py` |

En resumen: **lo que en otros frameworks se llama "controlador", en Django se llama "vista"**. Es una función o clase que recibe un `HttpRequest` y devuelve un `HttpResponse`. Django dice que el auténtico "controlador" es el propio framework, que decide qué vista llamar según la URL.

---

## 2. El viaje de una petición

```
 navegador / curl
       │  HTTP
       ▼
 servidor WSGI (runserver en desarrollo; gunicorn en producción)
       │  config/wsgi.py → get_wsgi_application()
       ▼
 WSGIHandler  ── crea el objeto HttpRequest
       │
       ▼
 ┌─ MIDDLEWARE (de arriba abajo al entrar) ─────────────────────────┐
 │  SecurityMiddleware → SessionMiddleware → CommonMiddleware →     │
 │  CsrfViewMiddleware → AuthenticationMiddleware → Message → XFrame│
 │        │                                                         │
 │        ▼                                                         │
 │  URL resolver: recorre ROOT_URLCONF hasta encontrar la vista     │
 │        │                                                         │
 │        ▼                                                         │
 │  VISTA(request, **parámetros) ──► usa Modelos (ORM → SQL)        │
 │        │                       ──► renderiza Template / JSON     │
 │        ▼                                                         │
 │  HttpResponse                                                    │
 └─ MIDDLEWARE (de abajo arriba al salir) ──────────────────────────┘
       │
       ▼
 respuesta HTTP
```

### WSGI

**WSGI** es un estándar de Python (PEP 3333): una función `app(environ, start_response)` que cualquier servidor sabe llamar. Gracias a él, Django no tiene que saber nada de sockets. Sin framework, habría que hacerlo a mano con `http.server`. Existe también **ASGI** (`config/asgi.py`), la versión asíncrona, para websockets y `async def`.

### Middleware: capas de cebolla

Cada middleware envuelve al siguiente, como una capa de cebolla: puede tocar la petición al entrar, la respuesta al salir, o cortar el camino y responder él mismo.

```python
class MiMiddleware:
    def __init__(self, get_response):      # se crea una vez al arrancar
        self.get_response = get_response    # "el resto de la cebolla"

    def __call__(self, request):
        # ... antes de la vista
        response = self.get_response(request)
        # ... después de la vista
        return response
```

En nuestro `settings.MIDDLEWARE`:
- `SessionMiddleware` lee la cookie y carga `request.session`.
- `AuthenticationMiddleware` usa esa sesión para poner `request.user`. Por eso el **orden importa**: tiene que ir después de Session.
- `CsrfViewMiddleware` rechaza los POST sin token CSRF. Por eso los formularios llevan `{% csrf_token %}`.
- `XFrameOptionsMiddleware` impide que otra web meta la nuestra en un `<iframe>` (clickjacking).

---

## 3. ¿Dónde viven las rutas?

En los **URLconf**: módulos de Python con una lista `urlpatterns`. Django empieza por el que indica `settings.ROOT_URLCONF = 'config.urls'`.

```python
# config/urls.py — la raíz
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("soporte.urls")),       # delega todo lo que empiece por api/ (DRF)
    path("api/token/", obtain_auth_token),
    path("", include("soporte.urls_ui")),        # interfaz web en la raíz
]

# soporte/urls_ui.py — rutas de la app
app_name = "ui"
urlpatterns = [
    path("tickets/<int:pk>/", views_ui.detalle, name="detalle"),
]
```

Cómo funciona:

1. El resolver prueba los patrones **en orden**; gana el primero que encaja.
2. `include()` corta el prefijo (`api/`) y sigue buscando en el otro módulo. Así cada app tiene sus propias rutas.
3. Los **convertidores** (`<int:pk>`, `<slug:x>`, `<uuid:id>`) validan y convierten: `/tickets/abc/` ni siquiera encaja, así que da 404 sin llegar a la vista. La vista recibe `pk=4` ya como `int`.
4. `name="detalle"` + `app_name="ui"` permiten la **resolución inversa**: `reverse("ui:detalle", args=[4])` en Python o `{% url 'ui:detalle' 4 %}` en templates. Si mañana cambias la URL, no hay que tocar ningún enlace. Pasó en este proyecto: la interfaz web estaba en `/ui/` y se movió a `/` cambiando una línea de `config/urls.py`. Todos los enlaces hechos con `{% url %}` y `redirect()` siguieron funcionando; el único que hubo que corregir fue uno escrito a mano en el menú.

**DRF** añade los **routers**: `DefaultRouter().register("tickets", TicketViewSet)` genera solo las rutas `tickets/` y `tickets/{pk}/`, más una por cada `@action` (`tickets/{pk}/estado/`…). Con el prefijo del `include` quedan como `/api/tickets/…`.

Sin framework, esto sería una lista de expresiones regulares y un bucle que las prueba una a una: la misma idea, pero sin convertidores, nombres ni `include`.

---

## 4. Modelos y ORM

```python
class Ticket(models.Model):
    asunto = models.CharField(max_length=200)
    prioridad = models.CharField(max_length=10, choices=Prioridad, default=Prioridad.MEDIA)
    agente = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
```

### Qué pasa al definir la clase (metaclase)

`models.Model` usa una **metaclase**, `ModelBase`: una clase que fabrica clases. Al cargar el archivo, antes de crear ningún ticket, la metaclase:
- recoge los atributos que son `Field` y construye `Ticket._meta` (nombre de la tabla `soporte_ticket`, columnas, relaciones…);
- quita esos atributos de la clase y los sustituye por **descriptores**, que controlan qué pasa al leer o escribir `ticket.asunto`;
- añade `id` si no lo defines, el manager `Ticket.objects` y las relaciones inversas (`ticket.historial`, `ticket.comentarios`, por el `related_name`);
- registra el modelo en el **registro de apps** (`django.apps.apps`).

Por eso escribir campos como atributos de clase "funciona por arte de magia": es programación **declarativa**. Tú declaras qué quieres y la metaclase lo convierte en código.

### QuerySets: perezosos y encadenables

```python
qs = Ticket.objects.filter(prioridad="alta")   # NO toca la base de datos
qs = qs.exclude(estado="cerrado").order_by("-creado")   # sigue sin tocarla
for t in qs: ...                               # AHORA ejecuta UN SELECT
print(qs.query)                                 # ver el SQL generado
```

Un QuerySet es una **descripción** de una consulta. Solo se ejecuta cuando hace falta el resultado (al iterar, con `list()`, `len()`, `[0]`, `exists()`…), y luego guarda los resultados en caché.

**El problema N+1**: `for t in Ticket.objects.all(): t.agente.username` hace 1 consulta para los tickets y otra **por cada ticket** para su agente. Se arregla con `select_related("agente")` (un JOIN) o con `prefetch_related` (para relaciones "muchos"). Por eso en `views.py` aparece `Ticket.objects.select_related("agente")`.

### Migraciones

`makemigrations` compara tus modelos con el estado que guardan las migraciones anteriores y escribe un archivo Python con la diferencia (`0001_initial.py`). `migrate` lo traduce a SQL de tu base de datos y apunta en la tabla `django_migrations` cuáles ya se aplicaron. Los cambios de esquema quedan **versionados en git**, igual que el código.

---

## 5. Cómo se validan los datos (y la trampa más común)

En Django la validación ocurre en **varias capas**, y no todas se ejecutan siempre:

| Capa | Se ejecuta | Ejemplo en el proyecto |
|---|---|---|
| 1. Base de datos | Siempre, al hacer el SQL | `NOT NULL`, claves foráneas, `max_length` en algunas BD |
| 2. Modelo: `full_clean()` | **Solo si la llamas** (los ModelForm sí la llaman) | `choices`, `blank=False`, validadores del campo |
| 3. Form / Serializer: `is_valid()` | En cada petición que valides | `TicketForm`, `TicketSerializer` |
| 4. Reglas de negocio propias | Donde las llames | `Ticket.validar_estado()` |

### La trampa: `save()` NO valida

Comprobado en este proyecto:

```python
>>> t = Ticket(asunto="", descripcion="", prioridad="urgentisima")
>>> t.save()                 # ¡se guarda sin quejarse!
>>> t.full_clean()
ValidationError: {'asunto': ['Este campo no puede estar vacío.'],
                  'prioridad': ["Valor 'urgentisima' no es una opción válida."], ...}
```

`choices` y `blank` **no son restricciones de la base de datos**, solo reglas de validación. Si creas objetos con `Ticket.objects.create(...)` en un script, nadie las comprueba. Por eso:
- la entrada de usuarios siempre pasa por un **Form** o un **Serializer**;
- las reglas críticas se comprueban **dentro del método que hace el cambio**: `cambiar_estado()` llama a `validar_estado()` antes de guardar, venga la llamada de la API, de la UI o de un script;
- si una regla tiene que cumplirse sí o sí, se pone también en la BD: `Meta.constraints = [CheckConstraint(...)]`.

### Orden de validación en un Form (y casi igual en DRF)

```
form.is_valid()
 └─ full_clean()
     ├─ por cada campo:  to_python()     "3" → 3, texto → fecha…        (tipo)
     │                   validate()      obligatorio, choices            (campo)
     │                   run_validators  max_length, EmailValidator…     (campo)
     │                   clean_<campo>() ← TU método, p. ej. EstadoForm.clean_estado
     ├─ clean()          ← TU método para reglas entre varios campos (AsignarForm.clean)
     └─ (ModelForm) instance.full_clean()  validación del modelo
 → form.errors / form.cleaned_data
```

En DRF: `to_internal_value` → validadores → `validate_<campo>()` (`EstadoSerializer.validate_estado`) → `validate()` (`AsignarSerializer.validate`) → `serializer.errors` / `serializer.validated_data`.

Las dos lanzan su propio `ValidationError`. Un Form entiende directamente el `ValidationError` de Django, pero DRF necesita el suyo. Por eso en `serializers.py` existe `aplicar_regla()`, que convierte uno en otro.

---

## 6. Atributos permitidos y no permitidos

### a) Qué campos acepta la entrada: *mass assignment*

El peligro es que un cliente mande `{"asunto": "x", "estado": "cerrado", "is_staff": true}` y se guarden campos que no debería tocar. Django y DRF lo evitan con **listas blancas**:

```python
class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ["id", "asunto", "descripcion", "prioridad", "estado", "agente", ...]  # lista blanca
        read_only_fields = ["estado", "creado", "actualizado"]  # se devuelven pero no se aceptan
    agente = serializers.SlugRelatedField(..., read_only=True)

class TicketForm(forms.ModelForm):
    class Meta:
        fields = ["asunto", "descripcion", "prioridad"]  # el form solo acepta estos
```

Comprobado:

```python
>>> s = TicketSerializer(data={"asunto": "a", "descripcion": "b", "estado": "cerrado", "hackeado": 1})
>>> s.is_valid(); s.validated_data
{'asunto': 'a', 'descripcion': 'b'}       # estado (read-only) y hackeado (desconocido) desaparecen
```

- Los campos **desconocidos se ignoran en silencio**, sin error.
- Los **read-only** se muestran en la respuesta pero se ignoran en la entrada.
- `fields = "__all__"` o `exclude = [...]` son cómodos pero peligrosos: un campo nuevo en el modelo quedaría expuesto sin que te des cuenta. Mejor listar los campos.

### b) Opciones de los campos del modelo

| Opción | Significado |
|---|---|
| `null=True` | La **base de datos** admite `NULL` |
| `blank=True` | La **validación** admite el campo vacío (forms, admin, `full_clean`) |
| `choices=` | Solo esos valores (validación, no BD) |
| `default=` | Valor si no se indica |
| `editable=False` | No aparece en forms ni en el admin |
| `auto_now_add` / `auto_now` | Fecha al crear / en cada `save()`; implican `editable=False` |
| `unique=True` | Índice único en la BD (este sí es una restricción real) |

Regla práctica: para texto opcional usa `blank=True` (cadena vacía), no `null=True`. Para una FK opcional usa los dos, como en `agente`.

### c) Qué se puede usar en un template

El lenguaje de templates está **limitado a propósito** para que la lógica no acabe en el HTML:
- `{{ ticket.agente.username }}` prueba, en este orden, diccionario → atributo → índice de lista.
- Se pueden llamar métodos, pero **sin argumentos** (`{{ ticket.get_estado_display }}`).
- **No** se puede acceder a nada que empiece por `_`.
- No se ejecutan métodos marcados con `alters_data = True` (como `delete()` o `save()`), así que un template no puede borrar datos por accidente.
- Toda variable se **escapa** automáticamente: si un asunto contiene `<script>`, se muestra como texto. Esto protege contra XSS.

### d) Atributos de la petición

`request.GET` / `request.POST` (QueryDict: una clave puede tener varios valores), `request.user`, `request.session`, `request.headers`, `request.method`. En DRF, `request.data` unifica JSON, form-data y multipart.

---

## 7. Vistas: funciones, clases y ViewSets

```python
# Función (views_ui.py): explícita, fácil de seguir
@solo_agentes
@require_POST
def cambiar_estado(request, pk): ...

# Clase genérica de Django: comportamiento heredado y ganchos que se sobrescriben
class TicketList(LoginRequiredMixin, ListView):
    model = Ticket
    def get_queryset(self): return super().get_queryset().filter(...)

# ViewSet de DRF (views.py): un recurso REST completo a partir de mixins
class TicketViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                    mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    def get_permissions(self): ...       # gancho que sobrescribimos
    @action(detail=True, methods=["patch"])
    def estado(self, request, pk=None): ...
```

Por eso `DELETE /api/tickets/1/` devuelve 405: no incluimos `DestroyModelMixin`, así que esa operación **no existe**. Lo que no está heredado no se puede hacer.

---

## 8. Patrones de diseño que usa Django

| Patrón | Dónde aparece |
|---|---|
| **MTV** (variante de MVC) | Separación modelo / template / vista |
| **Front Controller** | Un único punto de entrada (`WSGIHandler`) recibe todas las peticiones y las reparte |
| **Chain of Responsibility / Decorator** | Middleware: cada capa decide si pasa la petición a la siguiente. Los decoradores (`@require_POST`, `@user_passes_test`) envuelven vistas |
| **Active Record** | El objeto sabe guardarse: `ticket.save()`, `ticket.delete()` (frente a *Data Mapper*, donde un objeto aparte, el repositorio, guarda los datos) |
| **Metaclase / declarativo** | Modelos, Forms y Serializers: declaras campos como atributos de clase |
| **Lazy evaluation** | QuerySets, `reverse_lazy`, `gettext_lazy`, `settings` |
| **Template Method** | Vistas genéricas y DRF: el flujo está fijo y tú sobrescribes ganchos (`get_queryset`, `get_permissions`, `perform_create`, `clean_<campo>`) |
| **Mixins** | `LoginRequiredMixin`, `CreateModelMixin`…: comportamiento que se compone por herencia múltiple |
| **Strategy** | Piezas intercambiables desde settings: backends de BD, de caché, de templates, de autenticación; `authentication_classes` y `permission_classes` en DRF |
| **Observer** | Señales: `post_save`, `pre_delete`, `request_finished`… |
| **Registry** | `apps` (registro de apps y modelos), `admin.site.register` |
| **Unit of Work (parcial)** | `transaction.atomic`: todo o nada |
| **Convención sobre configuración** | `templates/` y `migrations/` dentro de cada app, `tests*.py`, `management/commands/` se descubren solos |

Lo que Django **no** usa: no hay *Identity Map*. Dos consultas al mismo ticket dan dos objetos Python distintos, y si cambias uno el otro no se entera (para eso existe `refresh_from_db()`).

---

## 9. Qué hace especialmente bien Django

1. **Pilas incluidas**: ORM, migraciones, auth, admin, forms, sesiones, caché, i18n, emails y tests vienen en la caja y encajan entre sí.
2. **El admin**: con unas pocas líneas tienes un panel de gestión con permisos, búsqueda y filtros.
3. **Seguridad por defecto**: el ORM parametriza el SQL (sin inyección), los templates escapan el HTML (XSS), CSRF viene activado, hay protección contra clickjacking, las contraseñas se guardan con hash (PBKDF2, con migración transparente a algoritmos mejores) y los validadores de contraseña vienen incluidos.
4. **Migraciones automáticas** a partir de los modelos.
5. **Apps reutilizables**: DRF, django-filter, el admin y el sistema de auth son apps que se "enchufan" con `INSTALLED_APPS`.
6. **Estabilidad**: versiones LTS con 3 años de soporte, una política de deprecación clara y una documentación de las mejores que hay.
7. **Tests**: base de datos de prueba automática, cliente HTTP falso y cada test aislado en una transacción que se deshace al acabar.

Y sus costes: mucha "magia" (metaclases, convenciones) que hay que entender para depurar, un `settings` global, el ORM puede generar consultas ineficientes si no miras el SQL, y es un monolito pensado para HTML + base de datos relacional.

---

## 10. Para experimentar

```bash
docker compose exec web python manage.py shell        # importa los modelos automáticamente
```

```python
qs = Ticket.objects.filter(prioridad="alta"); print(qs.query)   # el SQL
Ticket._meta.get_fields()                                         # lo que construyó la metaclase
from django.urls import get_resolver; get_resolver().url_patterns # rutas raíz
from django.conf import settings; settings.MIDDLEWARE             # la cebolla
from django.db import connection, reset_queries                   # contar consultas (con DEBUG=True):
reset_queries(); [t.agente for t in Ticket.objects.all()]; len(connection.queries)
reset_queries(); [t.agente for t in Ticket.objects.select_related("agente")]; len(connection.queries)
```
