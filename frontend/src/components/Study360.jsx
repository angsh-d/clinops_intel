import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Users, Database, DollarSign, BarChart3, Command, MapPin, ArrowRight, ArrowLeft, Shield, TrendingDown, Globe, Search, Clock } from 'lucide-react'
import { useStore } from '../lib/store'
import {
  getStudySummary,
  getEnrollmentDashboard,
  getDataQualityDashboard,
  getFinancialSummary,
  getVendorScorecards,
  getAttentionSites,
  getSitesOverview,
  getIntelligenceSummary,
  getThemeFindings,
} from '../lib/api'
import { WorldMap } from './WorldMap'
import { StudyNav } from './StudyNav'

const THEME_ICON_MAP = {
  'shield': Shield,
  'trending-down': TrendingDown,
  'dollar-sign': DollarSign,
  'bar-chart': BarChart3,
  'globe': Globe,
}

export function Study360() {
  const navigate = useNavigate()
  const { currentStudyId, toggleCommand, studyData, setStudyData, openCommandWithQuery, activeTheme, setActiveTheme, clearActiveTheme } = useStore()
  const basePath = `/study/${currentStudyId}`

  const [enrollment, setEnrollment] = useState(null)
  const [dataQuality, setDataQuality] = useState(null)
  const [financial, setFinancial] = useState(null)
  const [vendors, setVendors] = useState(null)
  const [sites, setSites] = useState([])
  const [intelligence, setIntelligence] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function fetchAll() {
      const [summaryR, enrollR, dqR, finR, vendR, attnR, sitesR, intelR] = await Promise.allSettled([
        getStudySummary(),
        getEnrollmentDashboard(),
        getDataQualityDashboard(),
        getFinancialSummary(),
        getVendorScorecards(),
        getAttentionSites(),
        getSitesOverview(),
        getIntelligenceSummary(),
      ])
      if (cancelled) return

      const summaryData = summaryR.status === 'fulfilled' ? summaryR.value : null
      if (summaryData) {
        setStudyData({
          enrolled: summaryData.enrolled,
          target: summaryData.target,
          studyName: summaryData.study_name,
          studyId: summaryData.study_id,
          phase: summaryData.phase,
          pctEnrolled: summaryData.pct_enrolled,
          totalSites: summaryData.total_sites,
          activeSites: summaryData.active_sites,
          countries: summaryData.countries,
          lastUpdated: summaryData.last_updated,
        })
      }

      if (enrollR.status === 'fulfilled') setEnrollment(enrollR.value)
      if (dqR.status === 'fulfilled') setDataQuality(dqR.value)
      if (finR.status === 'fulfilled') setFinancial(finR.value)
      if (vendR.status === 'fulfilled') setVendors(vendR.value)
      if (sitesR.status === 'fulfilled' && sitesR.value?.sites) setSites(sitesR.value.sites)
      if (intelR.status === 'fulfilled') setIntelligence(intelR.value)
      setLoading(false)
    }
    fetchAll()
    return () => { cancelled = true }
  }, [])

  const mapSites = useMemo(() => sites.map(s => ({
    id: s.site_id,
    name: s.site_name,
    country: s.country,
    status: s.status || 'healthy',
    enrollmentPercent: s.enrollment_percent || 0,
  })), [sites])

  if (loading) {
    return (
      <div className="min-h-screen bg-apple-bg flex items-center justify-center">
        <div className="flex items-center gap-3 text-apple-secondary">
          <div className="w-5 h-5 border-2 border-apple-secondary/30 border-t-apple-secondary rounded-full animate-spin" />
          <span className="text-body">Loading Study Overview...</span>
        </div>
      </div>
    )
  }

  // ── Derive KPIs ──────────────────────────────────────────────────────────

  const enrolled = studyData.enrolled || 0
  const target = studyData.target || 1
  const pctEnrolled = target > 0 ? (enrolled / target) * 100 : 0

  // Enrollment card
  const studyScreened = enrollment?.study_total_screened || 0
  const studyRandomized = enrollment?.study_total_randomized || 0
  const screenFailureRate = studyScreened > 0 ? ((studyScreened - studyRandomized) / studyScreened) * 100 : 0

  // Data quality card
  const meanLag = dataQuality?.study_mean_entry_lag ?? null
  const totalQueries = dataQuality?.study_total_queries ?? null
  const sitesWithAging = dataQuality?.sites
    ? dataQuality.sites.filter(s => (s.aging_over_14d || 0) > 0).length
    : null
  const totalDQSites = dataQuality?.sites?.length || 0

  // Financial card
  const totalBudget = financial?.total_budget || 0
  const spentToDate = financial?.spent_to_date || 0
  const budgetUtilization = totalBudget > 0 ? (spentToDate / totalBudget) * 100 : 0
  const variancePct = financial?.variance_pct ?? null
  const burnRate = financial?.burn_rate ?? null

  // Vendor card
  const vendorList = vendors?.vendors || []
  const vendorCount = vendorList.length
  const ragCounts = { Red: 0, Amber: 0, Green: 0 }
  let openIssues = 0
  vendorList.forEach(v => {
    const rag = v.overall_rag || 'Green'
    ragCounts[rag] = (ragCounts[rag] || 0) + 1
    openIssues += v.issue_count || 0
  })

  // ── Health indicators ────────────────────────────────────────────────────

  function enrollmentHealth() {
    if (pctEnrolled >= 60) return 'green'
    if (pctEnrolled >= 40) return 'amber'
    return 'red'
  }

  function dqHealth() {
    const agingPct = totalDQSites > 0 ? ((sitesWithAging || 0) / totalDQSites) * 100 : 0
    const lagOk = meanLag == null || meanLag <= 3
    const lagWarn = meanLag == null || meanLag <= 5
    if (lagOk && agingPct < 10) return 'green'
    if (lagWarn && agingPct < 25) return 'amber'
    return 'red'
  }

  function financialHealth() {
    if (variancePct == null) return 'green'
    const abs = Math.abs(variancePct)
    if (abs <= 3) return 'green'
    if (abs <= 8) return 'amber'
    return 'red'
  }

  function vendorHealth() {
    if (ragCounts.Red > 0) return 'red'
    const amberPct = vendorCount > 0 ? (ragCounts.Amber / vendorCount) * 100 : 0
    if (amberPct > 25) return 'amber'
    return 'green'
  }

  const cards = [
    {
      title: 'Enrollment',
      icon: Users,
      health: enrollmentHealth(),
      onClick: () => navigate(`${basePath}/sites`),
      rows: [
        { label: 'Enrolled / Target', value: `${enrolled} / ${target}`, bar: pctEnrolled },
        { label: '% of Target', value: `${pctEnrolled.toFixed(1)}%` },
        { label: 'Screen Failure Rate', value: `${screenFailureRate.toFixed(1)}%` },
      ],
    },
    {
      title: 'Data Quality',
      icon: Database,
      health: dqHealth(),
      onClick: () => navigate(`${basePath}/sites`),
      rows: [
        { label: 'Mean Entry Lag', value: meanLag != null ? `${meanLag.toFixed(1)}d` : '\u2014' },
        { label: 'Total Queries', value: totalQueries != null ? totalQueries.toLocaleString() : '\u2014' },
        { label: 'Sites w/ Aging >14d', value: sitesWithAging != null ? `${sitesWithAging}` : '\u2014' },
      ],
    },
    {
      title: 'Financial',
      icon: DollarSign,
      health: financialHealth(),
      onClick: () => navigate(`${basePath}/financials`),
      rows: [
        { label: 'Budget Utilization', value: `${budgetUtilization.toFixed(0)}%`, bar: budgetUtilization },
        { label: 'Variance', value: variancePct != null ? `${variancePct > 0 ? '+' : ''}${variancePct.toFixed(1)}%` : '\u2014' },
        { label: 'Burn Rate', value: burnRate != null ? formatCurrencyShort(burnRate) : '\u2014' },
      ],
    },
    {
      title: 'Vendor',
      icon: BarChart3,
      health: vendorHealth(),
      onClick: () => navigate(`${basePath}/vendors`),
      rows: [
        { label: 'Vendors', value: `${vendorCount}` },
        { label: 'RAG Distribution', ragCounts, rag: true },
        { label: 'Open Issues', value: `${openIssues}`, warn: openIssues > 0 },
      ],
    },
  ]

  return (
    <div className="min-h-screen bg-apple-bg flex flex-col">
      <StudyNav active="overview" />

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-10">
        <h2 className="text-2xl font-light text-apple-text mb-8">Study Health Overview</h2>

        {/* 4-card row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-5 mb-8">
          {cards.map((card, i) => (
            <motion.div
              key={card.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
            >
              <DomainCard card={card} />
            </motion.div>
          ))}
        </div>

        {/* Agentic Intelligence Panel */}
        {intelligence && !activeTheme && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35 }}
          >
            <AgenticIntelligencePanel
              data={intelligence}
              onThemeClick={(theme) => setActiveTheme(theme)}
              onSiteClick={(siteId) => openCommandWithQuery(`Investigate risk profile for ${siteId}`)}
            />
          </motion.div>
        )}

        {/* Theme Findings Drill-Down */}
        {activeTheme && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <ThemeFindings
              theme={activeTheme}
              onBack={() => clearActiveTheme()}
              onInvestigate={(query) => openCommandWithQuery(query)}
            />
          </motion.div>
        )}

        {/* Site Map */}
        {mapSites.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.45 }}
            className="mt-8"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-light text-apple-text">Site Footprint</h2>
              <button
                onClick={() => navigate(`${basePath}/sites`)}
                className="flex items-center gap-1.5 text-caption text-apple-secondary hover:text-apple-text transition-colors"
              >
                <span>Open Site Map</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <WorldMap
              sites={mapSites}
              onSiteClick={() => navigate(`${basePath}/sites`)}
              height="h-[360px]"
            />
          </motion.div>
        )}
      </main>
    </div>
  )
}


