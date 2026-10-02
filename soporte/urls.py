from rest_framework.routers import DefaultRouter

from .views import TicketViewSet

# El router genera /tickets/, /tickets/{id}/ y una ruta por cada @action.
router = DefaultRouter()
router.register("tickets", TicketViewSet, basename="ticket")

urlpatterns = router.urls
