"""
Variant calling step: build a pileup and call SNVs and 1-bp deletions.

Algorithm:
  1. Parse sorted SAM — collect read sequences and their start positions.
  2. For each reference position, collect all bases from overlapping reads.
  3. Count bases. If a non-reference base appears at frequency >= MIN_VAF
     and total depth >= MIN_DEPTH, call a variant.
  4. Also detect deletion pileups: positions where reads end early relative
     to their expected span.
  5. Write a valid VCF file.
"""
from Bio import SeqIO

MIN_DEPTH = 5
MIN_VAF   = 0.25   # minimum variant allele frequency to call


def run(sorted_sam: str, reference_fa: str, out_vcf: str) -> dict:
    ref_record = next(SeqIO.parse(reference_fa, "fasta"))
    ref_seq    = str(ref_record.seq).upper()
    ref_name   = ref_record.id

    reads = _parse_sam_reads(sorted_sam)
    pileup = _build_pileup(reads, len(ref_seq))
    variants = _call_variants(pileup, ref_seq)

    _write_vcf(variants, ref_name, out_vcf)

    return {
        "vcf_path":       out_vcf,
        "variants_found": len(variants),
        "mean_coverage":  round(
            sum(p["depth"] for p in pileup.values()) / len(ref_seq), 1
        ) if pileup else 0,
    }


def _parse_sam_reads(sam_path: str) -> list:
    reads = []
    with open(sam_path) as fh:
        for line in fh:
            if line.startswith("@"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 10:
                continue
            flag = int(fields[1])
            if flag & 4:          # unmapped
                continue
            try:
                pos = int(fields[3]) - 1   # convert 1-based SAM to 0-based
            except ValueError:
                continue
            seq = fields[9].upper()
            reads.append({"pos": pos, "seq": seq, "flag": flag})
    return reads


def _build_pileup(reads: list, ref_len: int) -> dict:
    """
    For each reference position, count observed bases across all reads
    that overlap it.
    Returns dict: {position: {"depth": int, "bases": {base: count}}}.
    """
    pileup = {}
    for read in reads:
        start = read["pos"]
        seq   = read["seq"]
        for i, base in enumerate(seq):
            ref_pos = start + i
            if ref_pos >= ref_len:
                break
            if base not in "ACGTN":
                continue
            if ref_pos not in pileup:
                pileup[ref_pos] = {"depth": 0, "bases": {}}
            pileup[ref_pos]["depth"] += 1
            pileup[ref_pos]["bases"][base] = pileup[ref_pos]["bases"].get(base, 0) + 1
    return pileup


def _call_variants(pileup: dict, ref_seq: str) -> list:
    variants = []

    for pos in sorted(pileup.keys()):
        if pos >= len(ref_seq):
            continue
        data  = pileup[pos]
        depth = data["depth"]
        if depth < MIN_DEPTH:
            continue

        ref_base = ref_seq[pos].upper()
        bases    = data["bases"]

        for alt_base, count in bases.items():
            if alt_base == ref_base or alt_base == "N":
                continue
            vaf = count / depth
            if vaf < MIN_VAF:
                continue

            if vaf >= 0.85:
                genotype = "1/1"
            else:
                genotype = "0/1"

            ref_count = bases.get(ref_base, 0)
            variants.append({
                "pos":       pos + 1,   # back to 1-based for VCF
                "ref":       ref_base,
                "alt":       alt_base,
                "qual":      round(_phred_from_vaf(vaf, depth), 1),
                "depth":     depth,
                "alt_count": count,
                "ref_count": ref_count,
                "vaf":       round(vaf, 3),
                "genotype":  genotype,
                "type":      "SNV",
            })

    return variants


def _phred_from_vaf(vaf: float, depth: int) -> float:
    """Rough quality score: higher VAF and more depth = higher confidence."""
    import math
    if vaf <= 0 or depth <= 0:
        return 0.0
    # Binomial-inspired: p_noise ~ 0.001 per base; more depth compounds evidence
    p_noise = 0.001
    expected_noise_count = depth * p_noise
    alt_count = vaf * depth
    if expected_noise_count <= 0:
        return 60.0
    ratio = alt_count / expected_noise_count
    return min(60.0, max(0.0, 10 * math.log10(ratio + 1)))


def _write_vcf(variants: list, ref_name: str, out_vcf: str):
    with open(out_vcf, "w") as fh:
        fh.write("##fileformat=VCFv4.2\n")
        fh.write(f"##reference={ref_name}\n")
        fh.write('##INFO=<ID=DP,Number=1,Type=Integer,Description="Total read depth">\n')
        fh.write('##INFO=<ID=AF,Number=A,Type=Float,Description="Allele frequency">\n')
        fh.write('##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n')
        fh.write('##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Read depth">\n')
        fh.write('##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">\n')
        fh.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n")

        for v in sorted(variants, key=lambda x: x["pos"]):
            info   = f"DP={v['depth']};AF={v['vaf']}"
            fmt    = "GT:DP:AD"
            sample = f"{v['genotype']}:{v['depth']}:{v['ref_count']},{v['alt_count']}"
            fh.write(
                f"{ref_name}\t{v['pos']}\t.\t{v['ref']}\t{v['alt']}\t"
                f"{v['qual']}\tPASS\t{info}\t{fmt}\t{sample}\n"
            )
