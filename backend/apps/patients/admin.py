from django.contrib import admin
from .models import Patient, Sample


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ["external_id", "sex", "date_of_birth", "created_at"]
    list_filter = ["sex"]
    search_fields = ["external_id", "clinical_info"]


@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = ["patient", "tissue_type", "collection_date", "sample_barcode"]
    list_filter = ["tissue_type"]
    search_fields = ["patient__external_id", "sample_barcode"]
