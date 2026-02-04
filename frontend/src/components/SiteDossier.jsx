import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, TrendingUp, TrendingDown, Minus, MapPin, AlertTriangle, Send, Loader2, Calendar, UserCheck, Clock, Activity, ChevronRight } from 'lucide-react'
import { useStore } from '../lib/store'
import { getSiteDetail, getSiteBriefs, getSiteJourney } from '../lib/api'

const TREND_MAP = {
  improving: { icon: TrendingUp, color: 'text-apple-success', bgColor: 'bg-apple-success/10', label: 'Improving' },
  stable: { icon: Minus, color: 'text-apple-grey-500', bgColor: 'bg-apple-grey-100', label: 'Stable' },
  deteriorating: { icon: TrendingDown, color: 'text-apple-critical', bgColor: 'bg-apple-critical/10', label: 'At Risk' },
}

export function SiteDossier() {
  const navigate = useNavigate()
  const { siteId, studyId } = useParams()
  const { setInvestigation, siteNameMap, currentStudyId } = useStore()

  const [siteDetail, setSiteDetail] = useState(null)
  const [briefs, setBriefs] = useState([])
  const [journey, setJourney] = useState(null)
  const [loading, setLoading] = useState(true)
  const [askInput, setAskInput] = useState('')

  const effectiveStudyId = studyId || currentStudyId

  useEffect(() => {
    if (!siteId) return
    let cancelled = false
    async function fetchAll() {
      const [detailR, briefsR, journeyR] = await Promise.allSettled([
        getSiteDetail(siteId),
        getSiteBriefs(siteId, 5),
        getSiteJourney(siteId, 30),
      ])
      if (cancelled) return
      if (detailR.status === 'fulfilled') setSiteDetail(detailR.value)
      if (briefsR.status === 'fulfilled' && Array.isArray(briefsR.value)) setBriefs(briefsR.value)
      if (journeyR.status === 'fulfilled') setJourney(journeyR.value)
      setLoading(false)
    }
    fetchAll()
    return () => { cancelled = true }
  }, [siteId])

  const handleAsk = () => {
    if (!askInput.trim()) return
    const siteName = siteNameMap[siteId] || siteId
    setInvestigation({ question: askInput.trim(), site: { id: siteId, name: siteName }, status: 'routing' })
    setAskInput('')
  }

  const siteName = siteNameMap[siteId] || siteDetail?.site_name || siteId
  const latestBrief = briefs[0]
  const trend = TREND_MAP[latestBrief?.trend_indicator] || TREND_MAP.stable

  if (loading) {
    return (
      <div className="min-h-screen bg-apple-bg">
        <header className="sticky top-0 z-50 bg-apple-surface/80 backdrop-blur-xl border-b border-apple-divider">
          <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-4">
            <button 
              onClick={() => navigate(`/study/${effectiveStudyId}`)}
              className="button-icon"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
          </div>
        </header>
        <div className="flex items-center justify-center h-64">
          <div className="flex items-center gap-3 text-apple-secondary">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span className="text-body">Loading...</span>
          </div>
        </div>
      </div>
    )
  }

  const detail = siteDetail || {}
  const enrollmentPct = detail.enrollment_percent || 0
  
  const getDqMetric = (label) => {
    const metric = detail.data_quality_metrics?.find(m => m.label === label)
    return { value: metric?.value, note: metric?.note }
  }
  
  const getEnrollMetric = (label) => {
    const metric = detail.enrollment_metrics?.find(m => m.label === label)
    return { value: metric?.value, note: metric?.note }
  }
  
  const dqScore = detail.data_quality_score ?? detail.dq_score ?? null
  const healthScore = dqScore != null ? Math.round(dqScore) : null
  const dqMetric = getDqMetric('DQ Score')
  const openQueriesMetric = getDqMetric('Open Queries')
  const entryLagMetric = getDqMetric('Entry Lag')
  const enrollmentMetric = getEnrollMetric('Enrollment %') || getEnrollMetric('Randomized')

  return (
    <div className="min-h-screen bg-apple-bg">
      {/* Minimal Header */}
      <header className="sticky top-0 z-50 bg-apple-surface/80 backdrop-blur-xl border-b border-apple-divider">
        <div className="max-w-5xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => navigate(`/study/${effectiveStudyId}`)}
              className="button-icon"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="h-5 w-px bg-apple-divider" />
            <div className="flex items-center gap-3">
              <span className="text-body font-semibold text-apple-text">{siteName}</span>
              <span className="text-caption text-apple-tertiary">
                {detail.country || ''}{detail.city ? ` · ${detail.city}` : ''}
              </span>
            </div>
          </div>
          
          {/* Status Pill */}
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${trend.bgColor}`}>
            <trend.icon className={`w-3.5 h-3.5 ${trend.color}`} />
            <span className={`text-caption font-medium ${trend.color}`}>{trend.label}</span>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
          className="mb-10"
        >
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-[32px] font-semibold text-apple-text tracking-tight">{siteName}</h1>
              <div className="flex items-center gap-4 mt-2">
                <span className="flex items-center gap-1.5 text-caption text-apple-secondary">
                  <MapPin className="w-3.5 h-3.5" />
                  {detail.country || 'Unknown'}{detail.city ? ` · ${detail.city}` : ''}
                </span>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Key Metrics Grid */}
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.05, ease: [0.25, 0.46, 0.45, 0.94] }}
          className="mb-10"
        >
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard 
              label="Enrollment" 
              value={`${enrollmentPct.toFixed(0)}%`}
              status={enrollmentPct >= 80 ? 'success' : enrollmentPct >= 50 ? 'neutral' : 'warning'}
              note={enrollmentMetric?.note}
            />
            <MetricCard 
              label="DQ Score" 
              value={healthScore != null ? `${healthScore}` : '--'}
              status={healthScore == null ? 'neutral' : healthScore >= 70 ? 'success' : healthScore >= 40 ? 'neutral' : 'warning'}
              note={dqMetric?.note}
            />
            <MetricCard 
              label="Open Queries" 
              value={openQueriesMetric?.value || '0'}
              status={parseInt(openQueriesMetric?.value || '0') <= 5 ? 'success' : parseInt(openQueriesMetric?.value || '0') <= 15 ? 'neutral' : 'warning'}
              note={openQueriesMetric?.note}
            />
            <MetricCard 
              label="Entry Lag" 
              value={entryLagMetric?.value || '--'}
              suffix={entryLagMetric?.value && entryLagMetric?.value !== '--' ? 'd' : ''}
              status={(entryLagMetric?.value || '--') === '--' ? 'neutral' : parseFloat(entryLagMetric?.value) <= 3 ? 'success' : parseFloat(entryLagMetric?.value) <= 7 ? 'neutral' : 'warning'}
              note={entryLagMetric?.note}
            />
          </div>
        </motion.section>

        {/* Intelligence Brief */}
        {latestBrief && (
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="mb-10"
          >
            <h2 className="section-header mb-4">Intelligence Brief</h2>
            <div className="card-elevated p-6">
              <p className="text-body text-apple-text leading-relaxed">
                {typeof latestBrief.risk_summary === 'string' 
                  ? latestBrief.risk_summary 
                  : latestBrief.risk_summary?.headline || 'No summary available'}
              </p>
              
              {latestBrief.risk_summary?.key_risks?.length > 0 && (
                <div className="mt-4 space-y-2">
                  {latestBrief.risk_summary.key_risks.map((risk, i) => (
                    <div key={i} className={`flex items-start gap-3 p-3 rounded-apple ${
                      risk.severity === 'critical' ? 'bg-apple-critical/5' : 'bg-apple-warning/5'
                    }`}>
                      <div className={`w-1.5 h-1.5 rounded-full mt-2 flex-shrink-0 ${
                        risk.severity === 'critical' ? 'bg-apple-critical' : 'bg-apple-warning'
                      }`} />
                      <div>
                        <span className="text-caption font-medium text-apple-text">{risk.risk}</span>
                        <p className="text-caption text-apple-secondary mt-0.5">{risk.evidence}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {latestBrief.vendor_accountability?.cro_issues?.length > 0 && (
                <div className="mt-5 pt-4 border-t border-apple-divider">
                  <p className="text-caption font-medium text-apple-text mb-2">Vendor Issues</p>
                  <ul className="space-y-1">
                    {latestBrief.vendor_accountability.cro_issues.map((issue, i) => (
                      <li key={i} className="text-caption text-apple-secondary flex items-start gap-2">
                        <span className="text-apple-grey-400 mt-0.5">•</span>
                        <span>{issue}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {latestBrief.recommended_actions?.length > 0 && (
                <div className="mt-5 pt-4 border-t border-apple-divider">
                  <p className="text-caption font-medium text-apple-text mb-3">Recommended Actions</p>
                  <div className="space-y-2">
                    {latestBrief.recommended_actions.map((a, i) => (
                      <div key={i} className="flex items-start gap-3">
                        <span className="text-caption text-apple-tertiary font-medium w-5 flex-shrink-0">{i + 1}.</span>
                        <div>
                          <span className="text-caption text-apple-text">{typeof a === 'string' ? a : a.action}</span>
                          {a.owner && <span className="text-caption text-apple-tertiary ml-2">({a.owner})</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Provenance */}
              <div className="mt-5 pt-4 border-t border-apple-divider">
                <p className="text-[11px] font-mono text-apple-muted">
                  Generated by {latestBrief.agent || 'proactive_briefing_agent'} · Updated {latestBrief.created_at ? new Date(latestBrief.created_at).toLocaleString() : 'recently'}
                </p>
              </div>
            </div>
          </motion.section>
        )}

        {/* Active Alerts */}
        {detail.alerts?.length > 0 && (
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.15, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="mb-10"
          >
            <h2 className="section-header mb-4">Active Alerts</h2>
            <div className="space-y-3">
              {detail.alerts.slice(0, 3).map((alert, i) => (
                <div key={i} className="card p-4 flex items-start gap-4">
                  <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                    alert.severity === 'critical' ? 'bg-apple-critical' : 
                    alert.severity === 'warning' ? 'bg-apple-warning' : 'bg-apple-grey-400'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-body text-apple-text font-medium">{alert.title}</p>
                    {alert.description && (
                      <p className="text-caption text-apple-secondary mt-1 line-clamp-2">{alert.description}</p>
                    )}
                    <p className="text-[11px] text-apple-muted font-mono mt-2">
                      {alert.agent_id} · {alert.created_at ? new Date(alert.created_at).toLocaleDateString() : ''}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </motion.section>
        )}

        {/* Site Journey Timeline */}
        <SiteJourneyTimeline journey={journey} />

        {/* Ask AI */}
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
          className="mt-10"
        >
          <h2 className="section-header mb-4">Ask About This Site</h2>
          <div className="card p-4">
            <div className="flex items-center gap-3">
              <input
                type="text"
                value={askInput}
                onChange={(e) => setAskInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
                placeholder="e.g., What's causing the high screen failure rate?"
                className="input-primary flex-1"
              />
              <button
                onClick={handleAsk}
                disabled={!askInput.trim()}
                className="button-primary flex items-center gap-2 disabled:opacity-40"
              >
                <Send className="w-4 h-4" />
                <span>Investigate</span>
              </button>
            </div>
          </div>
        </motion.section>
      </main>
    </div>
  )
}

function MetricCard({ label, value, suffix = '', status = 'neutral', note }) {
  const statusStyles = {
    success: 'border-l-apple-success',
    warning: 'border-l-apple-warning', 
    neutral: 'border-l-apple-grey-300'
  }
  
  return (
    <div className={`metric-card border-l-[3px] ${statusStyles[status]}`}>
      <p className="metric-label mb-2">{label}</p>
      <p className="metric-value">
        {value}
        {suffix && <span className="text-lg text-apple-secondary font-normal ml-0.5">{suffix}</span>}
      </p>
      {note && <p className="metric-note">{note}</p>}
    </div>
  )
}

function SiteJourneyTimeline({ journey }) {
  if (!journey || !journey.events || journey.events.length === 0) return null

  const formatDate = (dateStr) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const getSeverityDot = (severity) => {
    switch (severity) {
      case 'critical': return 'bg-apple-critical'
      case 'warning': return 'bg-apple-warning'
      case 'success': return 'bg-apple-success'
      default: return 'bg-apple-grey-400'
    }
  }

  const getEventIcon = (eventType) => {
    switch (eventType) {
      case 'cra_transition': return UserCheck
      case 'monitoring_visit': return Calendar
      case 'alert': return AlertTriangle
      default: return Activity
    }
  }

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="mb-10"
    >
      <div className="flex items-center justify-between mb-4">
        <h2 className="section-header">Site Journey</h2>
        <div className="flex items-center gap-3">
          {Object.entries(journey.event_counts || {}).slice(0, 4).map(([type, count]) => (
            <span key={type} className="text-[11px] text-apple-tertiary">
              {type.replace('_', ' ')}: <span className="font-medium text-apple-secondary">{count}</span>
            </span>
          ))}
        </div>
      </div>
      
      <div className="card-elevated p-6 max-h-[400px] overflow-y-auto scrollbar-minimal">
        <div className="space-y-0">
          {journey.events.slice(0, 15).map((event, i) => {
            const Icon = getEventIcon(event.event_type)
            return (
              <div key={i} className="timeline-event">
                <div className={`timeline-dot ${getSeverityDot(event.severity)}`} />
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Icon className="w-3.5 h-3.5 text-apple-tertiary flex-shrink-0" />
                      <p className="text-body text-apple-text font-medium truncate">{event.title}</p>
                    </div>
                    {event.description && (
                      <p className="text-caption text-apple-secondary mt-1 ml-5">{event.description}</p>
                    )}
                  </div>
                  <span className="text-[11px] text-apple-muted font-mono flex-shrink-0">{formatDate(event.date)}</span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
      
      <p className="text-[10px] text-apple-muted font-mono mt-3 text-center">
        Sources: {journey.data_sources?.join(', ') || 'N/A'}
      </p>
    </motion.section>
  )
}

export default SiteDossier
