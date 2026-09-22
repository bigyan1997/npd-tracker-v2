import { api } from './client'

export async function fetchProducts(filters) {
  const res = await api.get('/products/', { params: filters })
  return res.data
}

export async function createProduct(data) {
  const res = await api.post('/products/', data)
  return res.data
}

export async function updateProduct(id, data) {
  const res = await api.put(`/products/${id}/`, data)
  return res.data
}

export async function deleteProduct(id) {
  await api.delete(`/products/${id}/`)
}

export async function fetchProductHistory(id) {
  const res = await api.get(`/products/${id}/history/`)
  return res.data
}

export async function fetchDeletedProducts() {
  const res = await api.get('/products/deleted/')
  return res.data
}

export async function restoreProduct(auditId) {
  const res = await api.post(`/products/deleted/${auditId}/restore/`)
  return res.data
}
