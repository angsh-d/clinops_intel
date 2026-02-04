import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ChevronRight, TrendingUp, TrendingDown, Minus, Command, RefreshCw } from 'lucide-react'
import { useStore } from '../lib/store'
import { getStudySummary, getIntelligenceSummary, getAlerts, triggerScan, getScans, getSitesOverview } from '../lib/api'

const SEVERITY_COLORS = {
  critical: { dot: 'bg-red-500', border: 'border-red-200', bg: 'bg-red-50/50' },
  high: { dot: 'bg-amber-500', border: 'border-amber-200', bg: 'bg-amber-50/50' },
  warning: { dot: 'bg-yellow-500', border: 'border-yellow-200', bg: 'bg-yellow-50/50' },
  info: { dot: 'bg-blue-400', border: 'border-blue-200', bg: 'bg-blue-50/50' },
}

const TREND_ICONS = {
  improving: { icon: TrendingUp, color: 'text-green-600', arrow: '\u2197' },
  stable: { icon: Minus, color: 'text-neutral-400', arrow: '\u2192' },
  deteriorating: { icon: TrendingDown, color: 'text-red-500', arrow: '\u2198' },
}

export function MorningBrief() {
  const navigate = useNavigate()
  const { studyId: urlStudyId } = useParams()
  const { setInvestigation, toggleCommand, setStudyData, setCurrentStudyId, setSiteNameMap, currentStudyId } = useStore()
  const studyId = urlStudyId || currentStudyId
  const [intelligence, setIntelligence] = useState(null)
  const [studyInfo, setStudyInfo] = useState(null)
  const [alerts, setAlertsData] = useState(null)
  const [latestScan, setLatestScan] = useState(null)
  const [sitesOverview, setSitesOverview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function fetchAll() {
      const [summaryR, intelR, alertsR, scansR, sitesR] = await Promise.allSettled([
        getStudySummary(),
        getIntelligenceSummary(),
        getAlerts({ limit: 50 }),
        getScans(1),
        getSitesOverview(),
      ])
      if (cancelled) return

      if (summaryR.status === 'fulfilled' && summaryR.value) {
        const s = summaryR.value
        setStudyInfo(s)
        setCurrentStudyId(s.study_id || 'STUDY-001')
        setStudyData({
          enrolled: s.enrolled, target: s.target, studyName: s.study_name,
          studyId: s.study_id, phase: s.phase, totalSites: s.total_sites,
          activeSites: s.active_sites, countries: s.countries,
          lastUpdated: s.last_updated,
        })
      }
      if (intelR.status === 'fulfilled') setIntelligence(intelR.value)
      if (alertsR.status === 'fulfilled') setAlertsData(alertsR.value)
      if (scansR.status === 'fulfilled' && Array.isArray(scansR.value) && scansR.value.length > 0) {
        setLatestScan(scansR.value[0])
      }
      if (sitesR.status === 'fulfilled' && sitesR.value?.sites) {
        setSitesOverview(sitesR.value)
        const nameMap = {}
        for (const s of sitesR.value.sites) {
          if (s.site_name) nameMap[s.site_id] = s.site_name
        }
        setSiteNameMap(nameMap)
      }
      setLoading(false)
    }
    fetchAll()
    return () => { cancelled = true }
  }, [])

  const handleScan = async () => {
    setScanning(true)
    try {
      await triggerScan('api')
    } catch (error) {
      console.error('Scan trigger error:', error)
    } finally {
      setScanning(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-apple-bg flex items-center justify-center">
        <div className="flex items-center gap-3 text-apple-secondary">
          <div className="w-5 h-5 border-2 border-apple-secondary/30 border-t-apple-secondary rounded-full animate-spin" />
          <span className="text-body">Loading Morning Brief...</span>
        </div>
      </div>
    )
  }

  const enrolled = studyInfo?.enrolled || 0
  const target = studyInfo?.target || 0
  const themes = intelligence?.themes?.filter(t => t.finding_count > 0) || []
  const siteBriefs = intelligence?.site_briefs || []
  const allSites = sitesOverview?.sites || []
  const healthyCount = allSites.filter(s => s.status === 'healthy').length
  const warningCount = allSites.filter(s => s.status === 'warning').length
  const criticalCount = allSites.filter(s => s.status === 'critical').length

  // Build signal cards from highest-severity themes + site briefs
  const signalCards = []
  // Add critical/high site briefs as signal cards
  for (const brief of siteBriefs) {
    if (brief.risk_level === 'critical' || brief.risk_level === 'high') {
      signalCards.push({
        type: 'brief',
        severity: brief.risk_level,
        siteId: brief.site_id,
        headline: brief.headline || brief.risk_summary?.slice(0, 120),
        riskSummary: brief.risk_summary,
        vendorAccountability: brief.vendor_accountability,
        crossDomain: brief.cross_domain_correlations,
        recommendedActions: brief.recommended_actions,
        trend: brief.trend_indicator,
        causalChain: brief.cross_domain_correlations?.[0]?.causal_chain,
      })
    }
  }
  // Limit to top 5
  const topSignals = signalCards.slice(0, 5)

  // Time since last scan
  let scanLabel = 'No recent scans'
  if (latestScan?.created_at) {
    const delta = Date.now() - new Date(latestScan.created_at).getTime()
    const hours = Math.floor(delta / 3_600_000)
    const days = Math.floor(delta / 86_400_000)
    if (days > 0) scanLabel = `Scanned ${days}d ago`
    else if (hours > 0) scanLabel = `Scanned ${hours}h ago`
    else scanLabel = 'Scanned just now'
  }

  return (
    <div className="min-h-screen bg-apple-bg">
      {/* Header */}
      <header className="sticky top-0 z-50 glass border-b border-apple-border">
        <div className="px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/saama_logo.svg" alt="Saama" className="h-6" />
            <div className="w-px h-5 bg-apple-border" />
            <span className="text-body font-medium text-apple-text">Morning Brief</span>
          </div>
          <div className="flex items-center gap-4 text-caption">
            <span className="text-apple-secondary">{studyInfo?.study_id} · {studyInfo?.phase} · {enrolled}/{target} enrolled</span>
            <span className="text-apple-secondary/50">|</span>
            <span className="text-apple-secondary">{scanLabel}</span>
            <button
              onClick={handleScan}
              disabled={scanning}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-apple-surface border border-apple-border rounded-lg text-caption text-apple-secondary hover:text-apple-text transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-3 h-3 ${scanning ? 'animate-spin' : ''}`} />
              {scanning ? 'Scanning...' : 'Run Scan'}
            </button>
            <button
              onClick={() => navigate(`/study/${studyId}/overview`)}
              className="px-3 py-1.5 text-caption text-apple-secondary hover:text-apple-text hover:bg-apple-surface rounded-lg transition-all"
            >
              Study Overview
            </button>
            <button
              onClick={toggleCommand}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-apple-surface border border-apple-border rounded-lg text-caption text-apple-secondary hover:text-apple-text transition-all"
            >
              <Command className="w-3 h-3" />
              <span>K</span>
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-10">
        {/* Signal Cards */}
        {topSignals.length > 0 ? (
          <div className="space-y-4 mb-10">
            {topSignals.map((signal, i) => (
              <SignalCard
                key={`${signal.siteId}-${i}`}
                signal={signal}
                index={i}
                onInvestigate={(query) => setInvestigation({ question: query, status: 'routing' })}
                onViewSite={(siteId) => navigate(`/study/${studyId}/sites/${siteId}`)}
              />
            ))}
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-16 mb-10"
          >
            <div className="w-12 h-12 rounded-full bg-green-50 flex items-center justify-center mx-auto mb-4">
              <TrendingUp className="w-5 h-5 text-green-600" />
            </div>
            <p className="text-[17px] font-medium text-neutral-900">All Clear</p>
            <p className="text-[14px] text-neutral-500 mt-1">No critical signals detected. Run a scan to check for updates.</p>
          </motion.div>
        )}

        {/* Quiet Zones */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="mb-10"
        >
          <div className="flex items-center gap-3 text-caption text-apple-secondary">
            <span className="w-8 h-px bg-apple-border flex-shrink-0" />
            <span>
              <button onClick={() => navigate(`/study/${studyId}/sites`)} className="hover:text-apple-text transition-colors">
                <strong className="text-apple-text">{healthyCount}</strong> within parameters
              </button>
              {' · '}
              <button onClick={() => navigate(`/study/${studyId}/signals`)} className="hover:text-apple-text transition-colors">
                <strong className="text-apple-text">{warningCount}</strong> monitored
              </button>
              {' · '}
              <button onClick={() => navigate(`/study/${studyId}/signals`)} className="hover:text-apple-text transition-colors">
                <strong className="text-apple-critical">{criticalCount}</strong> need attention
              </button>
            </span>
            <span className="flex-1 h-px bg-apple-border" />
          </div>
        </motion.div>

        {/* Study Pulse Sparklines */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="mb-10"
        >
          <h3 className="text-[12px] font-medium text-neutral-400 uppercase tracking-wide mb-4">Study Pulse</h3>
          <div className="grid grid-cols-2 gap-4">
            <PulseMetric label="Enrollment" value={`${enrolled}/${target}`} trend={enrolled / target > 0.6 ? 'up' : 'down'} />
            <PulseMetric label="DQ Score" value={intelligence?.total_findings ? `${intelligence.total_findings} findings` : '--'} trend="neutral" />
            <PulseMetric label="Open Alerts" value={alerts?.total ? `${alerts.total}` : '0'} trend={alerts?.total > 10 ? 'down' : 'up'} />
            <PulseMetric label="Sites Flagged" value={`${criticalCount + warningCount}`} trend={criticalCount > 3 ? 'down' : 'up'} />
          </div>
        </motion.div>

        {/* Quick Nav */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="flex items-center gap-3 justify-center"
        >
          {[
            { label: 'Sites', path: `/study/${studyId}/sites` },
            { label: 'Signals', path: `/study/${studyId}/signals` },
            { label: 'Vendors', path: `/study/${studyId}/vendors` },
            { label: 'Financials', path: `/study/${studyId}/financials` },
            { label: 'Directives', path: `/study/${studyId}/directives` },
          ].map(item => (
            <button
              key={item.label}
              onClick={() => navigate(item.path)}
              className="px-4 py-2 text-caption text-apple-secondary hover:text-apple-text bg-apple-surface border border-apple-border rounded-lg hover:border-apple-text/20 transition-all"
            >
              {item.label}
            </button>
          ))}
        </motion.div>
      </main>
    </div>
  )
}


function SignalCard({ signal, index, onInvestigate, onViewSite }) {
  const { siteNameMap } = useStore()
  const sev = SEVERITY_COLORS[signal.severity] || SEVERITY_COLORS.info
  const trend = TREND_ICONS[signal.trend] || TREND_ICONS.stable
  const siteName = siteNameMap[signal.siteId] || signal.siteId

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.4 }}
      className={`rounded-2xl border ${sev.border} ${sev.bg} p-6 relative overflow-hidden`}
    >
      {/* Severity dot */}
      <div className="flex items-center gap-2.5 mb-3">
        <div className={`w-2.5 h-2.5 rounded-full ${sev.dot}`} />
        <span className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider">{signal.severity}</span>
        <span className={`text-[12px] ${trend.color} ml-auto`}>{trend.arrow}</span>
      </div>

      {/* Headline */}
      <p className="text-[15px] font-medium text-neutral-900 leading-relaxed mb-3">
        {signal.headline}
      </p>

      {/* Causal chain */}
      {signal.causalChain && (
        <div className="flex flex-wrap items-center gap-1.5 mb-4">
          {signal.causalChain.split(/\s*(?:\u2192|->)\s*/).filter(Boolean).map((node, i, arr) => (
            <div key={i} className="flex items-center gap-1.5">
              <span className="px-2.5 py-1 bg-purple-50 text-purple-700 text-[11px] font-medium rounded-full border border-purple-200/60">
                {node.trim()}
              </span>
              {i < arr.length - 1 && <ChevronRight className="w-3 h-3 text-purple-300" />}
            </div>
          ))}
        </div>
      )}

      {/* Site + vendor tags */}
      <div className="flex items-center gap-2 mb-4">
        <button
          onClick={() => onViewSite(signal.siteId)}
          className="text-[11px] font-mono px-2 py-1 bg-apple-surface border border-apple-border rounded text-apple-text hover:border-apple-text/30 transition-colors"
        >
          {siteName}
        </button>
        {signal.vendorAccountability && (
          <span className="text-[11px] text-apple-secondary">{signal.vendorAccountability.slice(0, 60)}</span>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => onInvestigate(`Investigate ${siteName}: ${signal.headline}`)}
          className="px-4 py-2 bg-neutral-900 text-white text-[13px] font-medium rounded-xl hover:bg-neutral-800 transition-colors"
        >
          Investigate
        </button>
        <button
          onClick={() => onViewSite(signal.siteId)}
          className="px-4 py-2 text-[13px] text-neutral-600 hover:text-neutral-900 transition-colors"
        >
          View Site
        </button>
      </div>
    </motion.div>
  )
}


function PulseMetric({ label, value, trend }) {
  const trendColor = trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-500' : 'text-neutral-400'
  const trendArrow = trend === 'up' ? '\u2197' : trend === 'down' ? '\u2198' : '\u2192'

  return (
    <div className="flex items-center justify-between p-3 bg-apple-surface rounded-xl border border-apple-border">
      <div>
        <p className="text-[11px] text-neutral-400 uppercase tracking-wide">{label}</p>
        <p className="text-[15px] font-mono font-medium text-neutral-900 mt-0.5">{value}</p>
      </div>
      <span className={`text-[18px] ${trendColor}`}>{trendArrow}</span>
    </div>
  )
}
