import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  AlertTriangle, TrendingDown, ChevronRight,
  Loader2, MapPin, DollarSign, ArrowLeft,
  Database, Truck, Activity, FileText,
  LayoutDashboard, Sparkles
} from 'lucide-react'
import { useStore } from '../lib/store'
import {
  getStudySummary, getAttentionSites, startInvestigation,
  connectInvestigationStream, getQueryStatus, getDataQualityDashboard,
  getEnrollmentDashboard, getSitesOverview, getKpiMetrics,
  getVendorScorecards, getFinancialSummary, getCostPerPatient,
  getIssueCategories
} from '../lib/api'
import { WorldMap } from './WorldMap'
import { AssistantPanel } from './AssistantPanel'
import { MVRBrowserModal } from './MVRBrowserModal'

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'enrollment', label: 'Enrollment', icon: Activity },
  { id: 'data-quality', label: 'Data Quality', icon: Database },
  { id: 'vendors', label: 'Vendors', icon: Truck },
  { id: 'financials', label: 'Financials', icon: DollarSign },
]

const QUICK_ACTIONS = [
  { label: 'Which sites need attention this week?', icon: AlertTriangle },
  { label: 'Show me enrollment bottlenecks', icon: TrendingDown },
  { label: 'Show key findings from the last 2 monitoring visit reports for SITE-114', icon: FileText },
  { label: 'What is driving budget variance?', icon: DollarSign },
]

const EXPLORE_ACTIONS = [
  { label: 'Vendor performance summary', icon: Truck, navId: 'vendors' },
  { label: 'Financial health overview', icon: DollarSign, navId: 'financials' },
  { label: 'Data quality trends', icon: Database, navId: 'data-quality' },
  { label: 'Enrollment velocity', icon: Activity, navId: 'enrollment' },
]

