#!/usr/bin/env python
"""
generate_mock_fastq.py

Simulate Illumina paired-end sequencing from a diploid mock BTK genome.
Plants 5 known variants and writes paired FASTQ files plus a ground truth JSON.

Outputs (written to backend/test_data/):
  mock_sample_R1.fastq         — Read 1 (forward reads)
  mock_sample_R2.fastq         — Read 2 (reverse reads)
  mock_planted_variants.json   — Ground truth for Step 6 validation
"""
import json
import random
from pathlib import Path

from Bio import SeqIO

random.seed(42)

BASE_DIR       = Path(__file__).resolve().parent.parent
REFERENCE_PATH = BASE_DIR / "reference_data" / "mock_btk_reference.fa"
OUTPUT_DIR     = BASE_DIR / "test_data"

READ_LENGTH          = 150
FRAGMENT_LENGTH_MEAN = 350
FRAGMENT_LENGTH_STD  = 50
NUM_FRAGMENTS        = 1000
CHROM                = "chrX"

# ── Planted variant definitions (positions 1-based, VCF convention) ───────
#
# desired_alt: the ALT base we want; if it equals REF, script cycles to next.
# type "DEL": 1-bp deletion of the base at this position.
# Positions are chosen to match the gene structure from Step 2:
#   350  → Exon 1  CDS offset 49   (codon 17, position 1) → missense
#   800  → Intron 1                                        → intronic
#   1350 → Exon 2  CDS offset 499  (codon 167, position 1) → synonymous
#   2650 → Exon 3  CDS offset 1099 (codon 367, position 1) → missense
#   3700 → Exon 4  CDS offset 1449 (codon 484, position 0) → frameshift

RAW_VARIANTS = [
    {
        "position": 350, "type": "SNV", "desired_alt": "G",
        "zygosity": "het",
        "expected_consequence": "missense_variant",
        "note": "Exon 1 heterozygous missense",
    },
    {
        "position": 800, "type": "SNV", "desired_alt": "T",
        "zygosity": "hom",
        "expected_consequence": "intron_variant",
        "note": "Intron 1 homozygous SNV",
    },
    {
        "position": 1350, "type": "SNV", "desired_alt": "C",
        "zygosity": "hom",
        "expected_consequence": "synonymous_variant",
        "note": "Exon 2 homozygous synonymous",
    },
    {
        "position": 2650, "type": "SNV", "desired_alt": "A",
        "zygosity": "het",
        "expected_consequence": "missense_variant",
        "note": "Exon 3 heterozygous missense",
    },
    {
        "position": 3700, "type": "DEL", "desired_alt": None,
        "zygosity": "het",
        "expected_consequence": "frameshift_variant",
        "note": "Exon 4 heterozygous 1-bp deletion (frameshift)",
    },
]


# ── Sequence utilities ────────────────────────────────────────────────────

COMPLEMENT = str.maketrans("ACGTNacgtn", "TGCANtgcan")


def reverse_complement(seq: str) -> str:
    return seq.translate(COMPLEMENT)[::-1]


def resolve_alt(ref_base: str, desired: str) -> str:
    """Return desired if it differs from ref; otherwise cycle through ACGT."""
    if desired and desired != ref_base:
        return desired
    for b in "ACGT":
        if b != ref_base:
            return b
    return desired


# ── Quality score model ───────────────────────────────────────────────────

def quality_scores(length: int) -> list:
    """
    Phred quality scores simulating Illumina signal decay.
    Starts at Q~37, decays linearly to Q~22 at the last base.
    1% of positions receive a sudden dip (chemistry artifact).
    """
    scores = []
    for i in range(length):
        base_q = 37.0 - 15.0 * i / (length - 1)
        q = base_q + random.gauss(0, 1.5)
        if random.random() < 0.01:
            q -= random.uniform(8, 15)
        scores.append(max(2, min(40, round(q))))
    return scores


def apply_errors(seq: str, quals: list) -> str:
    """Substitute bases at random according to their Phred error probabilities."""
    bases = list(seq)
    for i, (b, q) in enumerate(zip(bases, quals)):
        if random.random() < 10 ** (-q / 10.0):
            bases[i] = random.choice([x for x in "ACGT" if x != b])
    return "".join(bases)


def phred_string(quals: list) -> str:
    return "".join(chr(q + 33) for q in quals)


# ── Haplotype construction ────────────────────────────────────────────────

def build_haplotypes(ref: str, variants: list):
    """
    Build two haplotype strings from the reference by applying planted variants.

    haplotype 1 — wild-type (reference copy, no variants)
    haplotype 2 — variant copy (carries all planted alleles)

    Variants are applied in descending position order so that a deletion at a
    high index does not shift the indices of lower-position variants.

    Returns (hap1_str, hap2_str, resolved_variants) where resolved_variants
    adds 'ref_allele' and 'alt_allele' fields determined from the reference.
    """
    hap1 = list(ref)
    hap2 = list(ref)
    resolved = []

    for v in sorted(variants, key=lambda x: -x["position"]):
        idx = v["position"] - 1  # 0-based index into the reference

        if v["type"] == "SNV":
            ref_base = ref[idx]
            alt = resolve_alt(ref_base, v["desired_alt"])
            if v["zygosity"] == "het":
                hap2[idx] = alt
            else:
                hap1[idx] = alt
                hap2[idx] = alt
            resolved.append({**v, "ref_allele": ref_base, "alt_allele": alt})

        elif v["type"] == "DEL":
            ref_base = ref[idx]
            if v["zygosity"] == "het":
                hap2.pop(idx)
            else:
                hap1.pop(idx)
                hap2.pop(idx)
            resolved.append({**v, "ref_allele": ref_base, "alt_allele": ""})

    resolved.sort(key=lambda x: x["position"])
    return "".join(hap1), "".join(hap2), resolved


