const STAGES = [
  { key: 'qc',               label: 'Quality Control'   },
  { key: 'aligning',         label: 'Aligning Reads'    },
  { key: 'sorting',          label: 'Sorting'           },
  { key: 'calling_variants', label: 'Calling Variants'  },
  { key: 'parsing_vcf',      label: 'Parsing VCF'       },
  { key: 'annotating',       label: 'Annotating'        },
  { key: 'completed',        label: 'Completed'         },
]

const ORDER = STAGES.map(s => s.key)

export default function PipelineMonitor({ run }) {
  const currentIdx = ORDER.indexOf(run.status)
  const progress   = run.progress_percent ?? 0
  const failed     = run.status === 'failed'

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-700">Pipeline Progress</h2>
        <span className="text-sm text-gray-500">{progress}%</span>
      </div>

      <div className="w-full bg-gray-200 rounded-full h-1.5 mb-6">
        <div
          className={`h-1.5 rounded-full transition-all duration-700 ${failed ? 'bg-red-500' : 'bg-blue-500'}`}
          style={{ width: `${progress}%` }}
        />
      </div>

      <ul className="space-y-2">
        {STAGES.map((stage, i) => {
          const done   = run.status === 'completed' || (currentIdx > i && !failed)
          const active = !failed && ORDER[currentIdx] === stage.key && run.status !== 'completed'

          return (
            <li key={stage.key} className="flex items-center gap-3 text-sm">
              <span className={`w-5 h-5 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-medium
                ${done   ? 'bg-green-500 text-white' :
                  active ? 'bg-blue-500 text-white'  :
                           'bg-gray-200 text-gray-500'}`}>
                {done ? '✓' : i + 1}
              </span>
              <span className={
                done   ? 'text-gray-700' :
                active ? 'text-blue-700 font-medium' :
                         'text-gray-400'
              }>
                {stage.label}
              </span>
              {active && <span className="text-blue-400 text-xs animate-pulse">running…</span>}
            </li>
          )
        })}
      </ul>

      {failed && run.error_message && (
        <div className="mt-4 p-3 bg-red-50 rounded text-xs text-red-700 font-mono break-all">
          {run.error_message}
        </div>
      )}
    </div>
  )
}
