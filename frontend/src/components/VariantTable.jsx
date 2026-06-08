import React, { useState, useMemo } from 'react'
import {
  useReactTable, getCoreRowModel, getSortedRowModel,
  getPaginationRowModel, flexRender,
} from '@tanstack/react-table'
import VariantDetail from './VariantDetail'

const IMPACT_CLS = {
  HIGH:     'text-red-700 font-semibold',
  MODERATE: 'text-orange-600 font-medium',
  LOW:      'text-yellow-600',
  MODIFIER: 'text-gray-500',
}

// Pull annotation fields up to a flat object for display
function normalize(v) {
  const ann = v.annotations?.[0] ?? {}
  return {
    ...v,
    _gene:        ann.gene_symbol   ?? v.gene_symbol   ?? '',
    _consequence: ann.consequence   ?? v.consequence   ?? '',
    _impact:      ann.impact        ?? v.impact        ?? '',
    _is_iei:      ann.is_iei_gene   ?? v.is_iei_gene   ?? false,
  }
}

export default function VariantTable({ variants = [] }) {
  const [sorting,  setSorting]  = useState([])
  const [expanded, setExpanded] = useState(null)
  const [impact,   setImpact]   = useState('')
  const [gene,     setGene]     = useState('')

  const data = useMemo(() => {
    return variants
      .map(normalize)
      .filter(v => {
        if (impact && v._impact !== impact) return false
        if (gene   && !v._gene.toLowerCase().includes(gene.toLowerCase())) return false
        return true
      })
  }, [variants, impact, gene])

  const columns = useMemo(() => [
    { accessorKey: 'chromosome',    header: 'Chr',        size: 60 },
    { accessorKey: 'position',      header: 'Position',   size: 90 },
    { accessorKey: 'ref_allele',    header: 'REF',        size: 60 },
    { accessorKey: 'alt_allele',    header: 'ALT',        size: 60,
      cell: i => i.getValue() || '(del)' },
    { accessorKey: 'genotype',      header: 'GT',         size: 60 },
    { accessorKey: '_gene',         header: 'Gene',       size: 80 },
    { accessorKey: '_consequence',  header: 'Consequence',size: 180 },
    { accessorKey: '_impact',       header: 'Impact',     size: 90,
      cell: i => <span className={IMPACT_CLS[i.getValue()] ?? ''}>{i.getValue()}</span> },
    { accessorKey: 'read_depth',    header: 'Depth',      size: 70 },
    { accessorKey: 'allele_frequency', header: 'VAF',     size: 70,
      cell: i => i.getValue() != null ? `${(i.getValue()*100).toFixed(1)}%` : '—' },
  ], [])

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 20 } },
  })

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      {/* Filter bar */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-200 flex-wrap">
        <span className="text-sm text-gray-500">{data.length} variants</span>
        <select
          className="text-sm border border-gray-300 rounded px-2 py-1"
          value={impact} onChange={e => setImpact(e.target.value)}
        >
          <option value="">All impacts</option>
          {['HIGH','MODERATE','LOW','MODIFIER'].map(v => (
            <option key={v} value={v}>{v}</option>
          ))}
        </select>
        <input
          type="text" placeholder="Gene…"
          className="text-sm border border-gray-300 rounded px-2 py-1 w-28"
          value={gene} onChange={e => setGene(e.target.value)}
        />
        {(impact || gene) && (
          <button className="text-xs text-gray-400 hover:text-gray-600"
            onClick={() => { setImpact(''); setGene('') }}>
            Clear
          </button>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            {table.getHeaderGroups().map(hg => (
              <tr key={hg.id}>
                {hg.headers.map(h => (
                  <th key={h.id}
                    className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wide cursor-pointer select-none whitespace-nowrap"
                    onClick={h.column.getToggleSortingHandler()}>
                    {flexRender(h.column.columnDef.header, h.getContext())}
                    {{ asc: ' ↑', desc: ' ↓' }[h.column.getIsSorted()] ?? ''}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map(row => (
              <React.Fragment key={row.id}>
                <tr
                  className="border-b border-gray-100 hover:bg-blue-50 cursor-pointer"
                  onClick={() => setExpanded(expanded === row.id ? null : row.id)}
                >
                  {row.getVisibleCells().map(cell => (
                    <td key={cell.id} className="px-4 py-2.5 text-gray-700">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
                {expanded === row.id && (
                  <tr>
                    <td colSpan={columns.length} className="p-0">
                      <VariantDetail variant={row.original} />
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
        <span className="text-sm text-gray-500">
          Page {table.getState().pagination.pageIndex + 1} / {Math.max(1, table.getPageCount())}
        </span>
        <div className="flex gap-1">
          <button className="px-3 py-1 text-sm border rounded disabled:opacity-40"
            onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>
            Prev
          </button>
          <button className="px-3 py-1 text-sm border rounded disabled:opacity-40"
            onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
