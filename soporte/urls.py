from rest_framework.routers import DefaultRouter

from .views import TicketViewSet

# El router genera /api/tickets/, /api/tickets/{id}/ (prefijo "api/" en config/urls.py) y una ruta por cada @action.
router = DefaultRouter()
router.register("tickets", TicketViewSet, basename="ticket")

urlpatterns = router.urls
