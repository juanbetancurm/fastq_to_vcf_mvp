import django_filters
from rest_framework import viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import Variant, VariantAnnotation
from .serializers import VariantSerializer, VariantListSerializer


class VariantFilter(django_filters.FilterSet):
    run         = django_filters.NumberFilter(field_name="run__id")
    chromosome  = django_filters.CharFilter()
    genotype    = django_filters.CharFilter()
    impact      = django_filters.CharFilter(field_name="annotations__impact")
    is_iei_gene = django_filters.BooleanFilter(field_name="annotations__is_iei_gene")
    gene        = django_filters.CharFilter(
        field_name="annotations__gene_symbol", lookup_expr="iexact"
    )
    consequence = django_filters.CharFilter(
        field_name="annotations__consequence", lookup_expr="icontains"
    )

    class Meta:
        model = Variant
        fields = ["run", "chromosome", "genotype"]


class VariantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        Variant.objects.select_related("run__sample__patient")
        .prefetch_related("annotations")
        .order_by("chromosome", "position")
    )
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = VariantFilter
    search_fields = ["chromosome", "variant_id", "annotations__gene_symbol"]
    ordering_fields = ["chromosome", "position", "quality", "read_depth"]

    def get_serializer_class(self):
        if self.action == "list":
            return VariantListSerializer
        return VariantSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Distinct required when filtering through M2M/reverse FK (annotations)
        return qs.distinct()
