"""
Alignment step: map FASTQ reads to the reference genome.

Pure-Python fallback: slide each read along the reference, find the position
with the fewest mismatches, write a SAM record.

SAM mandatory fields (tab-separated):
  QNAME FLAG RNAME POS MAPQ CIGAR RNEXT PNEXT TLEN SEQ QUAL
"""
from pathlib import Path
from Bio import SeqIO

_COMP = str.maketrans("ACGTNacgtn", "TGCANtgcan")

def _reverse_complement(seq: str) -> str:
    return seq.translate(_COMP)[::-1]


def run(fastq_r1: str, fastq_r2: str, reference_fa: str, out_sam: str) -> dict:
    ref_record = next(SeqIO.parse(reference_fa, "fasta"))
    ref_seq    = str(ref_record.seq).upper()
    ref_name   = ref_record.id
    ref_len    = len(ref_seq)

    reads_r1 = _parse_fastq(fastq_r1)
    reads_r2 = _parse_fastq(fastq_r2) if fastq_r2 else []

    total_reads   = len(reads_r1) + len(reads_r2)
    aligned_reads = 0

    with open(out_sam, "w") as sam:
        # SAM header
        sam.write(f"@HD\tVN:1.6\tSO:unsorted\n")
        sam.write(f"@SQ\tSN:{ref_name}\tLN:{ref_len}\n")
        sam.write(f"@RG\tID:mock\tSM:mock_sample\tPL:ILLUMINA\n")

        for read in reads_r1:
            flag, pos, mapq, cigar = _align_read(read["seq"], ref_seq)
            if pos >= 0:
                aligned_reads += 1
            else:
                flag = 4   # SAM unmapped flag
                pos  = 0
            sam.write(_sam_line(read, flag, ref_name, pos, mapq, cigar))

        for read in reads_r2:
            # R2 was sequenced from the reverse strand. RC it to align against
            # the forward reference, then write the RC sequence in the SAM file
            # (SAM convention: reverse-strand reads store the forward-strand seq).
            rc_seq = _reverse_complement(read["seq"])
            flag, pos, mapq, cigar = _align_read(rc_seq, ref_seq)
            if pos >= 0:
                flag |= 16   # SAM flag: reverse strand
                aligned_reads += 1
            else:
                flag = 20    # unmapped + reverse
                pos  = 0
            rc_read = {**read, "seq": rc_seq, "qual": read["qual"][::-1]}
            sam.write(_sam_line(rc_read, flag, ref_name, pos, mapq, cigar))

    return {
        "total_reads":   total_reads,
        "aligned_reads": aligned_reads,
        "alignment_rate": round(aligned_reads / total_reads * 100, 1) if total_reads else 0,
        "sam_path": out_sam,
    }


def _parse_fastq(path: str) -> list:
    reads = []
    with open(path) as fh:
        while True:
            header = fh.readline().strip()
            if not header:
                break
            seq  = fh.readline().strip()
            _    = fh.readline()
            qual = fh.readline().strip()
            reads.append({
                "name": header[1:].split()[0],
                "seq":  seq,
                "qual": qual,
            })
    return reads


def _align_read(read_seq: str, ref_seq: str) -> tuple:
    """
    Slide the read along the reference and find the position with fewest
    mismatches. Returns (flag, pos_0based, mapq, cigar).
    pos=-1 means unmapped.
    """
    read_len = len(read_seq)
    ref_len  = len(ref_seq)

    if read_len > ref_len:
        return 4, -1, 0, "*"

    best_pos      = -1
    best_mismatches = read_len + 1
    second_best   = read_len + 1

    for start in range(ref_len - read_len + 1):
        ref_window = ref_seq[start:start + read_len]
        mismatches = sum(a != b for a, b in zip(read_seq, ref_window))
        if mismatches < best_mismatches:
            second_best   = best_mismatches
            best_mismatches = mismatches
            best_pos      = start
        elif mismatches < second_best:
            second_best = mismatches

    # Mapping quality: higher when best position is clearly better than second best
    if best_mismatches > read_len * 0.2:   # >20% mismatch rate → don't call it mapped
        return 4, -1, 0, "*"

    gap = second_best - best_mismatches
    mapq = min(60, max(0, gap * 5 + (10 - best_mismatches)))

    cigar = f"{read_len}M"   # simplified: treat all positions as match/mismatch
    flag  = 0                # forward strand
    pos_1based = best_pos + 1   # SAM is 1-based

    return flag, pos_1based, mapq, cigar


def _sam_line(read: dict, flag: int, rname: str, pos: int,
              mapq: int, cigar: str) -> str:
    return (
        f"{read['name']}\t{flag}\t{rname}\t{pos}\t{mapq}\t{cigar}"
        f"\t*\t0\t0\t{read['seq']}\t{read['qual']}\tRG:Z:mock\n"
    )
