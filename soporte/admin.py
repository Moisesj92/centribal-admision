from django.contrib import admin

from .models import Comentario, Historial, Ticket


class SoloLecturaInline(admin.TabularInline):
    """Comentarios e historial son el rastro de auditoría: se consultan, no se editan ni se borran."""

    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class ComentarioInline(SoloLecturaInline):
    model = Comentario
    fields = readonly_fields = ["autor", "texto", "fecha"]


class HistorialInline(SoloLecturaInline):
    model = Historial
    fields = readonly_fields = ["campo", "valor_anterior", "valor_nuevo", "autor", "fecha"]


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ["id", "asunto", "prioridad", "estado", "agente", "actualizado"]
    list_filter = ["estado", "prioridad", "agente"]
    search_fields = ["asunto", "descripcion"]
    # Estado y agente solo cambian por la API o la web, que validan y dejan historial.
    readonly_fields = ["estado", "agente", "creado", "actualizado"]
    inlines = [ComentarioInline, HistorialInline]

    def has_delete_permission(self, request, obj=None):
        # Borrar un ticket borraría en cascada su historial y sus comentarios.
        return False
