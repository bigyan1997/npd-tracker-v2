import { api } from './client'

export async function previewImport(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await api.post('/products/import/preview/', form)
  return res.data
}

export async function commitImport(rows) {
  const res = await api.post('/products/import/commit/', { rows })
  return res.data
}
