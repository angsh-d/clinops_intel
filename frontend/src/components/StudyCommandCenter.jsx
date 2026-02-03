import { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronUp, Command, MapPin, ArrowRight } from 'lucide-react'
import { useStore } from '../lib/store'
import { getStudySummary, getSitesOverview, getAttentionSites, getAgentInsights } from '../lib/api'
import { WorldMap } from './WorldMap'

/* ── Proactive Insights — cross-domain patterns requiring review ─────────── */

const PROACTIVE_INSIGHTS = [
  {
    id: 'cbcc-vendor-cascade',
    site: 'CBCC Global Research',
    siteId: 'SITE-022',
    category: 'Vendor Impact',
    query: 'Why is data quality degrading at CBCC Global Research and what is the financial impact?',
    agents: ['DQ', 'EF', 'VP', 'FI', 'CI'],
    accent: 'from-red-500 to-orange-500',
    apparent: 'Entry lag high, queries elevated — retrain site staff on data entry procedures',
    finding: 'Vendor CRA swap \u2192 4.2d lag spike \u2192 query flood \u2192 enrollment freeze \u2192 $340K in delay costs. Root cause is vendor staffing transition. Recommend vendor corrective action plan',
    provenance: [
      { agent: 'Data Quality', detail: 'Entry lag spiked to 4.2d (vs 1.8d study avg) coinciding with CRA-007 offboarding. Open query rate 34% above peer median.', action: 'Escalate lag source before retraining staff.' },
      { agent: 'Vendor Performance', detail: 'CRA-007 \u2192 CRA-012 transition left 18-day coverage gap. Visit completion dropped to 88.3%.', action: 'Issue CAPA to VEND-001 regarding staffing levels.' },
      { agent: 'Enrollment Funnel', detail: 'Enrollment velocity dropped 40% during lag spike period. 3 subjects in screening pipeline stalled.', action: 'Hold new screening until data backlog clears.' },
      { agent: 'Financial Intelligence', detail: 'Quality-driven rework costing $136K in unbudgeted monitoring. Projected $340K total delay cost at current trajectory.', action: 'Cap billable monitoring visits until quality stabilizes.' },
      { agent: 'Competitive Intelligence', detail: 'No competing trials detected in catchment area — confirms enrollment drop is internally driven, not market-related.', action: null },
    ],
  },
  {
    id: 'canterbury-supply-chain',
    site: 'Canterbury District Health Board',
    siteId: 'SITE-041',
    category: 'Supply Chain',
    query: 'Why are patients withdrawing consent at Canterbury District Health Board and what should we do about it?',
    agents: ['EF', 'DQ', 'VP', 'FI', 'SD'],
    accent: 'from-amber-500 to-yellow-500',
    apparent: 'Consent withdrawal rate spiking — investigate patient safety or treatment concerns',
    finding: 'Kit stockout \u2192 randomization frozen 23 days \u2192 67% consent withdrawal. Withdrawals driven by wait time, not treatment concerns. Site rescue-viable pending supply chain resolution',
    provenance: [
      { agent: 'Enrollment Funnel', detail: '67% consent withdrawal over 23-day period. All withdrawals cited wait time, not treatment concerns. Screening pipeline otherwise healthy (SF rate 18%).', action: null },
      { agent: 'Data Quality', detail: 'eCRF completion rate remained stable through withdrawal period — data entry discipline intact.', action: 'Not a data quality issue.' },
      { agent: 'Vendor Performance', detail: 'Kit vendor (VEND-003) had 3 shipment delays in 6 weeks. Regional depot stockout confirmed.', action: 'Escalate to vendor for expedited resupply.' },
      { agent: 'Financial Intelligence', detail: 'Sunk cost of $89K per withdrawn subject. Site closure would write off $1.2M. Rescue cost estimated at $180K.', action: 'Rescue ROI positive if supply restored within 30 days.' },
      { agent: 'Site Decision', detail: 'Site enrollment capacity at 85th percentile when operational. Recommend rescue with supply chain remediation.', action: 'Do not close — rescue-viable.' },
    ],
  },
  {
    id: 'cru-hungary-compliance',
    site: 'CRU Hungary',
    siteId: 'SITE-074',
    category: 'Compliance Risk',
    query: "Is CRU Hungary's perfect data quality genuine or is the data too good to be true?",
    agents: ['PC', 'DQ', 'EF', 'SD'],
    accent: 'from-purple-500 to-pink-500',
    apparent: 'All KRIs green — top-performing site, replicate best practices across the study',
    finding: 'Near-zero variance across all KRIs simultaneously \u2014 entry lag, queries, completions, monitoring. Statistically implausible for a real clinical site. Recommend for-cause audit',
    provenance: [
      { agent: 'Data Integrity', detail: 'KRI variance at 0.02 std dev across all metrics — 4.7 sigma below expected. Pattern consistent with data fabrication profile.', action: 'Initiate for-cause audit.' },
      { agent: 'Data Quality', detail: 'Entry lag consistently 1.0 \u00b1 0.1 days across all forms. Zero queries in 90 days. Zero corrections.', action: 'Statistically implausible for 47 active subjects.' },
      { agent: 'Enrollment Funnel', detail: 'Screen failure rate exactly 20.0% for 6 consecutive months. Randomization timing shows no natural variance.', action: 'Pattern suggests pre-determined outcomes.' },
      { agent: 'Site Decision', detail: 'If fabrication confirmed, 47 subjects may require re-consent or exclusion. Timeline impact: 4\u20136 month delay.', action: 'Prepare contingency enrollment plan.' },
    ],
  },
  {
    id: 'highlands-competitive',
    site: 'Highlands Oncology Group',
    siteId: 'SITE-055',
    category: 'Competitive Intelligence',
    query: 'Why has enrollment declined at Highlands Oncology Group and should we rescue or close the site?',
    agents: ['EF', 'CI', 'DQ', 'SD', 'FI'],
    accent: 'from-blue-500 to-indigo-500',
    apparent: 'Enrollment declining with improved screen failure rate — site winding down naturally',
    finding: 'Competing trial opened nearby \u2192 60% screening volume drop. Screen failure rate improved from 42% to 15% \u2014 selection bias from reduced volume, not genuine quality gain. Rescue decision depends on competitor trial duration',
    provenance: [
      { agent: 'Enrollment Funnel', detail: 'Screening volume dropped 60% (12/mo to 5/mo) over 8 weeks. SF rate improved from 42% to 15%.', action: 'Volume drop + SF improvement = selection bias, not quality gain.' },
      { agent: 'Competitive Intelligence', detail: 'Phase III oncology trial opened at competing site 12 miles away. Overlapping indication and eligibility. Expected duration 18 months.', action: 'Rescue depends on competitor timeline.' },
      { agent: 'Data Quality', detail: 'Data quality metrics stable — no degradation in entry lag or query rates.', action: 'Site operational discipline is intact.' },
      { agent: 'Site Decision', detail: 'At 5/mo screening rate, site misses target by 14 months. Break-even requires competitor closure within 6 months.', action: 'Conditional rescue with 90-day reassessment.' },
      { agent: 'Financial Intelligence', detail: '$420K invested to date. Closure write-off vs $95K rescue cost for 6-month extension.', action: 'Rescue NPV positive only if screening recovers to 8+/mo.' },
    ],
  },
  {
    id: 'leicester-monitoring',
    site: 'Leicester Royal Infirmary',
    siteId: 'SITE-017',
    category: 'Monitoring Efficacy',
    query: 'Why has enrollment dropped at Leicester Royal Infirmary despite increased monitoring?',
    agents: ['DQ', 'EF', 'VP', 'FI', 'CI'],
    accent: 'from-teal-500 to-cyan-500',
    apparent: 'Monitoring doubled but enrollment still declining — site has fundamental operational issues',
    finding: '2x monitoring frequency \u2192 PI audit anxiety \u2192 overcautious screening \u2192 30% enrollment drop + 15% more screen failures. Recommend reducing visit frequency to baseline and tracking enrollment recovery',
    provenance: [
      { agent: 'Data Quality', detail: 'Entry lag increased from 1.5d to 4.8d after monitoring frequency doubled. Query response time also degraded.', action: 'Site slowing down under oversight pressure.' },
      { agent: 'Enrollment Funnel', detail: 'Enrollment dropped 30% (10/mo to 7/mo). Screen failure rate increased from 22% to 37%. PI applying stricter exclusion criteria.', action: 'Overcautious screening since monitoring increase.' },
      { agent: 'Vendor Performance', detail: 'Monitoring vendor billed 2x visits. Visit findings decreased 40% — fewer issues found per visit despite more visits.', action: 'Diminishing returns on monitoring investment.' },
      { agent: 'Financial Intelligence', detail: 'Additional monitoring cost $67K with no quality improvement. Net negative ROI on monitoring increase.', action: 'Revert to standard monitoring frequency.' },
      { agent: 'Competitive Intelligence', detail: 'No external competitive factors. Enrollment decline is purely internal and coincides with monitoring change.', action: 'Confirms monitoring as causal factor.' },
    ],
  },
]

