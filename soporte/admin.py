from django.contrib import admin

from .models import Comentario, Historial, Ticket


class ComentarioInline(admin.TabularInline):
    model = Comentario
    extra = 0
    readonly_fields = ["fecha"]


class HistorialInline(admin.TabularInline):
    model = Historial
    extra = 0
    can_delete = False
    readonly_fields = ["campo", "valor_anterior", "valor_nuevo", "autor", "fecha"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ["id", "asunto", "prioridad", "estado", "agente", "actualizado"]
    list_filter = ["estado", "prioridad", "agente"]
    search_fields = ["asunto", "descripcion"]
    # Estado y agente se cambian por la API para que quede historial.
    readonly_fields = ["estado", "agente", "creado", "actualizado"]
    inlines = [ComentarioInline, HistorialInline]
