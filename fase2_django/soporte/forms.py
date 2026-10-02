"""Formularios de la UI: el equivalente HTML de los serializers de la API.

Las reglas (transiciones, reasignación) no se repiten: se llama a las validaciones del modelo.
"""

from django import forms
from django.contrib.auth import get_user_model

from .models import AGENTES, Comentario, Estado, Ticket


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["asunto", "descripcion", "prioridad"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 5})}

    def clean_asunto(self):
        asunto = self.cleaned_data["asunto"].strip()
        if not asunto:
            raise forms.ValidationError("El asunto no puede estar vacío.")
        return asunto


class EstadoForm(forms.Form):
    estado = forms.ChoiceField(choices=Estado.choices)

    def __init__(self, *args, ticket: Ticket, **kwargs):
        super().__init__(*args, **kwargs)
        self.ticket = ticket
        # Solo se ofrecen los estados a los que se puede pasar desde el actual.
        self.fields["estado"].choices = [(e.value, e.label) for e in ticket.estados_siguientes()]

    def clean_estado(self):
        nuevo = self.cleaned_data["estado"]
        self.ticket.validar_estado(nuevo)  # su ValidationError lo entiende el form directamente
        return nuevo


class AsignarForm(forms.Form):
    agente = forms.ModelChoiceField(
        queryset=get_user_model().objects.filter(**AGENTES).order_by("username"),
        required=False,
        empty_label="— sin asignar —",
    )

    def __init__(self, *args, ticket: Ticket, **kwargs):
        super().__init__(*args, initial={"agente": ticket.agente}, **kwargs)
        self.ticket = ticket

    def clean(self):
        datos = super().clean()
        if "agente" in datos:
            self.ticket.validar_asignacion(datos["agente"])
        return datos


class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ["texto"]
        widgets = {"texto": forms.Textarea(attrs={"rows": 3, "placeholder": "Comentario interno…"})}
        labels = {"texto": ""}
