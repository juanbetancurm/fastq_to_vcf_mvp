from django.db import models


class Patient(models.Model):
    SEX_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
        ("U", "Unknown"),
    ]

    external_id = models.CharField(max_length=64, unique=True, db_index=True)
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)
    date_of_birth = models.DateField(null=True, blank=True)
    clinical_info = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["external_id"]

    def __str__(self):
        return f"{self.external_id} ({self.get_sex_display()})"


class Sample(models.Model):
    TISSUE_CHOICES = [
        ("peripheral_blood", "Peripheral Blood"),
        ("bone_marrow", "Bone Marrow"),
        ("saliva", "Saliva"),
        ("skin_biopsy", "Skin Biopsy"),
        ("other", "Other"),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="samples")
    tissue_type = models.CharField(max_length=32, choices=TISSUE_CHOICES)
    collection_date = models.DateField()
    sample_barcode = models.CharField(max_length=64, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-collection_date"]

    def __str__(self):
        return f"{self.patient.external_id} — {self.tissue_type} ({self.collection_date})"
