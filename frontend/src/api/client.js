import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
})

// Everyone shares one login, so each request says who is actually working
// (picked in "Who's working?"); the server records it in History.
api.interceptors.request.use((config) => {
  let name = ''
  try {
    name = localStorage.getItem('npd-staff-name') ?? ''
  } catch {
    // storage unavailable — the server will ask for a name before changes
  }
  // Encoded: header values must be plain ASCII (names may not be).
  if (name) config.headers.set('X-Staff-Name', encodeURIComponent(name))
  return config
})
