import fs from 'node:fs/promises'
import { spawn } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import YAML from 'yaml'

import { serviceLogoDomains } from './service-logo-domains.mjs'

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

function parseArgs(argv) {
  return {
    fetchLogos: argv.includes('--fetch-logos'),
  }
}

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      stdio: 'inherit',
      ...options,
    })

    child.on('error', reject)
    child.on('close', (code) => {
      if (code === 0) {
        resolve()
        return
      }

      reject(new Error(`${command} exited with code ${code ?? 'unknown'}`))
    })
  })
}

async function removeLegacySvgIcons(outDir) {
  const entries = await fs.readdir(outDir, { withFileTypes: true }).catch(() => [])

  await Promise.all(
    entries
      .filter((entry) => entry.isFile() && entry.name.endsWith('.svg'))
      .map((entry) => fs.unlink(path.join(outDir, entry.name))),
  )
}

async function fetchLogos(repoRoot) {
  const scriptPath = path.join(repoRoot, 'web', 'scripts', 'logo.py')
  const outDir = path.join(repoRoot, 'web', 'public', 'service-icons')

  await fs.mkdir(outDir, { recursive: true })
  await removeLegacySvgIcons(outDir)

  const failures = []

  for (const [serviceId, domain] of Object.entries(serviceLogoDomains)) {
    const outPath = path.join(outDir, `${serviceId}.png`)

    if (!domain) {
      await fs.rm(outPath, { force: true })
      console.log(`skip ${serviceId}: no domain configured`)
      continue
    }

    try {
      await run('uv', ['run', '--with', 'requests', '--with', 'pillow', scriptPath, domain, '--format', 'png', '--out', outPath], {
        cwd: path.join(repoRoot, 'web'),
      })
    } catch (error) {
      failures.push({ serviceId, domain, message: error instanceof Error ? error.message : String(error) })
      await fs.rm(outPath, { force: true })
    }
  }

  if (failures.length > 0) {
    for (const failure of failures) {
      console.error(`failed ${failure.serviceId} <- ${failure.domain}: ${failure.message}`)
    }
    process.exitCode = 1
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2))
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

  if (args.fetchLogos) {
    await fetchLogos(repoRoot)
  }
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
