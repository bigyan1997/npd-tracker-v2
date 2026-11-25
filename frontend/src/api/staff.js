import { api } from './client'

// The name picked in "Who's working?" — remembered per browser and sent with
// every request (see client.js) so edits are recorded under the right person.
const KEY = 'npd-staff-name'

export function getStaffName() {
  try {
    return localStorage.getItem(KEY) ?? ''
  } catch {
    return ''
  }
}

export function setStaffName(name) {
  try {
    if (name) localStorage.setItem(KEY, name)
    else localStorage.removeItem(KEY)
  } catch {
    // private window etc. — the picker will just ask again next time
  }
}

export async function fetchStaff() {
  const res = await api.get('/auth/staff/')
  return res.data
}

export async function addStaff(name) {
  const res = await api.post('/auth/staff/', { name })
  return res.data
}

export async function removeStaff(name) {
  const res = await api.delete('/auth/staff/', { data: { name } })
  return res.data
}
