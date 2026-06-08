from rest_framework.routers import DefaultRouter
from .views import PatientViewSet, SampleViewSet

router = DefaultRouter()
router.register("patients", PatientViewSet, basename="patient")
router.register("samples", SampleViewSet, basename="sample")

urlpatterns = router.urls
