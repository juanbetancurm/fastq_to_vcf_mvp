import time
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Dispatch a test Celery task and watch it progress through pipeline states."

    def handle(self, *args, **options):
        from celery.result import AsyncResult
        from apps.pipeline.tasks import test_pipeline_task

        self.stdout.write("Dispatching test task to Celery worker...")
        result = test_pipeline_task.delay()
        self.stdout.write(f"Task ID: {result.id}\n")

        seen_states = set()

        while not result.ready():
            info = result.info
            if isinstance(info, dict):
                status   = info.get("status", "?")
                label    = info.get("label", "?")
                progress = info.get("progress", 0)
                key = status
                if key not in seen_states:
                    self.stdout.write(f"  [{progress:3d}%] {label}")
                    seen_states.add(key)
            time.sleep(0.2)

        if result.successful():
            final = result.get()
            self.stdout.write(
                self.style.SUCCESS(f"\n  [100%] Completed")
            )
            self.stdout.write(self.style.SUCCESS(
                "\nCelery test passed — Django, Redis, and the worker are all connected."
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"\nTask failed: {result.result}"
            ))
