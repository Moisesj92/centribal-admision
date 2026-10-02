from django.conf import settings
from django.db import models, transaction


class Prioridad(models.TextChoices):
    BAJA = "baja", "Baja"
    MEDIA = "media", "Media"
    ALTA = "alta", "Alta"
    CRITICA = "critica", "Crítica"


class Estado(models.TextChoices):
    ABIERTO = "abierto", "Abierto"
    EN_PROGRESO = "en_progreso", "En progreso"
    RESUELTO = "resuelto", "Resuelto"
    CERRADO = "cerrado", "Cerrado"


# Mismas reglas que en la fase 1: un ticket cerrado no se reabre.
TRANSICIONES = {
    Estado.ABIERTO: {Estado.EN_PROGRESO, Estado.RESUELTO, Estado.CERRADO},
    Estado.EN_PROGRESO: {Estado.ABIERTO, Estado.RESUELTO, Estado.CERRADO},
    Estado.RESUELTO: {Estado.ABIERTO, Estado.CERRADO},
    Estado.CERRADO: set(),
}

AGENTES = {"is_staff": True}  # en Django un "agente" es un usuario con is_staff


class Ticket(models.Model):
    asunto = models.CharField(max_length=200)
    descripcion = models.TextField()
    prioridad = models.CharField(max_length=10, choices=Prioridad, default=Prioridad.MEDIA)
    estado = models.CharField(max_length=12, choices=Estado, default=Estado.ABIERTO)
    agente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        limit_choices_to=AGENTES,
        related_name="tickets_asignados",
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"#{self.pk} {self.asunto}"

    def puede_pasar_a(self, nuevo: str) -> bool:
        return nuevo in TRANSICIONES[Estado(self.estado)]

    @transaction.atomic
    def cambiar_estado(self, nuevo: str, autor) -> None:
        """Cambia el estado y registra el historial en la misma transacción.

        La validación (transición permitida) se hace antes, en el serializer.
        """
        anterior, self.estado = self.estado, nuevo
        self.save(update_fields=["estado", "actualizado"])
        self.historial.create(campo="estado", valor_anterior=anterior, valor_nuevo=nuevo, autor=autor)

    @transaction.atomic
    def asignar(self, agente, autor) -> None:
        anterior = self.agente.get_username() if self.agente else None
        self.agente = agente
        self.save(update_fields=["agente", "actualizado"])
        self.historial.create(
            campo="agente",
            valor_anterior=anterior,
            valor_nuevo=agente.get_username() if agente else None,
            autor=autor,
        )


class Comentario(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comentarios")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    texto = models.TextField()
    es_interno = models.BooleanField(default=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Comentario de {self.autor} en {self.ticket}"


class Historial(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="historial")
    campo = models.CharField(max_length=20)
    valor_anterior = models.CharField(max_length=150, null=True, blank=True)
    valor_nuevo = models.CharField(max_length=150, null=True, blank=True)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name_plural = "historial"

    def __str__(self):
        return f"{self.ticket}: {self.campo} {self.valor_anterior} → {self.valor_nuevo}"
