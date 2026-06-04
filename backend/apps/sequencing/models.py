from django.db import models
from apps.patients.models import Sample


class SequencingRun(models.Model):
    PLATFORM_CHOICES = [
        ("illumina_novaseq", "Illumina NovaSeq"),
        ("illumina_nextseq", "Illumina NextSeq"),
        ("illumina_miseq", "Illumina MiSeq"),
        ("mock", "Mock (Test Data)"),
    ]

    SEQUENCING_TYPE_CHOICES = [
        ("WES", "Whole Exome Sequencing"),
        ("WGS", "Whole Genome Sequencing"),
    ]

    REFERENCE_GENOME_CHOICES = [
        ("GRCh38", "GRCh38 / hg38"),
        ("GRCh37", "GRCh37 / hg19"),
        ("mock_btk", "Mock BTK (Test)"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("qc", "Quality Control"),
        ("aligning", "Aligning Reads"),
        ("sorting", "Sorting BAM"),
        ("calling_variants", "Calling Variants"),
        ("parsing_vcf", "Parsing VCF"),
        ("annotating", "Annotating Variants"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    sample = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name="sequencing_runs")
    platform = models.CharField(max_length=32, choices=PLATFORM_CHOICES, default="mock")
    sequencing_type = models.CharField(max_length=8, choices=SEQUENCING_TYPE_CHOICES, default="WES")
    read_length = models.IntegerField(default=150)
    reference_genome = models.CharField(max_length=16, choices=REFERENCE_GENOME_CHOICES, default="mock_btk")
    fastq_r1 = models.FileField(upload_to="fastq/")
    fastq_r2 = models.FileField(upload_to="fastq/", null=True, blank=True)

    # Pipeline state machine
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="pending", db_index=True)
    progress_percent = models.IntegerField(default=0)
    celery_task_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)

    # Pipeline outputs — populated as stages complete
    qc_metrics = models.JSONField(default=dict)
    bam_path = models.CharField(max_length=512, blank=True)
    vcf_path = models.CharField(max_length=512, blank=True)

    # Summary statistics
    total_reads = models.BigIntegerField(null=True, blank=True)
    aligned_reads = models.BigIntegerField(null=True, blank=True)
    mean_coverage = models.FloatField(null=True, blank=True)
    variants_found = models.IntegerField(null=True, blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def duration(self):
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    def __str__(self):
        return f"Run {self.pk} — {self.sample} [{self.status}]"
