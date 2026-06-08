import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchRuns } from '../api/client'
import StatusBadge from '../components/StatusBadge'

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['runs'],
    queryFn: fetchRuns,
    refetchInterval: 5000,
  })

  if (isLoading) return <p className="text-gray-400 text-sm">Loading runs…</p>
  if (error)     return <p className="text-red-500 text-sm">Error: {error.message}</p>

  const runs = data?.results ?? (Array.isArray(data) ? data : [])

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold text-gray-900">Sequencing Runs</h1>
        <Link to="/upload"
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700">
          New Analysis
        </Link>
      </div>

      {runs.length === 0 ? (
        <div className="text-center py-20 text-gray-400 text-sm">
          No runs yet.{' '}
          <Link to="/upload" className="text-blue-500 hover:underline">Upload FASTQ files</Link>{' '}
          to start.
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {['Run', 'Patient', 'Reference', 'Type', 'Status', 'Variants', 'Coverage', 'Date'].map(h => (
                  <th key={h} className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {runs.map(run => (
                <tr key={run.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3">
                    <Link to={`/runs/${run.id}`} className="text-blue-600 hover:underline font-mono">
                      #{run.id}
                    </Link>
                  </td>
                  <td className="px-5 py-3 text-gray-700">{run.patient_external_id}</td>
                  <td className="px-5 py-3 text-gray-500">{run.reference_genome}</td>
                  <td className="px-5 py-3 text-gray-500">{run.sequencing_type}</td>
                  <td className="px-5 py-3"><StatusBadge status={run.status} /></td>
                  <td className="px-5 py-3 text-gray-700">{run.variants_found ?? '—'}</td>
                  <td className="px-5 py-3 text-gray-500">
                    {run.mean_coverage ? `${run.mean_coverage}x` : '—'}
                  </td>
                  <td className="px-5 py-3 text-gray-400">
                    {new Date(run.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
