from django.contrib import admin
from .models import SequencingRun


@admin.register(SequencingRun)
class SequencingRunAdmin(admin.ModelAdmin):
    list_display = ["pk", "sample", "platform", "sequencing_type", "reference_genome", "status", "progress_percent", "created_at"]
    list_filter = ["status", "platform", "sequencing_type", "reference_genome"]
    search_fields = ["sample__patient__external_id", "celery_task_id"]
    readonly_fields = ["created_at", "updated_at", "started_at", "completed_at"]
