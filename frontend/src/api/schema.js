import { api } from './client'

export async function fetchSchema() {
  const res = await api.get('/schema/')
  return res.data
}
