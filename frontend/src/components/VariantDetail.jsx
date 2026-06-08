const IMPACT_CLS = {
  HIGH:     'text-red-700 bg-red-50',
  MODERATE: 'text-orange-700 bg-orange-50',
  LOW:      'text-yellow-700 bg-yellow-50',
  MODIFIER: 'text-gray-600 bg-gray-100',
}

function Row({ label, value }) {
  return (
    <div className="flex gap-2 text-sm">
      <dt className="text-gray-400 w-32 flex-shrink-0">{label}</dt>
      <dd className="text-gray-900">{value ?? '—'}</dd>
    </div>
  )
}

export default function VariantDetail({ variant }) {
  const ann = variant.annotations?.[0]

  return (
    <div className="px-6 py-5 bg-gray-50 border-t border-gray-100">
      <div className="grid grid-cols-2 gap-8">
        <div>
          <p className="text-xs font-semibold text-gray-400 uppercase mb-3">Variant</p>
          <dl className="space-y-1.5">
            <Row label="Chromosome"    value={variant.chromosome} />
            <Row label="Position"      value={variant.position} />
            <Row label="REF → ALT"     value={`${variant.ref_allele} → ${variant.alt_allele || '(del)'}`} />
            <Row label="Genotype"      value={variant.genotype} />
            <Row label="Read depth"    value={variant.read_depth} />
            <Row label="VAF"           value={variant.allele_frequency != null
              ? `${(variant.allele_frequency * 100).toFixed(1)}%` : null} />
            <Row label="Quality"       value={variant.quality} />
            <Row label="Filter"        value={variant.filter_status} />
          </dl>
        </div>

        {ann ? (
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase mb-3">Annotation</p>
            <dl className="space-y-1.5">
              <Row label="Gene"         value={ann.gene_symbol} />
              <Row label="Transcript"   value={ann.transcript_id} />
              <Row label="Exon"         value={ann.exon_number || null} />
              <Row label="Consequence"  value={ann.consequence} />
              <Row label="Impact"       value={
                <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${IMPACT_CLS[ann.impact] ?? ''}`}>
                  {ann.impact}
                </span>
              } />
              {ann.codon_change      && <Row label="Codon change"  value={ann.codon_change} />}
              {ann.amino_acid_change && <Row label="AA change"     value={ann.amino_acid_change} />}
              {ann.protein_position  && <Row label="Protein pos"   value={`p.${ann.protein_position}`} />}
              <Row label="IEI gene"     value={ann.is_iei_gene ? 'Yes' : 'No'} />
            </dl>
          </div>
        ) : (
          <div className="text-sm text-gray-400 pt-6">No annotation data.</div>
        )}
      </div>
    </div>
  )
}
