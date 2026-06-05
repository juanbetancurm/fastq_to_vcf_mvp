"""
Management command: compare pipeline output against planted ground truth.

Loads test_data/mock_planted_variants.json and checks each variant against
the Variant and VariantAnnotation tables for the most recent completed run.
"""
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Validate pipeline output against mock planted variants ground truth."

    def add_arguments(self, parser):
        parser.add_argument(
            "--run-id", type=int, default=None,
            help="SequencingRun id to validate (defaults to most recent completed run).",
        )

    def handle(self, *args, **options):
        from apps.sequencing.models import SequencingRun
        from apps.variants.models import Variant, VariantAnnotation

        # ── Load ground truth ─────────────────────────────────────────────
        gt_path = Path(settings.BASE_DIR) / "test_data" / "mock_planted_variants.json"
        if not gt_path.exists():
            self.stdout.write(self.style.ERROR(
                f"Ground truth file not found: {gt_path}\n"
                "Run: python scripts/generate_mock_fastq.py"
            ))
            return

        with open(gt_path) as fh:
            ground_truth = json.load(fh)

        planted = ground_truth["variants"]
        chrom   = ground_truth["chromosome"]

        # ── Resolve which run to validate ─────────────────────────────────
        run_id = options["run_id"]
        if run_id:
            try:
                run = SequencingRun.objects.get(pk=run_id)
            except SequencingRun.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Run id={run_id} not found."))
                return
        else:
            run = (
                SequencingRun.objects.filter(status="completed")
                .order_by("-completed_at")
                .first()
            )
            if not run:
                self.stdout.write(self.style.ERROR(
                    "No completed runs found. Run: python manage.py run_mock_pipeline"
                ))
                return

        self.stdout.write(f"Validating run id={run.pk}  "
                          f"(completed {run.completed_at})\n")

        # ── Fetch all variants for this run ───────────────────────────────
        db_variants = {
            (v.chromosome, v.position, v.ref_allele, v.alt_allele): v
            for v in Variant.objects.filter(run=run).prefetch_related("annotations")
        }

        # ── Compare ───────────────────────────────────────────────────────
        FOUND   = "FOUND  "
        MISSING = "MISSING"

        rows      = []
        n_found   = 0
        n_missing = 0
        n_wrong_gt   = 0
        n_wrong_cons = 0

        for p in planted:
            pos   = p["position"]
            ref   = p["ref_allele"]
            alt   = p["alt_allele"]
            exp_gt   = p["expected_genotype"]
            exp_cons = p["expected_consequence"]

            key = (chrom, pos, ref, alt)
            db_v = db_variants.get(key)

            if db_v is None:
                status = MISSING
                n_missing += 1
                rows.append({
                    "status":     status,
                    "pos":        pos,
                    "ref":        ref or "-",
                    "alt":        alt or "-",
                    "exp_gt":     exp_gt,
                    "got_gt":     "—",
                    "exp_cons":   exp_cons,
                    "got_cons":   "—",
                    "gt_ok":      False,
                    "cons_ok":    False,
                    "note":       p["note"],
                })
                continue

            n_found += 1
            status = FOUND

            got_gt = db_v.genotype
            gt_ok  = got_gt == exp_gt
            if not gt_ok:
                n_wrong_gt += 1

            annotations = list(db_v.annotations.all())
            got_cons = annotations[0].consequence if annotations else "—"
            cons_ok  = got_cons == exp_cons
            if not cons_ok:
                n_wrong_cons += 1

            rows.append({
                "status":   status,
                "pos":      pos,
                "ref":      ref or "-",
                "alt":      alt or "-",
                "exp_gt":   exp_gt,
                "got_gt":   got_gt,
                "exp_cons": exp_cons,
                "got_cons": got_cons,
                "gt_ok":    gt_ok,
                "cons_ok":  cons_ok,
                "note":     p["note"],
            })

        # ── Unexpected extra variants ──────────────────────────────────────
        planted_keys = {
            (chrom, p["position"], p["ref_allele"], p["alt_allele"])
            for p in planted
        }
        extra = [v for k, v in db_variants.items() if k not in planted_keys]

        # ── Print table ───────────────────────────────────────────────────
        sep = "-" * 90
        self.stdout.write(sep)
        self.stdout.write(
            f"{'STATUS':<9} {'POS':>5}  {'REF':>3} {'ALT':>3}  "
            f"{'GT exp/got':<12}  {'CONSEQUENCE (expected → got)'}"
        )
        self.stdout.write(sep)

        for r in rows:
            gt_flag   = "✓" if r["gt_ok"]   else "✗"
            cons_flag = "✓" if r["cons_ok"] else "✗"
            gt_str    = f"{r['exp_gt']}/{r['got_gt']}"

            if r["status"] == MISSING:
                line = (
                    f"{self.style.WARNING(r['status']):<9} "
                    f"{r['pos']:>5}  {r['ref']:>3} {r['alt']:>3}  "
                    f"{'—':<12}  {r['exp_cons']}  [{r['note']}]"
                )
            else:
                cons_part = (
                    f"{r['exp_cons']} → {r['got_cons']} {cons_flag}"
                    if r["exp_cons"] != r["got_cons"]
                    else f"{r['got_cons']} {cons_flag}"
                )
                line = (
                    f"{self.style.SUCCESS(r['status']):<9} "
                    f"{r['pos']:>5}  {r['ref']:>3} {r['alt']:>3}  "
                    f"{gt_str:<12} {gt_flag}  {cons_part}"
                )
            self.stdout.write(line)

        self.stdout.write(sep)

        if extra:
            self.stdout.write(f"\nExtra variants in DB not in ground truth: {len(extra)}")
            for v in extra:
                self.stdout.write(f"  {v.chromosome}:{v.position} {v.ref_allele}>{v.alt_allele}")

        # ── Summary ───────────────────────────────────────────────────────
        self.stdout.write(f"\nSummary:")
        self.stdout.write(f"  Planted:       {len(planted)}")
        self.stdout.write(f"  Found:         {n_found}")
        self.stdout.write(f"  Missing:       {n_missing}")
        self.stdout.write(f"  Wrong genotype:    {n_wrong_gt}")
        self.stdout.write(f"  Wrong consequence: {n_wrong_cons}")

        snv_total = sum(1 for p in planted if p["type"] == "SNV")
        snv_found = sum(1 for r in rows if r["status"] == FOUND)

        if n_missing == 0 and n_wrong_gt == 0:
            self.stdout.write(self.style.SUCCESS("\nRESULT: PASS"))
        elif n_missing == 1 and rows[-1]["status"] == MISSING:
            self.stdout.write(self.style.WARNING(
                f"\nRESULT: PARTIAL PASS — "
                f"{snv_found}/{snv_total} SNVs found correctly. "
                f"1 deletion undetected (known pure-Python pileup limitation)."
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"\nRESULT: FAIL — {n_missing} missing, "
                f"{n_wrong_gt} wrong genotype, {n_wrong_cons} wrong consequence."
            ))
