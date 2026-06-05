import time
from pathlib import Path
from celery import shared_task
from django.utils import timezone


@shared_task(bind=True, name="pipeline.test_task")
def test_pipeline_task(self):
    """Walks through pipeline states with delays. Verifies Celery + Redis."""
    stages = [
        ("qc",               "Quality Control",      10),
        ("aligning",         "Aligning Reads",       30),
        ("sorting",          "Sorting BAM",          50),
        ("calling_variants", "Calling Variants",     70),
        ("parsing_vcf",      "Parsing VCF",          85),
        ("annotating",       "Annotating Variants",  95),
        ("completed",        "Completed",           100),
    ]
    for status, label, progress in stages:
        self.update_state(
            state="PROGRESS",
            meta={"status": status, "label": label, "progress": progress},
        )
        time.sleep(0.5)
    return {"status": "completed", "progress": 100}


@shared_task(bind=True, name="pipeline.run_pipeline")
def run_pipeline_task(self, run_id: int):
    """
    Orchestrate the full bioinformatics pipeline for a SequencingRun.
    Updates run.status and run.progress_percent after each stage.
    """
    from apps.sequencing.models import SequencingRun
    from apps.pipeline.utils import work_dir, reference_path, gene_info_path
    from apps.pipeline.steps import qc, alignment, sorting, variant_calling, vcf_parser, annotation

    def update(status: str, progress: int, label: str):
        SequencingRun.objects.filter(pk=run_id).update(
            status=status, progress_percent=progress
        )
        self.update_state(
            state="PROGRESS",
            meta={"status": status, "label": label, "progress": progress},
        )

    run = SequencingRun.objects.get(pk=run_id)
    run.started_at = timezone.now()
    run.save(update_fields=["started_at"])

    wdir = work_dir(run_id)
    ref  = str(reference_path())

    try:
        # ── Stage 1: QC ───────────────────────────────────────────────────
        update("qc", 5, "Quality Control")
        r1_path = run.fastq_r1.path if hasattr(run.fastq_r1, "path") else str(run.fastq_r1)
        r2_path = run.fastq_r2.path if (run.fastq_r2 and hasattr(run.fastq_r2, "path")) else (str(run.fastq_r2) if run.fastq_r2 else None)
        qc_result = qc.run(r1_path, r2_path)
        SequencingRun.objects.filter(pk=run_id).update(
            qc_metrics=qc_result,
            total_reads=qc_result.get("r1", {}).get("total_reads", 0),
        )

        # ── Stage 2: Alignment ────────────────────────────────────────────
        update("aligning", 20, "Aligning Reads")
        sam_unsorted = str(wdir / "aligned.sam")
        aln_result = alignment.run(r1_path, r2_path, ref, sam_unsorted)
        SequencingRun.objects.filter(pk=run_id).update(
            aligned_reads=aln_result["aligned_reads"],
        )

        # ── Stage 3: Sort ─────────────────────────────────────────────────
        update("sorting", 45, "Sorting BAM")
        sam_sorted = str(wdir / "sorted.sam")
        sort_result = sorting.run(sam_unsorted, sam_sorted)

        # ── Stage 4: Variant calling ──────────────────────────────────────
        update("calling_variants", 60, "Calling Variants")
        vcf_out = str(wdir / "variants.vcf")
        vc_result = variant_calling.run(sam_sorted, ref, vcf_out)
        SequencingRun.objects.filter(pk=run_id).update(
            vcf_path=vcf_out,
            bam_path=sam_sorted,
            mean_coverage=vc_result["mean_coverage"],
        )

        # ── Stage 5: VCF parsing ──────────────────────────────────────────
        update("parsing_vcf", 75, "Parsing VCF")
        n_variants = vcf_parser.run(vcf_out, run_id)

        # ── Stage 6: Annotation ───────────────────────────────────────────
        update("annotating", 88, "Annotating Variants")
        n_annotations = annotation.run(
            run_id,
            str(gene_info_path()),
            ref,
        )

        # ── Complete ──────────────────────────────────────────────────────
        SequencingRun.objects.filter(pk=run_id).update(
            status="completed",
            progress_percent=100,
            variants_found=n_variants,
            completed_at=timezone.now(),
        )
        self.update_state(
            state="SUCCESS",
            meta={"status": "completed", "progress": 100,
                  "variants_found": n_variants,
                  "annotations": n_annotations},
        )
        return {
            "status": "completed",
            "variants_found": n_variants,
            "annotations": n_annotations,
        }

    except Exception as exc:
        SequencingRun.objects.filter(pk=run_id).update(
            status="failed",
            error_message=str(exc),
        )
        raise
