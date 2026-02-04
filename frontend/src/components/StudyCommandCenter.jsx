import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronUp, ArrowRight } from 'lucide-react'
import { useStore } from '../lib/store'
import { getStudySummary, getSitesOverview, getAttentionSites, getAgentInsights } from '../lib/api'
import { WorldMap } from './WorldMap'
import { StudyNav } from './StudyNav'

const SEVERITY_ACCENT = {
  critical: 'from-red-500 to-orange-500',
  high: 'from-amber-500 to-yellow-500',
  warning: 'from-purple-500 to-pink-500',
  info: 'from-blue-500 to-indigo-500',
}

/* ────────────────────────────────────────────────────────────────────────────
 * StudyCommandCenter — 2-column study view
 * Left rail: Risk Posture + Active Signals + Site Table
 * Center: Interactive WorldMap (full remaining width)
 * ──────────────────────────────────────────────────────────────────────────── */

export function StudyCommandCenter() {
  const navigate = useNavigate()
  const { currentStudyId, setSelectedSite, setInvestigation, setSites, setSiteNameMap, siteNameMap, toggleCommand, studyData, setStudyData } = useStore()

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
      <StudyNav active="sites" />

      {/* Proactive Insights strip */}
      {insights.length > 0 && (
        <div className="border-b border-apple-border bg-apple-bg/50">
          <div className="px-5 py-3">
            <div className="flex items-center gap-2 mb-2.5">
              <h3 className="text-caption font-medium text-apple-secondary uppercase tracking-wider">Proactive Insights</h3>
              <span className="text-[10px] text-apple-secondary/50 font-mono">{insights.length}</span>
            </div>
            <div className="flex gap-3 overflow-x-auto snap-x snap-mandatory pb-2 -mx-1 px-1">
              {insights.map((insight) => (
                <InsightCard
                  key={insight.id}
                  insight={insight}
                  defaultExpanded={false}
                  onInvestigate={() => handleInvestigate(
                    `Investigate: ${insight.title}`,
                    insight.sites?.[0] ? { id: insight.sites[0], name: siteNameMap[insight.sites[0]] || insight.sites[0] } : undefined
                  )}
                />
              ))}
            </div>
          </div>
        </div>
      )}

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

/* CommandHeader removed — now using shared StudyNav component */


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
  const [showDetail, setShowDetail] = useState(defaultExpanded)
  const accent = SEVERITY_ACCENT[insight.severity] || SEVERITY_ACCENT.info

  return (
    <div className="min-w-[300px] max-w-[340px] snap-start flex-shrink-0 card flex flex-col">
      <div className={`h-[2px] bg-gradient-to-r ${accent} rounded-t-2xl`} />
      <div className="p-3.5 flex flex-col flex-1">
        {/* Title + severity */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <h4 className="text-caption font-medium text-apple-text leading-snug">{insight.title}</h4>
          <span className="text-[10px] text-apple-secondary bg-apple-bg border border-apple-border rounded px-1.5 py-0.5 flex-shrink-0 whitespace-nowrap">
            {insight.severity}
          </span>
        </div>

        {/* Agent + confidence */}
        <div className="flex flex-wrap items-center gap-1 mb-2.5">
          <span className="px-1 py-px text-[9px] font-mono rounded bg-apple-bg border border-apple-border text-apple-secondary/70">
            {insight.agent}
          </span>
          {insight.confidence > 0 && (
            <span className="text-[9px] text-apple-secondary/50 font-mono">{Math.round(insight.confidence * 100)}%</span>
          )}
          {insight.sites?.length > 0 && (
            <span className="text-[9px] text-apple-secondary/50">{insight.sites.length} site{insight.sites.length > 1 ? 's' : ''}</span>
          )}
        </div>

        {/* Summary */}
        <p className="text-[11px] text-apple-text leading-relaxed">{insight.summary}</p>

        {/* Detail toggle */}
        {(insight.recommendation || insight.impact) && (
          <>
            <button
              onClick={() => setShowDetail(v => !v)}
              className="mt-2.5 flex items-center gap-1.5 text-[11px] font-medium text-apple-accent hover:text-apple-accent/80 transition-colors self-start"
            >
              {showDetail ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              <span>{showDetail ? 'Hide details' : 'Show details'}</span>
            </button>

            <AnimatePresence initial={false}>
              {showDetail && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="mt-2 space-y-2 max-h-[220px] overflow-y-auto pr-0.5">
                    {insight.recommendation && (
                      <div className="bg-apple-bg rounded-lg p-2.5 border border-apple-border/50">
                        <span className="text-[9px] font-semibold uppercase tracking-wider text-apple-accent">Recommendation</span>
                        <p className="text-[10px] text-apple-text leading-relaxed mt-1">{insight.recommendation}</p>
                      </div>
                    )}
                    {insight.impact && (
                      <div className="bg-apple-bg rounded-lg p-2.5 border border-apple-border/50">
                        <span className="text-[9px] font-semibold uppercase tracking-wider text-apple-accent">Impact</span>
                        <p className="text-[10px] text-apple-text leading-relaxed mt-1">{insight.impact}</p>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}

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


