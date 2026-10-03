from rest_framework.permissions import BasePermission


class EsAgente(BasePermission):
    """Solo usuarios activos del grupo "Agentes" (sin credenciales → 401, sin rol → 403)."""

    message = "Solo los agentes pueden realizar esta acción."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.es_agente)