export function CommandCenter() {
  const navigate = useNavigate()
  const { studyId } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const { setStudyData, siteNameMap, setSiteNameMap, assistantPanelWidth, setAssistantPanelWidth } = useStore()

  const [studySummary, setStudySummary] = useState(null)
  const [attentionItems, setAttentionItems] = useState([])
  const [allSites, setAllSites] = useState([])
  const [kpis, setKpis] = useState(null)
  const [kpiMetrics, setKpiMetrics] = useState(null)
  const [issueCategories, setIssueCategories] = useState(null)
  const [loading, setLoading] = useState(true)

  const [query, setQuery] = useState('')
  const [isInvestigating, setIsInvestigating] = useState(false)
  const [currentPhase, setCurrentPhase] = useState(null)
  const [phases, setPhases] = useState([])
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const [conversationHistory, setConversationHistory] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const [showExplore, setShowExplore] = useState(false)
  const [autoSubmitHandled, setAutoSubmitHandled] = useState(false)
  const [activeView, setActiveView] = useState('dashboard')
  const [mvrBrowserSite, setMvrBrowserSite] = useState(null)

  const wsRef = useRef(null)

  useEffect(() => {
    async function loadData() {
      try {
        const [summary, attention, dqData, enrollData, sitesData, kpiData] = await Promise.all([
          getStudySummary(),
          getAttentionSites(),
          getDataQualityDashboard().catch(() => null),
          getEnrollmentDashboard().catch(() => null),
          getSitesOverview().catch(() => null),
          getKpiMetrics().catch(() => null)
        ])

        setKpiMetrics(kpiData)

        // Fetch issue categories separately — LLM call can take 30s+, don't block dashboard
        getIssueCategories().then(setIssueCategories).catch(() => null)

        setStudySummary(summary)
        if (summary) {
          setStudyData({
            studyId: summary.study_id,
            studyName: summary.study_name,
            enrolled: summary.enrolled,
            target: summary.target,
            phase: summary.phase,
            totalSites: summary.total_sites,
            countries: summary.countries || [],
          })
        }

        const nameMap = {}
        attention?.sites?.forEach(s => {
          nameMap[s.site_id] = s.site_name
        })
        setSiteNameMap(nameMap)

        const items = (attention?.sites || []).slice(0, 5).map(site => ({
          id: site.site_id,
          name: site.site_name,
          type: site.risk_level === 'critical' ? 'critical' : 'watch',
          metric: site.primary_issue,
          value: site.issue_detail,
          trend: site.trend,
        }))
        setAttentionItems(items)

        const totalScreened = enrollData?.study_total_screened || 0
        const totalRandomized = enrollData?.study_total_randomized || 0
        const screenFailRate = totalScreened > 0
          ? Math.round(((totalScreened - totalRandomized) / totalScreened) * 100)
          : null

        const siteDqScores = dqData?.sites?.map(s => {
          const lagPenalty = Math.min((s.mean_entry_lag || 0) * 2, 20)
          const queryPenalty = Math.min((s.open_queries || 0), 30)
          return Math.max(100 - lagPenalty - queryPenalty, 0)
        }) || []
        const avgDqScore = siteDqScores.length > 0
          ? Math.round(siteDqScores.reduce((a, b) => a + b, 0) / siteDqScores.length)
          : null

        const criticalCount = sitesData?.sites?.filter(s => s.status === 'critical').length || 0

        setKpis({
          dqScore: avgDqScore,
          criticalSites: criticalCount,
          screenFailRate,
          pctOfTarget: enrollData?.study_pct_of_target || null,
        })

        if (sitesData?.sites) {
          setAllSites(sitesData.sites.map(s => ({
            id: s.site_id,
            site_id: s.site_id,
            name: s.site_name || s.site_id,
            country: s.country || 'USA',
            city: s.city,
            status: s.status,
            enrollmentPercent: s.enrollment_percent || 0,
          })))
        }
      } catch (err) {
        console.error('Failed to load data:', err)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [studyId])

  useEffect(() => {
    const urlQuery = searchParams.get('q')
    if (urlQuery && !autoSubmitHandled && !loading) {
      setAutoSubmitHandled(true)
      setSearchParams({})
      setQuery(urlQuery)
      setTimeout(() => {
        setConversationHistory(prev => [...prev, { role: 'user', content: urlQuery }])
        setQuery('')
        setIsInvestigating(true)
        setCurrentPhase('routing')
        setPhases([])
        setResult(null)
        setError(null)
        startInvestigation(urlQuery, null, sessionId).then(({ query_id, session_id: returnedSessionId }) => {
          if (returnedSessionId && !sessionId) {
            setSessionId(returnedSessionId)
          }
          wsRef.current = connectInvestigationStream(query_id, {
            onPhase: (phase) => {
              setCurrentPhase(phase.phase)
              setPhases(prev => [...prev, phase])
            },
            onComplete: (data) => {
              setResult(data)
              setCurrentPhase('complete')
              setIsInvestigating(false)
              setConversationHistory(prev => [...prev, {
                role: 'assistant',
                content: data,
                query: urlQuery
              }])
            },
            onError: (err) => {
              setError(typeof err === 'string' ? err : (err.message || 'Investigation failed'))
              setIsInvestigating(false)
            },
          })
        }).catch(err => {
          setError(err.message || 'Failed to start investigation')
          setIsInvestigating(false)
        })
      }, 100)
    }
  }, [searchParams, loading, autoSubmitHandled])

  const handleSubmit = async (e) => {
    e?.preventDefault()
    if (!query.trim() || isInvestigating) return

    const userQuery = query.trim()
    setConversationHistory(prev => [...prev, { role: 'user', content: userQuery }])
    setQuery('')
    setIsInvestigating(true)
    setCurrentPhase('routing')
    setPhases([])
    setResult(null)
    setError(null)
    try {
      const { query_id, session_id: returnedSessionId } = await startInvestigation(userQuery, null, sessionId)
      if (returnedSessionId && !sessionId) {
        setSessionId(returnedSessionId)
      }

      wsRef.current = connectInvestigationStream(query_id, {
        onPhase: (phase) => {
          setCurrentPhase(phase.phase)
          setPhases(prev => [...prev, phase])
        },
        onComplete: (data) => {
          setResult(data)
          setCurrentPhase('complete')
          setIsInvestigating(false)
          setConversationHistory(prev => [...prev, {
            role: 'assistant',
            content: data,
            query: userQuery
          }])
        },
        onError: (err) => {
          setError(typeof err === 'string' ? err : (err.message || 'Investigation failed'))
          setIsInvestigating(false)
        },
      })
    } catch (err) {
      setError(typeof err === 'string' ? err : (err.message || 'Failed to start investigation'))
      setIsInvestigating(false)
    }
  }

  const handleQuickAction = (actionQuery) => {
    setQuery(actionQuery)
    setTimeout(() => handleSubmit(), 50)
  }

  const handleSiteClick = (siteId) => {
    navigate(`/study/${studyId}/site/${siteId}`)
  }

  const resolveText = (text) => {
    if (!text) return text
    return text.replace(/\[\[SITE:([^\]]+)\]\]/g, (_, id) => {
      const name = siteNameMap[id] || id
      return name
    })
  }

  const progress = studySummary?.target > 0
    ? Math.round((studySummary?.enrolled / studySummary?.target) * 100)
    : 0

  const clearConversation = () => {
    setConversationHistory([])
    setResult(null)
    setError(null)
    setSessionId(null)
  }

  return (
    <div className="min-h-screen bg-apple-bg">
      {/* Header - full width */}
      <header className="sticky top-0 z-50 bg-apple-surface/80 backdrop-blur-xl border-b border-apple-divider">
        <div className="px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/')}
              className="button-icon"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="h-5 w-px bg-apple-divider" />
            <span className="text-[15px] font-semibold text-apple-text tracking-tight">ClinOps Intel</span>
            <div className="h-5 w-px bg-apple-divider" />
            <div className="flex items-center gap-3">
              <span className="text-body font-semibold text-apple-text">{studySummary?.study_id || studyId}</span>
              <span className="text-caption text-apple-tertiary">{studySummary?.phase}</span>
            </div>
          </div>

          <div className="flex items-center gap-6 text-caption">
            <div className="flex items-center gap-3">
              <div className="w-16 h-1 bg-apple-grey-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-apple-grey-600 rounded-full transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className="font-mono text-apple-secondary text-[12px]">
                {studySummary?.enrolled || 0}/{studySummary?.target || 0}
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-apple-tertiary">
              <MapPin className="w-3.5 h-3.5" />
              <span>{studySummary?.total_sites || 0} sites</span>
            </div>
            {conversationHistory.length > 0 && (
              <button
                onClick={clearConversation}
                className="button-ghost text-caption"
              >
                New chat
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Three-column layout */}
      <div className="flex" style={{ height: 'calc(100vh - 57px)', marginRight: assistantPanelWidth }}>
        {/* Left Sidebar */}
        <aside className="w-[200px] flex-shrink-0 bg-apple-surface border-r border-apple-divider overflow-y-auto">
          <div className="px-4 py-5">
            <p className="text-[13px] font-semibold text-apple-text truncate">{studySummary?.study_name || 'Loading...'}</p>
            <p className="text-[11px] text-apple-tertiary mt-0.5">{studySummary?.phase || ''}</p>
          </div>
          <div className="h-px bg-apple-divider mx-4" />
          <nav className="px-3 py-3 space-y-0.5">
            {NAV_ITEMS.map(item => {
              const isActive = activeView === item.id
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveView(item.id)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] transition-all ${
                    isActive
                      ? 'bg-apple-grey-100 text-apple-text font-medium'
                      : 'text-apple-secondary hover:bg-apple-grey-50'
                  }`}
                >
                  <item.icon className="w-4 h-4 flex-shrink-0" />
                  <span>{item.label}</span>
                </button>
              )
            })}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto">
          <div className="px-6 py-8 space-y-8">
            {activeView === 'dashboard' && (
              <DashboardView
                studySummary={studySummary}
                kpis={kpis}
                kpiMetrics={kpiMetrics}
                allSites={allSites}
                attentionItems={attentionItems}
                progress={progress}
                onSiteClick={handleSiteClick}
                issueCategories={issueCategories}
                onCategoryClick={(i) => navigate(`/study/${studyId}/category/${i}`)}
                onViewMVRs={setMvrBrowserSite}
              />
            )}
            {activeView === 'enrollment' && <EnrollmentView />}
            {activeView === 'data-quality' && <DataQualityView />}
            {activeView === 'vendors' && <VendorView />}
            {activeView === 'financials' && <FinancialView />}
          </div>
        </main>
      </div>

      <AssistantPanel
        conversationHistory={conversationHistory}
        isInvestigating={isInvestigating}
        currentPhase={currentPhase}
        error={error}
        query={query}
        setQuery={setQuery}
        onSubmit={handleSubmit}
        onSiteClick={handleSiteClick}
        resolveText={resolveText}
        quickActions={QUICK_ACTIONS}
        exploreActions={EXPLORE_ACTIONS}
        onQuickAction={handleQuickAction}
        onNavigate={setActiveView}
        showExplore={showExplore}
        setShowExplore={setShowExplore}
        width={assistantPanelWidth}
        onResize={setAssistantPanelWidth}
      />

      {mvrBrowserSite && (
        <MVRBrowserModal siteId={mvrBrowserSite} onClose={() => setMvrBrowserSite(null)} />
      )}
    </div>
  )
}

// ── Dashboard View ───────────────────────────────────────────────────────────
const MVR_SITE_IDS = new Set(['SITE-012', 'SITE-022', 'SITE-033', 'SITE-055', 'SITE-074'])

function DashboardView({ studySummary, kpis, kpiMetrics, allSites, attentionItems, progress, onSiteClick, issueCategories, onCategoryClick, onViewMVRs }) {
  return (
    <>
      {/* AI Summary Card */}
      {studySummary && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl p-5 shadow-sm border border-apple-grey-100"
        >
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#5856D6]/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Sparkles className="w-4 h-4 text-[#5856D6]" />
            </div>
            <div>
              <p className="text-[13px] font-medium text-apple-text mb-1">Study Overview</p>
              <p className="text-[12px] text-apple-secondary leading-relaxed">
                {studySummary.study_name} is in {studySummary.phase} with {studySummary.enrolled || 0} of {studySummary.target || 0} patients enrolled ({progress}% of target) across {studySummary.total_sites || 0} sites{studySummary.countries?.length > 0 ? ` in ${studySummary.countries.length} ${studySummary.countries.length === 1 ? 'country' : 'countries'}` : ''}.
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {/* KPI Cards */}
      {kpis && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-4"
        >
          <KPICard
            label="Enrolled"
            value={`${studySummary?.enrolled || 0}`}
            subvalue={`of ${studySummary?.target || 0}`}
            trend={progress >= 80 ? 'good' : progress >= 50 ? 'neutral' : 'warn'}
            metric={kpiMetrics?.enrolled}
          />
          <KPICard
            label="Sites at Risk"
            value={`${kpis.criticalSites}`}
            trend={kpis.criticalSites === 0 ? 'good' : kpis.criticalSites <= 3 ? 'neutral' : 'warn'}
            metric={kpiMetrics?.sites_at_risk}
          />
          <KPICard
            label="DQ Score"
            value={kpis.dqScore ? `${Math.round(kpis.dqScore)}` : '—'}
            trend={kpis.dqScore >= 85 ? 'good' : kpis.dqScore >= 70 ? 'neutral' : 'warn'}
            metric={kpiMetrics?.dq_score}
          />
          <KPICard
            label="Screen Fail"
            value={kpis.screenFailRate !== null ? `${kpis.screenFailRate}%` : '—'}
            trend={kpis.screenFailRate === null ? 'neutral' : kpis.screenFailRate <= 25 ? 'good' : kpis.screenFailRate <= 40 ? 'neutral' : 'warn'}
            metric={kpiMetrics?.screen_fail_rate}
          />
        </motion.div>
      )}

      {/* Map + Attention: side by side on large screens */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.08 }}
        className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6 lg:h-[400px]"
      >
        {allSites.length > 0 && (
          <div className="h-full overflow-hidden">
            <WorldMap
              sites={allSites}
              onSiteClick={(site) => onSiteClick(site.site_id || site.id)}
              onSiteHover={() => {}}
              hoveredSite={null}
              height="h-full"
              needsAttentionSiteIds={new Set(attentionItems.map(a => a.id))}
            />
          </div>
        )}

        {attentionItems.length > 0 && (
          <div className="flex flex-col h-full overflow-hidden">
            <h2 className="text-[11px] font-semibold text-apple-tertiary uppercase tracking-wider mb-3 flex-shrink-0">
              Needs Attention
            </h2>
            <div className="bg-white rounded-2xl shadow-sm border border-apple-grey-100 overflow-y-auto flex-1 min-h-0 divide-y divide-apple-grey-100">
              {attentionItems.map((item) => (
                <div key={item.id} className="hover:bg-apple-grey-50 transition-all group">
                  <button
                    onClick={() => onSiteClick(item.id)}
                    className="w-full p-3.5 text-left"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                          item.type === 'critical' ? 'bg-red-500' : 'bg-amber-500'
                        }`} />
                        <span className="text-[13px] font-medium text-apple-text">{item.name}</span>
                      </div>
                      <ChevronRight className="w-4 h-4 text-apple-grey-300 group-hover:text-apple-grey-500 transition-colors flex-shrink-0" />
                    </div>
                    {item.metric && (
                      <p className="text-[11px] font-medium text-apple-secondary pl-4 mb-0.5">{item.metric}</p>
                    )}
                    {item.value && (
                      <p className="text-[11px] text-apple-muted pl-4 leading-relaxed line-clamp-2">{item.value}</p>
                    )}
                  </button>
                  {MVR_SITE_IDS.has(item.id) && (
                    <div className="px-3.5 pb-2.5 pl-8">
                      <button
                        onClick={(e) => { e.stopPropagation(); onViewMVRs(item.id) }}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-apple-grey-50 border border-apple-grey-200 text-[10px] font-medium text-apple-secondary hover:text-apple-text hover:border-apple-grey-300 transition-all"
                      >
                        <FileText className="w-3 h-3" />
                        View MVRs
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </motion.div>

      {/* Issue Categories */}
      {issueCategories?.categories?.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.12 }}
          className="bg-white rounded-2xl p-5 shadow-sm border border-apple-grey-100"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <h2 className="text-[13px] font-semibold text-apple-text">Issue Categories</h2>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-md bg-apple-grey-100 text-apple-tertiary">
                {issueCategories.site_count} sites
              </span>
            </div>
          </div>
          {issueCategories.summary && (
            <p className="text-[12px] text-apple-secondary leading-relaxed mb-4">{issueCategories.summary}</p>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {issueCategories.categories.map((cat, i) => (
              <button
                key={i}
                onClick={() => onCategoryClick(i)}
                className="border border-apple-grey-100 rounded-xl p-3.5 hover:border-apple-grey-200 hover:shadow-sm transition-all text-left cursor-pointer"
              >
                <div className="flex items-center gap-2 mb-2">
                  <div className={`w-2 h-2 rounded-full ${cat.severity === 'critical' ? 'bg-red-500' : 'bg-amber-500'}`} />
                  <span className="text-[12px] font-medium text-apple-text">{cat.theme}</span>
                  <span className="text-[10px] font-mono text-apple-tertiary ml-auto">{cat.count}</span>
                </div>
                <p className="text-[11px] text-apple-secondary leading-relaxed mb-2.5">{cat.description}</p>
                <div className="flex flex-wrap gap-1">
                  {cat.affected_sites.slice(0, 5).map(siteId => (
                    <span
                      key={siteId}
                      className="text-[10px] px-1.5 py-0.5 rounded-md bg-apple-grey-50 text-apple-secondary"
                    >
                      {siteId}
                    </span>
                  ))}
                  {cat.affected_sites.length > 5 && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-apple-grey-50 text-apple-tertiary">
                      +{cat.affected_sites.length - 5} more
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </motion.div>
      )}
    </>
  )
}

// ── KPI Card ─────────────────────────────────────────────────────────────────
function KPICard({ label, value, subvalue, trend, metric }) {
  const [showTooltip, setShowTooltip] = useState(false)
  const dotStyles = {
    good: 'from-emerald-500 to-emerald-400',
    neutral: 'from-amber-500 to-amber-400',
    warn: 'from-red-500 to-red-400',
  }
  const dotStyle = dotStyles[trend] || 'from-apple-grey-400 to-apple-grey-300'

  return (
    <div
      className="bg-white rounded-2xl p-5 shadow-sm border border-apple-grey-100 hover:shadow-md transition-shadow duration-200 relative cursor-help"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <div className="flex items-start justify-between mb-3">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-apple-tertiary">{label}</p>
        <div className={`w-2 h-2 rounded-full bg-gradient-to-br ${dotStyle}`} />
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-[36px] font-light text-apple-text tracking-tight leading-none">{value}</span>
        {subvalue && (
          <span className="text-[14px] text-apple-muted">{subvalue}</span>
        )}
      </div>

      {showTooltip && metric && (
        <div className="absolute left-0 right-0 top-full mt-2 z-50 p-4 bg-apple-grey-900 text-white rounded-xl shadow-xl text-xs">
          <div className="space-y-2">
            <div>
              <span className="text-apple-grey-400 uppercase tracking-wider text-[10px]">Formula</span>
              <p className="text-apple-grey-100 font-mono text-[11px] mt-0.5">{metric.formula}</p>
            </div>
            <div>
              <span className="text-apple-grey-400 uppercase tracking-wider text-[10px]">Data Source</span>
              <p className="text-apple-grey-100 mt-0.5">{metric.data_source}</p>
            </div>
            <div>
              <span className="text-apple-grey-400 uppercase tracking-wider text-[10px]">Sample Size</span>
              <p className="text-apple-grey-100 mt-0.5">{metric.sample_size?.toLocaleString() || 'N/A'} records</p>
            </div>
          </div>
          <div className="absolute -top-2 left-1/2 transform -translate-x-1/2 border-8 border-transparent border-b-apple-grey-900"></div>
        </div>
      )}
    </div>
  )
}

// ── Vendor View ──────────────────────────────────────────────────────────────
function VendorView() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getVendorScorecards()
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const vendors = data?.vendors || []
  const ragCounts = { green: 0, amber: 0, red: 0 }
  vendors.forEach(v => {
    const rag = (v.overall_rag || '').toLowerCase()
    if (rag === 'green') ragCounts.green++
    else if (rag === 'amber') ragCounts.amber++
    else if (rag === 'red') ragCounts.red++
  })

  return (
    <>
      <div className="mb-6">
        <h1 className="text-[20px] font-semibold text-apple-text">Vendor Performance</h1>
        <p className="text-caption text-apple-secondary mt-1">{vendors.length} vendors tracked</p>
      </div>
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-5 h-5 animate-spin text-apple-tertiary" />
        </div>
      ) : error ? (
        <p className="text-[13px] text-red-600 text-center py-8">{error}</p>
      ) : (
        <div className="space-y-5">
          {/* RAG summary row */}
          <div className="flex items-center gap-6 justify-center">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-apple-grey-300" />
              <span className="text-[11px] text-apple-tertiary">{ragCounts.green} on track</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-apple-grey-500" />
              <span className="text-[11px] text-apple-tertiary">{ragCounts.amber} watch</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-apple-grey-800" />
              <span className="text-[11px] text-apple-tertiary">{ragCounts.red} action needed</span>
            </div>
          </div>

          {/* Vendor cards grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {vendors.map(v => {
              const rag = (v.overall_rag || '').toLowerCase()
              const ragDot = rag === 'green' ? 'bg-apple-grey-400' : rag === 'amber' ? 'bg-apple-grey-500' : 'bg-apple-grey-800'
              const kpis = v.kpi_summary || []
              const issues = v.top_issues || []
              const milestones = v.milestones || []
              return (
                <div key={v.vendor_id} className="bg-white rounded-xl border border-apple-grey-100 p-4 hover:border-apple-grey-200 transition-colors">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <div className={`w-1.5 h-1.5 rounded-full ${ragDot}`} />
                        <span className="text-[13px] font-medium text-apple-text">{v.name}</span>
                      </div>
                      <span className="text-[11px] text-apple-tertiary mt-0.5 block pl-3.5">{v.vendor_type}{v.country_hq ? ` · ${v.country_hq}` : ''}</span>
                    </div>
                    <span className="text-[12px] font-mono text-apple-tertiary">
                      ${((v.contract_value || 0) / 1_000_000).toFixed(1)}M
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-[11px] text-apple-tertiary mb-3 pl-3.5">
                    <span>{v.active_sites || 0} sites</span>
                    <span className="text-apple-grey-200">·</span>
                    <span>{kpis.length} KPIs</span>
                    {v.issue_count > 0 && (<>
                      <span className="text-apple-grey-200">·</span>
                      <span className="text-apple-text font-medium">{v.issue_count} open</span>
                    </>)}
                  </div>

                  {kpis.length > 0 && (
                    <div className="border-t border-apple-grey-50 pt-2.5 mb-2.5 space-y-1.5">
                      {kpis.map((k, i) => {
                        const kStatus = (k.status || '').toLowerCase()
                        const isOff = kStatus === 'red' || kStatus === 'amber'
                        return (
                          <div key={i} className="flex items-center justify-between pl-3.5">
                            <span className={`text-[10px] ${isOff ? 'text-apple-text' : 'text-apple-tertiary'}`}>{k.kpi_name}</span>
                            <span className={`text-[10px] font-mono ${isOff ? 'text-apple-text font-medium' : 'text-apple-tertiary'}`}>
                              {k.value != null ? (k.kpi_name.includes('%') || k.kpi_name.includes('Rate') ? `${k.value.toFixed(0)}%` : k.value.toFixed(1)) : '—'}
                              {k.target != null && <span className="text-apple-grey-300"> / {k.kpi_name.includes('%') || k.kpi_name.includes('Rate') ? `${k.target.toFixed(0)}%` : k.target.toFixed(0)}</span>}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  )}

                  {issues.length > 0 && (
                    <div className="border-t border-apple-grey-50 pt-2.5 mb-2.5 space-y-1 pl-3.5">
                      {issues.map((iss, i) => (
                        <p key={i} className="text-[10px] text-apple-secondary leading-snug">
                          <span className="text-apple-text font-medium">{iss.severity}</span> — {iss.description}
                        </p>
                      ))}
                    </div>
                  )}

                  {milestones.length > 0 && (
                    <div className="border-t border-apple-grey-50 pt-2.5 flex items-center gap-1.5 flex-wrap pl-3.5">
                      {milestones.map((m, i) => {
                        const isLate = (m.status || '').toLowerCase() === 'delayed' || (m.status || '').toLowerCase() === 'at risk'
                        return (
                          <span key={i} className={`text-[9px] px-1.5 py-0.5 rounded-md ${isLate ? 'bg-apple-grey-100 text-apple-text font-medium' : 'bg-apple-grey-50 text-apple-tertiary'}`}>
                            {m.milestone_name}{m.delay_days > 0 ? ` +${m.delay_days}d` : ''}
                          </span>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </>
  )
}

// ── Financial View ───────────────────────────────────────────────────────────
function FinancialView() {
  const [summary, setSummary] = useState(null)
  const [costData, setCostData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([
      getFinancialSummary(),
      getCostPerPatient().catch(() => null),
    ])
      .then(([s, c]) => { setSummary(s); setCostData(c) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const fmt = (n) => {
    if (n == null) return '—'
    if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
    if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(0)}K`
    return `$${n.toLocaleString()}`
  }

  const topSites = (costData?.sites || [])
    .sort((a, b) => Math.abs(b.variance_pct || 0) - Math.abs(a.variance_pct || 0))
    .slice(0, 8)

  return (
    <>
      <div className="mb-6">
        <h1 className="text-[20px] font-semibold text-apple-text">Financial Overview</h1>
        <p className="text-caption text-apple-secondary mt-1">Budget, spend & cost variance</p>
      </div>
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-5 h-5 animate-spin text-apple-tertiary" />
        </div>
      ) : error ? (
        <p className="text-[13px] text-red-600 text-center py-8">{error}</p>
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: 'Total Budget', value: fmt(summary?.total_budget) },
              { label: 'Spent', value: fmt(summary?.spent_to_date) },
              { label: 'Remaining', value: fmt(summary?.remaining) },
              { label: 'Forecast', value: fmt(summary?.forecast_total) },
            ].map(m => (
              <div key={m.label} className="bg-white rounded-xl border border-apple-grey-100 p-4 text-center">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-apple-tertiary mb-1">{m.label}</p>
                <p className="text-[22px] font-light font-mono text-apple-text">{m.value}</p>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-center gap-6">
            {summary?.variance_pct != null && (
              <span className={`text-[12px] font-mono px-2.5 py-1 rounded-lg ${
                summary.variance_pct > 5 ? 'bg-red-50 text-red-600' : summary.variance_pct > 0 ? 'bg-amber-50 text-amber-600' : 'bg-emerald-50 text-emerald-600'
              }`}>
                Variance: {summary.variance_pct > 0 ? '+' : ''}{summary.variance_pct.toFixed(1)}%
              </span>
            )}
            {summary?.burn_rate != null && (
              <span className="text-[12px] font-mono text-apple-secondary">
                Burn: {fmt(summary.burn_rate)}/mo
              </span>
            )}
            {summary?.spend_trend && (
              <span className="text-[11px] text-apple-tertiary">
                Trend: {summary.spend_trend}
              </span>
            )}
          </div>

          {topSites.length > 0 && (
            <div className="bg-white rounded-xl border border-apple-grey-100 overflow-hidden">
              <div className="px-4 py-3 border-b border-apple-grey-100">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-apple-tertiary">Top Sites by Cost Variance</p>
              </div>
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="text-[10px] uppercase tracking-wider text-apple-tertiary border-b border-apple-grey-50">
                    <th className="text-left px-4 py-2 font-semibold">Site</th>
                    <th className="text-right px-4 py-2 font-semibold">Cost/Patient</th>
                    <th className="text-right px-4 py-2 font-semibold">Variance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-apple-grey-50">
                  {topSites.map((s, i) => (
                    <tr key={i} className="hover:bg-apple-grey-50 transition-colors">
                      <td className="px-4 py-2 text-apple-text">{s.site_name || s.site_id}</td>
                      <td className="px-4 py-2 text-right font-mono text-apple-secondary">
                        ${(s.cost_per_randomized || 0).toLocaleString()}
                      </td>
                      <td className="px-4 py-2 text-right font-mono">
                        <span className={s.variance_pct > 10 ? 'text-red-500' : s.variance_pct > 0 ? 'text-amber-500' : 'text-emerald-500'}>
                          {s.variance_pct > 0 ? '+' : ''}{(s.variance_pct || 0).toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </>
  )
}

// ── Data Quality View ────────────────────────────────────────────────────────
function DataQualityView() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getDataQualityDashboard()
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const sites = (data?.sites || [])
    .sort((a, b) => (b.mean_entry_lag || 0) - (a.mean_entry_lag || 0))
    .slice(0, 12)

  const maxLag = Math.max(...sites.map(s => s.mean_entry_lag || 0), 1)
  const maxOpen = Math.max(...sites.map(s => s.open_queries || 0), 1)

  return (
    <>
      <div className="mb-6">
        <h1 className="text-[20px] font-semibold text-apple-text">Data Quality</h1>
        <p className="text-caption text-apple-secondary mt-1">Entry lag, queries & corrections across sites</p>
      </div>
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-5 h-5 animate-spin text-apple-tertiary" />
        </div>
      ) : error ? (
        <p className="text-[13px] text-red-600 text-center py-8">{error}</p>
      ) : (
        <div className="space-y-5">
          <div className="flex items-center justify-center gap-8">
            <div className="text-center">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-apple-tertiary mb-1">Study Mean Entry Lag</p>
              <p className="text-[28px] font-light font-mono text-apple-text">{(data?.study_mean_entry_lag || 0).toFixed(1)}<span className="text-[14px] text-apple-tertiary ml-1">days</span></p>
            </div>
            <div className="w-px h-10 bg-apple-grey-200" />
            <div className="text-center">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-apple-tertiary mb-1">Total Queries</p>
              <p className="text-[28px] font-light font-mono text-apple-text">{(data?.study_total_queries || 0).toLocaleString()}</p>
            </div>
          </div>

          {sites.length > 0 && (
            <div className="bg-white rounded-xl border border-apple-grey-100 overflow-hidden">
              <div className="px-4 py-3 border-b border-apple-grey-100">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-apple-tertiary">Worst DQ Sites (by Entry Lag)</p>
              </div>
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="text-[10px] uppercase tracking-wider text-apple-tertiary border-b border-apple-grey-50">
                    <th className="text-left px-4 py-2 font-semibold">Site</th>
                    <th className="text-right px-4 py-2 font-semibold">Entry Lag</th>
                    <th className="px-4 py-2 font-semibold w-24"></th>
                    <th className="text-right px-4 py-2 font-semibold">Open Queries</th>
                    <th className="px-4 py-2 font-semibold w-24"></th>
                    <th className="text-right px-4 py-2 font-semibold">Corrections</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-apple-grey-50">
                  {sites.map((s, i) => (
                    <tr key={i} className="hover:bg-apple-grey-50 transition-colors">
                      <td className="px-4 py-2 text-apple-text">{s.site_id}</td>
                      <td className="px-4 py-2 text-right font-mono text-apple-secondary">{(s.mean_entry_lag || 0).toFixed(1)}d</td>
                      <td className="px-4 py-2">
                        <div className="w-full h-1.5 bg-apple-grey-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${(s.mean_entry_lag || 0) > maxLag * 0.7 ? 'bg-red-400' : (s.mean_entry_lag || 0) > maxLag * 0.4 ? 'bg-amber-400' : 'bg-emerald-400'}`}
                            style={{ width: `${((s.mean_entry_lag || 0) / maxLag) * 100}%` }}
                          />
                        </div>
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-apple-secondary">{s.open_queries || 0}</td>
                      <td className="px-4 py-2">
                        <div className="w-full h-1.5 bg-apple-grey-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${(s.open_queries || 0) > maxOpen * 0.7 ? 'bg-red-400' : (s.open_queries || 0) > maxOpen * 0.4 ? 'bg-amber-400' : 'bg-emerald-400'}`}
                            style={{ width: `${((s.open_queries || 0) / maxOpen) * 100}%` }}
                          />
                        </div>
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-apple-secondary">{s.correction_count || 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </>
  )
}

// ── Enrollment View ──────────────────────────────────────────────────────────
function EnrollmentView() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getEnrollmentDashboard()
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const totalScreened = data?.study_total_screened || 0
  const totalRandomized = data?.study_total_randomized || 0
  const target = data?.study_target || 0
  const pctTarget = data?.study_pct_of_target || 0
  const passed = totalScreened > 0 ? totalScreened - Math.round(totalScreened * 0.3) : 0

  const sites = (data?.sites || [])
    .map(s => ({
      ...s,
      enrollPct: s.target > 0 ? ((s.randomized || 0) / s.target) * 100 : 0,
    }))
    .sort((a, b) => a.enrollPct - b.enrollPct)
    .slice(0, 12)

  return (
    <>
      <div className="mb-6">
        <h1 className="text-[20px] font-semibold text-apple-text">Enrollment</h1>
        <p className="text-caption text-apple-secondary mt-1">Screening, randomization & site progress</p>
      </div>
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-5 h-5 animate-spin text-apple-tertiary" />
        </div>
      ) : error ? (
        <p className="text-[13px] text-red-600 text-center py-8">{error}</p>
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: 'Screened', value: totalScreened.toLocaleString() },
              { label: 'Randomized', value: totalRandomized.toLocaleString() },
              { label: 'Target', value: target.toLocaleString() },
              { label: '% of Target', value: `${pctTarget.toFixed(0)}%` },
            ].map(m => (
              <div key={m.label} className="bg-white rounded-xl border border-apple-grey-100 p-4 text-center">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-apple-tertiary mb-1">{m.label}</p>
                <p className="text-[22px] font-light font-mono text-apple-text">{m.value}</p>
              </div>
            ))}
          </div>

          <div className="bg-white rounded-xl border border-apple-grey-100 p-5">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-apple-tertiary mb-3">Enrollment Funnel</p>
            <div className="space-y-2">
              {[
                { label: 'Screened', count: totalScreened, pct: 100 },
                { label: 'Passed Screening', count: passed, pct: totalScreened > 0 ? (passed / totalScreened) * 100 : 0 },
                { label: 'Randomized', count: totalRandomized, pct: totalScreened > 0 ? (totalRandomized / totalScreened) * 100 : 0 },
              ].map(stage => (
                <div key={stage.label} className="flex items-center gap-3">
                  <span className="text-[11px] text-apple-secondary w-32 text-right shrink-0">{stage.label}</span>
                  <div className="flex-1 h-5 bg-apple-grey-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-apple-grey-500 rounded-full transition-all"
                      style={{ width: `${stage.pct}%` }}
                    />
                  </div>
                  <span className="text-[11px] font-mono text-apple-secondary w-16 shrink-0">{stage.count.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>

          {sites.length > 0 && (
            <div className="bg-white rounded-xl border border-apple-grey-100 overflow-hidden">
              <div className="px-4 py-3 border-b border-apple-grey-100">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-apple-tertiary">Lowest Enrollment Sites</p>
              </div>
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="text-[10px] uppercase tracking-wider text-apple-tertiary border-b border-apple-grey-50">
                    <th className="text-left px-4 py-2 font-semibold">Site</th>
                    <th className="text-right px-4 py-2 font-semibold">Randomized</th>
                    <th className="text-right px-4 py-2 font-semibold">Target</th>
                    <th className="px-4 py-2 font-semibold">Progress</th>
                    <th className="text-right px-4 py-2 font-semibold">%</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-apple-grey-50">
                  {sites.map((s, i) => (
                    <tr key={i} className="hover:bg-apple-grey-50 transition-colors">
                      <td className="px-4 py-2 text-apple-text">{s.site_name || s.site_id}</td>
                      <td className="px-4 py-2 text-right font-mono text-apple-secondary">{s.randomized || 0}</td>
                      <td className="px-4 py-2 text-right font-mono text-apple-secondary">{s.target || 0}</td>
                      <td className="px-4 py-2">
                        <div className="w-full h-1.5 bg-apple-grey-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${s.enrollPct > 70 ? 'bg-emerald-400' : s.enrollPct > 40 ? 'bg-amber-400' : 'bg-red-400'}`}
                            style={{ width: `${Math.min(s.enrollPct, 100)}%` }}
                          />
                        </div>
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-apple-secondary">{s.enrollPct.toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </>
  )
}
