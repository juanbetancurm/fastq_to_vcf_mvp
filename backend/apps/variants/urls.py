from rest_framework.routers import DefaultRouter
from .views import VariantViewSet

router = DefaultRouter()
router.register("variants", VariantViewSet, basename="variant")

urlpatterns = router.urls
