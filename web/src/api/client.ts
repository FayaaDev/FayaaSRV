import type {
  PublicServicesResponse,
  SessionStatus,
  SetupPhasePayload,
  SetupPhaseSubmitResult,
  SetupResume,
  SetupRunStatus,
  SetupState,
} from './types'

const sessionBootstrapPath = '/api/session/bootstrap'
const sessionBootstrapTokenPath = '/api/session/bootstrap-token'
let csrfToken: string | null = null

export type SessionBootstrapResult = {
  ok: boolean
  message?: string
  csrf_token?: string
}

export type SessionBootstrapTokenResult = {
  token: string | null
  auth_enabled: boolean
}

export class ApiError extends Error {
  status: number
  fieldErrors?: Record<string, string>

  constructor(message: string, status: number, fieldErrors?: Record<string, string>) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fieldErrors = fieldErrors
  }
}

async function readErrorMessage(response: Response) {
  try {
    const payload = (await response.json()) as {
      message?: string
      detail?: string | { message?: string; field_errors?: Record<string, string> }
    }

    if (typeof payload.detail === 'object' && payload.detail !== null) {
      return {
        message: payload.detail.message ?? payload.message ?? `Request failed with ${response.status}`,
        fieldErrors: payload.detail.field_errors,
      }
    }

    return {
      message: payload.message ?? payload.detail ?? `Request failed with ${response.status}`,
    }
  } catch {
    return { message: `Request failed with ${response.status}` }
  }
}

async function fetchApi<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    credentials: 'include',
    headers: {
      'Cache-Control': 'no-store',
    },
  })

  if (!response.ok) {
    const details = await readErrorMessage(response)
    throw new ApiError(details.message, response.status, details.fieldErrors)
  }

  return (await response.json()) as T
}

async function fetchStaticJson<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    headers: {
      'Cache-Control': 'no-store',
    },
  })

  if (!response.ok) {
    throw new ApiError(`Request failed with ${response.status}`, response.status)
  }

  return (await response.json()) as T
}

function rememberCsrfToken(token: string | null | undefined) {
  csrfToken = token?.trim() || null
}

function csrfHeader(): Record<string, string> {
  return csrfToken ? { 'X-CSRF-Token': csrfToken } : {}
}

export async function bootstrapSession(token: string): Promise<SessionBootstrapResult> {
  const response = await fetch(sessionBootstrapPath, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-store',
    },
    body: JSON.stringify({ token }),
  })

  if (response.ok) {
    const payload = (await response.json()) as SessionBootstrapResult
    rememberCsrfToken(payload.csrf_token)
    return { ok: true, csrf_token: payload.csrf_token }
  }

  let message: string | undefined

  try {
    const payload = (await response.json()) as { message?: string; detail?: string }
    message = payload.message ?? payload.detail
  } catch {
    message = undefined
  }

  return {
    ok: false,
    message,
  }
}

export async function fetchSession(): Promise<SessionStatus> {
  const session = await fetchApi<SessionStatus>('/api/session')
  rememberCsrfToken(session.csrf_token)
  return session
}

export async function fetchBootstrapToken(): Promise<SessionBootstrapTokenResult> {
  return fetchApi<SessionBootstrapTokenResult>(sessionBootstrapTokenPath)
}

export async function fetchSetupState(): Promise<SetupState> {
  return fetchApi<SetupState>('/api/state')
}

export async function fetchSetupResume(): Promise<SetupResume> {
  return fetchApi<SetupResume>('/api/state/resume')
}

export async function fetchSetupPhase(phase: number): Promise<SetupPhasePayload> {
  return fetchApi<SetupPhasePayload>(`/api/questions/phases/${phase}`)
}

export async function submitSetupPhase(
  phase: number,
  payload: { answers: Record<string, unknown>; confirmations?: Record<string, boolean> },
): Promise<SetupPhaseSubmitResult> {
  const response = await fetch(`/api/questions/phases/${phase}/answers`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-store',
      ...csrfHeader(),
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const details = await readErrorMessage(response)
    throw new ApiError(details.message, response.status, details.fieldErrors)
  }

  return (await response.json()) as SetupPhaseSubmitResult
}

export async function fetchSetupRunStatus(): Promise<SetupRunStatus> {
  return fetchApi<SetupRunStatus>('/api/run')
}

export async function fetchPublicServices(): Promise<PublicServicesResponse> {
  // Frontend is deployed standalone (Cloudflare Pages/Workers); serve the catalog as a static asset.
  return fetchStaticJson<PublicServicesResponse>('/services.json')
}

export async function startSetupRun(mode: 'full_setup' | 'service_sync' = 'full_setup'): Promise<SetupRunStatus> {
  const response = await fetch('/api/run/start', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-store',
      ...csrfHeader(),
    },
    body: JSON.stringify({ mode }),
  })

  if (!response.ok) {
    const details = await readErrorMessage(response)
    throw new ApiError(details.message, response.status, details.fieldErrors)
  }

  return (await response.json()) as SetupRunStatus
}
