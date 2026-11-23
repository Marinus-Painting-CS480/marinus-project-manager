// The one place where the React app talks to the Django API.
// Pages should call these helpers (usually through TanStack Query), not `fetch` directly.
//
// - Same origin: Vite forwards /api to Django in development; Django serves the app in
//   production. So the session cookie is sent automatically.
// - Every non-GET request sends Django's CSRF token from the `csrftoken` cookie.
// - Errors throw an ApiError with the HTTP status and Django Ninja's `detail` message.
// - Money arrives as strings ("1250.00"); keep it as a string or format it, don't use floats.

// Backend URL from .env (empty = same origin).
const API_BASE = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === 'string' ? detail : `Request failed (${status})`)
    this.status = status
    this.detail = detail
  }
}

function getCookie(name) {
  const match = document.cookie.split('; ').find((row) => row.startsWith(`${name}=`))
  return match ? decodeURIComponent(match.split('=')[1]) : null
}

let csrfReady = null

// Call once when the app starts (and before login) so the csrftoken cookie exists.
export function ensureCsrf() {
  if (!csrfReady) {
    csrfReady = fetch(`${API_BASE}/api/auth/csrf`, { credentials: 'same-origin' })
  }
  return csrfReady
}

export async function apiFetch(path, { method = 'GET', body, headers = {} } = {}) {
  const options = { method, credentials: 'same-origin', headers: { ...headers } }

  if (method !== 'GET') {
    await ensureCsrf()
    options.headers['X-CSRFToken'] = getCookie('csrftoken')
  }
  if (body instanceof FormData) {
    options.body = body // the browser sets the multipart boundary itself
  } else if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(body)
  }

  const response = await fetch(`${API_BASE}/api${path}`, options)
  if (response.status === 204) return null

  const data = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, data?.detail)
  return data
}

// ---- Auth ----
export const auth = {
  me: () => apiFetch('/auth/me'),
  login: (email, password) =>
    apiFetch('/auth/login', { method: 'POST', body: { email, password } }),
  logout: () => apiFetch('/auth/logout', { method: 'POST' }),
  setLocale: (locale) => apiFetch('/auth/me', { method: 'PATCH', body: { locale } }),
}

export const users = {
  list: (role) => apiFetch(role ? `/users?role=${role}` : '/users'),
}

// ---- Intake ----
export const customers = {
  search: (search = '') => apiFetch(`/customers?search=${encodeURIComponent(search)}`),
  create: (customer) => apiFetch('/customers', { method: 'POST', body: customer }),
}

export const projects = {
  list: (params = {}) => apiFetch(`/projects?${new URLSearchParams(params)}`),
  summary: () => apiFetch('/projects/summary'),
  get: (id) => apiFetch(`/projects/${id}`),
  create: (project) => apiFetch('/projects', { method: 'POST', body: project }),
  saveDraft: (id, project) => apiFetch(`/projects/${id}`, { method: 'PUT', body: project }),
  submitForEstimate: (id) => apiFetch(`/projects/${id}/submit`, { method: 'POST' }),
  uploadPhotos: (id, files, areaId) => {
    const form = new FormData()
    for (const file of files) form.append('files', file)
    if (areaId) form.append('area_id', areaId)
    return apiFetch(`/projects/${id}/photos`, { method: 'POST', body: form })
  },
  deletePhoto: (photoId) => apiFetch(`/photos/${photoId}`, { method: 'DELETE' }),
}

// ---- Estimating ----
export const estimates = {
  tiers: () => apiFetch('/quality-tiers'),
  start: (projectId) => apiFetch(`/projects/${projectId}/estimate`, { method: 'POST' }),
  get: (id) => apiFetch(`/estimates/${id}`),
  save: (id, estimate) => apiFetch(`/estimates/${id}`, { method: 'PUT', body: estimate }),
  send: (id) => apiFetch(`/estimates/${id}/proposals`, { method: 'POST' }),
  newLink: (proposalId) => apiFetch(`/proposals/${proposalId}/link`, { method: 'POST' }),
  email: (proposalId) => apiFetch(`/proposals/${proposalId}/email`, { method: 'POST' }),
  revoke: (proposalId) => apiFetch(`/proposals/${proposalId}/revoke`, { method: 'POST' }),
}

// ---- Work orders ----
export const workOrders = {
  list: (status) => apiFetch(status ? `/work-orders?status=${status}` : '/work-orders'),
  get: (id) => apiFetch(`/work-orders/${id}`),
  updateSchedule: (id, changes) =>
    apiFetch(`/work-orders/${id}`, { method: 'PATCH', body: changes }),
  setCrew: (id, assignments) =>
    apiFetch(`/work-orders/${id}/assignments`, { method: 'PUT', body: { assignments } }),
  addNote: (id, note) => apiFetch(`/work-orders/${id}/notes`, { method: 'POST', body: { note } }),
  newCustomerLink: (id) => apiFetch(`/work-orders/${id}/customer-link`, { method: 'POST' }),
}

// ---- Customer pages (no account; token comes from the /p/:token or /w/:token URL) ----
export const publicLinks = {
  proposal: (token) => apiFetch(`/public/proposals/${token}`),
  approve: (token, approval) =>
    apiFetch(`/public/proposals/${token}/approve`, { method: 'POST', body: approval }),
  workOrder: (token) => apiFetch(`/public/work-orders/${token}`),
}
