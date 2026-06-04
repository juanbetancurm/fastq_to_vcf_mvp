#!/usr/bin/env python
"""
generate_mock_reference.py

Generate a synthetic 5,000 bp BTK gene fragment for use as the mock reference
genome. The region structure is designed so that Step 3's planted variants
land at predictable positions (exons, intron, coding sequence).

Outputs (written to backend/reference_data/):
  mock_btk_reference.fa    — FASTA sequence, chromosome name "chrX"
  mock_btk_exons.bed       — Exon coordinates in 0-based BED format
  mock_btk_gene_info.json  — Gene model used by the annotation step
"""
import json
import random
from pathlib import Path

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

random.seed(42)

BASE_DIR   = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "reference_data"

CHROM          = "chrX"
GENE_SYMBOL    = "BTK"
TRANSCRIPT_ID  = "ENST00000MOCK001"
TOTAL_LENGTH   = 5000

# ── Genomic region boundaries (0-based, half-open) ────────────────────────
#
# Planted variants from Step 3 and which region they must land in:
#   1-based pos 350  → index 349 → EXON1  = [100, 450)   coding, missense
#   1-based pos 800  → index 799 → INTRON1= [450, 1000)  intronic
#   1-based pos 1350 → index 1349→ EXON2  = [1000,1500)  coding, synonymous
#   1-based pos 2650 → index 2649→ EXON3  = [2200,2800)  coding, missense
#   1-based pos 3700 → index 3699→ EXON4  = [3500,3999)  coding, frameshift

UPSTREAM   = (0,    100)
EXON1      = (100,  450)
INTRON1    = (450,  1000)
EXON2      = (1000, 1500)
INTRON2    = (1500, 2200)
EXON3      = (2200, 2800)
INTRON3    = (2800, 3500)
EXON4      = (3500, 3999)
DOWNSTREAM = (3999, 5000)

EXONS   = [EXON1, EXON2, EXON3, EXON4]
INTRONS = [INTRON1, INTRON2, INTRON3]

# CDS boundaries (0-based):
#   ATG start codon at index 300 (1-based position 301, inside EXON1)
#   stop codon TAA   at index 3897-3899 (inside EXON4), CDS ends at 3900
CDS_START = 300
CDS_END   = 3900  # exclusive; TAA occupies [3897, 3900)

# CDS per-exon lengths: 150 + 500 + 600 + 400 = 1650 bp = 550 codons ✓


# ── Sequence generation ───────────────────────────────────────────────────

