from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("admin/", admin.site.urls),
    path("ui/", include("soporte.urls_ui")),                 # interfaz HTML (templates)
    path("cuentas/", include("django.contrib.auth.urls")),   # login/logout de la interfaz
    path("api-auth/", include("rest_framework.urls")),  # login/logout de la API navegable
    path("token/", obtain_auth_token),                   # POST usuario+contraseña → token
    path("", include("soporte.urls")),
]
