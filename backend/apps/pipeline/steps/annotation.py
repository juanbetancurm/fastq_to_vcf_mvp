"""
Annotation step: for each Variant, determine which gene region it falls in,
what codon is affected, and what the protein consequence is.

Uses mock_btk_gene_info.json from Step 2 as the gene model.
Implements the full standard genetic code (64 codons).
"""
import json
from pathlib import Path


# ── Standard genetic code ─────────────────────────────────────────────────
CODON_TABLE = {
    "TTT": "Phe", "TTC": "Phe", "TTA": "Leu", "TTG": "Leu",
    "CTT": "Leu", "CTC": "Leu", "CTA": "Leu", "CTG": "Leu",
    "ATT": "Ile", "ATC": "Ile", "ATA": "Ile", "ATG": "Met",
    "GTT": "Val", "GTC": "Val", "GTA": "Val", "GTG": "Val",
    "TCT": "Ser", "TCC": "Ser", "TCA": "Ser", "TCG": "Ser",
    "CCT": "Pro", "CCC": "Pro", "CCA": "Pro", "CCG": "Pro",
    "ACT": "Thr", "ACC": "Thr", "ACA": "Thr", "ACG": "Thr",
    "GCT": "Ala", "GCC": "Ala", "GCA": "Ala", "GCG": "Ala",
    "TAT": "Tyr", "TAC": "Tyr", "TAA": "*",   "TAG": "*",
    "CAT": "His", "CAC": "His", "CAA": "Gln", "CAG": "Gln",
    "AAT": "Asn", "AAC": "Asn", "AAA": "Lys", "AAG": "Lys",
    "GAT": "Asp", "GAC": "Asp", "GAA": "Glu", "GAG": "Glu",
    "TGT": "Cys", "TGC": "Cys", "TGA": "*",   "TGG": "Trp",
    "CGT": "Arg", "CGC": "Arg", "CGA": "Arg", "CGG": "Arg",
    "AGT": "Ser", "AGC": "Ser", "AGA": "Arg", "AGG": "Arg",
    "GGT": "Gly", "GGC": "Gly", "GGA": "Gly", "GGG": "Gly",
}


def run(run_id: int, gene_info_path: str, reference_fa_path: str) -> int:
    """Annotate all Variant rows for the given run. Returns annotation count."""
    from apps.variants.models import Variant, VariantAnnotation
    from Bio import SeqIO

    with open(gene_info_path) as fh:
        gene_info = json.load(fh)

    ref_record = next(SeqIO.parse(reference_fa_path, "fasta"))
    ref_seq    = str(ref_record.seq).upper()

    # Pre-build the full CDS string for codon lookups
    cds_seq = _assemble_cds(ref_seq, gene_info)

    variants = Variant.objects.filter(run_id=run_id)
    annotation_count = 0

    for variant in variants:
        VariantAnnotation.objects.filter(variant=variant).delete()
        annotations = _annotate_variant(variant, gene_info, ref_seq, cds_seq)
        for ann_data in annotations:
            VariantAnnotation.objects.create(variant=variant, **ann_data)
            annotation_count += 1

    return annotation_count


# ── Gene region lookup ────────────────────────────────────────────────────

def _find_region(pos_1based: int, gene_info: dict) -> tuple:
    """
    Return (region_type, region_index) for a 1-based position.
    region_type: 'exon', 'intron', or 'intergenic'
    region_index: 0-based index into gene_info['exons'] or ['introns']
    """
    idx = pos_1based - 1  # 0-based
    for i, exon in enumerate(gene_info["exons"]):
        if exon["genomic_start"] <= idx < exon["genomic_end"]:
            return "exon", i
    for i, intron in enumerate(gene_info["introns"]):
        if intron["genomic_start"] <= idx < intron["genomic_end"]:
            return "intron", i
    return "intergenic", -1


def _is_in_cds(pos_1based: int, gene_info: dict) -> bool:
    idx = pos_1based - 1
    return gene_info["cds_start"] <= idx < gene_info["cds_end"]


def _cds_offset_of(pos_1based: int, gene_info: dict) -> int:
    """
    Return the 0-based offset within the CDS for a position that is in a
    coding exon. Returns -1 if not in CDS.
    """
    idx = pos_1based - 1
    for exon in gene_info["exons"]:
        if exon["cds_start"] <= idx < exon["cds_end"]:
            return exon["cds_offset"] + (idx - exon["cds_start"])
    return -1


def _assemble_cds(ref_seq: str, gene_info: dict) -> str:
    pieces = []
    for exon in gene_info["exons"]:
        pieces.append(ref_seq[exon["cds_start"]:exon["cds_end"]])
    return "".join(pieces)


# ── Consequence classification ────────────────────────────────────────────

