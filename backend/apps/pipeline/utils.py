"""
Shared utilities for the pipeline steps.
"""
from pathlib import Path
from django.conf import settings


def work_dir(run_id: int) -> Path:
    """Return (and create) a working directory for a specific run."""
    d = Path(settings.PIPELINE_WORK_DIR) / f"run_{run_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def reference_path() -> Path:
    return Path(settings.REFERENCE_DATA_DIR) / "mock_btk_reference.fa"


def exons_bed_path() -> Path:
    return Path(settings.REFERENCE_DATA_DIR) / "mock_btk_exons.bed"


def gene_info_path() -> Path:
    return Path(settings.REFERENCE_DATA_DIR) / "mock_btk_gene_info.json"