# ── Fragment and read generation ──────────────────────────────────────────

def generate_reads(hap1: str, hap2: str) -> list:
    """
    Simulate NUM_FRAGMENTS paired-end sequencing fragments.

    For each fragment:
      1. Pick a haplotype at random (50/50), giving het variants ~50% VAF.
      2. Pick a random start position and fragment length (Gaussian).
      3. R1 = forward strand of first READ_LENGTH bases.
      4. R2 = reverse complement of last READ_LENGTH bases.
      5. Generate quality scores, then inject errors per Phred probability.
    """
    reads = []
    haplotypes = [hap1, hap2]

    for frag_idx in range(NUM_FRAGMENTS):
        hap = random.choice(haplotypes)

        frag_len = round(random.gauss(FRAGMENT_LENGTH_MEAN, FRAGMENT_LENGTH_STD))
        frag_len = max(READ_LENGTH * 2, min(frag_len, len(hap) - 1))
        max_start = len(hap) - frag_len
        if max_start <= 0:
            continue
        start = random.randint(0, max_start)
        fragment = hap[start : start + frag_len]

        r1_raw = fragment[:READ_LENGTH]
        r2_raw = reverse_complement(fragment[-READ_LENGTH:])

        r1_quals = quality_scores(READ_LENGTH)
        r2_quals = quality_scores(READ_LENGTH)

        r1 = apply_errors(r1_raw, r1_quals)
        r2 = apply_errors(r2_raw, r2_quals)

        reads.append((r1, r1_quals, r2, r2_quals, frag_idx + 1))

    return reads


def write_fastq_files(reads: list, r1_path: Path, r2_path: Path):
    """Write R1 and R2 FASTQ files with Illumina-style read headers."""
    with open(r1_path, "w") as f1, open(r2_path, "w") as f2:
        for r1, r1_q, r2, r2_q, idx in reads:
            header = f"@MockIllumina:1:MOCK001:1:1001:{idx}:0"
            f1.write(f"{header} 1:N:0:ATCG\n{r1}\n+\n{phred_string(r1_q)}\n")
            f2.write(f"{header} 2:N:0:ATCG\n{r2}\n+\n{phred_string(r2_q)}\n")
    n = len(reads)
    print(f"R1     → {r1_path}  ({n * 4} lines, {n} reads)")
    print(f"R2     → {r2_path}  ({n * 4} lines, {n} reads)")


def write_ground_truth(resolved: list, ref_len: int):
    ground_truth = {
        "description": (
            "Variants planted in mock FASTQ. "
            "Used by validate_pipeline management command (Step 6)."
        ),
        "chromosome": CHROM,
        "parameters": {
            "read_length":          READ_LENGTH,
            "fragment_length_mean": FRAGMENT_LENGTH_MEAN,
            "fragment_length_std":  FRAGMENT_LENGTH_STD,
            "num_fragments":        NUM_FRAGMENTS,
            "reference_length":     ref_len,
            "random_seed":          42,
        },
        "variants": [
            {
                "position":             v["position"],
                "type":                 v["type"],
                "ref_allele":           v["ref_allele"],
                "alt_allele":           v["alt_allele"],
                "zygosity":             v["zygosity"],
                "expected_genotype":    "0/1" if v["zygosity"] == "het" else "1/1",
                "expected_consequence": v["expected_consequence"],
                "note":                 v["note"],
            }
            for v in resolved
        ],
    }
    path = OUTPUT_DIR / "mock_planted_variants.json"
    with open(path, "w") as fh:
        json.dump(ground_truth, fh, indent=2)
    print(f"JSON   → {path}")


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Loading reference sequence...")
    record = next(SeqIO.parse(str(REFERENCE_PATH), "fasta"))
    ref = str(record.seq).upper()
    print(f"  {record.id}: {len(ref)} bp\n")

    print("Building haplotypes with planted variants:")
    hap1, hap2, resolved = build_haplotypes(ref, RAW_VARIANTS)
    for v in resolved:
        gt  = "0/1" if v["zygosity"] == "het" else "1/1"
        ref_d = v["ref_allele"] or "-"
        alt_d = v["alt_allele"] or "-"
        print(f"  pos {v['position']:4d}  {ref_d} → {alt_d:<3}  {gt}  {v['note']}")

    print(f"\nSimulating {NUM_FRAGMENTS} paired-end fragments "
          f"(read_length={READ_LENGTH}, mean_insert={FRAGMENT_LENGTH_MEAN})...")
    reads = generate_reads(hap1, hap2)
    total_bases = len(reads) * READ_LENGTH * 2
    print(f"  {len(reads)} fragments  |  {total_bases:,} bases  "
          f"|  ~{total_bases / len(ref):.0f}x coverage\n")

    r1_path = OUTPUT_DIR / "mock_sample_R1.fastq"
    r2_path = OUTPUT_DIR / "mock_sample_R2.fastq"
    write_fastq_files(reads, r1_path, r2_path)
    write_ground_truth(resolved, len(ref))

    print("\nDone.")
