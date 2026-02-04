import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, TrendingUp, TrendingDown, Minus, MessageSquare, MapPin, AlertTriangle, Shield, DollarSign, Send, Loader2, Calendar, UserCheck } from 'lucide-react'
import { useStore } from '../lib/store'
import { getSiteDetail, getSiteBriefs } from '../lib/api'

const TREND_MAP = {
  improving: { icon: TrendingUp, color: 'text-green-600', label: 'improving' },
  stable: { icon: Minus, color: 'text-neutral-400', label: 'stable' },
  deteriorating: { icon: TrendingDown, color: 'text-red-500', label: 'deteriorating' },
}

export function SiteDossier() {
  const navigate = useNavigate()
  const { siteId, studyId } = useParams()
  const { setInvestigation, siteNameMap, currentStudyId } = useStore()

  const [siteDetail, setSiteDetail] = useState(null)
  const [briefs, setBriefs] = useState([])
  const [loading, setLoading] = useState(true)
  const [askInput, setAskInput] = useState('')

  const effectiveStudyId = studyId || currentStudyId

  useEffect(() => {
    if (!siteId) return
    let cancelled = false
    async function fetchAll() {
      const [detailR, briefsR] = await Promise.allSettled([
        getSiteDetail(siteId),
        getSiteBriefs(siteId, 5),
      ])
      if (cancelled) return
      if (detailR.status === 'fulfilled') setSiteDetail(detailR.value)
      if (briefsR.status === 'fulfilled' && Array.isArray(briefsR.value)) setBriefs(briefsR.value)
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
        <header className="sticky top-0 z-50 glass border-b border-apple-border">
          <div className="px-6 py-4 flex items-center gap-4">
            <button 
              onClick={() => navigate(`/study/${effectiveStudyId}`)}
              className="flex items-center gap-2 text-apple-secondary hover:text-apple-text transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back</span>
            </button>
          </div>
        </header>
        <div className="flex items-center justify-center h-64">
          <div className="flex items-center gap-3 text-apple-secondary">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span className="text-body">Loading Site Dossier...</span>
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

  const healthColor = healthScore == null ? 'text-neutral-400'
    : healthScore >= 70 ? 'text-green-600'
    : healthScore >= 40 ? 'text-amber-600'
    : 'text-red-500'

  const healthBg = healthScore == null ? 'bg-neutral-100'
    : healthScore >= 70 ? 'bg-green-50 border-green-200'
    : healthScore >= 40 ? 'bg-amber-50 border-amber-200'
    : 'bg-red-50 border-red-200'

  return (
    <div className="min-h-screen bg-apple-bg">
      <header className="sticky top-0 z-50 glass border-b border-apple-border">
        <div className="px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => navigate(`/study/${effectiveStudyId}`)}
              className="flex items-center gap-2 text-apple-secondary hover:text-apple-text transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <img src="/saama_logo.svg" alt="Saama" className="h-6" />
            </button>
            <div className="w-px h-5 bg-apple-border" />
            <span className="text-body font-medium text-apple-text">{siteName}</span>
            <span className="text-caption text-apple-secondary">{detail.country || ''}{detail.city ? ` · ${detail.city}` : ''}</span>
          </div>
          <div className={`px-3 py-1.5 rounded-lg ${healthBg}`}>
            <span className={`text-sm font-semibold ${healthColor}`}>
              DQ Score: {healthScore != null ? healthScore : '--'}
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        {/* Site Hero Card */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-6 bg-apple-surface border border-apple-border rounded-2xl mb-8"
        >
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-medium text-apple-text">{siteName}</h1>
              <div className="flex items-center gap-3 mt-2 text-caption text-apple-secondary">
                <span className="flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5" />
                  {detail.country || 'Unknown'}{detail.city ? ` · ${detail.city}` : ''}
                </span>
                <span className="text-apple-secondary/30">|</span>
                <span>Enrollment: {enrollmentPct.toFixed(0)}%</span>
                <span className="text-apple-secondary/30">|</span>
                <span className={`flex items-center gap-1 ${trend.color}`}>
                  <trend.icon className="w-3 h-3" /> {trend.label}
                </span>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Intelligence Brief */}
        {latestBrief && (
          <motion.section
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8"
          >
            <h3 className="text-[12px] font-medium text-neutral-400 uppercase tracking-wide mb-3">Intelligence Brief</h3>
            <div className="p-5 bg-purple-50/30 border border-purple-200/40 rounded-2xl">
              <p className="text-[15px] text-neutral-800 leading-relaxed">
                {typeof latestBrief.risk_summary === 'string' 
                  ? latestBrief.risk_summary 
                  : latestBrief.risk_summary?.headline || 'No summary available'}
              </p>
              {latestBrief.risk_summary?.key_risks?.length > 0 && (
                <div className="mt-3 space-y-2">
                  {latestBrief.risk_summary.key_risks.map((risk, i) => (
                    <div key={i} className={`text-[13px] p-2 rounded ${risk.severity === 'critical' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'}`}>
                      <span className="font-medium">{risk.risk}:</span> {risk.evidence}
                    </div>
                  ))}
                </div>
              )}
              {latestBrief.vendor_accountability?.cro_issues?.length > 0 && (
                <div className="text-[13px] text-neutral-500 mt-3 leading-relaxed">
                  <span className="font-medium text-neutral-700">Vendor Issues:</span>
                  <ul className="list-disc list-inside mt-1">
                    {latestBrief.vendor_accountability.cro_issues.map((issue, i) => (
                      <li key={i}>{issue}</li>
                    ))}
                  </ul>
                </div>
              )}
              {latestBrief.cross_domain_correlations?.length > 0 && (
                <div className="mt-3 space-y-2">
                  {latestBrief.cross_domain_correlations.map((corr, i) => (
                    <div key={i} className="text-[12px] text-neutral-600">
                      <span className="font-medium">{corr.agents_involved?.join(', ')}:</span> {corr.finding}
                      {corr.causal_chain && (
                        <div className="flex flex-wrap items-center gap-1 mt-1">
                          {corr.causal_chain.split(/\s*(?:\u2192|->)\s*/).filter(Boolean).map((node, j, arr) => (
                            <span key={j} className="flex items-center gap-1">
                              <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-[10px] font-medium rounded-full">{node.trim()}</span>
                              {j < arr.length - 1 && <span className="text-purple-300">\u2192</span>}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {latestBrief.recommended_actions?.length > 0 && (
                <div className="mt-4 pt-3 border-t border-purple-200/30">
                  <p className="text-[11px] font-medium text-neutral-500 mb-1.5">Recommended Actions</p>
                  {latestBrief.recommended_actions.map((a, i) => (
                    <div key={i} className="text-[12px] text-neutral-600 mb-2">
                      <span className="font-medium">{i + 1}. {typeof a === 'string' ? a : a.action}</span>
                      {a.owner && <span className="text-neutral-400 ml-2">({a.owner})</span>}
                    </div>
                  ))}
                </div>
              )}
              
              {/* Data Provenance for Intelligence Brief */}
              <div className="mt-4 pt-3 border-t border-purple-200/30">
                <p className="text-[10px] font-mono text-neutral-400 flex items-center gap-2">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>
                    Generated by: {latestBrief.agent || 'proactive_briefing_agent'} | 
                    Sources: site_financial_metrics, queries, enrollment_progress, ecrf_entries | 
                    Updated: {latestBrief.created_at ? new Date(latestBrief.created_at).toLocaleString() : 'Recently'}
                  </span>
                </p>
              </div>
            </div>
          </motion.section>
        )}

        {/* Performance Metrics */}
        {(detail.enrollment_percent !== undefined || detail.dq_score !== undefined) && (
          <motion.section
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="mb-8"
          >
            <h3 className="text-xs font-medium text-apple-secondary uppercase tracking-wide mb-3">Performance Metrics</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <MetricCard 
                label="Enrollment" 
                value={`${enrollmentPct.toFixed(0)}%`} 
                trend={enrollmentPct >= 80 ? 'good' : enrollmentPct >= 50 ? 'neutral' : 'warn'} 
                provenance={enrollmentMetric?.note || `Target: ${detail.enrollment_metrics?.find(m => m.label === 'Randomized')?.note || 'N/A'}`}
              />
              <MetricCard 
                label="DQ Score" 
                value={healthScore != null ? `${healthScore}` : '--'} 
                trend={healthScore == null ? 'neutral' : healthScore >= 70 ? 'good' : healthScore >= 40 ? 'neutral' : 'warn'} 
                provenance={dqMetric?.note || 'Formula: 100 - (open_queries × 5)'}
              />
              <MetricCard 
                label="Open Queries" 
                value={openQueriesMetric?.value || '0'} 
                trend={parseInt(openQueriesMetric?.value || '0') <= 5 ? 'good' : parseInt(openQueriesMetric?.value || '0') <= 15 ? 'neutral' : 'warn'} 
                provenance={openQueriesMetric?.note || 'Source: queries table'}
              />
              <MetricCard 
                label="Entry Lag" 
                value={entryLagMetric?.value || '--'} 
                trend={(entryLagMetric?.value || '--') === '--' ? 'neutral' : parseFloat(entryLagMetric?.value) <= 3 ? 'good' : parseFloat(entryLagMetric?.value) <= 7 ? 'neutral' : 'warn'} 
                provenance={entryLagMetric?.note || 'Source: ecrf_entries table'}
              />
            </div>
          </motion.section>
        )}

        {/* Site Journey Timeline */}
        <SiteJourneyTimeline 
          visits={detail.monitoring_visits} 
          craAssignments={detail.cra_assignments} 
        />

        {/* AI Summary */}
        {detail.ai_summary && (
          <motion.section
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mb-8"
          >
            <h3 className="text-[12px] font-medium text-neutral-400 uppercase tracking-wide mb-3">AI Assessment</h3>
            <div className="p-4 bg-apple-surface border border-apple-border rounded-xl">
              <p className="text-caption text-apple-text leading-relaxed">{detail.ai_summary}</p>
            </div>
          </motion.section>
        )}

        {/* Ask About This Site */}
        <motion.section
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-10 border-t border-neutral-100 pt-6"
        >
          <div className="flex items-center gap-2 mb-3">
            <MessageSquare className="w-4 h-4 text-neutral-400" />
            <span className="text-[12px] font-medium text-neutral-500 uppercase tracking-wide">Ask About This Site</span>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="text"
              value={askInput}
              onChange={(e) => setAskInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
              placeholder={`Ask a question about ${siteName}...`}
              className="flex-1 bg-neutral-50 border border-neutral-200 rounded-xl px-4 py-3 text-[14px] text-neutral-900 placeholder:text-neutral-400 outline-none focus:border-neutral-400 transition-colors"
            />
            {askInput.trim() && (
              <button
                onClick={handleAsk}
                className="px-4 py-3 bg-neutral-900 text-white rounded-xl text-[14px] font-medium hover:bg-neutral-800 transition-colors"
              >
                Investigate
              </button>
            )}
          </div>
        </motion.section>
      </main>
    </div>
  )
}

function MetricCard({ label, value, trend, provenance }) {
  const trendStyles = {
    good: { text: 'text-emerald-600', bg: 'bg-emerald-50', dot: 'bg-emerald-500' },
    neutral: { text: 'text-amber-600', bg: 'bg-amber-50', dot: 'bg-amber-500' },
    warn: { text: 'text-red-600', bg: 'bg-red-50', dot: 'bg-red-500' },
  }
  const style = trendStyles[trend] || { text: 'text-apple-text', bg: 'bg-apple-surface', dot: 'bg-apple-secondary' }
  
  return (
    <div className={`p-4 ${style.bg} border border-apple-border rounded-xl relative overflow-hidden`}>
      <div className={`absolute top-3 right-3 w-2 h-2 rounded-full ${style.dot}`} />
      <p className="text-caption text-apple-secondary mb-1">{label}</p>
      <span className={`text-xl font-semibold ${style.text}`}>
        {value}
      </span>
      {provenance && (
        <p className="text-[11px] text-neutral-500 mt-2 font-mono leading-relaxed border-t border-neutral-200/50 pt-2">
          {provenance}
        </p>
      )}
    </div>
  )
}

function SiteJourneyTimeline({ visits, craAssignments }) {
  const events = []
  
  if (craAssignments && Array.isArray(craAssignments)) {
    craAssignments.forEach(cra => {
      if (cra.start_date) {
        events.push({
          type: 'cra_start',
          date: cra.start_date,
          label: cra.cra_id,
          isCurrent: cra.is_current,
          details: cra.is_current ? 'Current' : 'Previous'
        })
      }
    })
  }
  
  if (visits && Array.isArray(visits)) {
    visits.forEach(visit => {
      const isMissed = visit.status === 'Missed'
      const eventDate = visit.visit_date || visit.planned_date
      if (eventDate) {
        events.push({
          type: isMissed ? 'missed_visit' : 'visit',
          date: eventDate,
          label: isMissed ? 'Missed' : (visit.visit_type || 'Visit'),
          visitType: visit.visit_type,
          findings: visit.findings_count || 0,
          critical: visit.critical_findings || 0,
          daysOverdue: visit.days_overdue || 0,
          isMissed
        })
      }
    })
  }
  
  const sortedEvents = events.sort((a, b) => new Date(a.date) - new Date(b.date))
  const missedEvents = sortedEvents.filter(e => e.type === 'missed_visit')
  const otherEvents = sortedEvents.filter(e => e.type !== 'missed_visit')
  const recentOthers = otherEvents.slice(-(6 - missedEvents.length))
  const allEvents = [...missedEvents, ...recentOthers].sort((a, b) => new Date(a.date) - new Date(b.date))

  if (allEvents.length === 0) return null

  const formatDate = (dateStr) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15 }}
      className="mb-8"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-neutral-400" />
          <h3 className="text-xs font-medium text-apple-secondary uppercase tracking-wide">Site Journey</h3>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-neutral-900" />
            <span className="text-[10px] text-neutral-400">CRA</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-neutral-400" />
            <span className="text-[10px] text-neutral-400">Visit</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full border-2 border-red-500 border-dashed" />
            <span className="text-[10px] text-neutral-400">Missed</span>
          </div>
        </div>
      </div>
      
      <div className="relative px-4 py-2 bg-neutral-50 rounded-xl">
        <div className="absolute left-4 right-4 top-[26px] h-px bg-neutral-200" />
        
        <div className="flex justify-between items-start relative">
          {allEvents.map((event, i) => {
            const isCRA = event.type === 'cra_start'
            const isMissedVisit = event.type === 'missed_visit'
            const hasCritical = event.critical > 0
            const hasFindings = event.findings > 0
            
            let markerStyle = 'bg-neutral-300 border-neutral-200'
            let useDashed = false
            
            if (isCRA) {
              markerStyle = event.isCurrent ? 'bg-neutral-900 border-neutral-900' : 'bg-neutral-500 border-neutral-500'
            } else if (isMissedVisit) {
              markerStyle = 'bg-white border-red-500'
              useDashed = true
            } else {
              markerStyle = 'bg-white border-neutral-300'
            }
            
            return (
              <div
                key={i}
                className="flex flex-col items-center group"
                style={{ flex: 1 }}
              >
                <div className="relative mb-2">
                  <div 
                    className={`w-3 h-3 rounded-full border-2 ${markerStyle}`}
                    style={useDashed ? { borderStyle: 'dashed' } : {}}
                  >
                    {isCRA && <UserCheck className="w-1.5 h-1.5 text-white absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />}
                  </div>
                  {hasCritical && <div className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-red-500" />}
                  {!hasCritical && hasFindings && <div className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-amber-500" />}
                </div>
                
                <div className="text-center max-w-[80px]">
                  <p className={`text-[10px] font-medium leading-tight truncate ${isMissedVisit ? 'text-red-600' : 'text-neutral-700'}`}>
                    {isCRA ? event.label : event.label}
                  </p>
                  <p className="text-[9px] text-neutral-400 mt-0.5">{formatDate(event.date)}</p>
                  {isCRA && event.details && (
                    <span className={`inline-block mt-0.5 text-[8px] px-1 py-0.5 rounded-full ${event.isCurrent ? 'bg-neutral-100 text-neutral-600' : 'bg-neutral-50 text-neutral-400'}`}>
                      {event.details}
                    </span>
                  )}
                  {isMissedVisit && (
                    <span className="inline-block mt-0.5 text-[8px] px-1 py-0.5 rounded-full bg-red-50 text-red-600">
                      {event.daysOverdue}d late
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
        
        <p className="text-[9px] text-neutral-400 mt-3 font-mono text-center border-t border-neutral-200 pt-2">
          Source: cra_assignments, monitoring_visits tables
        </p>
      </div>
    </motion.section>
  )
}
