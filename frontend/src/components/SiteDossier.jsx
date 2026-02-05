import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, ArrowRight, TrendingUp, TrendingDown, Minus, MapPin, AlertTriangle, Loader2, Calendar, UserCheck, Clock, Activity, ChevronRight, ChevronDown, Bot, Sparkles, Database, GitBranch, Gauge, Search, HelpCircle, Users, Edit3, Filter, DollarSign, PieChart, BarChart2, AlertCircle, Flag, BarChart, Grid, Briefcase, EyeOff, GitCommit, RotateCw, Globe, CheckCircle2, XCircle, Info } from 'lucide-react'
import { useStore } from '../lib/store'
import { getSiteDetail, getSiteBriefs, getSiteJourney } from '../lib/api'
import FloatingAssistant from './FloatingAssistant'

const TREND_MAP = {
  improving: { icon: TrendingUp, color: 'text-apple-success', bgColor: 'bg-apple-success/10', label: 'Improving' },
  stable: { icon: Minus, color: 'text-apple-grey-500', bgColor: 'bg-apple-grey-100', label: 'Stable' },
  deteriorating: { icon: TrendingDown, color: 'text-apple-critical', bgColor: 'bg-apple-critical/10', label: 'At Risk' },
}

const STEP_ICON_MAP = {
  'clock': Clock,
  'help-circle': HelpCircle,
  'calendar': Calendar,
  'users': Users,
  'edit-3': Edit3,
  'filter': Filter,
  'trending-up': TrendingUp,
  'alert-triangle': AlertTriangle,
  'map-pin': MapPin,
  'globe': Globe,
  'dollar-sign': DollarSign,
  'pie-chart': PieChart,
  'activity': Activity,
  'bar-chart-2': BarChart2,
  'alert-circle': AlertCircle,
  'flag': Flag,
  'bar-chart': BarChart,
  'grid': Grid,
  'briefcase': Briefcase,
  'eye-off': EyeOff,
  'git-commit': GitCommit,
  'rotate-cw': RotateCw,
  'search': Search,
  'database': Database,
}