/* ────────────────────────────────────────────────────────────────────────────
 * StudyCommandCenter — 2-column study view
 * Left rail: Risk Posture + Active Signals + Site Table
 * Center: Interactive WorldMap (full remaining width)
 * ──────────────────────────────────────────────────────────────────────────── */

export function StudyCommandCenter() {
  const { setView, setSelectedSite, setInvestigation, setSites, setSiteNameMap, toggleCommand, studyData, setStudyData } = useStore()

  const [sites, setSitesLocal] = useState([])
  const [attentionSites, setAttentionSites] = useState([])
  const [insights, setInsights] = useState([])
  const [loading, setLoading] = useState(true)
  const [hoveredSite, setHoveredSite] = useState(null)
  const [riskFilter, setRiskFilter] = useState(null)
  const [siteTableExpanded, setSiteTableExpanded] = useState(false)
  const [siteTableSort, setSiteTableSort] = useState({ key: 'status', dir: 'asc' })

  // Fetch all data on mount — each endpoint independent so one failure doesn't block others
  useEffect(() => {
    let cancelled = false
    async function fetchAll() {
      const [summaryResult, sitesResult, attentionResult, insightsResult] = await Promise.allSettled([
        getStudySummary(),
        getSitesOverview(),
        getAttentionSites(),
        getAgentInsights(),
      ])
      if (cancelled) return

      const summaryData = summaryResult.status === 'fulfilled' ? summaryResult.value : null
      const sitesData = sitesResult.status === 'fulfilled' ? sitesResult.value : null
      const attentionData = attentionResult.status === 'fulfilled' ? attentionResult.value : null
      const insightsData = insightsResult.status === 'fulfilled' ? insightsResult.value : null

      if (summaryData) {
        setStudyData({
          enrolled: summaryData.enrolled,
          target: summaryData.target,
          criticalSites: 0,
          watchSites: 0,
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

      if (sitesData?.sites) {
        setSitesLocal(sitesData.sites)
        setSites(sitesData.sites)
        const nameMap = {}
        for (const s of sitesData.sites) {
          if (s.site_name) nameMap[s.site_id] = s.site_name
        }
        setSiteNameMap(nameMap)
      }

      if (attentionData?.sites) setAttentionSites(attentionData.sites)
      if (insightsData?.insights) setInsights(insightsData.insights)
      setLoading(false)
    }
    fetchAll()
    return () => { cancelled = true }
  }, [])

  // Compute risk posture counts
  const riskCounts = useMemo(() => {
    const critical = sites.filter(s => s.status === 'critical').length
    const warning = sites.filter(s => s.status === 'warning').length
    const healthy = sites.filter(s => s.status === 'healthy').length
    return { critical, warning, healthy }
  }, [sites])

  // Filter sites by risk posture
  const filteredSites = useMemo(() => {
    if (!riskFilter) return sites
    return sites.filter(s => s.status === riskFilter)
  }, [sites, riskFilter])

  // Map sites — always show all sites so highlighted signals remain visible regardless of risk filter
  const mapSites = useMemo(() => sites.map(s => ({
    id: s.site_id,
    name: s.site_name,
    country: s.country,
    status: s.status || 'healthy',
    enrollmentPercent: s.enrollment_percent || 0,
  })), [sites])

  // Highlighted sites from insights — only include names that resolve to a known site
  const highlightedSiteNames = useMemo(() => {
    const siteById = new Map(sites.map(s => [s.site_id, s]))
    const knownNames = new Set(sites.map(s => s.site_name))
    const names = new Set()
    insights.forEach(i => {
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

  const handleSiteClick = (site) => setSelectedSite(site)
  const handleInvestigate = (query, site = null) => setInvestigation({ question: query, site, status: 'routing' })

  const handleRiskFilter = (status) => {
    setRiskFilter(prev => prev === status ? null : status)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-apple-bg flex items-center justify-center">
        <div className="flex items-center gap-3 text-apple-secondary">
          <div className="w-5 h-5 border-2 border-apple-secondary/30 border-t-apple-secondary rounded-full animate-spin" />
          <span className="text-body">Loading Study Command Center...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-apple-bg flex flex-col">
      <CommandHeader
        studyData={studyData}
        setView={setView}
        toggleCommand={toggleCommand}
      />

      {/* Proactive Insights strip */}
      <div className="border-b border-apple-border bg-apple-bg/50">
        <div className="px-5 py-3">
          <div className="flex items-center gap-2 mb-2.5">
            <h3 className="text-caption font-medium text-apple-secondary uppercase tracking-wider">Proactive Insights</h3>
            <span className="text-[10px] text-apple-secondary/50 font-mono">{PROACTIVE_INSIGHTS.length}</span>
          </div>
          <div className="flex gap-3 overflow-x-auto snap-x snap-mandatory pb-2 -mx-1 px-1">
            {PROACTIVE_INSIGHTS.map((insight, i) => (
              <InsightCard
                key={insight.id}
                insight={insight}
                defaultExpanded={false}
                onInvestigate={() => handleInvestigate(insight.query, { id: insight.siteId, name: insight.site })}
              />
            ))}
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* LEFT RAIL */}
        <div className="w-[280px] flex-shrink-0 border-r border-apple-border overflow-y-auto max-h-[calc(100vh-200px)]">
          <div className="p-4 space-y-4">
            <RiskPosture counts={riskCounts} active={riskFilter} onFilter={handleRiskFilter} />
            <ActiveSignalPanel
              highlightedNames={highlightedSiteNames}
              sites={sites}
              attentionSites={attentionSites}
              insights={insights}
              onHover={setHoveredSite}
              onClick={handleSiteClick}
              onInvestigate={handleInvestigate}
            />
            <SiteTableToggle
              sites={filteredSites}
              expanded={siteTableExpanded}
              onToggle={() => setSiteTableExpanded(v => !v)}
              sort={siteTableSort}
              onSort={setSiteTableSort}
              onClick={handleSiteClick}
            />
          </div>
        </div>

        {/* CENTER MAP — full remaining width */}
        <div className="flex-1 min-w-0 p-4 flex flex-col">
          <MapPanel
            sites={mapSites}
            hoveredSite={hoveredSite}
            onSiteHover={setHoveredSite}
            onSiteClick={handleSiteClick}
            highlightedSiteNames={highlightedSiteNames}
          />
        </div>
      </div>
    </div>
  )
}


/* ── CommandHeader ───────────────────────────────────────────────────────── */

function CommandHeader({ studyData, setView, toggleCommand }) {
  const enrolled = studyData.enrolled || 0
  const target = studyData.target || 0
  const progress = target > 0 ? Math.round((enrolled / target) * 100) : 0
  const totalSites = studyData.totalSites || studyData.total_sites || 0
  const countries = studyData.countries?.length || 0

  return (
    <header className="sticky top-0 z-50 glass border-b border-apple-border">
      <div className="px-5 py-3 flex items-center justify-between gap-4">
        {/* Left: Logo + Study */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <button onClick={() => setView('study360')} className="flex items-center gap-3 hover:opacity-80 transition-opacity">
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


/* ── RiskPosture ─────────────────────────────────────────────────────────── */

function RiskPosture({ counts, active, onFilter }) {
  return (
    <div>
      <h3 className="text-caption font-medium text-apple-secondary uppercase tracking-wider mb-3">Risk Posture</h3>
      <div className="flex gap-2">
        <RiskPill
          label="Critical"
          count={counts.critical}
          color="bg-apple-critical"
          textColor="text-apple-critical"
          active={active === 'critical'}
          onClick={() => onFilter('critical')}
        />
        <RiskPill
          label="Watch"
          count={counts.warning}
          color="bg-apple-warning"
          textColor="text-apple-warning"
          active={active === 'warning'}
          onClick={() => onFilter('warning')}
        />
        <RiskPill
          label="OK"
          count={counts.healthy}
          color="bg-apple-success"
          textColor="text-apple-success"
          active={active === 'healthy'}
          onClick={() => onFilter('healthy')}
        />
      </div>
    </div>
  )
}

function RiskPill({ label, count, color, textColor, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-caption transition-all ${
        active
          ? `${color}/20 ${textColor} font-medium ring-1 ring-current/30`
          : 'bg-apple-surface text-apple-secondary hover:bg-apple-bg'
      }`}
    >
      <div className={`w-2 h-2 rounded-full ${color}`} />
      <span>{count}</span>
      <span className="hidden sm:inline">{label}</span>
    </button>
  )
}


/* ── SiteTableToggle ─────────────────────────────────────────────────────── */

function SiteTableToggle({ sites, expanded, onToggle, sort, onSort, onClick }) {
  const sorted = useMemo(() => {
    const arr = [...sites]
    const statusOrder = { critical: 0, warning: 1, healthy: 2 }
    arr.sort((a, b) => {
      let diff = 0
      if (sort.key === 'status') {
        diff = (statusOrder[a.status] ?? 3) - (statusOrder[b.status] ?? 3)
      } else if (sort.key === 'enrollment') {
        diff = (a.enrollment_percent || 0) - (b.enrollment_percent || 0)
      }
      if (diff !== 0) return sort.dir === 'asc' ? diff : -diff
      return (a.site_name || '').localeCompare(b.site_name || '')
    })
    return arr
  }, [sites, sort])

  return (
    <div>
      <button
        onClick={onToggle}
        className="flex items-center gap-2 text-caption text-apple-accent hover:underline"
      >
        {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        <span>View all {sites.length} sites</span>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden mt-3"
          >
            <div className="max-h-[400px] overflow-y-auto rounded-lg border border-apple-border">
              <table className="w-full text-caption">
                <thead className="sticky top-0 bg-apple-surface">
                  <tr>
                    <th
                      className="text-left p-2 text-apple-secondary font-medium cursor-pointer hover:text-apple-text"
                      onClick={() => onSort({ key: 'status', dir: sort.key === 'status' && sort.dir === 'asc' ? 'desc' : 'asc' })}
                    >
                      Site
                    </th>
                    <th
                      className="text-right p-2 text-apple-secondary font-medium cursor-pointer hover:text-apple-text"
                      onClick={() => onSort({ key: 'enrollment', dir: sort.key === 'enrollment' && sort.dir === 'asc' ? 'desc' : 'asc' })}
                    >
                      Enroll %
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((site) => (
                    <tr
                      key={site.site_id}
                      className="border-t border-apple-border/50 hover:bg-apple-bg cursor-pointer"
                      onClick={() => onClick?.({ id: site.site_id, name: site.site_name, country: site.country })}
                    >
                      <td className="p-2">
                        <div className="flex items-center gap-1.5">
                          <div className={`w-1.5 h-1.5 rounded-full ${
                            site.status === 'critical' ? 'bg-apple-critical' :
                            site.status === 'warning' ? 'bg-apple-warning' :
                            'bg-apple-success'
                          }`} />
                          <span className="text-apple-text truncate max-w-[160px]">{site.site_name || site.site_id}</span>
                        </div>
                      </td>
                      <td className="p-2 text-right font-mono text-apple-secondary">
                        {Math.round(site.enrollment_percent || 0)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}


/* ── MapPanel ────────────────────────────────────────────────────────────── */

function MapPanel({ sites, hoveredSite, onSiteHover, onSiteClick, highlightedSiteNames }) {
  return (
    <WorldMap
      sites={sites}
      onSiteClick={onSiteClick}
      onSiteHover={onSiteHover}
      hoveredSite={hoveredSite}
      height="h-full"
      highlightedSiteNames={highlightedSiteNames}
    />
  )
}


/* ── InsightCard ─────────────────────────────────────────────────────────── */

function InsightCard({ insight, onInvestigate, defaultExpanded = false }) {
  const [showProvenance, setShowProvenance] = useState(defaultExpanded)

  return (
    <div className="min-w-[300px] max-w-[340px] snap-start flex-shrink-0 card flex flex-col">
      <div className={`h-[2px] bg-gradient-to-r ${insight.accent} rounded-t-2xl`} />
      <div className="p-3.5 flex flex-col flex-1">
        {/* Site name + category */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <h4 className="text-caption font-medium text-apple-text leading-snug">{insight.site}</h4>
          <span className="text-[10px] text-apple-secondary bg-apple-bg border border-apple-border rounded px-1.5 py-0.5 flex-shrink-0 whitespace-nowrap">
            {insight.category}
          </span>
        </div>

        {/* Agent badges */}
        <div className="flex flex-wrap gap-1 mb-2.5">
          {insight.agents.map(a => (
            <span key={a} className="px-1 py-px text-[9px] font-mono rounded bg-apple-bg border border-apple-border text-apple-secondary/70">
              {a}
            </span>
          ))}
        </div>

        {/* Apparent cause (strikethrough) */}
        <p className="text-[11px] text-apple-secondary/60 line-through mb-1.5 leading-snug">{insight.apparent}</p>

        {/* Actual finding */}
        <p className="text-[11px] text-apple-text leading-relaxed">{insight.finding}</p>

        {/* Provenance toggle */}
        <button
          onClick={() => setShowProvenance(v => !v)}
          className="mt-2.5 flex items-center gap-1.5 text-[11px] font-medium text-apple-accent hover:text-apple-accent/80 transition-colors self-start"
        >
          {showProvenance ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          <span>What the data shows ({insight.provenance.length})</span>
        </button>

        {/* Provenance detail */}
        <AnimatePresence initial={false}>
          {showProvenance && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="mt-2 space-y-2 max-h-[220px] overflow-y-auto pr-0.5">
                {insight.provenance.map((p, i) => (
                  <div key={i} className="bg-apple-bg rounded-lg p-2.5 border border-apple-border/50">
                    <div className="flex items-baseline gap-1.5 mb-1">
                      <span className="text-[9px] font-semibold uppercase tracking-wider text-apple-accent">{p.agent}</span>
                      <span className="text-[9px] text-apple-secondary/40">&middot;</span>
                      <span className="text-[9px] text-apple-secondary/50">{insight.site} ({insight.siteId})</span>
                    </div>
                    <p className="text-[10px] text-apple-text leading-relaxed">{p.detail}</p>
                    {p.action && (
                      <p className="text-[10px] text-apple-secondary italic mt-1">{p.action}</p>
                    )}
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Investigate */}
        <button
          onClick={onInvestigate}
          className="mt-3 w-full flex items-center justify-center gap-1 px-2.5 py-1.5 text-[11px] font-medium text-apple-accent bg-apple-accent/8 hover:bg-apple-accent/15 rounded-lg transition-colors"
        >
          Investigate
          <ArrowRight className="w-3 h-3" />
        </button>
      </div>
    </div>
  )
}


/* ── ActiveSignalPanel ───────────────────────────────────────────────────── */

function ActiveSignalPanel({ highlightedNames, sites, attentionSites, insights, onHover, onClick, onInvestigate }) {
  // Build a map of site_name -> reasons why it's an active signal
  const signalSites = useMemo(() => {
    const siteMap = {}
    for (const name of highlightedNames) {
      siteMap[name] = { name, reasons: [], source: [], siteData: null }
    }
    // Match site data
    for (const s of sites) {
      if (siteMap[s.site_name]) {
        siteMap[s.site_name].siteData = s
      }
    }
    // Add attention reasons (threshold-based)
    for (const a of attentionSites) {
      if (siteMap[a.site_name]) {
        siteMap[a.site_name].reasons.push(a.issue || 'Attention flagged')
        siteMap[a.site_name].source.push('threshold')
      }
    }
    // Add insight reasons (AI agent findings)
    const siteById = new Map(sites.map(s => [s.site_id, s]))
    for (const i of insights) {
      for (const sid of (i.sites || [])) {
        const site = siteById.get(sid)
        if (site && siteMap[site.site_name]) {
          siteMap[site.site_name].reasons.push(i.title || 'AI insight')
          siteMap[site.site_name].source.push('ai')
        }
      }
    }
    // Deduplicate and filter out entries with no siteData (unresolvable names)
    for (const entry of Object.values(siteMap)) {
      entry.reasons = [...new Set(entry.reasons)]
      entry.source = [...new Set(entry.source)]
    }
    return Object.values(siteMap).filter(e => e.siteData).sort((a, b) => {
      // AI-flagged sites first, then by severity
      const srcA = a.source.includes('ai') ? 0 : 1
      const srcB = b.source.includes('ai') ? 0 : 1
      if (srcA !== srcB) return srcA - srcB
      const sevA = a.siteData?.status === 'critical' ? 0 : a.siteData?.status === 'warning' ? 1 : 2
      const sevB = b.siteData?.status === 'critical' ? 0 : b.siteData?.status === 'warning' ? 1 : 2
      return sevA - sevB
    })
  }, [highlightedNames, sites, attentionSites, insights])

  if (signalSites.length === 0) {
    return (
      <div>
        <h3 className="text-caption font-medium text-apple-secondary uppercase tracking-wider mb-3">Active Signals</h3>
        <p className="text-caption text-apple-secondary/50">No active signals</p>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <div className="relative w-4 h-4 flex items-center justify-center shrink-0">
          <div className="absolute w-4 h-4 rounded-full bg-[#5856D6]/20 animate-ping" />
          <div className="w-2.5 h-2.5 rounded-full bg-[#5856D6]" />
        </div>
        <h3 className="text-caption font-medium text-apple-secondary uppercase tracking-wider">
          Active Signals
        </h3>
        <span className="text-[10px] text-apple-secondary/60 font-mono">{signalSites.length}</span>
      </div>
      <div className="space-y-1">
        {signalSites.map((entry) => {
          const s = entry.siteData
          const hasAI = entry.source.includes('ai')
          return (
            <div
              key={entry.name}
              className="w-full text-left p-2.5 rounded-lg hover:bg-apple-surface transition-colors group"
              onMouseEnter={() => s && onHover?.({ id: s.site_id, name: s.site_name, country: s.country, status: s.status, enrollmentPercent: s.enrollment_percent || 0 })}
              onMouseLeave={() => onHover?.(null)}
            >
              <div className="flex items-center gap-2 mb-0.5">
                <div className={`w-2 h-2 rounded-full shrink-0 ${
                  s?.status === 'critical' ? 'bg-apple-critical' :
                  s?.status === 'warning' ? 'bg-apple-warning' :
                  'bg-[#5856D6]'
                }`} />
                <button
                  className="text-caption font-medium text-apple-text truncate text-left hover:underline"
                  onClick={() => s && onClick?.({ id: s.site_id, name: s.site_name, country: s.country })}
                >
                  {entry.name}
                </button>
              </div>
              <div className="pl-4">
                <p className="text-[11px] text-apple-secondary truncate leading-relaxed">
                  {entry.reasons[0]}
                  {entry.reasons.length > 1 && ` (+${entry.reasons.length - 1} more)`}
                </p>
                {hasAI && (
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] text-[#5856D6] font-medium">AI flagged</span>
                    <button
                      onClick={() => onInvestigate?.(`Investigate ${entry.name} — ${entry.reasons[0]}`)}
                      className="text-[10px] text-apple-accent hover:underline opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      Investigate →
                    </button>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}


