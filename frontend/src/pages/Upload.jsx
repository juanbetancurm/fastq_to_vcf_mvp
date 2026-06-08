import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import { createRun } from '../api/client'

function FileDropzone({ label, file, onFile, required }) {
  const onDrop = useCallback(files => onFile(files[0] ?? null), [onFile])
  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, maxFiles: 1 })

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      <div {...getRootProps()} className={`border-2 border-dashed rounded-lg p-5 text-center cursor-pointer transition-colors
        ${isDragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}`}>
        <input {...getInputProps()} />
        {file
          ? <p className="text-sm text-green-700 font-medium">{file.name}</p>
          : <p className="text-sm text-gray-400">
              {isDragActive ? 'Drop here' : 'Drag & drop or click to select'}
            </p>
        }
      </div>
    </div>
  )
}

function Field({ label, required, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  )
}

const INPUT = "w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"

export default function Upload() {
  const navigate     = useNavigate()
  const queryClient  = useQueryClient()
  const [r1, setR1]  = useState(null)
  const [r2, setR2]  = useState(null)
  const [form, setForm] = useState({
    patient_external_id: '',
    patient_sex:         'U',
    tissue_type:         'peripheral_blood',
    collection_date:     new Date().toISOString().slice(0, 10),
    platform:            'mock',
    sequencing_type:     'WES',
    reference_genome:    'mock_btk',
  })

  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }))

  const mutation = useMutation({
    mutationFn: createRun,
    onSuccess: data => {
      queryClient.invalidateQueries({ queryKey: ['runs'] })
      navigate(`/runs/${data.id}`)
    },
  })

  const handleSubmit = e => {
    e.preventDefault()
    if (!r1) return
    const fd = new FormData()
    Object.entries(form).forEach(([k, v]) => fd.append(k, v))
    fd.append('fastq_r1', r1)
    if (r2) fd.append('fastq_r2', r2)
    mutation.mutate(fd)
  }

  return (
    <div className="max-w-xl">
      <h1 className="text-lg font-semibold text-gray-900 mb-6">New Analysis</h1>

      <form onSubmit={handleSubmit} className="space-y-5 bg-white rounded-lg border border-gray-200 p-6">

        <div className="grid grid-cols-2 gap-4">
          <Field label="Patient ID" required>
            <input required className={INPUT} placeholder="e.g. IEI-042"
              value={form.patient_external_id} onChange={set('patient_external_id')} />
          </Field>
          <Field label="Sex">
            <select className={INPUT} value={form.patient_sex} onChange={set('patient_sex')}>
              <option value="M">Male</option>
              <option value="F">Female</option>
              <option value="U">Unknown</option>
            </select>
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Tissue type">
            <select className={INPUT} value={form.tissue_type} onChange={set('tissue_type')}>
              <option value="peripheral_blood">Peripheral Blood</option>
              <option value="bone_marrow">Bone Marrow</option>
              <option value="saliva">Saliva</option>
              <option value="skin_biopsy">Skin Biopsy</option>
              <option value="other">Other</option>
            </select>
          </Field>
          <Field label="Collection date" required>
            <input type="date" required className={INPUT}
              value={form.collection_date} onChange={set('collection_date')} />
          </Field>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <Field label="Platform">
            <select className={INPUT} value={form.platform} onChange={set('platform')}>
              <option value="mock">Mock (Test)</option>
              <option value="illumina_novaseq">NovaSeq</option>
              <option value="illumina_nextseq">NextSeq</option>
              <option value="illumina_miseq">MiSeq</option>
            </select>
          </Field>
          <Field label="Type">
            <select className={INPUT} value={form.sequencing_type} onChange={set('sequencing_type')}>
              <option value="WES">WES</option>
              <option value="WGS">WGS</option>
            </select>
          </Field>
          <Field label="Reference">
            <select className={INPUT} value={form.reference_genome} onChange={set('reference_genome')}>
              <option value="mock_btk">Mock BTK</option>
              <option value="GRCh38">GRCh38</option>
              <option value="GRCh37">GRCh37</option>
            </select>
          </Field>
        </div>

        <FileDropzone label="FASTQ R1" file={r1} onFile={setR1} required />
        <FileDropzone label="FASTQ R2 (optional)" file={r2} onFile={setR2} />

        {mutation.isError && (
          <p className="text-sm text-red-600">
            {mutation.error?.response?.data
              ? JSON.stringify(mutation.error.response.data)
              : mutation.error?.message}
          </p>
        )}

        <button type="submit" disabled={!r1 || mutation.isPending}
          className="w-full py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">
          {mutation.isPending ? 'Submitting…' : 'Start Analysis'}
        </button>
      </form>
    </div>
  )
}