export function SiteDossier() {
  const navigate = useNavigate()
  const { siteId, studyId } = useParams()
  const { setInvestigation, siteNameMap, currentStudyId } = useStore()

  const [siteDetail, setSiteDetail] = useState(null)
  const [briefs, setBriefs] = useState([])
  const [journey, setJourney] = useState(null)
  const [loading, setLoading] = useState(true)
  const [expandedRisks, setExpandedRisks] = useState({})
  const [expandedSignals, setExpandedSignals] = useState({})
  const [showInvestigationTrail, setShowInvestigationTrail] = useState(false)

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
                    <div key={i} className="rounded-xl bg-apple-grey-50/50 overflow-hidden">
                      <button
                        onClick={() => setExpandedSignals(prev => ({ ...prev, [i]: !prev[i] }))}
                        className="w-full p-3 text-left"
                      >
                        <div className="flex items-start gap-3">
                          <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                            alert.severity === 'critical' ? 'bg-red-500' : 
                            alert.severity === 'warning' ? 'bg-amber-500' : 'bg-apple-grey-400'
                          }`} />
                          <div className="flex-1 min-w-0">
                            <p className="text-[13px] text-apple-text font-medium leading-relaxed">{alert.message}</p>
                            <p className="text-[10px] text-apple-muted font-mono mt-1.5">{alert.time}</p>
                          </div>
                          <ChevronDown className={`w-4 h-4 text-apple-tertiary transition-transform flex-shrink-0 ${expandedSignals[i] ? 'rotate-180' : ''}`} />
                        </div>
                      </button>
                      
                      {/* Expandable Reasoning */}
                      {expandedSignals[i] && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          className="px-3 pb-3 border-t border-apple-grey-100/50"
                        >
                          <div className="pt-3 space-y-2.5">
                            {/* Agent - only show if data exists */}
                            {alert.agent && (
                              <div className="flex items-center gap-2">
                                <Bot className="w-3 h-3 text-apple-tertiary" />
                                <span className="text-[9px] font-medium text-apple-muted uppercase">Agent</span>
                                <span className="text-[10px] font-mono text-apple-text bg-white px-1.5 py-0.5 rounded border border-apple-grey-100">
                                  {alert.agent}
                                </span>
                              </div>
                            )}
                            
                            {/* Reasoning - only show if data exists */}
                            {alert.reasoning ? (
                              <div className="flex items-start gap-2">
                                <Sparkles className="w-3 h-3 text-apple-tertiary mt-0.5" />
                                <div className="flex-1">
                                  <span className="text-[9px] font-medium text-apple-muted uppercase">Reasoning</span>
                                  <p className="text-[10px] text-apple-secondary mt-0.5 leading-relaxed">
                                    {alert.reasoning}
                                  </p>
                                </div>
                              </div>
                            ) : null}
                            
                            {/* Causal Reasoning Chain - step-by-step plain English */}
                            {alert.causal_chain_explained && alert.causal_chain_explained.length > 0 && (
                              <div className="mt-2 pt-2 border-t border-apple-grey-100">
                                <span className="text-[9px] font-medium text-apple-muted uppercase flex items-center gap-1 mb-2">
                                  <ArrowRight className="w-3 h-3" />
                                  Causal Reasoning Chain
                                </span>
                                <div className="space-y-2">
                                  {alert.causal_chain_explained.map((step, stepIdx) => (
                                    <div key={stepIdx} className={`flex items-start gap-2 p-1.5 rounded ${step.grounded === false ? 'bg-amber-50/50 border-l-2 border-amber-300' : ''}`}>
                                      <div className={`flex-shrink-0 w-4 h-4 rounded-full flex items-center justify-center text-[8px] font-medium mt-0.5 ${
                                        step.grounded === true ? 'bg-emerald-100 text-emerald-600' : 
                                        step.grounded === false ? 'bg-amber-100 text-amber-600' : 
                                        'bg-apple-grey-100 text-apple-tertiary'
                                      }`}>
                                        {step.grounded === true ? <CheckCircle2 className="w-3 h-3" /> : 
                                         step.grounded === false ? <Info className="w-3 h-3" /> : 
                                         stepIdx + 1}
                                      </div>
                                      <div className="flex-1">
                                        <div className="flex items-center gap-1.5 flex-wrap">
                                          <span className="text-[10px] font-medium text-apple-secondary">{step.step}</span>
                                          {step.grounding_type === 'inference' && (
                                            <span className="text-[8px] px-1 py-0.5 rounded bg-purple-100 text-purple-600 font-medium">INFERENCE</span>
                                          )}
                                          {step.grounding_type === 'unverified' && (
                                            <span className="text-[8px] px-1 py-0.5 rounded bg-amber-100 text-amber-700 font-medium">UNVERIFIED</span>
                                          )}
                                          {step.grounded === true && (
                                            <span className="text-[8px] px-1 py-0.5 rounded bg-emerald-100 text-emerald-600 font-medium">VERIFIED</span>
                                          )}
                                          {step.confidence != null && (
                                            <span className={`text-[8px] px-1 py-0.5 rounded font-medium ${
                                              step.confidence >= 0.8 ? 'bg-emerald-50 text-emerald-600' :
                                              step.confidence >= 0.5 ? 'bg-amber-50 text-amber-600' :
                                              'bg-red-50 text-red-600'
                                            }`}>
                                              {Math.round(step.confidence * 100)}%
                                            </span>
                                          )}
                                        </div>
                                        <p className="text-[10px] text-apple-tertiary leading-relaxed">{step.explanation}</p>
                                        {step.data_source?.tool && (
                                          <div className="flex items-center gap-1 mt-0.5">
                                            <Database className="w-2.5 h-2.5 text-apple-muted" />
                                            <span className="text-[8px] font-mono text-apple-muted">{step.data_source.tool}</span>
                                            {step.data_source.row_count !== undefined && (
                                              <span className="text-[8px] text-apple-muted">({step.data_source.row_count} rows)</span>
                                            )}
                                          </div>
                                        )}
                                        {step.grounding_issue && (
                                          <p className="text-[8px] text-amber-600 mt-0.5 flex items-center gap-1">
                                            <AlertTriangle className="w-2.5 h-2.5" />
                                            {step.grounding_issue}
                                          </p>
                                        )}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            
                            {/* Data Source - only show if data exists */}
                            {alert.data_source && (
                              <div className="flex items-center gap-2">
                                <Database className="w-3 h-3 text-apple-tertiary" />
                                <span className="text-[9px] font-medium text-apple-muted uppercase">Source</span>
                                <span className="text-[10px] font-mono text-apple-tertiary bg-white px-1.5 py-0.5 rounded border border-apple-grey-100">
                                  {alert.data_source}
                                </span>
                              </div>
                            )}
                            
                            {/* Empty state if no reasoning data */}
                            {!alert.agent && !alert.reasoning && !alert.data_source && (
                              <p className="text-[10px] text-apple-muted italic">Detailed reasoning not available for this signal.</p>
                            )}
                          </div>
                        </motion.div>
                      )}
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
                
                {/* Expandable Investigation Trail */}
                <button
                  onClick={() => setShowInvestigationTrail(!showInvestigationTrail)}
                  className="mt-4 flex items-center gap-2 text-[11px] text-apple-tertiary hover:text-apple-text transition-colors"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span className="font-medium">View Investigation Trail</span>
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showInvestigationTrail ? 'rotate-180' : ''}`} />
                </button>
                
                {showInvestigationTrail && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    className="mt-4 pt-4 border-t border-apple-grey-100"
                  >
                    {/* Multi-Agent Collaboration */}
                    <div className="mb-4">
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-apple-muted">Contributing Agents</span>
                      {latestBrief.contributing_agents?.length > 0 ? (
                        <div className="flex flex-wrap gap-2 mt-2">
                          {latestBrief.contributing_agents.map((agent, i) => (
                            <div key={i} className="flex items-center gap-2 bg-apple-grey-50 px-3 py-1.5 rounded-lg border border-apple-grey-100">
                              <Bot className="w-3.5 h-3.5 text-apple-tertiary" />
                              <div>
                                <span className="text-[10px] font-mono text-apple-text">{agent.name}</span>
                                {agent.role && <span className="text-[9px] text-apple-muted ml-2">{agent.role}</span>}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : latestBrief.agent ? (
                        <div className="mt-2 flex items-center gap-2 bg-apple-grey-50 px-3 py-1.5 rounded-lg border border-apple-grey-100">
                          <Bot className="w-3.5 h-3.5 text-apple-tertiary" />
                          <span className="text-[10px] font-mono text-apple-text">{latestBrief.agent}</span>
                        </div>
                      ) : (
                        <p className="mt-2 text-[10px] text-apple-muted italic">Agent attribution not available.</p>
                      )}
                    </div>
                    
                    {/* Investigation Timeline */}
                    <div>
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-apple-muted">Investigation Steps</span>
                      {latestBrief.investigation_steps?.length > 0 ? (
                        <div className="mt-2 flex items-center gap-2 overflow-x-auto pb-2">
                          {latestBrief.investigation_steps.map((step, i, arr) => {
                            const IconComponent = STEP_ICON_MAP[step.icon] || Search
                            return (
                              <div key={i} className="flex items-center gap-2 flex-shrink-0">
                                <div className="flex flex-col items-center">
                                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${step.success === false ? 'bg-amber-50' : 'bg-apple-grey-100'}`}>
                                    <IconComponent className={`w-4 h-4 ${step.success === false ? 'text-amber-500' : 'text-apple-secondary'}`} />
                                  </div>
                                  <span className="text-[9px] text-apple-secondary mt-1 text-center max-w-[80px] leading-tight line-clamp-2">{step.step}</span>
                                  {step.tool && <code className="text-[8px] text-apple-muted mt-0.5">{step.tool}</code>}
                                </div>
                                {i < arr.length - 1 && (
                                  <ChevronRight className="w-3 h-3 text-apple-grey-300" />
                                )}
                              </div>
                            )
                          })}
                        </div>
                      ) : (
                        <p className="mt-2 text-[10px] text-apple-muted italic">Detailed investigation steps not available for this brief.</p>
                      )}
                    </div>
                  </motion.div>
                )}
              </div>

              {/* Key Risks */}
              {latestBrief.risk_summary?.key_risks?.length > 0 && (
                <div className="p-6 border-b border-apple-grey-100">
                  <h3 className="text-[10px] font-semibold uppercase tracking-wider text-apple-muted mb-4">Key Risks</h3>
                  <div className="space-y-3">
                    {latestBrief.risk_summary.key_risks.map((risk, i) => (
                      <div key={i} className={`rounded-xl overflow-hidden ${
                        risk.severity === 'critical' 
                          ? 'bg-gradient-to-r from-red-50 to-red-50/30 border border-red-100' 
                          : 'bg-gradient-to-r from-amber-50 to-amber-50/30 border border-amber-100'
                      }`}>
                        <button
                          onClick={() => setExpandedRisks(prev => ({ ...prev, [i]: !prev[i] }))}
                          className="w-full p-4 text-left"
                        >
                          <div className="flex items-start gap-3">
                            <div className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${
                              risk.severity === 'critical' ? 'bg-red-500' : 'bg-amber-500'
                            }`} />
                            <div className="flex-1">
                              <span className="text-[13px] font-semibold text-apple-text">{risk.risk}</span>
                              <p className="text-[12px] text-apple-secondary mt-1 leading-relaxed">{risk.evidence}</p>
                            </div>
                            <ChevronDown className={`w-4 h-4 text-apple-tertiary transition-transform ${expandedRisks[i] ? 'rotate-180' : ''}`} />
                          </div>
                        </button>
                        
                        {/* Expandable Reasoning Section */}
                        {expandedRisks[i] && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="px-4 pb-4 border-t border-apple-grey-100/50"
                          >
                            <div className="pt-4 space-y-3">
                              {/* Agent Attribution - only show if data exists */}
                              {(risk.agent || latestBrief.agent) && (
                                <div className="flex items-center gap-2">
                                  <Bot className="w-3.5 h-3.5 text-apple-tertiary" />
                                  <span className="text-[10px] font-medium text-apple-muted uppercase tracking-wider">Detected by</span>
                                  <span className="text-[11px] font-mono text-apple-text bg-apple-grey-100 px-2 py-0.5 rounded">
                                    {risk.agent || latestBrief.agent}
                                  </span>
                                </div>
                              )}
                              
                              {/* Investigation Steps - only show if data exists */}
                              {risk.reasoning_steps?.length > 0 ? (
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2">
                                    <GitBranch className="w-3.5 h-3.5 text-apple-tertiary" />
                                    <span className="text-[10px] font-medium text-apple-muted uppercase tracking-wider">Investigation Steps</span>
                                  </div>
                                  <div className="ml-5 space-y-1.5">
                                    {risk.reasoning_steps.map((step, j) => (
                                      <div key={j} className="flex items-center gap-2 text-[11px]">
                                        <span className="w-4 h-4 rounded bg-apple-grey-100 text-[9px] font-semibold text-apple-tertiary flex items-center justify-center">{j + 1}</span>
                                        <span className="text-apple-secondary">{step.step}</span>
                                        {step.tool && <code className="text-[9px] text-apple-muted bg-apple-grey-50 px-1.5 py-0.5 rounded">{step.tool}</code>}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              ) : (
                                <div className="flex items-center gap-2">
                                  <GitBranch className="w-3.5 h-3.5 text-apple-tertiary" />
                                  <span className="text-[10px] text-apple-muted italic">Investigation steps not recorded for this finding.</span>
                                </div>
                              )}
                              
                              {/* Causal Reasoning Chain */}
                              {risk.causal_chain_explained?.length > 0 && (
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2">
                                    <ArrowRight className="w-3.5 h-3.5 text-apple-tertiary" />
                                    <span className="text-[10px] font-medium text-apple-muted uppercase tracking-wider">Causal Reasoning Chain</span>
                                  </div>
                                  <div className="ml-5 space-y-2">
                                    {risk.causal_chain_explained.map((item, j) => (
                                      <div key={j} className={`flex items-start gap-2 p-2 rounded-lg ${item.grounded === false ? 'bg-amber-50/50 border-l-2 border-amber-300' : 'bg-apple-grey-50'}`}>
                                        <span className={`w-5 h-5 rounded-full text-[10px] font-semibold flex items-center justify-center flex-shrink-0 mt-0.5 ${
                                          item.grounded === true ? 'bg-emerald-100 text-emerald-600' :
                                          item.grounded === false ? 'bg-amber-100 text-amber-600' :
                                          'bg-apple-grey-100 text-apple-tertiary'
                                        }`}>
                                          {item.grounded === true ? <CheckCircle2 className="w-3 h-3" /> :
                                           item.grounded === false ? <Info className="w-3 h-3" /> :
                                           j + 1}
                                        </span>
                                        <div className="flex-1">
                                          <div className="flex items-center gap-2 flex-wrap">
                                            <span className="text-[11px] font-semibold text-apple-text">{item.step}</span>
                                            {item.grounding_type === 'inference' && (
                                              <span className="text-[8px] px-1.5 py-0.5 rounded bg-purple-100 text-purple-600 font-medium">INFERENCE</span>
                                            )}
                                            {item.grounding_type === 'unverified' && (
                                              <span className="text-[8px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-medium">UNVERIFIED</span>
                                            )}
                                            {item.grounded === true && (
                                              <span className="text-[8px] px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-600 font-medium">DATA VERIFIED</span>
                                            )}
                                            {item.confidence != null && (
                                              <span className={`text-[8px] px-1.5 py-0.5 rounded font-medium ${
                                                item.confidence >= 0.8 ? 'bg-emerald-50 text-emerald-600' :
                                                item.confidence >= 0.5 ? 'bg-amber-50 text-amber-600' :
                                                'bg-red-50 text-red-600'
                                              }`}>
                                                {Math.round(item.confidence * 100)}% conf
                                              </span>
                                            )}
                                          </div>
                                          <p className="text-[11px] text-apple-secondary leading-relaxed mt-0.5">{item.explanation}</p>
                                          {item.data_source?.tool && (
                                            <div className="flex items-center gap-1.5 mt-1">
                                              <Database className="w-3 h-3 text-apple-muted" />
                                              <span className="text-[9px] font-mono text-apple-muted bg-white px-1.5 py-0.5 rounded border border-apple-grey-100">{item.data_source.tool}</span>
                                              {item.data_source.metric && (
                                                <span className="text-[9px] text-apple-muted">{item.data_source.metric}</span>
                                              )}
                                              {item.data_source.row_count !== undefined && item.data_source.row_count > 0 && (
                                                <span className="text-[9px] text-apple-muted">({item.data_source.row_count} rows)</span>
                                              )}
                                            </div>
                                          )}
                                          {item.grounding_issue && (
                                            <p className="text-[9px] text-amber-600 mt-1 flex items-center gap-1">
                                              <AlertTriangle className="w-3 h-3" />
                                              {item.grounding_issue}
                                            </p>
                                          )}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                              
                              {/* Evidence Sources - only show if data exists */}
                              {risk.data_sources?.length > 0 && (
                                <div className="flex items-start gap-2">
                                  <Database className="w-3.5 h-3.5 text-apple-tertiary mt-0.5" />
                                  <div>
                                    <span className="text-[10px] font-medium text-apple-muted uppercase tracking-wider">Data Sources</span>
                                    <div className="flex flex-wrap gap-1.5 mt-1">
                                      {risk.data_sources.map((src, j) => (
                                        <span key={j} className="text-[10px] font-mono text-apple-tertiary bg-apple-grey-50 px-2 py-0.5 rounded border border-apple-grey-100">
                                          {src}
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                </div>
                              )}
                              
                              {/* Confidence - only show if data exists */}
                              {risk.confidence != null && (
                                <div className="flex items-center gap-2">
                                  <Gauge className="w-3.5 h-3.5 text-apple-tertiary" />
                                  <span className="text-[10px] font-medium text-apple-muted uppercase tracking-wider">Confidence</span>
                                  <div className="flex items-center gap-1.5">
                                    <div className="w-16 h-1.5 bg-apple-grey-100 rounded-full overflow-hidden">
                                      <div 
                                        className={`h-full rounded-full ${
                                          risk.confidence >= 0.8 ? 'bg-emerald-500' : 
                                          risk.confidence >= 0.6 ? 'bg-amber-500' : 'bg-red-500'
                                        }`}
                                        style={{ width: `${risk.confidence * 100}%` }}
                                      />
                                    </div>
                                    <span className="text-[10px] font-semibold text-apple-text">{Math.round(risk.confidence * 100)}%</span>
                                  </div>
                                </div>
                              )}
                              
                              {/* Show message if no reasoning data available */}
                              {!risk.agent && !latestBrief.agent && !risk.reasoning_steps?.length && !risk.data_sources?.length && risk.confidence == null && (
                                <p className="text-[10px] text-apple-muted italic">Detailed reasoning not available for this finding.</p>
                              )}
                            </div>
                          </motion.div>
                        )}
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
                  {latestBrief.agent && <>Generated by {latestBrief.agent} · </>}Updated {latestBrief.created_at ? new Date(latestBrief.created_at).toLocaleString() : 'recently'}
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
