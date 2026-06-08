import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchRun, fetchRunVariants } from '../api/client'
import StatusBadge from '../components/StatusBadge'
import PipelineMonitor from '../components/PipelineMonitor'
import QualitySummary from '../components/QualitySummary'
import VariantTable from '../components/VariantTable'

const RUNNING = new Set(['pending','qc','aligning','sorting','calling_variants','parsing_vcf','annotating'])

export default function RunDetail() {
  const { id } = useParams()

  const { data: run, isLoading } = useQuery({
    queryKey: ['run', id],
    queryFn: () => fetchRun(id),
    refetchInterval: query => {
      const s = query.state.data?.status
      return (!s || RUNNING.has(s)) ? 2000 : false
    },
  })

  const { data: variantData } = useQuery({
    queryKey: ['run-variants', id],
    queryFn: () => fetchRunVariants(id),
    enabled: run?.status === 'completed',
  })

  if (isLoading) return <p className="text-gray-400 text-sm">Loading…</p>
  if (!run)      return <p className="text-red-500 text-sm">Run not found.</p>

  const variants  = variantData?.results ?? (Array.isArray(variantData) ? variantData : [])
  const isRunning = RUNNING.has(run.status)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-1">
          <Link to="/" className="text-sm text-gray-400 hover:text-gray-600">← Runs</Link>
        </div>
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold text-gray-900">Run #{run.id}</h1>
          <StatusBadge status={run.status} />
        </div>
        <p className="text-sm text-gray-500 mt-1">
          Patient: <strong className="text-gray-700">{run.patient_external_id}</strong>
          <span className="mx-1.5 text-gray-300">·</span>
          {run.reference_genome}
          <span className="mx-1.5 text-gray-300">·</span>
          {run.sequencing_type}
          <span className="mx-1.5 text-gray-300">·</span>
          {new Date(run.created_at).toLocaleString()}
        </p>
      </div>

      {/* Pipeline monitor while running or failed */}
      {(isRunning || run.status === 'failed') && (
        <PipelineMonitor run={run} />
      )}

      {/* Results when completed */}
      {run.status === 'completed' && (
        <>
          <QualitySummary run={run} />
          <div>
            <h2 className="text-sm font-semibold text-gray-700 mb-3">
              Variants ({run.variants_found ?? 0})
            </h2>
            <VariantTable variants={variants} />
          </div>
        </>
      )}
    </div>
  )
}
