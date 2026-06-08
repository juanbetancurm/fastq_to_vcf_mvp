from rest_framework import viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import Patient, Sample
from .serializers import PatientSerializer, SampleSerializer


class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all().order_by("external_id")
    serializer_class = PatientSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["sex"]
    search_fields = ["external_id", "clinical_info"]
    ordering_fields = ["external_id", "created_at"]


class SampleViewSet(viewsets.ModelViewSet):
    queryset = Sample.objects.select_related("patient").order_by("-collection_date")
    serializer_class = SampleSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["patient", "tissue_type"]
    search_fields = ["patient__external_id", "sample_barcode"]
