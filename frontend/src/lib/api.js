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

async function postApi(endpoint, body) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }
  return await response.json()
}

async function putApi(endpoint, body) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }
  return await response.json()
}

// ── Dashboard endpoints ──────────────────────────────────────────────────────

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

export async function getSiteJourney(siteId, limit = 50) {
  return cachedFetch(`/dashboard/site/${siteId}/journey?limit=${limit}`)
}

export async function getIntelligenceSummary() {
  return cachedFetch('/dashboard/intelligence-summary')
}

export async function getThemeFindings(themeId) {
  return cachedFetch(`/dashboard/theme/${themeId}/findings`)
}

export async function getAgentActivity() {
  return cachedFetch('/dashboard/agent-activity')
}

export async function getAlertEnhanced(alertId) {
  return cachedFetch(`/dashboard/alert-enhanced/${alertId}`)
}

export async function getKpiMetrics() {
  return cachedFetch('/dashboard/kpi-metrics')
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

// ── Alert endpoints ──────────────────────────────────────────────────────

export async function getAlerts({ status, severity, site_id, limit = 50 } = {}) {
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (severity) params.set('severity', severity)
  if (site_id) params.set('site_id', site_id)
  if (limit) params.set('limit', String(limit))
  const qs = params.toString()
  return cachedFetch(`/alerts/${qs ? '?' + qs : ''}`, 30_000)
}

export async function getAlert(alertId) {
  return fetchApi(`/alerts/${alertId}`)
}

export async function acknowledgeAlert(alertId, acknowledgedBy = 'CODM Lead') {
  return postApi(`/alerts/${alertId}/acknowledge`, { acknowledged_by: acknowledgedBy })
}

export async function suppressAlert(alertId, { reason, created_by = 'CODM Lead', expires_in_days = 7 }) {
  return postApi(`/alerts/${alertId}/suppress`, { reason, created_by, expires_in_days })
}

// ── Proactive scan endpoints ─────────────────────────────────────────────

export async function triggerScan(triggerType = 'api', agentFilter = null) {
  const body = { trigger_type: triggerType }
  if (agentFilter) body.agent_filter = agentFilter
  return postApi('/proactive/scan', body)
}

export async function getScanStatus(scanId) {
  return fetchApi(`/proactive/scan/${scanId}`)
}

export async function getScans(limit = 20, offset = 0) {
  return cachedFetch(`/proactive/scans?limit=${limit}&offset=${offset}`, 30_000)
}

export async function getScanBriefs(scanId) {
  return cachedFetch(`/proactive/briefs/scan/${scanId}`, 60_000)
}

export async function getSiteBriefs(siteId, limit = 10) {
  return cachedFetch(`/proactive/briefs/${siteId}?limit=${limit}`, 60_000)
}

// ── Directive endpoints ──────────────────────────────────────────────────

export async function getDirectives() {
  return cachedFetch('/proactive/directives', 60_000)
}

export async function toggleDirective(directiveId, enabled) {
  invalidateApiCache()
  return putApi(`/proactive/directives/${directiveId}/toggle`, { enabled })
}

export async function createDirective({ directive_id, agent_id, name, description, prompt_text, priority }) {
  invalidateApiCache()
  return postApi('/proactive/directives', { directive_id, agent_id, name, description, prompt_text, priority })
}

// ── Agent endpoints ──────────────────────────────────────────────────────

export async function getAgents() {
  return cachedFetch('/agents/', 300_000)
}

export async function getAgentFindings(agentId, limit = 20) {
  return cachedFetch(`/agents/${agentId}/findings?limit=${limit}`, 30_000)
}

// ── Query endpoints (follow-up, status) ──────────────────────────────────

export async function getQueryStatus(queryId) {
  return fetchApi(`/query/${queryId}/status`)
}

export async function submitFollowUp(queryId, question) {
  return postApi(`/query/${queryId}/follow-up`, { question })
}

// ── Feeds ────────────────────────────────────────────────────────────────

export async function getHealthCheck() {
  return cachedFetch('/feeds/health', 60_000)
}

// ── Investigation (existing) ─────────────────────────────────────────────

export async function startInvestigation(query, siteId, sessionId = null) {
  const response = await fetch(`${API_BASE}/agents/investigate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      query, 
      site_id: siteId,
      session_id: sessionId,
    }),
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
      if (msg.phase === 'keepalive') {
        return
      }
      if (msg.phase === 'complete') {
        completed = true
        invalidateApiCache()
        onComplete?.(msg)
      } else if (msg.phase === 'info') {
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
