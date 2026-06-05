"""
Sorting step: sort SAM alignments by chromosome then position.

Real pipelines convert SAM→BAM (binary compressed) and build a .bai index.
Our fallback keeps SAM format (no pysam required) but sorts correctly so the
variant caller can process positions in order.
"""


def run(in_sam: str, out_sam: str) -> dict:
    headers = []
    alignments = []

    with open(in_sam) as fh:
        for line in fh:
            if line.startswith("@"):
                headers.append(line)
            else:
                alignments.append(line)

    def sort_key(line: str):
        fields = line.split("\t")
        chrom = fields[2] if len(fields) > 2 else ""
        try:
            pos = int(fields[3]) if len(fields) > 3 else 0
        except ValueError:
            pos = 0
        return (chrom, pos)

    alignments.sort(key=sort_key)

    with open(out_sam, "w") as fh:
        for h in headers:
            fh.write(h)
        for a in alignments:
            fh.write(a)

    return {
        "sorted_sam_path": out_sam,
        "total_alignments": len(alignments),
    }
