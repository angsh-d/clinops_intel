import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, TrendingUp, TrendingDown, Minus, MapPin, AlertTriangle, Loader2, Calendar, UserCheck, Clock, Activity, ChevronRight } from 'lucide-react'
import { useStore } from '../lib/store'
import { getSiteDetail, getSiteBriefs, getSiteJourney } from '../lib/api'
import FloatingAssistant from './FloatingAssistant'

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

        {/* Two Column Layout: Active Alerts + Site Journey */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1, ease: [0.25, 0.46, 0.45, 0.94] }}
          className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10"
        >
          {/* Active Alerts - Left Column */}
          <div>
            <h2 className="text-[11px] font-semibold uppercase tracking-wider text-apple-tertiary mb-4">Active Signals</h2>
            <div className="bg-white rounded-2xl shadow-sm border border-apple-grey-100 h-[360px] overflow-hidden flex flex-col">
              {detail.alerts?.length > 0 ? (
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {detail.alerts.slice(0, 5).map((alert, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 rounded-xl bg-apple-grey-50/50">
                      <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                        alert.severity === 'critical' ? 'bg-red-500' : 
                        alert.severity === 'warning' ? 'bg-amber-500' : 'bg-apple-grey-400'
                      }`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-[13px] text-apple-text font-medium leading-relaxed">{alert.message}</p>
                        <p className="text-[10px] text-apple-muted font-mono mt-1.5">{alert.time}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center text-apple-tertiary">
                  <p className="text-[13px]">No active signals</p>
                </div>
              )}
            </div>
          </div>

          {/* Site Journey - Right Column */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-[11px] font-semibold uppercase tracking-wider text-apple-tertiary">Site Journey</h2>
              <div className="flex items-center gap-3">
                {journey?.event_counts && Object.entries(journey.event_counts).slice(0, 3).map(([type, count]) => (
                  <span key={type} className="text-[9px] text-apple-muted">
                    {type.replace('_', ' ')}: <span className="font-semibold text-apple-tertiary">{count}</span>
                  </span>
                ))}
              </div>
            </div>
            <div className="bg-white rounded-2xl shadow-sm border border-apple-grey-100 h-[360px] overflow-hidden">
              {journey?.events?.length > 0 ? (
                <div className="h-full overflow-y-auto p-4">
                  <div className="relative">
                    <div className="absolute left-[5px] top-2 bottom-2 w-px bg-apple-grey-200" />
                    <div className="space-y-3">
                      {(detail.alerts?.length > 0 
                        ? journey.events.filter(e => e.event_type !== 'alert') 
                        : journey.events
                      ).slice(0, 12).map((event, i) => (
                        <div key={i} className="relative flex items-start gap-3 pl-5">
                          <div className={`absolute left-0 top-1 w-[10px] h-[10px] rounded-full border-2 border-white shadow-sm ${
                            event.severity === 'critical' ? 'bg-red-500' :
                            event.severity === 'warning' ? 'bg-amber-500' :
                            event.severity === 'success' ? 'bg-emerald-500' : 'bg-apple-grey-400'
                          }`} />
                          <div className="flex-1 min-w-0">
                            <p className="text-[12px] text-apple-text font-medium leading-snug">{event.title}</p>
                            {event.description && (
                              <p className="text-[10px] text-apple-secondary mt-0.5 leading-relaxed">{event.description}</p>
                            )}
                          </div>
                          <span className="text-[9px] text-apple-muted font-mono flex-shrink-0">
                            {new Date(event.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="h-full flex items-center justify-center text-apple-tertiary">
                  <p className="text-[13px]">No journey events</p>
                </div>
              )}
            </div>
          </div>
        </motion.div>

        {/* Intelligence Brief - Full Width Below */}
        {latestBrief && (
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.15, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="mb-10"
          >
            <h2 className="text-[11px] font-semibold uppercase tracking-wider text-apple-tertiary mb-4">Intelligence Brief</h2>
            <div className="bg-white rounded-2xl shadow-sm border border-apple-grey-100 overflow-hidden">
              {/* Header Summary */}
              <div className="p-6 bg-gradient-to-b from-apple-grey-50/50 to-white border-b border-apple-grey-100">
                <p className="text-[16px] text-apple-text leading-relaxed font-medium">
                  {typeof latestBrief.risk_summary === 'string' 
                    ? latestBrief.risk_summary 
                    : latestBrief.risk_summary?.headline || 'No summary available'}
                </p>
              </div>

              {/* Key Risks */}
              {latestBrief.risk_summary?.key_risks?.length > 0 && (
                <div className="p-6 border-b border-apple-grey-100">
                  <h3 className="text-[10px] font-semibold uppercase tracking-wider text-apple-muted mb-4">Key Risks</h3>
                  <div className="space-y-3">
                    {latestBrief.risk_summary.key_risks.map((risk, i) => (
                      <div key={i} className={`p-4 rounded-xl ${
                        risk.severity === 'critical' 
                          ? 'bg-gradient-to-r from-red-50 to-red-50/30 border border-red-100' 
                          : 'bg-gradient-to-r from-amber-50 to-amber-50/30 border border-amber-100'
                      }`}>
                        <div className="flex items-start gap-3">
                          <div className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${
                            risk.severity === 'critical' ? 'bg-red-500' : 'bg-amber-500'
                          }`} />
                          <div>
                            <span className="text-[13px] font-semibold text-apple-text">{risk.risk}</span>
                            <p className="text-[12px] text-apple-secondary mt-1 leading-relaxed">{risk.evidence}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Two Column: Vendor Issues + Recommended Actions */}
              <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-apple-grey-100">
                {/* Vendor Issues */}
                <div className="p-6">
                  <h3 className="text-[10px] font-semibold uppercase tracking-wider text-apple-muted mb-4">Vendor Issues</h3>
                  {latestBrief.vendor_accountability?.cro_issues?.length > 0 ? (
                    <div className="space-y-3">
                      {latestBrief.vendor_accountability.cro_issues.map((issue, i) => (
                        <div key={i} className="flex items-start gap-3 p-3 bg-apple-grey-50/50 rounded-lg">
                          <AlertTriangle className="w-4 h-4 text-apple-tertiary mt-0.5 flex-shrink-0" />
                          <span className="text-[12px] text-apple-secondary leading-relaxed">{issue}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-[12px] text-apple-muted italic">No vendor issues identified</p>
                  )}
                </div>

                {/* Recommended Actions */}
                <div className="p-6">
                  <h3 className="text-[10px] font-semibold uppercase tracking-wider text-apple-muted mb-4">Recommended Actions</h3>
                  {latestBrief.recommended_actions?.length > 0 ? (
                    <div className="space-y-3">
                      {latestBrief.recommended_actions.map((a, i) => (
                        <div key={i} className="flex items-start gap-3">
                          <span className="w-6 h-6 rounded-lg bg-apple-grey-800 text-[11px] font-semibold text-white flex items-center justify-center flex-shrink-0">
                            {i + 1}
                          </span>
                          <div className="flex-1 pt-0.5">
                            <p className="text-[12px] text-apple-text leading-relaxed">{typeof a === 'string' ? a : a.action}</p>
                            {a.owner && (
                              <span className="inline-block mt-1.5 text-[10px] text-apple-muted bg-apple-grey-100 px-2 py-0.5 rounded-full">
                                {a.owner}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-[12px] text-apple-muted italic">No actions recommended</p>
                  )}
                </div>
              </div>
              
              {/* Provenance Footer */}
              <div className="px-6 py-3 bg-apple-grey-50/50 border-t border-apple-grey-100">
                <p className="text-[10px] font-mono text-apple-muted">
                  Generated by {latestBrief.agent || 'proactive_briefing_agent'} · Updated {latestBrief.created_at ? new Date(latestBrief.created_at).toLocaleString() : 'recently'}
                </p>
              </div>
            </div>
          </motion.section>
        )}
      </main>

      {/* Floating AI Assistant */}
      <FloatingAssistant siteName={siteName} siteId={siteId} />
    </div>
  )
}

function MetricCard({ label, value, suffix = '', status = 'neutral', note }) {
  const statusStyles = {
    success: 'from-emerald-500 to-emerald-400',
    warning: 'from-amber-500 to-amber-400', 
    neutral: 'from-apple-grey-400 to-apple-grey-300'
  }
  
  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-apple-grey-100 hover:shadow-md transition-shadow duration-200">
      <div className="flex items-start justify-between mb-3">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-apple-tertiary">{label}</p>
        <div className={`w-2 h-2 rounded-full bg-gradient-to-br ${statusStyles[status]}`} />
      </div>
      <p className="text-[36px] font-light text-apple-text tracking-tight leading-none">
        {value}
        {suffix && <span className="text-xl text-apple-secondary font-normal">{suffix}</span>}
      </p>
      {note && (
        <p className="text-[10px] text-apple-muted mt-3 leading-relaxed font-mono">
          {note}
        </p>
      )}
    </div>
  )
}

function SiteJourneyTimeline({ journey, excludeAlerts = false }) {
  if (!journey || !journey.events || journey.events.length === 0) return null
  
  const filteredEvents = excludeAlerts 
    ? journey.events.filter(e => e.event_type !== 'alert')
    : journey.events
  
  if (filteredEvents.length === 0) return null

  const formatDate = (dateStr) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const getSeverityStyles = (severity) => {
    switch (severity) {
      case 'critical': return 'bg-red-500'
      case 'warning': return 'bg-amber-500'
      case 'success': return 'bg-emerald-500'
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
        <h2 className="text-[11px] font-semibold uppercase tracking-wider text-apple-tertiary">Site Journey</h2>
        <div className="flex items-center gap-4">
          {Object.entries(journey.event_counts || {}).slice(0, 4).map(([type, count]) => (
            <span key={type} className="text-[10px] text-apple-muted">
              {type.replace('_', ' ')}: <span className="font-semibold text-apple-tertiary">{count}</span>
            </span>
          ))}
        </div>
      </div>
      
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-apple-grey-100 max-h-[420px] overflow-y-auto">
        <div className="relative">
          <div className="absolute left-[7px] top-3 bottom-3 w-px bg-apple-grey-200" />
          <div className="space-y-4">
            {filteredEvents.slice(0, 15).map((event, i) => {
              const Icon = getEventIcon(event.event_type)
              return (
                <div key={i} className="relative flex items-start gap-4 pl-6">
                  <div className={`absolute left-0 top-1.5 w-[14px] h-[14px] rounded-full border-2 border-white ${getSeverityStyles(event.severity)} shadow-sm`} />
                  <div className="flex-1 min-w-0 py-0.5">
                    <div className="flex items-center gap-2">
                      <Icon className="w-3.5 h-3.5 text-apple-tertiary flex-shrink-0" />
                      <p className="text-[13px] text-apple-text font-medium">{event.title}</p>
                    </div>
                    {event.description && (
                      <p className="text-[11px] text-apple-secondary mt-1 ml-5 leading-relaxed">{event.description}</p>
                    )}
                  </div>
                  <span className="text-[10px] text-apple-muted font-mono flex-shrink-0 mt-0.5">{formatDate(event.date)}</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>
      
      <p className="text-[9px] text-apple-muted font-mono mt-3 text-center uppercase tracking-wider">
        Data sources: {journey.data_sources?.join(' · ') || 'N/A'}
      </p>
    </motion.section>
  )
}

export default SiteDossier
