"""
VCF parser step: read VCF file and create Variant database records.
"""


def run(vcf_path: str, run_id: int) -> int:
    """Parse VCF and insert Variant rows. Returns number of variants created."""
    from apps.variants.models import Variant
    from apps.sequencing.models import SequencingRun

    run = SequencingRun.objects.get(pk=run_id)
    Variant.objects.filter(run=run).delete()   # clear any previous run

    created = 0
    with open(vcf_path) as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 10:
                continue

            chrom, pos, vid, ref, alt, qual, filt, info, fmt, sample = fields[:10]

            # Parse INFO field into a dict
            raw_info = {}
            for item in info.split(";"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    raw_info[k] = v
                else:
                    raw_info[item] = True

            # Parse FORMAT / SAMPLE fields
            fmt_keys = fmt.split(":")
            smp_vals = sample.split(":")
            fmt_dict = dict(zip(fmt_keys, smp_vals))

            genotype = fmt_dict.get("GT", "./.")
            try:
                depth = int(fmt_dict.get("DP", 0))
            except ValueError:
                depth = None
            try:
                quality = float(qual) if qual not in (".", "") else None
            except ValueError:
                quality = None

            # Allele frequency from AD field
            allele_freq = None
            ad = fmt_dict.get("AD", "")
            if ad and "," in ad:
                try:
                    counts = [int(x) for x in ad.split(",")]
                    total  = sum(counts)
                    allele_freq = round(counts[1] / total, 3) if total > 0 else None
                except ValueError:
                    pass

            Variant.objects.create(
                run=run,
                chromosome=chrom,
                position=int(pos),
                variant_id=vid if vid != "." else "",
                ref_allele=ref,
                alt_allele=alt,
                quality=quality,
                filter_status=filt,
                genotype=genotype,
                read_depth=depth,
                allele_frequency=allele_freq,
                raw_info=raw_info,
            )
            created += 1

    return created
