import time
from celery import shared_task

# Pipeline stage sequence: (status_slug, display_label, progress_percent)
PIPELINE_STAGES = [
    ("qc",               "Quality Control",       10),
    ("aligning",         "Aligning Reads",        30),
    ("sorting",          "Sorting BAM",           50),
    ("calling_variants", "Calling Variants",      70),
    ("parsing_vcf",      "Parsing VCF",           85),
    ("annotating",       "Annotating Variants",   95),
    ("completed",        "Completed",            100),
]


@shared_task(bind=True, name="pipeline.test_task")
def test_pipeline_task(self):
    """
    Walks through the pipeline state machine with artificial delays.
    Used by test_celery management command to verify Celery + Redis works
    before real pipeline code is added in Step 5.
    """
    for status, label, progress in PIPELINE_STAGES:
        self.update_state(
            state="PROGRESS",
            meta={"status": status, "label": label, "progress": progress},
        )
        time.sleep(0.5)

    return {"status": "completed", "progress": 100}


@shared_task(bind=True, name="pipeline.run_pipeline")
def run_pipeline_task(self, run_id: int):
    """
    Real pipeline task — implemented in Step 5.
    Placeholder so imports don't fail before Step 5.
    """
    raise NotImplementedError("Pipeline task implemented in Step 5.")