def _classify_snv(ref_base: str, alt_base: str, cds_offset: int,
                  cds_seq: str) -> dict:
    """
    Determine consequence for a SNV at the given CDS offset.
    Returns a dict with consequence, impact, codon_change, amino_acid_change,
    protein_position.
    """
    codon_index    = cds_offset // 3    # 0-based codon number
    codon_pos      = cds_offset % 3     # 0, 1, or 2 within the codon
    codon_start    = codon_index * 3

    if codon_start + 3 > len(cds_seq):
        return {
            "consequence": "incomplete_terminal_codon_variant",
            "impact": "LOW",
            "codon_change": "",
            "amino_acid_change": "",
            "protein_position": codon_index + 1,
        }

    ref_codon = cds_seq[codon_start:codon_start + 3]
    alt_codon = ref_codon[:codon_pos] + alt_base + ref_codon[codon_pos + 1:]

    ref_aa = CODON_TABLE.get(ref_codon, "?")
    alt_aa = CODON_TABLE.get(alt_codon, "?")

    codon_change     = f"{ref_codon}/{alt_codon}"
    amino_acid_change = f"{ref_aa}/{alt_aa}"
    protein_pos       = codon_index + 1   # 1-based

    if alt_aa == "*" and ref_aa != "*":
        consequence = "stop_gained"
        impact      = "HIGH"
    elif ref_aa == "*" and alt_aa != "*":
        consequence = "stop_lost"
        impact      = "HIGH"
    elif ref_aa == alt_aa:
        consequence = "synonymous_variant"
        impact      = "LOW"
    else:
        consequence = "missense_variant"
        impact      = "MODERATE"

    return {
        "consequence":      consequence,
        "impact":           impact,
        "codon_change":     codon_change,
        "amino_acid_change": amino_acid_change,
        "protein_position": protein_pos,
    }


# ── Main annotation logic ─────────────────────────────────────────────────

def _annotate_variant(variant, gene_info: dict, ref_seq: str,
                      cds_seq: str) -> list:
    """Return a list of annotation dicts (one per transcript — just one here)."""
    region_type, region_idx = _find_region(variant.position, gene_info)
    in_cds = _is_in_cds(variant.position, gene_info)

    base = {
        "gene_symbol":     gene_info["gene_symbol"],
        "transcript_id":   gene_info["transcript_id"],
        "is_iei_gene":     gene_info.get("is_iei_gene", False),
        "codon_change":     "",
        "amino_acid_change": "",
        "protein_position": None,
        "exon_number":     "",
        "clinvar_significance": "",
        "clinvar_id":      "",
        "sift_prediction": "",
        "sift_score":      None,
        "polyphen_prediction": "",
        "polyphen_score":  None,
        "extra_data":      {},
    }

    if region_type == "intron":
        # Check for splice site disruption (within 2 bp of exon boundary)
        intron = gene_info["introns"][region_idx]
        dist_to_donor    = abs(variant.position - 1 - intron["genomic_start"])
        dist_to_acceptor = abs(variant.position - 1 - (intron["genomic_end"] - 2))

        if dist_to_donor <= 2 or dist_to_acceptor <= 2:
            base["consequence"] = "splice_region_variant"
            base["impact"]      = "HIGH"
        else:
            base["consequence"] = "intron_variant"
            base["impact"]      = "MODIFIER"
        return [base]

    if region_type == "exon":
        exon = gene_info["exons"][region_idx]
        base["exon_number"] = str(exon["exon_number"])

        if not in_cds:
            # UTR region
            base["consequence"] = "UTR_variant"
            base["impact"]      = "MODIFIER"
            return [base]

        cds_off = _cds_offset_of(variant.position, gene_info)

        # Deletion: frameshift (simplified — treat all deletions as frameshift)
        if variant.alt_allele == "" or len(variant.alt_allele) < len(variant.ref_allele):
            base["consequence"] = "frameshift_variant"
            base["impact"]      = "HIGH"
            base["protein_position"] = cds_off // 3 + 1
            return [base]

        # Insertion: frameshift if not divisible by 3
        if len(variant.alt_allele) > len(variant.ref_allele):
            ins_len = len(variant.alt_allele) - len(variant.ref_allele)
            if ins_len % 3 != 0:
                base["consequence"] = "frameshift_variant"
                base["impact"]      = "HIGH"
            else:
                base["consequence"] = "inframe_insertion"
                base["impact"]      = "MODERATE"
            base["protein_position"] = cds_off // 3 + 1
            return [base]

        # SNV in coding region
        snv_ann = _classify_snv(
            variant.ref_allele, variant.alt_allele, cds_off, cds_seq
        )
        base.update(snv_ann)
        return [base]

    # Intergenic
    base["consequence"] = "intergenic_variant"
    base["impact"]      = "MODIFIER"
    return [base]
