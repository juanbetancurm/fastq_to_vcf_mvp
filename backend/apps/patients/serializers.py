from rest_framework import serializers
from .models import Patient, Sample


class SampleSerializer(serializers.ModelSerializer):
    patient_external_id = serializers.CharField(
        source="patient.external_id", read_only=True
    )

    class Meta:
        model = Sample
        fields = [
            "id", "patient", "patient_external_id", "tissue_type",
            "collection_date", "sample_barcode", "notes", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PatientSerializer(serializers.ModelSerializer):
    sample_count = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            "id", "external_id", "sex", "date_of_birth", "clinical_info",
            "created_at", "updated_at", "sample_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_sample_count(self, obj):
        return obj.samples.count()
