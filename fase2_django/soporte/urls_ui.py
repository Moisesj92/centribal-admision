from django.urls import path

from . import views_ui

app_name = "ui"  # permite {% url 'ui:detalle' ticket.pk %} en los templates

urlpatterns = [
    path("", views_ui.lista, name="lista"),
    path("nuevo/", views_ui.nuevo_ticket, name="nuevo"),
    path("tickets/<int:pk>/", views_ui.detalle, name="detalle"),
    path("tickets/<int:pk>/estado/", views_ui.cambiar_estado, name="estado"),
    path("tickets/<int:pk>/asignar/", views_ui.asignar, name="asignar"),
    path("tickets/<int:pk>/comentar/", views_ui.comentar, name="comentar"),
]
