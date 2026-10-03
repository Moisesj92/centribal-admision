from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from cuentas.models import GRUPO_AGENTES


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


class ConflictoConcurrente(Exception):
    """Otra petición cambió el ticket entre la lectura y la escritura (→ HTTP 409)."""


# Un ticket cerrado no se reabre.
TRANSICIONES = {
    Estado.ABIERTO: {Estado.EN_PROGRESO, Estado.RESUELTO, Estado.CERRADO},
    Estado.EN_PROGRESO: {Estado.ABIERTO, Estado.RESUELTO, Estado.CERRADO},
    Estado.RESUELTO: {Estado.ABIERTO, Estado.CERRADO},
    Estado.CERRADO: set(),
}



MAX_DESCRIPCION = 5000
MAX_COMENTARIO = 2000


class Ticket(models.Model):
    asunto = models.CharField(max_length=200)
    descripcion = models.TextField(max_length=MAX_DESCRIPCION)
    prioridad = models.CharField(max_length=10, choices=Prioridad, default=Prioridad.MEDIA)
    estado = models.CharField(max_length=12, choices=Estado, default=Estado.ABIERTO)
    agente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        # PROTECT: un agente con tickets no se borra (se desactiva), así no se pierde quién los llevaba
        # ni se cambia la asignación sin dejar historial, como haría SET_NULL.
        on_delete=models.PROTECT,
        limit_choices_to={"is_active": True, "groups__name": GRUPO_AGENTES},
        related_name="tickets_asignados",
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        # choices y blank solo se validan en forms/serializers (save() no valida). Estas
        # restricciones hacen que la base de datos rechace datos imposibles venga de donde venga.
        constraints = [
            models.CheckConstraint(condition=models.Q(estado__in=Estado.values), name="ticket_estado_valido"),
            models.CheckConstraint(condition=models.Q(prioridad__in=Prioridad.values), name="ticket_prioridad_valida"),
            models.CheckConstraint(condition=~models.Q(asunto=""), name="ticket_asunto_no_vacio"),
            models.CheckConstraint(condition=~models.Q(descripcion=""), name="ticket_descripcion_no_vacia"),
        ]

    def __str__(self):
        return f"#{self.pk} {self.asunto}"

    # Las reglas viven en el modelo para que la API (serializers) y la UI (forms) usen las mismas.

    def estados_siguientes(self) -> list[Estado]:
        return [e for e in Estado if e in TRANSICIONES[Estado(self.estado)]]

    def validar_estado(self, nuevo: str) -> None:
        if nuevo == self.estado:
            raise ValidationError(f"El ticket ya está en estado {nuevo}.")
        if nuevo not in TRANSICIONES[Estado(self.estado)]:
            raise ValidationError(f"No se puede pasar de {self.estado} a {nuevo}.")

    def validar_asignacion(self, agente) -> None:
        if self.estado == Estado.CERRADO:
            raise ValidationError("No se puede reasignar un ticket cerrado.")
        if agente == self.agente:
            raise ValidationError("El ticket ya está asignado a ese agente.")

    # Concurrencia optimista: la validación usa el estado leído en memoria, así que el UPDATE
    # solo se aplica si la fila sigue igual que cuando se leyó. Si otra petición la cambió
    # entretanto (p. ej. la cerró), no se actualiza ninguna fila y se lanza ConflictoConcurrente.
    # Funciona en cualquier base de datos, también en SQLite, donde select_for_update no bloquea.

    def _actualizar_si_no_cambio(self, condicion: dict, **cambios) -> None:
        ahora = timezone.now()
        filas = Ticket.objects.filter(pk=self.pk, **condicion).update(**cambios, actualizado=ahora)
        if filas == 0:
            raise ConflictoConcurrente("El ticket cambió mientras tanto. Recarga e inténtalo de nuevo.")
        for campo, valor in cambios.items():
            setattr(self, campo, valor)
        self.actualizado = ahora

    @transaction.atomic
    def cambiar_estado(self, nuevo: str, autor) -> None:
        """Valida, cambia el estado y registra el historial en la misma transacción."""
        self.validar_estado(nuevo)
        anterior = self.estado
        self._actualizar_si_no_cambio({"estado": anterior}, estado=nuevo)
        self.historial.create(campo="estado", valor_anterior=anterior, valor_nuevo=nuevo, autor=autor)

    @transaction.atomic
    def asignar(self, agente, autor) -> None:
        self.validar_asignacion(agente)
        anterior = self.agente.get_username() if self.agente else None
        # Condición: mismo agente que al leer y que nadie lo haya cerrado entretanto.
        condicion = {"agente": self.agente_id, "estado__in": [e for e in Estado if e != Estado.CERRADO]}
        self._actualizar_si_no_cambio(condicion, agente=agente)
        self.historial.create(
            campo="agente",
            valor_anterior=anterior,
            valor_nuevo=agente.get_username() if agente else None,
            autor=autor,
        )


class Comentario(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comentarios")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    texto = models.TextField(max_length=MAX_COMENTARIO)  # todos los comentarios son internos (solo agentes)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [models.CheckConstraint(condition=~models.Q(texto=""), name="comentario_texto_no_vacio")]

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
