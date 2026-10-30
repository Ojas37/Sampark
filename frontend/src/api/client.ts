export type User = {
  id: number
  name: string
  email: string
  role: string
  region_code: string | null
  institution_id: number | null
}

export type Application = {
  id: number
  reference_no: string
  institution: string
  institution_id: number
  region_code: string
  application_type: string
  template: string
  template_version: number
  stage: string
  status: string
  owner_role: string
  priority: number
  visit_mode: string
  created_at: string
  version: number
  open_deficiencies: number
}

type ApiOptions = RequestInit & { headers?: HeadersInit }

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const token = localStorage.getItem('flowwise_token')
  const headers = new Headers(options.headers)
  headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(path, { ...options, headers })
  const payload = await response.json() as T | {error?: {code: string; message: string}}
  if (!response.ok) {
    const errorPayload = payload as {error?: {message?: string}}
    const message = errorPayload.error?.message ?? `Request failed (${response.status})`
    if (response.status === 401) {
      localStorage.removeItem('flowwise_token')
      localStorage.removeItem('flowwise_user')
      window.location.assign('/login')
    }
    throw new Error(message)
  }
  return payload as T
}

export type DocumentSummary = {
  id: number
  filename: string
  doc_type: string
  doc_date: string | null
  institution: string | null
  sha256: string
  source: string
  pages: number
  pending_candidates: number
  accepted_candidates: number
  last_run: { id: number; provider: string; candidates_total: number; candidates_discarded: number; latency_ms: number } | null
}

export type Candidate = {
  id: number
  run_id: number
  document_id: number
  kind: string
  category: string
  description: string
  responsible_party: string
  due_date: string | null
  due_expression: string | null
  field_name: string | null
  field_value: string | null
  source_page: number
  source_quote: string
  confidence: number
  grounded: boolean
  status: string
  edited: boolean
}

export async function login(email: string, password: string): Promise<{access_token: string; token_type: string; user: User}> {
  return api('/api/v1/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })
}
