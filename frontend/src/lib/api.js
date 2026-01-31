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

export async function runInvestigation(query, siteId) {
  try {
    const response = await fetch(`${API_BASE}/agents/investigate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query, site_id: siteId }),
    })
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    return await response.json()
  } catch (error) {
    console.error('Failed to run investigation:', error)
    throw error
  }
}
