import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

function Metric({ label, value }) {
  return (
    <div className="text-center">
      <p className="text-lg font-semibold text-gray-900">{value}</p>
      <p className="text-xs text-gray-500 mt-0.5">{label}</p>
    </div>
  )
}

export default function QualitySummary({ run }) {
  const r1 = run.qc_metrics?.r1 ?? {}

  const posData = Object.entries(r1.pos_quality ?? {})
    .map(([pos, q]) => ({ pos: +pos + 1, quality: q }))
    .sort((a, b) => a.pos - b.pos)

  const alignPct = run.total_reads && run.aligned_reads
    ? Math.round((run.aligned_reads / run.total_reads) * 100)
    : null

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-sm font-semibold text-gray-700 mb-4">QC Summary</h2>

      <div className="grid grid-cols-5 gap-4 mb-6">
        <Metric label="Total Reads"   value={run.total_reads?.toLocaleString() ?? '—'} />
        <Metric label="Aligned"       value={run.aligned_reads?.toLocaleString() ?? '—'} />
        <Metric label="Align Rate"    value={alignPct != null ? `${alignPct}%` : '—'} />
        <Metric label="Coverage"      value={run.mean_coverage ? `${run.mean_coverage}x` : '—'} />
        <Metric label="Mean Quality"  value={r1.mean_quality ?? '—'} />
      </div>

      {posData.length > 0 && (
        <>
          <p className="text-xs text-gray-400 mb-1">Per-position mean Phred quality (R1, first & last positions)</p>
          <ResponsiveContainer width="100%" height={110}>
            <BarChart data={posData} barSize={6} margin={{ top: 0, right: 0, left: -10, bottom: 0 }}>
              <XAxis dataKey="pos" tick={{ fontSize: 10 }} interval={1} />
              <YAxis domain={[0, 42]} tick={{ fontSize: 10 }} />
              <Tooltip formatter={(v) => [`Q${v}`, 'Quality']} />
              <Bar dataKey="quality" fill="#3b82f6" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  )
}
