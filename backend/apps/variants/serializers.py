from rest_framework import serializers
from .models import Variant, VariantAnnotation


class VariantAnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VariantAnnotation
        exclude = ["variant"]


class VariantSerializer(serializers.ModelSerializer):
    annotations = VariantAnnotationSerializer(many=True, read_only=True)

    class Meta:
        model = Variant
        fields = [
            "id", "run", "chromosome", "position",
            "variant_id", "ref_allele", "alt_allele",
            "quality", "filter_status", "genotype",
            "read_depth", "allele_frequency", "genotype_quality",
            "raw_info", "annotations",
        ]


class VariantListSerializer(serializers.ModelSerializer):
    """Flatter serializer for list views — skips raw_info to reduce payload."""
    gene_symbol  = serializers.SerializerMethodField()
    consequence  = serializers.SerializerMethodField()
    impact       = serializers.SerializerMethodField()
    is_iei_gene  = serializers.SerializerMethodField()

    class Meta:
        model = Variant
        fields = [
            "id", "run", "chromosome", "position",
            "ref_allele", "alt_allele", "genotype",
            "read_depth", "allele_frequency",
            "gene_symbol", "consequence", "impact", "is_iei_gene",
        ]

    def _first_ann(self, obj):
        anns = obj.annotations.all()
        return anns[0] if anns else None

    def get_gene_symbol(self, obj):
        a = self._first_ann(obj)
        return a.gene_symbol if a else None

    def get_consequence(self, obj):
        a = self._first_ann(obj)
        return a.consequence if a else None

    def get_impact(self, obj):
        a = self._first_ann(obj)
        return a.impact if a else None

    def get_is_iei_gene(self, obj):
        a = self._first_ann(obj)
        return a.is_iei_gene if a else None
