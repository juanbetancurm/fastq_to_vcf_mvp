from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import SequencingRun
from .serializers import (
    SequencingRunSerializer,
    SequencingRunStatusSerializer,
    SequencingRunCreateSerializer,
)


class SequencingRunViewSet(viewsets.ModelViewSet):
    queryset = SequencingRun.objects.select_related(
        "sample__patient"
    ).order_by("-created_at")
    serializer_class = SequencingRunSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "platform", "sequencing_type", "reference_genome"]
    search_fields = ["sample__patient__external_id", "celery_task_id"]
    ordering_fields = ["created_at", "status", "variants_found"]

    def get_serializer_class(self):
        if self.action == "create":
            return SequencingRunCreateSerializer
        if self.action == "status":
            return SequencingRunStatusSerializer
        return SequencingRunSerializer

    def create(self, request, *args, **kwargs):
        serializer = SequencingRunCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        from apps.patients.models import Patient, Sample
        from apps.pipeline.tasks import run_pipeline_task
        from django.utils import timezone

        patient, _ = Patient.objects.get_or_create(
            external_id=d["patient_external_id"],
            defaults={
                "sex":          d["patient_sex"],
                "clinical_info": d.get("clinical_info", ""),
            },
        )

        sample = Sample.objects.create(
            patient=patient,
            tissue_type=d["tissue_type"],
            collection_date=d["collection_date"],
        )

        run = SequencingRun.objects.create(
            sample=sample,
            platform=d["platform"],
            sequencing_type=d["sequencing_type"],
            reference_genome=d["reference_genome"],
            fastq_r1=d["fastq_r1"],
            fastq_r2=d.get("fastq_r2"),
            status="pending",
        )

        task = run_pipeline_task.delay(run.pk)
        run.celery_task_id = task.id
        run.save(update_fields=["celery_task_id"])

        return Response(
            SequencingRunSerializer(run).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="status")
    def status(self, request, pk=None):
        """Lightweight polling endpoint — returns only status fields."""
        run = self.get_object()
        return Response(SequencingRunStatusSerializer(run).data)

    @action(detail=True, methods=["get"], url_path="variants")
    def variants(self, request, pk=None):
        """Return paginated variants for this run with optional filtering."""
        from apps.variants.models import Variant
        from apps.variants.serializers import VariantSerializer

        run = self.get_object()
        qs = Variant.objects.filter(run=run).prefetch_related("annotations")

        # Optional filters from query params
        chrom    = request.query_params.get("chromosome")
        genotype = request.query_params.get("genotype")
        impact   = request.query_params.get("impact")
        iei_only = request.query_params.get("is_iei_gene")

        if chrom:
            qs = qs.filter(chromosome=chrom)
        if genotype:
            qs = qs.filter(genotype=genotype)
        if impact:
            qs = qs.filter(annotations__impact=impact)
        if iei_only and iei_only.lower() in ("true", "1"):
            qs = qs.filter(annotations__is_iei_gene=True)

        qs = qs.distinct()

        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(VariantSerializer(page, many=True).data)
        return Response(VariantSerializer(qs, many=True).data)
