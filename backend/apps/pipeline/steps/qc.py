"""
QC step: count reads, measure quality score distributions, compute GC content.
Returns a metrics dict stored in SequencingRun.qc_metrics.
"""


def run(fastq_r1: str, fastq_r2: str = None) -> dict:
    metrics = _analyze_fastq(fastq_r1, label="R1")
    if fastq_r2:
        r2 = _analyze_fastq(fastq_r2, label="R2")
        metrics["r2"] = r2["r1"]
    return metrics


def _analyze_fastq(path: str, label: str) -> dict:
    total_reads = 0
    total_bases = 0
    quality_sum = 0
    gc_count = 0
    base_count = 0
    per_position_quality = {}

    with open(path) as fh:
        while True:
            header = fh.readline().strip()
            if not header:
                break
            seq  = fh.readline().strip()
            _    = fh.readline()          # '+'
            qual = fh.readline().strip()

            total_reads += 1
            total_bases += len(seq)

            gc_count  += seq.count("G") + seq.count("C")
            base_count += len(seq)

            for i, ch in enumerate(qual):
                q = ord(ch) - 33
                quality_sum += q
                per_position_quality.setdefault(i, []).append(q)

    mean_quality = quality_sum / total_bases if total_bases else 0
    gc_fraction  = gc_count / base_count if base_count else 0

    # Per-position mean quality (first 10 and last 10 positions)
    pos_means = {
        pos: round(sum(qs) / len(qs), 1)
        for pos, qs in per_position_quality.items()
    }

    return {
        "r1": {
            "total_reads":   total_reads,
            "total_bases":   total_bases,
            "mean_quality":  round(mean_quality, 2),
            "gc_fraction":   round(gc_fraction, 3),
            "pos_quality": {
                str(k): v for k, v in pos_means.items()
                if k < 10 or k >= (max(pos_means) - 9)
            },
        }
    }
