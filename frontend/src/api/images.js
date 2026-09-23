import { api } from './client'

// Freshly synced from Google Drive, so it includes photos staff added there
// directly. Returns { images, photoFolders: { product, nutrition } }.
export async function fetchProductImages(productId) {
  const res = await api.get(`/products/${productId}/images/`)
  return res.data
}

export async function uploadProductImage(productId, category, file) {
  const form = new FormData()
  form.append('category', category)
  form.append('image', file)
  const res = await api.post(`/products/${productId}/images/`, form)
  return res.data
}

export async function deleteProductImage(productId, imageId) {
  await api.delete(`/products/${productId}/images/${imageId}/`)
}
