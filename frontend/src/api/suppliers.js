import { api } from './client'

export async function fetchSuppliers() {
  const res = await api.get('/suppliers/')
  return res.data
}

export async function createSupplier(name) {
  const res = await api.post('/suppliers/', { name })
  return res.data
}

export async function deleteSupplier(name) {
  const res = await api.delete('/suppliers/', { data: { name } })
  return res.data
}
