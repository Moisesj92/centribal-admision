"""Vistas de la UI: Django "clásico", devuelven HTML generado con templates.

Comparar con views.py (DRF), que devuelve JSON con la misma lógica de fondo.
"""

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import AsignarForm, ComentarioForm, EstadoForm, TicketForm
from .models import Estado, Prioridad, Ticket

# Igual que EsAgente en la API: solo usuarios del grupo "Agentes". Si no, a la página de login.
solo_agentes = user_passes_test(lambda usuario: usuario.is_authenticated and usuario.es_agente)


def nuevo_ticket(request):
    """Formulario público para que un cliente abra una solicitud."""
    form = TicketForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ticket = form.save()
        return render(request, "soporte/ticket_creado.html", {"ticket": ticket})
    return render(request, "soporte/nuevo_ticket.html", {"form": form})


@solo_agentes
def lista(request):
    tickets = Ticket.objects.select_related("agente")
    filtros = {campo: request.GET.get(campo, "") for campo in ("estado", "prioridad", "agente")}
    if filtros["estado"]:
        tickets = tickets.filter(estado=filtros["estado"])
    if filtros["prioridad"]:
        tickets = tickets.filter(prioridad=filtros["prioridad"])
    if filtros["agente"] == "yo":
        tickets = tickets.filter(agente=request.user)
    elif filtros["agente"] == "nadie":
        tickets = tickets.filter(agente__isnull=True)
    contexto = {
        "tickets": tickets,
        "filtros": filtros,
        "estados": Estado.choices,
        "prioridades": Prioridad.choices,
    }
    return render(request, "soporte/lista.html", contexto)


def _contexto_detalle(ticket, **forms):
    return {
        "ticket": ticket,
        "estado_form": forms.get("estado_form") or EstadoForm(ticket=ticket),
        "asignar_form": forms.get("asignar_form") or AsignarForm(ticket=ticket),
        "comentario_form": forms.get("comentario_form") or ComentarioForm(),
        "comentarios": ticket.comentarios.select_related("autor"),
        "historial": ticket.historial.select_related("autor"),
    }


@solo_agentes
def detalle(request, pk):
    ticket = get_object_or_404(Ticket.objects.select_related("agente"), pk=pk)
    return render(request, "soporte/detalle.html", _contexto_detalle(ticket))


# Las acciones siguen el patrón POST → redirect → GET: si el agente recarga la página
# no se repite la acción. Si el formulario tiene errores, se vuelve a pintar el detalle con ellos.


@solo_agentes
@require_POST
def cambiar_estado(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    form = EstadoForm(request.POST, ticket=ticket)
    if not form.is_valid():
        return render(request, "soporte/detalle.html", _contexto_detalle(ticket, estado_form=form), status=400)
    ticket.cambiar_estado(form.cleaned_data["estado"], autor=request.user)
    messages.success(request, f"Estado cambiado a «{ticket.get_estado_display()}».")
    return redirect("ui:detalle", pk=pk)


@solo_agentes
@require_POST
def asignar(request, pk):
    ticket = get_object_or_404(Ticket.objects.select_related("agente"), pk=pk)
    form = AsignarForm(request.POST, ticket=ticket)
    if not form.is_valid():
        return render(request, "soporte/detalle.html", _contexto_detalle(ticket, asignar_form=form), status=400)
    ticket.asignar(form.cleaned_data["agente"], autor=request.user)
    messages.success(request, f"Asignado a {ticket.agente or 'nadie'}.")
    return redirect("ui:detalle", pk=pk)


@solo_agentes
@require_POST
def comentar(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    form = ComentarioForm(request.POST)
    if not form.is_valid():
        return render(request, "soporte/detalle.html", _contexto_detalle(ticket, comentario_form=form), status=400)
    comentario = form.save(commit=False)  # crea el objeto sin guardarlo para completar ticket y autor
    comentario.ticket, comentario.autor = ticket, request.user
    comentario.save()
    ticket.save(update_fields=["actualizado"])
    messages.success(request, "Comentario añadido.")
    return redirect("ui:detalle", pk=pk)
