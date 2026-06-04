from django.db import models
from apps.sequencing.models import SequencingRun


class Variant(models.Model):
    run = models.ForeignKey(SequencingRun, on_delete=models.CASCADE, related_name="variants")
    chromosome = models.CharField(max_length=16, db_index=True)
    position = models.IntegerField()
    variant_id = models.CharField(max_length=32, blank=True)  # dbSNP rsID e.g. "rs28933281"
    ref_allele = models.CharField(max_length=500)
    alt_allele = models.CharField(max_length=500)
    quality = models.FloatField(null=True, blank=True)
    filter_status = models.CharField(max_length=64, default=".")
    genotype = models.CharField(max_length=16)  # e.g. "0/1", "1/1"
    read_depth = models.IntegerField(null=True, blank=True)
    allele_frequency = models.FloatField(null=True, blank=True)
    genotype_quality = models.IntegerField(null=True, blank=True)
    raw_info = models.JSONField(default=dict)

    class Meta:
        ordering = ["chromosome", "position"]
        indexes = [
            models.Index(fields=["chromosome", "position"]),
        ]
        unique_together = [("run", "chromosome", "position", "ref_allele", "alt_allele")]

    def __str__(self):
        return f"{self.chromosome}:{self.position} {self.ref_allele}>{self.alt_allele} ({self.genotype})"


class VariantAnnotation(models.Model):
    IMPACT_CHOICES = [
        ("HIGH", "High"),
        ("MODERATE", "Moderate"),
        ("LOW", "Low"),
        ("MODIFIER", "Modifier"),
    ]

    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name="annotations")
    gene_symbol = models.CharField(max_length=32, db_index=True)
    transcript_id = models.CharField(max_length=64, blank=True)
    consequence = models.CharField(max_length=64)   # SO term e.g. "missense_variant"
    impact = models.CharField(max_length=16, choices=IMPACT_CHOICES, db_index=True)
    codon_change = models.CharField(max_length=32, blank=True)       # e.g. "Agt/Tgt"
    amino_acid_change = models.CharField(max_length=32, blank=True)  # e.g. "S/C"
    protein_position = models.IntegerField(null=True, blank=True)
    exon_number = models.CharField(max_length=16, blank=True)
    is_iei_gene = models.BooleanField(default=False, db_index=True)
    clinvar_significance = models.CharField(max_length=64, blank=True)
    clinvar_id = models.CharField(max_length=32, blank=True)
    sift_prediction = models.CharField(max_length=32, blank=True)
    sift_score = models.FloatField(null=True, blank=True)
    polyphen_prediction = models.CharField(max_length=32, blank=True)
    polyphen_score = models.FloatField(null=True, blank=True)
    extra_data = models.JSONField(default=dict)

    class Meta:
        ordering = ["impact", "gene_symbol"]

    def __str__(self):
        return f"{self.gene_symbol} {self.consequence} ({self.impact})"
