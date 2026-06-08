const STYLES = {
  pending:          'bg-gray-100 text-gray-600',
  qc:               'bg-blue-100 text-blue-700',
  aligning:         'bg-blue-100 text-blue-700',
  sorting:          'bg-blue-100 text-blue-700',
  calling_variants: 'bg-purple-100 text-purple-700',
  parsing_vcf:      'bg-purple-100 text-purple-700',
  annotating:       'bg-indigo-100 text-indigo-700',
  completed:        'bg-green-100 text-green-700',
  failed:           'bg-red-100 text-red-700',
}

export default function StatusBadge({ status }) {
  const cls = STYLES[status] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {status?.replace(/_/g, ' ') ?? '—'}
    </span>
  )
}
