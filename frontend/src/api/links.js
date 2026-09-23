import { api } from './client'

// { sheet, photos } — URLs for the header shortcuts; either may be null.
export async function fetchLinks() {
  const res = await api.get('/links/')
  return res.data
}
