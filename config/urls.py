from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("salud/", lambda request: HttpResponse("ok")),  # healthcheck de Docker
    path("admin/", admin.site.urls),
    path("api/", include("soporte.urls")),  # API REST (DRF): /api/tickets/…
    path("api/token/", obtain_auth_token),  # POST usuario+contraseña → token
    path("api-auth/", include("rest_framework.urls")),  # login/logout de la API navegable
    path("cuentas/", include("django.contrib.auth.urls")),  # login/logout de la interfaz web
    path("", include("soporte.urls_ui")),  # interfaz web en la raíz
]
