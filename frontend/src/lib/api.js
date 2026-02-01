const API_BASE = '/api'

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
  return fetchApi('/dashboard/study-summary')
}

export async function getAttentionSites() {
  return fetchApi('/dashboard/attention-sites')
}

export async function getSitesOverview() {
  return fetchApi('/dashboard/sites-overview')
}

export async function getAgentInsights() {
  return fetchApi('/dashboard/agent-insights')
}

export async function getDataQualityDashboard() {
  return fetchApi('/dashboard/data-quality')
}

export async function getEnrollmentDashboard() {
  return fetchApi('/dashboard/enrollment-funnel')
}

export async function getSiteMetadata() {
  return fetchApi('/dashboard/site-metadata')
}

export async function getKRITimeseries(siteId) {
  return fetchApi(`/dashboard/kri-timeseries/${siteId}`)
}

export async function getEnrollmentVelocity(siteId) {
  return fetchApi(`/dashboard/enrollment-velocity/${siteId}`)
}

export async function getAgentActivity() {
  return fetchApi('/dashboard/agent-activity')
}

export async function getSiteDetail(siteId) {
  return fetchApi(`/dashboard/site/${siteId}`)
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
