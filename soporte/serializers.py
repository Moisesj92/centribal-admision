from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework import serializers

from .models import AGENTES, Comentario, Estado, Historial, Ticket

Usuario = get_user_model()


def aplicar_regla(regla, *args):
    """Ejecuta una validación del modelo y convierte su error al formato de DRF."""
    try:
        regla(*args)
    except ValidationError as error:
        raise serializers.ValidationError(error.messages) from None


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
        aplicar_regla(self.instance.validar_estado, nuevo)
        return nuevo

    def update(self, ticket, datos):
        ticket.cambiar_estado(datos["estado"], autor=self.context["request"].user)
        return ticket


class AsignarSerializer(serializers.Serializer):
    agente = serializers.SlugRelatedField(
        slug_field="username", queryset=Usuario.objects.filter(**AGENTES), allow_null=True
    )

    def validate(self, datos):
        aplicar_regla(self.instance.validar_asignacion, datos["agente"])
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
