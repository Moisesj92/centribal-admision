from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import AGENTES, Comentario, Estado, Historial, Ticket

Usuario = get_user_model()


class TicketSerializer(serializers.ModelSerializer):
    # Estado y agente solo cambian por sus endpoints, para que quede historial.
    agente = serializers.SlugRelatedField(slug_field="username", read_only=True)

    class Meta:
        model = Ticket
        fields = ["id", "asunto", "descripcion", "prioridad", "estado", "agente", "creado", "actualizado"]
        read_only_fields = ["estado", "creado", "actualizado"]

    def validate_asunto(self, valor):
        if not valor.strip():
            raise serializers.ValidationError("El asunto no puede estar vacío.")
        return valor.strip()


class EstadoSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=Estado.choices)

    def validate_estado(self, nuevo):
        ticket = self.instance
        if nuevo == ticket.estado:
            raise serializers.ValidationError(f"El ticket ya está en estado {nuevo}.")
        if not ticket.puede_pasar_a(nuevo):
            raise serializers.ValidationError(f"No se puede pasar de {ticket.estado} a {nuevo}.")
        return nuevo

    def update(self, ticket, datos):
        ticket.cambiar_estado(datos["estado"], autor=self.context["request"].user)
        return ticket


class AsignarSerializer(serializers.Serializer):
    agente = serializers.SlugRelatedField(
        slug_field="username", queryset=Usuario.objects.filter(**AGENTES), allow_null=True
    )

    def validate(self, datos):
        ticket = self.instance
        if ticket.estado == Estado.CERRADO:
            raise serializers.ValidationError("No se puede reasignar un ticket cerrado.")
        if datos["agente"] == ticket.agente:
            raise serializers.ValidationError("El ticket ya está asignado a ese agente.")
        return datos

    def update(self, ticket, datos):
        ticket.asignar(datos["agente"], autor=self.context["request"].user)
        return ticket


class ComentarioSerializer(serializers.ModelSerializer):
    autor = serializers.SlugRelatedField(slug_field="username", read_only=True)

    class Meta:
        model = Comentario
        fields = ["id", "autor", "texto", "es_interno", "fecha"]
        read_only_fields = ["es_interno", "fecha"]


class HistorialSerializer(serializers.ModelSerializer):
    autor = serializers.SlugRelatedField(slug_field="username", read_only=True)

    class Meta:
        model = Historial
        fields = ["id", "campo", "valor_anterior", "valor_nuevo", "autor", "fecha"]