def random_nuc(length: int, gc: float) -> str:
    """Return a random nucleotide string of the given length and GC fraction."""
    gc_count = round(length * gc)
    at_count = length - gc_count
    # Build pool with exact counts, then shuffle
    pool = (["G", "C"] * ((gc_count + 1) // 2))[:gc_count] + \
           (["A", "T"] * ((at_count + 1) // 2))[:at_count]
    random.shuffle(pool)
    return "".join(pool)


def build_sequence() -> str:
    seq = list("N" * TOTAL_LENGTH)

    # Flanking regions: ~42% GC (low complexity)
    for start, end in [UPSTREAM, DOWNSTREAM]:
        seq[start:end] = list(random_nuc(end - start, gc=0.42))

    # Exons: ~50% GC (typical coding sequence)
    for start, end in EXONS:
        seq[start:end] = list(random_nuc(end - start, gc=0.50))

    # Introns: ~40% GC (AT-rich intronic sequence)
    for start, end in INTRONS:
        seq[start:end] = list(random_nuc(end - start, gc=0.40))

    # ATG start codon at CDS_START
    seq[CDS_START:CDS_START + 3] = list("ATG")

    # TAA stop codon immediately before CDS_END
    seq[CDS_END - 3:CDS_END] = list("TAA")

    # GT–AG splice signals at every intron boundary (GT-AG rule)
    for i_start, i_end in INTRONS:
        seq[i_start:i_start + 2] = list("GT")   # donor site
        seq[i_end - 2:i_end]     = list("AG")   # acceptor site

    return "".join(seq)


# ── CDS assembly and validation ───────────────────────────────────────────

def assemble_cds(ref: str) -> str:
    """Concatenate the CDS-overlapping portion of each exon."""
    pieces = []
    for ex_start, ex_end in EXONS:
        s = max(ex_start, CDS_START)
        e = min(ex_end,   CDS_END)
        if s < e:
            pieces.append(ref[s:e])
    return "".join(pieces)


def validate_cds(cds: str):
    assert cds[:3] == "ATG", \
        f"CDS does not begin with ATG — got '{cds[:3]}'"
    assert cds[-3:] in {"TAA", "TAG", "TGA"}, \
        f"CDS does not end with a stop codon — got '{cds[-3:]}'"
    assert len(cds) % 3 == 0, \
        f"CDS length {len(cds)} is not divisible by 3"


# ── File writers ──────────────────────────────────────────────────────────

def write_fasta(ref: str):
    record = SeqRecord(
        Seq(ref),
        id=CHROM,
        description=f"Mock {GENE_SYMBOL} gene fragment | {TOTAL_LENGTH} bp",
    )
    path = OUTPUT_DIR / "mock_btk_reference.fa"
    with open(path, "w") as fh:
        SeqIO.write(record, fh, "fasta")
    print(f"FASTA  → {path}  ({TOTAL_LENGTH} bp)")


def write_bed():
    """
    BED format: chromosome, 0-based start, 0-based exclusive end, name.
    One row per exon.
    """
    path = OUTPUT_DIR / "mock_btk_exons.bed"
    with open(path, "w") as fh:
        for i, (start, end) in enumerate(EXONS, start=1):
            fh.write(f"{CHROM}\t{start}\t{end}\texon{i}\t0\t+\n")
    print(f"BED    → {path}  ({len(EXONS)} exons)")


def write_gene_info(ref: str, cds: str):
    """
    JSON gene model consumed by the annotation step (Step 5).
    Includes per-exon CDS offsets so the annotator can translate genomic
    coordinates into codon positions.
    """
    exon_records = []
    cds_offset = 0
    for i, (ex_start, ex_end) in enumerate(EXONS, start=1):
        cds_s = max(ex_start, CDS_START)
        cds_e = min(ex_end,   CDS_END)
        cds_len = max(0, cds_e - cds_s)
        exon_records.append({
            "exon_number":   i,
            "genomic_start": ex_start,   # 0-based
            "genomic_end":   ex_end,     # 0-based exclusive
            "cds_start":     cds_s,      # 0-based start of CDS within this exon
            "cds_end":       cds_e,      # 0-based exclusive end of CDS
            "cds_offset":    cds_offset, # total CDS bases before this exon
            "phase":         cds_offset % 3,  # 0,1,2 — bases of codon carried over
        })
        cds_offset += cds_len

    protein_length = len(cds) // 3 - 1  # subtract the stop codon

    gene_info = {
        "gene_symbol":    GENE_SYMBOL,
        "transcript_id":  TRANSCRIPT_ID,
        "chromosome":     CHROM,
        "strand":         "+",
        "total_length":   TOTAL_LENGTH,
        "cds_start":      CDS_START,
        "cds_end":        CDS_END,
        "cds_length":     len(cds),
        "protein_length": protein_length,
        "exons":          exon_records,
        "introns": [
            {"genomic_start": s, "genomic_end": e}
            for s, e in INTRONS
        ],
        "is_iei_gene": True,
    }

    path = OUTPUT_DIR / "mock_btk_gene_info.json"
    with open(path, "w") as fh:
        json.dump(gene_info, fh, indent=2)
    print(f"JSON   → {path}")

    print(f"\n  Gene:            {GENE_SYMBOL}  ({TRANSCRIPT_ID})")
    print(f"  Total length:    {TOTAL_LENGTH} bp")
    print(f"  CDS:             {CDS_START}–{CDS_END}  ({len(cds)} bp)")
    print(f"  Protein:         {protein_length} aa")
    print(f"  CDS start/end:   {cds[:6]}...{cds[-6:]}")
    print(f"  Exon CDS lengths: {[ex['cds_end']-ex['cds_start'] for ex in exon_records]}")


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Generating mock BTK reference sequence...\n")
    ref = build_sequence()
    cds = assemble_cds(ref)
    validate_cds(cds)
    write_fasta(ref)
    write_bed()
    write_gene_info(ref, cds)
    print("\nDone.")
