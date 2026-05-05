import type { SessionStatus, SetupPhasePayload, SetupPhaseSubmitResult, SetupResume, SetupState } from './types'

const sessionBootstrapPath = '/api/session/bootstrap'

export type SessionBootstrapResult = {
  ok: boolean
  message?: string
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
    return { ok: true }
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
  return fetchApi<SessionStatus>('/api/session')
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
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const details = await readErrorMessage(response)
    throw new ApiError(details.message, response.status, details.fieldErrors)
  }

  return (await response.json()) as SetupPhaseSubmitResult
}
