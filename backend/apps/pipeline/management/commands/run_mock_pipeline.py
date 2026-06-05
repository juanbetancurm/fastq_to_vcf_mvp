"""
Management command: run the full pipeline synchronously on mock data.
Creates a Patient, Sample, and SequencingRun pointing to the mock FASTQ
files, then runs every pipeline stage in-process (no Celery required).
"""
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Run the full bioinformatics pipeline on mock FASTQ data (no Celery)."

    def handle(self, *args, **options):
        from apps.patients.models import Patient, Sample
        from apps.sequencing.models import SequencingRun
        from apps.pipeline.utils import work_dir, reference_path, gene_info_path
        from apps.pipeline.steps import qc, alignment, sorting, variant_calling, vcf_parser, annotation

        test_data = Path(settings.BASE_DIR) / "test_data"
        r1_path   = str(test_data / "mock_sample_R1.fastq")
        r2_path   = str(test_data / "mock_sample_R2.fastq")
        ref       = str(reference_path())

        # ── Create or reuse database records ──────────────────────────────
        patient, _ = Patient.objects.get_or_create(
            external_id="MOCK-001",
            defaults={"sex": "M", "clinical_info": "Mock patient for pipeline testing"},
        )
        sample, _ = Sample.objects.get_or_create(
            patient=patient,
            tissue_type="peripheral_blood",
            defaults={"collection_date": "2026-01-01"},
        )

        # Delete any previous mock run so we start clean
        SequencingRun.objects.filter(sample=sample).delete()

        run = SequencingRun.objects.create(
            sample=sample,
            platform="mock",
            sequencing_type="WES",
            reference_genome="mock_btk",
            fastq_r1=r1_path,
            fastq_r2=r2_path,
            status="pending",
        )
        self.stdout.write(f"Created SequencingRun id={run.pk}\n")

        wdir = work_dir(run.pk)

        def step(name: str):
            self.stdout.write(f"  → {name}...")

        # ── Stage 1: QC ───────────────────────────────────────────────────
        step("QC")
        qc_result = qc.run(r1_path, r2_path)
        run.status      = "qc"
        run.qc_metrics  = qc_result
        run.total_reads = qc_result.get("r1", {}).get("total_reads", 0)
        run.save(update_fields=["status", "qc_metrics", "total_reads"])
        self.stdout.write(
            f"     reads={run.total_reads}, "
            f"mean_q={qc_result['r1']['mean_quality']}, "
            f"gc={qc_result['r1']['gc_fraction']}"
        )

        # ── Stage 2: Alignment ────────────────────────────────────────────
        step("Alignment")
        sam_unsorted = str(wdir / "aligned.sam")
        aln_result = alignment.run(r1_path, r2_path, ref, sam_unsorted)
        run.status        = "aligning"
        run.aligned_reads = aln_result["aligned_reads"]
        run.save(update_fields=["status", "aligned_reads"])
        self.stdout.write(
            f"     aligned={aln_result['aligned_reads']}/{aln_result['total_reads']} "
            f"({aln_result['alignment_rate']}%)"
        )

        # ── Stage 3: Sort ─────────────────────────────────────────────────
        step("Sort")
        sam_sorted = str(wdir / "sorted.sam")
        sorting.run(sam_unsorted, sam_sorted)
        run.status = "sorting"
        run.save(update_fields=["status"])

        # ── Stage 4: Variant calling ──────────────────────────────────────
        step("Variant calling")
        vcf_out = str(wdir / "variants.vcf")
        vc_result = variant_calling.run(sam_sorted, ref, vcf_out)
        run.status       = "calling_variants"
        run.vcf_path     = vcf_out
        run.bam_path     = sam_sorted
        run.mean_coverage = vc_result["mean_coverage"]
        run.save(update_fields=["status", "vcf_path", "bam_path", "mean_coverage"])
        self.stdout.write(
            f"     variants_called={vc_result['variants_found']}, "
            f"mean_coverage={vc_result['mean_coverage']}x"
        )

        # ── Stage 5: VCF parsing ──────────────────────────────────────────
        step("VCF parsing")
        n_variants = vcf_parser.run(vcf_out, run.pk)
        run.status = "parsing_vcf"
        run.save(update_fields=["status"])
        self.stdout.write(f"     {n_variants} variants stored in database")

        # ── Stage 6: Annotation ───────────────────────────────────────────
        step("Annotation")
        n_ann = annotation.run(run.pk, str(gene_info_path()), ref)
        run.status         = "annotating"
        run.variants_found = n_variants
        run.save(update_fields=["status", "variants_found"])
        self.stdout.write(f"     {n_ann} annotations created")

        # ── Complete ──────────────────────────────────────────────────────
        from django.utils import timezone
        run.status       = "completed"
        run.progress_percent = 100
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "progress_percent", "completed_at"])

        self.stdout.write(self.style.SUCCESS(
            f"\nPipeline complete for run id={run.pk}. "
            f"{n_variants} variants, {n_ann} annotations."
        ))
