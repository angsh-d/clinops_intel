const API_BASE = '/api'

// ── Client-side TTL cache with in-flight dedup ───────────────────────────────
const _cache = new Map()
const _inflight = new Map()
const DASHBOARD_TTL = 120_000 // 120 seconds

function cachedFetch(endpoint, ttlMs = DASHBOARD_TTL) {
  const now = Date.now()
  const entry = _cache.get(endpoint)
  if (entry && now - entry.ts < ttlMs) {
    return Promise.resolve(entry.data)
  }
  if (_inflight.has(endpoint)) {
    return _inflight.get(endpoint)
  }
  const promise = fetchApi(endpoint).then((data) => {
    _cache.set(endpoint, { data, ts: Date.now() })
    _inflight.delete(endpoint)
    return data
  }).catch((err) => {
    _inflight.delete(endpoint)
    throw err
  })
  _inflight.set(endpoint, promise)
  return promise
}

export function invalidateApiCache() {
  _cache.clear()
  _inflight.clear()
}

async function fetchApi(endpoint) {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`)
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    return await response.json()
  } catch (error) {
    console.error(`Failed to fetch ${endpoint}:`, error)
    throw error
  }
}

export async function getStudySummary() {
  return cachedFetch('/dashboard/study-summary')
}

export async function getAttentionSites() {
  return cachedFetch('/dashboard/attention-sites')
}

export async function getSitesOverview() {
  return cachedFetch('/dashboard/sites-overview')
}

export async function getAgentInsights() {
  return cachedFetch('/dashboard/agent-insights')
}

export async function getDataQualityDashboard() {
  return cachedFetch('/dashboard/data-quality')
}

export async function getEnrollmentDashboard() {
  return cachedFetch('/dashboard/enrollment-funnel')
}

export async function getSiteMetadata() {
  return cachedFetch('/dashboard/site-metadata')
}

export async function getKriTimeseries(siteId) {
  return cachedFetch(`/dashboard/kri-timeseries/${siteId}`)
}

export async function getEnrollmentVelocity(siteId) {
  return cachedFetch(`/dashboard/enrollment-velocity/${siteId}`)
}

export async function getSiteDetail(siteId) {
  return cachedFetch(`/dashboard/site/${siteId}`)
}

// ── Vendor endpoints ──────────────────────────────────────────────────────

export async function getVendorScorecards() {
  return cachedFetch('/dashboard/vendor-scorecards')
}

export async function getVendorDetail(vendorId) {
  return cachedFetch(`/dashboard/vendor/${vendorId}`)
}

export async function getVendorComparison() {
  return cachedFetch('/dashboard/vendor-comparison')
}

// ── Financial endpoints ───────────────────────────────────────────────────

export async function getFinancialSummary() {
  return cachedFetch('/dashboard/financial-summary')
}

export async function getFinancialWaterfall() {
  return cachedFetch('/dashboard/financial-waterfall')
}

export async function getFinancialByCountry() {
  return cachedFetch('/dashboard/financial-by-country')
}

export async function getFinancialByVendor() {
  return cachedFetch('/dashboard/financial-by-vendor')
}

export async function getCostPerPatient() {
  return cachedFetch('/dashboard/cost-per-patient')
}

export async function startInvestigation(query, siteId) {
  const response = await fetch(`${API_BASE}/agents/investigate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, site_id: siteId }),
  })
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }
  return await response.json()
}

export function connectInvestigationStream(queryId, { onPhase, onComplete, onError }) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/query/${queryId}`
  const ws = new WebSocket(wsUrl)
  let completed = false

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.error) {
        completed = true
        onError?.(msg.error)
        return
      }
      if (msg.phase === 'complete') {
        completed = true
        invalidateApiCache()
        onComplete?.(msg)
      } else if (msg.phase === 'info') {
        // Server info message (e.g. query already processing) — treat as phase
        onPhase?.(msg)
      } else {
        onPhase?.(msg)
      }
    } catch (e) {
      console.error('WebSocket parse error:', e)
    }
  }

  ws.onerror = (event) => {
    console.error('WebSocket error:', event)
    completed = true
    onError?.('WebSocket connection error')
  }

  ws.onclose = () => {
    if (!completed) {
      onError?.('Connection closed before investigation completed')
    }
  }

  return ws
}
