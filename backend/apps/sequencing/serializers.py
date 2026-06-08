from rest_framework import serializers
from .models import SequencingRun


class SequencingRunSerializer(serializers.ModelSerializer):
    duration        = serializers.SerializerMethodField()
    patient_external_id = serializers.CharField(
        source="sample.patient.external_id", read_only=True
    )
    sample_tissue   = serializers.CharField(
        source="sample.tissue_type", read_only=True
    )

    class Meta:
        model = SequencingRun
        fields = [
            "id", "sample", "patient_external_id", "sample_tissue",
            "platform", "sequencing_type", "read_length", "reference_genome",
            "fastq_r1", "fastq_r2",
            "status", "progress_percent", "celery_task_id", "error_message",
            "qc_metrics", "bam_path", "vcf_path",
            "total_reads", "aligned_reads", "mean_coverage", "variants_found",
            "started_at", "completed_at", "created_at", "updated_at",
            "duration",
        ]
        read_only_fields = [
            "id", "status", "progress_percent", "celery_task_id",
            "error_message", "qc_metrics", "bam_path", "vcf_path",
            "total_reads", "aligned_reads", "mean_coverage", "variants_found",
            "started_at", "completed_at", "created_at", "updated_at",
        ]

    def get_duration(self, obj):
        d = obj.duration
        return str(d) if d else None


class SequencingRunStatusSerializer(serializers.ModelSerializer):
    """Lightweight serializer for progress polling — minimal fields."""

    class Meta:
        model = SequencingRun
        fields = [
            "id", "status", "progress_percent", "error_message",
            "variants_found", "mean_coverage",
        ]


class SequencingRunCreateSerializer(serializers.Serializer):
    """
    Accepts multipart form data for new run creation.
    Patient and Sample are created/looked up server-side.
    """
    # Patient fields
    patient_external_id = serializers.CharField(max_length=64)
    patient_sex         = serializers.ChoiceField(
        choices=[("M", "Male"), ("F", "Female"), ("U", "Unknown")], default="U"
    )
    clinical_info       = serializers.CharField(required=False, allow_blank=True, default="")

    # Sample fields
    tissue_type     = serializers.ChoiceField(choices=[
        "peripheral_blood", "bone_marrow", "saliva", "skin_biopsy", "other"
    ], default="peripheral_blood")
    collection_date = serializers.DateField()

    # Run fields
    platform         = serializers.ChoiceField(choices=[
        "illumina_novaseq", "illumina_nextseq", "illumina_miseq", "mock"
    ], default="mock")
    sequencing_type  = serializers.ChoiceField(choices=["WES", "WGS"], default="WES")
    reference_genome = serializers.ChoiceField(
        choices=["GRCh38", "GRCh37", "mock_btk"], default="mock_btk"
    )
    fastq_r1 = serializers.FileField()
    fastq_r2 = serializers.FileField(required=False, allow_null=True)
