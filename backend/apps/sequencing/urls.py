from rest_framework.routers import DefaultRouter
from .views import SequencingRunViewSet

router = DefaultRouter()
router.register("runs", SequencingRunViewSet, basename="run")

urlpatterns = router.urls
