export type SessionStatus = {
  authenticated: boolean
  auth_enabled: boolean
  csrf_token: string | null
}

export type SetupPhaseSummary = {
  phase: number
  complete: boolean
  writes_state: string[]
  has_service_catalog: boolean
  route: string
}

export type SetupResume = {
  resume_phase: number
  confirmed: boolean
  deployment_succeeded: boolean
  phases: SetupPhaseSummary[]
}

export type SetupState = {
  state: Record<string, unknown>
  confirmed: boolean
  resume_phase: number
  deployment_succeeded: boolean
}

export type SetupDeployedUrl = {
  service: string
  label: string
  url: string
}

export type SetupFieldEntry = {
  key?: string
  when?: string
}

export type SetupQuestionField = {
  id: string
  type: string
  prompt?: string
  prompt_template?: string
  when?: string | null
  default?: unknown
  repeat_for?: string | null
  canonical_values?: string[]
  numeric_aliases?: Record<string, string>
  aliases?: Record<string, string[]>
  accepted_inputs?: Record<string, unknown>
  records: string[]
  summary_fields?: string[]
  entries?: SetupFieldEntry[]
  required?: boolean
}

export type SetupServiceCatalogItem = {
  slug: string
  label?: string
  default_subdomain?: string | null
  category?: string | null
}

export type SetupServiceCatalog = {
  foundation_bundle?: SetupServiceCatalogItem[]
  optional_services?: SetupServiceCatalogItem[]
  host_addons?: SetupServiceCatalogItem[]
}

export type SetupPhasePayload = {
  phase: number
  complete: boolean
  reads_state: string[]
  writes_state: string[]
  fields: SetupQuestionField[]
  service_catalog: SetupServiceCatalog
  rules: Array<Record<string, unknown>>
  execution_generated_only: Array<Record<string, unknown>>
  answers: Record<string, unknown>
}

export type SetupPhaseSubmitResult = {
  ok: boolean
  phase: SetupPhasePayload
  resume_phase: number
  confirmed: boolean
}

export type SetupRunStatus = {
  status: 'idle' | 'running' | 'succeeded' | 'failed'
  operation: 'full_setup' | 'service_sync'
  message: string
  started_at: string | null
  finished_at: string | null
  exit_code: number | null
  command: string[]
  log_path: string | null
  pid: number | null
  running: boolean
  can_start: boolean
  confirmed: boolean
  deployment_succeeded: boolean
  resume_phase: number
  log_tail: string[]
  deployed_urls: SetupDeployedUrl[]
  attention: { type: 'cloudflare_auth'; url: string } | null
  host_auth: {
    ok: boolean
    code: string
    message: string
    command: string | null
    requires_restart: boolean
  }
}

export type PublicService = {
  id: string
  required: boolean
  optional: boolean
  foundation: boolean
  host_service: boolean
  default_subdomain: string | null
  default_port: number | null
  category: string
  name: string
  description: string
  icon: string | null
}

export type PublicServicesResponse = {
  services: PublicService[]
}
