from django.contrib import admin
from .models import Variant, VariantAnnotation


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ["chromosome", "position", "ref_allele", "alt_allele", "genotype", "read_depth", "run"]
    list_filter = ["chromosome", "genotype"]
    search_fields = ["chromosome", "variant_id"]


@admin.register(VariantAnnotation)
class VariantAnnotationAdmin(admin.ModelAdmin):
    list_display = ["gene_symbol", "consequence", "impact", "is_iei_gene", "amino_acid_change", "variant"]
    list_filter = ["impact", "is_iei_gene"]
    search_fields = ["gene_symbol", "transcript_id", "clinvar_id"]
