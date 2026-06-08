import axios from 'axios'

// Vite proxies /api → http://localhost:8000/api
const client = axios.create({ baseURL: '/api' })

export const fetchRuns        = ()       => client.get('/runs/').then(r => r.data)
export const fetchRun         = (id)     => client.get(`/runs/${id}/`).then(r => r.data)
export const fetchRunStatus   = (id)     => client.get(`/runs/${id}/status/`).then(r => r.data)
export const fetchRunVariants = (id, p)  => client.get(`/runs/${id}/variants/`, { params: p }).then(r => r.data)

export const createRun = (formData) =>
  client.post('/runs/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)

export default client