/* ── Agentic Intelligence Panel ─────────────────────────────────────────── */

function AgenticIntelligencePanel({ data, onThemeClick, onSiteClick }) {
  const trendArrow = { improving: '\u2191', stable: '\u2192', deteriorating: '\u2193' }
  const trendColor = {
    improving: 'text-apple-success',
    stable: 'text-apple-secondary',
    deteriorating: 'text-apple-critical',
  }
  const riskColor = {
    critical: 'bg-apple-critical/10 border-apple-critical/30 text-apple-critical',
    high: 'bg-apple-warning/10 border-apple-warning/30 text-apple-warning',
    medium: 'bg-apple-secondary/10 border-apple-border text-apple-secondary',
    low: 'bg-apple-success/10 border-apple-success/30 text-apple-success',
    unknown: 'bg-apple-secondary/10 border-apple-border text-apple-secondary',
  }

  // Time ago for latest scan
  let latestLabel = null
  if (data.latest_scan_timestamp) {
    const delta = Date.now() - new Date(data.latest_scan_timestamp).getTime()
    const hours = Math.floor(delta / 3_600_000)
    const days = Math.floor(delta / 86_400_000)
    if (days > 0) latestLabel = `${days}d ago`
    else if (hours > 0) latestLabel = `${hours}h ago`
    else latestLabel = 'Just now'
  }

  return (
    <div className="card relative overflow-hidden">
      {/* Purple accent line */}
      <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#5856D6] to-[#AF52DE] rounded-l-2xl" />

      {/* Header + Stats */}
      <div className="px-6 pt-5 pb-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-medium text-apple-text">Agentic Intelligence</h3>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-caption">
          <StatPill label={`${data.total_findings} findings`} />
          <span className="text-apple-secondary/30">|</span>
          <StatPill label={`${data.critical_count} critical`} severe={data.critical_count > 0} />
          <span className="text-apple-secondary/30">|</span>
          <StatPill label={`${data.high_count} high`} warn={data.high_count > 0} />
          <span className="text-apple-secondary/30">|</span>
          <StatPill label={`${data.sites_flagged} sites flagged`} />
          <span className="text-apple-secondary/30">|</span>
          <StatPill label={`${data.open_alerts} open alerts`} />
          {latestLabel && (
            <>
              <span className="text-apple-secondary/30">|</span>
              <StatPill label={`Latest: ${latestLabel}`} />
            </>
          )}
        </div>
      </div>

      {/* Theme Clusters */}
      <div className="px-6 pb-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {data.themes.filter(t => t.finding_count > 0).map(theme => {
            const Icon = THEME_ICON_MAP[theme.icon] || Shield
            const sevDot = theme.severity === 'critical' ? 'bg-apple-critical' : theme.severity === 'high' ? 'bg-apple-warning' : 'bg-apple-secondary/40'

            return (
              <button
                key={theme.theme_id}
                onClick={() => onThemeClick({ themeId: theme.theme_id, label: theme.label, icon: theme.icon, query: theme.investigation_query })}
                className="text-left p-4 rounded-xl bg-apple-bg border border-apple-border hover:border-apple-text/20 hover:shadow-apple transition-all group"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Icon className="w-4 h-4 text-apple-secondary" />
                  <span className="text-caption font-medium text-apple-text flex-1">{theme.label}</span>
                  <div className={`w-2 h-2 rounded-full ${sevDot}`} />
                  <span className="text-[11px] font-mono text-apple-secondary bg-apple-surface px-1.5 py-0.5 rounded">
                    {theme.finding_count}
                  </span>
                </div>
                {theme.top_summaries.length > 0 && (
                  <ul className="space-y-1 mb-2">
                    {theme.top_summaries.map((s, i) => (
                      <li key={i} className="text-[11px] text-apple-secondary leading-tight truncate">
                        {s}
                      </li>
                    ))}
                  </ul>
                )}
                {theme.affected_sites.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {theme.affected_sites.slice(0, 5).map(sid => (
                      <span key={sid} className="text-[10px] font-mono px-1.5 py-0.5 bg-apple-surface border border-apple-border rounded text-apple-secondary">
                        {sid}
                      </span>
                    ))}
                    {theme.affected_sites.length > 5 && (
                      <span className="text-[10px] text-apple-secondary">+{theme.affected_sites.length - 5}</span>
                    )}
                  </div>
                )}
                <ArrowRight className="w-3.5 h-3.5 text-apple-secondary/0 group-hover:text-apple-secondary transition-colors mt-2" />
              </button>
            )
          })}
        </div>
      </div>

      {/* Study-Wide Intelligence (Layer 2) */}
      {data.study_synthesis && (
        <div className="px-6 pb-4 pt-2 border-t border-apple-border">
          <p className="text-caption font-medium text-apple-text mb-2">Study-Wide Intelligence</p>
          {data.study_synthesis.executive_summary && (
            <p className="text-caption text-apple-secondary mb-3 leading-relaxed">{data.study_synthesis.executive_summary}</p>
          )}
          {data.study_synthesis.hypotheses?.length > 0 && (
            <div className="space-y-2 mb-3">
              {data.study_synthesis.hypotheses.map((h, i) => (
                <div key={i} className="p-3 rounded-xl bg-apple-bg border border-apple-border">
                  <p className="text-caption text-apple-text mb-1.5">{h.hypothesis}</p>
                  {h.causal_chain && (
                    <p className="text-[11px] font-mono text-apple-secondary mb-1.5">{h.causal_chain}</p>
                  )}
                  <div className="flex flex-wrap items-center gap-1.5">
                    {h.affected_sites?.map(sid => (
                      <span key={sid} className="text-[10px] font-mono px-1.5 py-0.5 bg-apple-surface border border-apple-border rounded text-apple-secondary">{sid}</span>
                    ))}
                    {h.agents_involved?.map(aid => (
                      <span key={aid} className="text-[10px] px-1.5 py-0.5 rounded bg-[#5856D6]/10 text-[#5856D6] border border-[#5856D6]/20">{aid}</span>
                    ))}
                    {h.confidence != null && (
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-apple-surface text-apple-secondary ml-auto">{(h.confidence * 100).toFixed(0)}%</span>
                    )}
                    {h.urgency && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded border ${
                        h.urgency === 'immediate' ? 'bg-apple-critical/10 text-apple-critical border-apple-critical/20' :
                        h.urgency === 'this_week' ? 'bg-apple-warning/10 text-apple-warning border-apple-warning/20' :
                        'bg-apple-secondary/10 text-apple-secondary border-apple-border'
                      }`}>{h.urgency}</span>
                    )}
                  </div>
                  {h.recommended_action && (
                    <p className="text-[11px] text-apple-secondary mt-1.5"><span className="font-medium text-apple-text">Action:</span> {h.recommended_action}</p>
                  )}
                </div>
              ))}
            </div>
          )}
          {data.study_synthesis.systemic_risks?.length > 0 && (
            <div className="mt-2">
              <p className="text-[11px] font-medium text-apple-text mb-1">Systemic Risks</p>
              <ul className="space-y-0.5">
                {data.study_synthesis.systemic_risks.map((r, i) => (
                  <li key={i} className="text-[11px] text-apple-secondary leading-tight pl-3 relative before:content-[''] before:absolute before:left-0 before:top-[7px] before:w-1.5 before:h-1.5 before:rounded-full before:bg-apple-critical/40">{r}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Cross-Domain Insights (Layer 1) */}
      {data.cross_domain_correlations?.length > 0 && (
        <div className="px-6 pb-4 pt-2 border-t border-apple-border">
          <p className="text-caption font-medium text-apple-text mb-2">Cross-Domain Insights</p>
          <div className="space-y-2">
            {data.cross_domain_correlations.map((corr, i) => (
              <div key={i} className="p-3 rounded-xl bg-apple-bg border border-apple-border">
                <p className="text-caption text-apple-text mb-1.5">{corr.finding}</p>
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-[10px] font-mono px-1.5 py-0.5 bg-apple-surface border border-apple-border rounded text-apple-secondary">{corr.site_id}</span>
                  {corr.agents_involved?.map(aid => (
                    <span key={aid} className="text-[10px] px-1.5 py-0.5 rounded bg-[#5856D6]/10 text-[#5856D6] border border-[#5856D6]/20">{aid}</span>
                  ))}
                  {corr.confidence != null && (
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-apple-surface text-apple-secondary ml-auto">{(corr.confidence * 100).toFixed(0)}%</span>
                  )}
                </div>
                {corr.causal_chain && (
                  <p className="text-[11px] font-mono text-apple-secondary mt-1.5">{corr.causal_chain}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Site Intelligence Strip */}
      {data.site_briefs.length > 0 && (
        <div className="px-6 pb-5 pt-2 border-t border-apple-border">
          <p className="text-caption text-apple-secondary mb-2">Site Intelligence Briefs</p>
          <div className="flex flex-wrap gap-2">
            {data.site_briefs.map(brief => (
              <button
                key={brief.site_id}
                onClick={() => onSiteClick(brief.site_id)}
                title={brief.headline || ''}
                className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg border text-[11px] font-mono transition-all hover:shadow-apple cursor-pointer ${
                  riskColor[brief.risk_level] || riskColor.unknown
                }`}
              >
                <span>{brief.site_id}</span>
                <span className={trendColor[brief.trend_indicator] || 'text-apple-secondary'}>
                  {trendArrow[brief.trend_indicator] || '\u2192'}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Theme Findings Drill-Down ────────────────────────────────────────── */

function ThemeFindings({ theme, onBack, onInvestigate }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setData(null)
    setLoading(true)
    setError(null)
    getThemeFindings(theme.themeId)
      .then(result => { if (!cancelled) setData(result) })
      .catch(err => { if (!cancelled) setError(err.message) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [theme.themeId])

  const Icon = THEME_ICON_MAP[theme.icon] || Shield

  const severityStripe = {
    critical: 'bg-apple-critical',
    high: 'bg-apple-warning',
    warning: 'bg-yellow-400',
    info: 'bg-apple-secondary/40',
  }

  const severityBadge = {
    critical: 'bg-apple-critical/10 text-apple-critical border-apple-critical/20',
    high: 'bg-apple-warning/10 text-apple-warning border-apple-warning/20',
    warning: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    info: 'bg-apple-secondary/10 text-apple-secondary border-apple-border',
  }

  function timeAgo(isoStr) {
    if (!isoStr) return null
    const delta = Date.now() - new Date(isoStr).getTime()
    const days = Math.floor(delta / 86_400_000)
    const hours = Math.floor(delta / 3_600_000)
    if (days > 0) return `${days}d ago`
    if (hours > 0) return `${hours}h ago`
    return 'Just now'
  }

  return (
    <div className="card relative overflow-hidden">
      {/* Purple accent line */}
      <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#5856D6] to-[#AF52DE] rounded-l-2xl" />

      {/* Header */}
      <div className="px-6 pt-5 pb-4">
        <div className="flex items-center gap-3 mb-3">
          <button
            onClick={onBack}
            className="p-1.5 -ml-1.5 rounded-lg hover:bg-apple-surface transition-colors"
          >
            <ArrowLeft className="w-4 h-4 text-apple-secondary" />
          </button>
          <Icon className="w-5 h-5 text-apple-secondary" />
          <h3 className="text-lg font-medium text-apple-text flex-1">{theme.label}</h3>
          <button
            onClick={() => onInvestigate(theme.query)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#5856D6]/10 border border-[#5856D6]/20 rounded-lg text-caption text-[#5856D6] hover:bg-[#5856D6]/20 transition-colors"
          >
            <Search className="w-3 h-3" />
            <span>Investigate further</span>
          </button>
        </div>

        {/* Stats bar */}
        {data && (
          <div className="flex flex-wrap items-center gap-2 text-caption">
            <StatPill label={`${data.total} findings`} />
            <span className="text-apple-secondary/30">|</span>
            <StatPill label={`${data.critical_count} critical`} severe={data.critical_count > 0} />
            <span className="text-apple-secondary/30">|</span>
            <StatPill label={`${data.high_count} high`} warn={data.high_count > 0} />
            <span className="text-apple-secondary/30">|</span>
            <StatPill label={`${data.affected_sites.length} sites`} />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="px-6 pb-5">
        {loading && (
          <div className="flex items-center gap-3 py-8 justify-center text-apple-secondary">
            <div className="w-4 h-4 border-2 border-apple-secondary/30 border-t-apple-secondary rounded-full animate-spin" />
            <span className="text-caption">Loading findings...</span>
          </div>
        )}

        {!loading && error && (
          <div className="py-8 text-center text-caption text-apple-critical">{error}</div>
        )}

        {!loading && !error && data && data.findings.length === 0 && (
          <div className="py-8 text-center text-caption text-apple-secondary">No findings for this theme</div>
        )}

        {!loading && !error && data && data.findings.length > 0 && (
          <div className="space-y-3">
            {data.findings.map(f => (
              <div
                key={f.id}
                className="relative rounded-xl bg-apple-bg border border-apple-border overflow-hidden"
              >
                {/* Severity stripe */}
                <div className={`absolute left-0 top-0 bottom-0 w-1 ${severityStripe[f.severity] || severityStripe.info}`} />

                <div className="pl-5 pr-4 py-4">
                  {/* Top row: badges */}
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <span className={`text-[11px] px-2 py-0.5 rounded-md border font-medium ${severityBadge[f.severity] || severityBadge.info}`}>
                      {f.severity}
                    </span>
                    <span className="text-[11px] px-2 py-0.5 rounded-md bg-[#5856D6]/10 text-[#5856D6] border border-[#5856D6]/20">
                      {f.agent_name}
                    </span>
                    {f.site_id && (
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-apple-surface border border-apple-border text-apple-secondary">
                        {f.site_id}
                      </span>
                    )}
                    {f.confidence != null && (
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-apple-surface text-apple-secondary ml-auto">
                        {(f.confidence * 100).toFixed(0)}% conf
                      </span>
                    )}
                    {f.created_at && (
                      <span className="text-[10px] text-apple-secondary flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {timeAgo(f.created_at)}
                      </span>
                    )}
                  </div>

                  {/* Summary */}
                  <p className="text-caption text-apple-text leading-relaxed mb-2">{f.summary}</p>

                  {/* Root cause / causal chain */}
                  {(f.root_cause || f.causal_chain) && (
                    <div className="mb-2 space-y-1">
                      {f.root_cause && (
                        <p className="text-[11px] text-apple-secondary">
                          <span className="font-medium text-apple-text">Root cause:</span> {f.root_cause}
                        </p>
                      )}
                      {f.causal_chain && (
                        <p className="text-[11px] text-apple-secondary">
                          <span className="font-medium text-apple-text">Causal chain:</span> {f.causal_chain}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Recommended action */}
                  {f.recommended_action && (
                    <div className="mt-2 px-3 py-2 bg-apple-surface rounded-lg border border-apple-border">
                      <p className="text-[11px] text-apple-secondary">
                        <span className="font-medium text-apple-text">Recommended:</span> {f.recommended_action}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Cross-Domain Hypotheses */}
            {data.cross_domain_hypotheses?.length > 0 && (
              <div className="mt-4 pt-4 border-t border-apple-border">
                <p className="text-caption font-medium text-apple-text mb-2">Cross-Domain Hypotheses</p>
                <div className="space-y-2">
                  {data.cross_domain_hypotheses.map((corr, i) => (
                    <div key={i} className="p-3 rounded-xl bg-apple-bg border border-apple-border">
                      <p className="text-caption text-apple-text mb-1.5">{corr.finding}</p>
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-[10px] font-mono px-1.5 py-0.5 bg-apple-surface border border-apple-border rounded text-apple-secondary">{corr.site_id}</span>
                        {corr.agents_involved?.map(aid => (
                          <span key={aid} className="text-[10px] px-1.5 py-0.5 rounded bg-[#5856D6]/10 text-[#5856D6] border border-[#5856D6]/20">{aid}</span>
                        ))}
                        {corr.confidence != null && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-apple-surface text-apple-secondary ml-auto">{(corr.confidence * 100).toFixed(0)}%</span>
                        )}
                      </div>
                      {corr.causal_chain && (
                        <p className="text-[11px] font-mono text-apple-secondary mt-1.5">{corr.causal_chain}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}


function StatPill({ label, severe, warn }) {
  let cls = 'text-apple-secondary'
  if (severe) cls = 'text-apple-critical font-medium'
  else if (warn) cls = 'text-apple-warning font-medium'
  return <span className={cls}>{label}</span>
}


/* ── Domain Card ──────────────────────────────────────────────────────────── */

function DomainCard({ card }) {
  const Icon = card.icon
  const healthColor = {
    green: 'bg-apple-success',
    amber: 'bg-apple-warning',
    red: 'bg-apple-critical',
  }[card.health] || 'bg-apple-secondary/30'

  return (
    <button
      onClick={card.onClick}
      className="w-full h-full text-left p-5 transition-all hover:shadow-apple-lg cursor-pointer relative group card hover:border-apple-text/20"
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 bg-apple-bg border border-apple-border">
          <Icon className="w-[18px] h-[18px] text-apple-text" />
        </div>
        <span className="text-body font-medium text-apple-text">{card.title}</span>
        <ArrowRight className="w-4 h-4 text-apple-secondary/0 group-hover:text-apple-secondary transition-colors ml-auto" />
      </div>

      {/* KPI rows */}
      <div className="space-y-3 pr-5">
        {card.rows.map((row) => (
          <div key={row.label}>
            <div className="flex items-baseline justify-between text-caption mb-0.5 gap-3 min-w-0">
              <span className="text-apple-secondary flex-shrink-0">{row.label}</span>
              {row.rag && row.ragCounts ? (
                <span className="text-[12px] font-mono flex items-center gap-1.5 flex-shrink-0">
                  <span className="text-apple-critical">{row.ragCounts.Red}R</span>
                  <span className="text-apple-secondary/30">&middot;</span>
                  <span className="text-apple-warning">{row.ragCounts.Amber}A</span>
                  <span className="text-apple-secondary/30">&middot;</span>
                  <span className="text-apple-success">{row.ragCounts.Green}G</span>
                </span>
              ) : (
                <span className={`font-mono min-w-0 truncate ${
                  row.warn ? 'text-apple-warning text-apple-text' : 'text-apple-text'
                }`}>
                  {row.value}
                </span>
              )}
            </div>
            {row.bar != null && (
              <div className="h-1.5 bg-apple-border rounded-full overflow-hidden">
                <div
                  className="h-full bg-apple-text rounded-full transition-all"
                  style={{ width: `${Math.min(row.bar, 100)}%` }}
                />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Health dot */}
      <div className="absolute bottom-4 right-4">
        <div className={`w-2.5 h-2.5 rounded-full ${healthColor}`} />
      </div>
    </button>
  )
}



/* Study360Header removed — now using shared StudyNav component */


/* ── Helpers ──────────────────────────────────────────────────────────────── */

function formatCurrencyShort(val) {
  if (val == null) return '$0'
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`
  if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`
  return `$${val.toFixed(0)}`
}
