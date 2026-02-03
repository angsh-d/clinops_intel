import { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Users, Database, DollarSign, BarChart3, Brain, Command, MapPin, ArrowRight } from 'lucide-react'
import { useStore } from '../lib/store'
import {
  getStudySummary,
  getEnrollmentDashboard,
  getDataQualityDashboard,
  getFinancialSummary,
  getVendorScorecards,
  getAgentInsights,
  getAttentionSites,
  getSitesOverview,
} from '../lib/api'
import { WorldMap } from './WorldMap'

export function Study360() {
  const { setView, toggleCommand, studyData, setStudyData } = useStore()

  const [enrollment, setEnrollment] = useState(null)
  const [dataQuality, setDataQuality] = useState(null)
  const [financial, setFinancial] = useState(null)
  const [vendors, setVendors] = useState(null)
  const [insights, setInsights] = useState(null)
  const [attentionSites, setAttentionSites] = useState([])
  const [sites, setSites] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function fetchAll() {
      const [summaryR, enrollR, dqR, finR, vendR, insR, attnR, sitesR] = await Promise.allSettled([
        getStudySummary(),
        getEnrollmentDashboard(),
        getDataQualityDashboard(),
        getFinancialSummary(),
        getVendorScorecards(),
        getAgentInsights(),
        getAttentionSites(),
        getSitesOverview(),
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
      if (insR.status === 'fulfilled') setInsights(insR.value)
      if (attnR.status === 'fulfilled' && attnR.value?.sites) setAttentionSites(attnR.value.sites)
      if (sitesR.status === 'fulfilled' && sitesR.value?.sites) setSites(sitesR.value.sites)
      setLoading(false)
    }
    fetchAll()
    return () => { cancelled = true }
  }, [])

  // useMemo must be before any early return to satisfy rules of hooks
  const mapSites = useMemo(() => sites.map(s => ({
    id: s.site_id,
    name: s.site_name,
    country: s.country,
    status: s.status || 'healthy',
    enrollmentPercent: s.enrollment_percent || 0,
  })), [sites])

  // Count unique flagged site names (matches StudyCommandCenter's "Active Signals" count)
  const flaggedNames = useMemo(() => {
    const insightList = insights?.insights || []
    const siteById = new Map(sites.map(s => [s.site_id, s]))
    const knownNames = new Set(sites.map(s => s.site_name))
    const names = new Set()
    insightList.forEach(i => {
      i.sites?.forEach(sid => {
        const site = siteById.get(sid)
        if (site?.site_name) names.add(site.site_name)
      })
    })
    attentionSites.forEach(s => {
      if (s.site_name && knownNames.has(s.site_name)) names.add(s.site_name)
    })
    return names
  }, [insights, attentionSites, sites])

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

  // AI Signals card
  const insightList = insights?.insights || []
  const insightCount = insightList.length
  const criticalSignals = insightList.filter(i => i.severity === 'critical').length
  const highSignals = insightList.filter(i => i.severity === 'high').length
  const latestSignal = insightList[0]?.title || null
  const flaggedSiteCount = flaggedNames.size

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

  function aiHealth() {
    if (criticalSignals > 0) return 'red'
    if (highSignals > 0) return 'amber'
    return 'green'
  }

  const cards = [
    {
      title: 'Enrollment',
      icon: Users,
      health: enrollmentHealth(),
      onClick: () => setView('study'),
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
      onClick: () => setView('study'),
      rows: [
        { label: 'Mean Entry Lag', value: meanLag != null ? `${meanLag.toFixed(1)}d` : '—' },
        { label: 'Total Queries', value: totalQueries != null ? totalQueries.toLocaleString() : '—' },
        { label: 'Sites w/ Aging >14d', value: sitesWithAging != null ? `${sitesWithAging}` : '—' },
      ],
    },
    {
      title: 'Financial',
      icon: DollarSign,
      health: financialHealth(),
      onClick: () => setView('financials'),
      rows: [
        { label: 'Budget Utilization', value: `${budgetUtilization.toFixed(0)}%`, bar: budgetUtilization },
        { label: 'Variance', value: variancePct != null ? `${variancePct > 0 ? '+' : ''}${variancePct.toFixed(1)}%` : '—' },
        { label: 'Burn Rate', value: burnRate != null ? formatCurrencyShort(burnRate) : '—' },
      ],
    },
    {
      title: 'Vendor',
      icon: BarChart3,
      health: vendorHealth(),
      onClick: () => setView('vendors'),
      rows: [
        { label: 'Vendors', value: `${vendorCount}` },
        { label: 'RAG Distribution', ragCounts, rag: true },
        { label: 'Open Issues', value: `${openIssues}`, warn: openIssues > 0 },
      ],
    },
    {
      title: 'AI Signals',
      icon: Brain,
      health: aiHealth(),
      onClick: toggleCommand,
      gradient: true,
      span2: true,
      rows: [
        { label: 'Flagged Sites', value: `${flaggedSiteCount}` },
        { label: 'Insights', value: `${insightCount} (${criticalSignals} critical)` },
        { label: 'Latest', value: latestSignal || '—', full: true },
      ],
    },
  ]

  return (
    <div className="min-h-screen bg-apple-bg flex flex-col">
      <Study360Header studyData={studyData} setView={setView} toggleCommand={toggleCommand} />

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-10">
        <h2 className="text-2xl font-light text-apple-text mb-8">Study Health Overview</h2>

        {/* Top row: 3 cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-5">
          {cards.slice(0, 3).map((card, i) => (
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

        {/* Bottom row: Vendor (1col) + AI Signals (2col) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {cards.slice(3).map((card, i) => (
            <motion.div
              key={card.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: (i + 3) * 0.08 }}
              className={card.span2 ? 'md:col-span-2' : ''}
            >
              <DomainCard card={card} />
            </motion.div>
          ))}
        </div>

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
                onClick={() => setView('study')}
                className="flex items-center gap-1.5 text-caption text-apple-secondary hover:text-apple-text transition-colors"
              >
                <span>Open Site Map</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
            <WorldMap
              sites={mapSites}
              onSiteClick={() => setView('study')}
              height="h-[360px]"
            />
          </motion.div>
        )}
      </main>
    </div>
  )
}


/* ── Domain Card ──────────────────────────────────────────────────────────── */

function DomainCard({ card }) {
  const Icon = card.icon
  const healthColor = {
    green: 'bg-apple-success',
    amber: 'bg-apple-warning',
    red: 'bg-apple-critical',
  }[card.health] || 'bg-apple-secondary/30'

  const inner = (
    <button
      onClick={card.onClick}
      className={`w-full h-full text-left p-5 transition-all hover:shadow-apple-lg cursor-pointer relative group ${
        card.gradient
          ? 'bg-apple-surface rounded-[15px]'
          : 'card hover:border-apple-text/20'
      }`}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${
          card.gradient
            ? 'bg-gradient-to-br from-[#5856D6] to-[#AF52DE]'
            : 'bg-apple-bg border border-apple-border'
        }`}>
          <Icon className={`w-[18px] h-[18px] ${card.gradient ? 'text-white' : 'text-apple-text'}`} />
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
                  <span className="text-apple-secondary/30">·</span>
                  <span className="text-apple-warning">{row.ragCounts.Amber}A</span>
                  <span className="text-apple-secondary/30">·</span>
                  <span className="text-apple-success">{row.ragCounts.Green}G</span>
                </span>
              ) : (
                <span className={`font-mono min-w-0 truncate ${
                  row.full ? 'text-[11px] text-apple-secondary' :
                  row.warn ? 'text-apple-warning text-apple-text' :
                  'text-apple-text'
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

  if (card.gradient) {
    return (
      <div className="rounded-2xl p-[1.5px] bg-gradient-to-br from-[#5856D6] to-[#AF52DE] shadow-apple h-full">
        {inner}
      </div>
    )
  }

  return inner
}



/* ── Header ───────────────────────────────────────────────────────────────── */

function Study360Header({ studyData, setView, toggleCommand }) {
  const enrolled = studyData.enrolled || 0
  const target = studyData.target || 0
  const progress = target > 0 ? Math.round((enrolled / target) * 100) : 0
  const totalSites = studyData.totalSites || studyData.total_sites || 0
  const countries = studyData.countries?.length || 0

  return (
    <header className="sticky top-0 z-50 glass border-b border-apple-border">
      <div className="px-5 py-3 flex items-center justify-between gap-4">
        {/* Left: Logo + back to Home */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <button onClick={() => setView('home')} className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <img src="/saama_logo.svg" alt="Saama" className="h-6" />
            <div className="w-px h-5 bg-apple-border" />
            <span className="text-body font-medium text-apple-text">DSP</span>
          </button>
        </div>

        {/* Center: Study KPI strip */}
        <div className="flex items-center gap-5 text-caption">
          <span className="font-medium text-apple-text">{studyData.studyId || ''}</span>
          <span className="text-apple-secondary">{studyData.phase || ''}</span>
          <div className="flex items-center gap-2">
            <div className="w-24 h-1.5 bg-apple-border rounded-full overflow-hidden">
              <div className="h-full bg-apple-text rounded-full transition-all" style={{ width: `${progress}%` }} />
            </div>
            <span className="font-mono text-apple-text">{enrolled}/{target}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <MapPin className="w-3 h-3 text-apple-secondary" />
            <span className="text-apple-secondary">{totalSites} sites</span>
            <span className="text-apple-secondary/40 mx-0.5">/</span>
            <span className="text-apple-secondary">{countries} ctry</span>
          </div>
        </div>

        {/* Right: Nav */}
        <nav className="flex items-center gap-3 flex-shrink-0">
          <button
            onClick={() => setView('study')}
            className="px-3 py-1.5 text-caption text-apple-secondary hover:text-apple-text hover:bg-apple-surface rounded-lg transition-all"
          >
            Sites
          </button>
          <button
            onClick={() => setView('vendors')}
            className="px-3 py-1.5 text-caption text-apple-secondary hover:text-apple-text hover:bg-apple-surface rounded-lg transition-all"
          >
            Vendors
          </button>
          <button
            onClick={() => setView('financials')}
            className="px-3 py-1.5 text-caption text-apple-secondary hover:text-apple-text hover:bg-apple-surface rounded-lg transition-all"
          >
            Financials
          </button>
          <button
            onClick={toggleCommand}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-apple-surface border border-apple-border rounded-lg text-caption text-apple-secondary hover:text-apple-text hover:border-apple-text/20 transition-all"
          >
            <Command className="w-3 h-3" />
            <span>Ask</span>
            <kbd className="ml-0.5 px-1 py-0.5 bg-apple-bg rounded text-[10px] font-mono">K</kbd>
          </button>
        </nav>
      </div>
    </header>
  )
}


/* ── Helpers ──────────────────────────────────────────────────────────────── */

function formatCurrencyShort(val) {
  if (val == null) return '$0'
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`
  if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`
  return `$${val.toFixed(0)}`
}
