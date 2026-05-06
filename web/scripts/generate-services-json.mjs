import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import YAML from 'yaml'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

function fallbackCategory(svc) {
  if (svc.required || String(svc.state_bucket || '').trim() === 'always') return 'Core'
  if (svc.foundation) return 'Foundation'
  if (svc.host_service) return 'Host Add-ons'
  return 'Other'
}

function normalizeService(svc) {
  const homepage = svc.homepage && typeof svc.homepage === 'object' ? svc.homepage : {}

  const category = String(homepage.category || '').trim() || fallbackCategory(svc)
  const id = String(svc.id || '').trim()
  const name = String(homepage.name || '').trim() || id
  const description = String(homepage.description || '').trim() || String(svc.notes || '').trim()
  const icon = String(homepage.icon || '').trim() || null

  return {
    id,
    required: Boolean(svc.required),
    optional: Boolean(svc.optional),
    foundation: Boolean(svc.foundation),
    host_service: Boolean(svc.host_service),
    default_subdomain: svc.default_subdomain ?? null,
    default_port: svc.default_port ?? null,
    category,
    name,
    description,
    icon,
  }
}

async function main() {
  const repoRoot = path.resolve(__dirname, '..', '..')
  const registryPath = path.join(repoRoot, 'src', 'rakkib', 'data', 'registry.yaml')
  const outPath = path.join(repoRoot, 'web', 'public', 'services.json')

  const registryText = await fs.readFile(registryPath, 'utf8')
  const registry = YAML.parse(registryText)

  const services = Array.isArray(registry?.services) ? registry.services : []
  const payload = {
    services: services
      .filter((svc) => svc && typeof svc === 'object')
      .map(normalizeService)
      .filter((svc) => svc.id)
      .sort((a, b) => {
        const keyA = `${a.category}\u0000${a.name}\u0000${a.id}`
        const keyB = `${b.category}\u0000${b.name}\u0000${b.id}`
        return keyA.localeCompare(keyB)
      }),
  }

  await fs.mkdir(path.dirname(outPath), { recursive: true })
  await fs.writeFile(outPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8')
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
