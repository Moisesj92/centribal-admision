from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Ticket
from .serializers import (
    AsignarSerializer,
    ComentarioSerializer,
    EstadoSerializer,
    HistorialSerializer,
    TicketSerializer,
)


class TicketViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Tickets de soporte.

    - `POST /api/tickets/` es público (lo usa el cliente).
    - El resto exige un agente autenticado (permiso por defecto IsAdminUser = is_staff).
    """

    queryset = Ticket.objects.select_related("agente")
    serializer_class = TicketSerializer
    filterset_fields = ["estado", "prioridad", "agente__username"]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return super().get_permissions()

    def _actualizar(self, request, serializer_class):
        ticket = self.get_object()
        serializer = serializer_class(ticket, data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TicketSerializer(ticket).data)

    @action(detail=True, methods=["patch"], serializer_class=EstadoSerializer)
    def estado(self, request, pk=None):
        return self._actualizar(request, EstadoSerializer)

    @action(detail=True, methods=["patch"], serializer_class=AsignarSerializer)
    def asignar(self, request, pk=None):
        return self._actualizar(request, AsignarSerializer)

    @action(detail=True, methods=["get", "post"], serializer_class=ComentarioSerializer)
    def comentarios(self, request, pk=None):
        ticket = self.get_object()
        if request.method == "POST":
            serializer = ComentarioSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(ticket=ticket, autor=request.user)
            ticket.save(update_fields=["actualizado"])
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(ComentarioSerializer(ticket.comentarios.select_related("autor"), many=True).data)

    @action(detail=True, methods=["get"], serializer_class=HistorialSerializer)
    def historial(self, request, pk=None):
        ticket = self.get_object()
        return Response(HistorialSerializer(ticket.historial.select_related("autor"), many=True).data)
