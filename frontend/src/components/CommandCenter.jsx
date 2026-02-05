import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Send, AlertTriangle, TrendingDown, Clock, ChevronRight, 
  Loader2, MapPin, Shield, DollarSign, Users, X, ArrowLeft,
  MessageSquare, Sparkles, BarChart3, Database, Truck, History,
  Activity, FileText, ChevronDown, ExternalLink
} from 'lucide-react'
import { useStore } from '../lib/store'
import { 
  getStudySummary, getAttentionSites, startInvestigation, 
  connectInvestigationStream, getQueryStatus, getDataQualityDashboard,
  getEnrollmentDashboard, getSitesOverview
} from '../lib/api'
import { WorldMap } from './WorldMap'

const QUICK_ACTIONS = [
  { label: 'Which sites need attention this week?', icon: AlertTriangle },
  { label: 'Show me enrollment bottlenecks', icon: TrendingDown },
  { label: 'Any data integrity concerns?', icon: Shield },
  { label: 'What is driving budget variance?', icon: DollarSign },
]

const EXPLORE_ACTIONS = [
  { label: 'Vendor performance summary', icon: Truck, query: 'Give me a vendor performance summary' },
  { label: 'Financial health overview', icon: DollarSign, query: 'What is the financial health of this study?' },
  { label: 'Data quality trends', icon: Database, query: 'Show me data quality trends across sites' },
  { label: 'Enrollment velocity', icon: Activity, query: 'What is the enrollment velocity and trajectory?' },
]

const PHASE_LABELS = {
  routing: 'Analyzing query...',
  perceive: 'Gathering data...',
  reason: 'Analyzing patterns...',
  plan: 'Planning investigation...',
  act: 'Running analysis...',
  reflect: 'Evaluating findings...',
  synthesize: 'Preparing response...',
  complete: 'Complete',
}

export function CommandCenter() {
  const navigate = useNavigate()
  const { studyId } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const { setStudyData, siteNameMap, setSiteNameMap } = useStore()
  
  const [studySummary, setStudySummary] = useState(null)
  const [attentionItems, setAttentionItems] = useState([])
  const [allSites, setAllSites] = useState([])
  const [kpis, setKpis] = useState(null)
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
  
  const inputRef = useRef(null)
  const resultsRef = useRef(null)
  const wsRef = useRef(null)

  useEffect(() => {
    async function loadData() {
      try {
        const [summary, attention, dqData, enrollData, sitesData] = await Promise.all([
          getStudySummary(),
          getAttentionSites(),
          getDataQualityDashboard().catch(() => null),
          getEnrollmentDashboard().catch(() => null),
          getSitesOverview().catch(() => null)
        ])
        
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

        setKpis({
          dqScore: avgDqScore,
          criticalSites: attention?.sites?.filter(s => s.risk_level === 'critical').length || 0,
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
      <header className="sticky top-0 z-50 bg-apple-surface/80 backdrop-blur-xl border-b border-apple-divider">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => navigate('/')}
              className="button-icon"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
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

      <main className="max-w-7xl mx-auto px-6 py-8">
        {conversationHistory.length === 0 && !isInvestigating ? (
          <div className="space-y-10">
            {kpis && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="grid grid-cols-2 md:grid-cols-4 gap-4"
              >
                <KPICard 
                  label="Enrolled" 
                  value={`${studySummary?.enrolled || 0}`}
                  subvalue={`of ${studySummary?.target || 0}`}
                  trend={progress >= 80 ? 'good' : progress >= 50 ? 'neutral' : 'warn'}
                />
                <KPICard 
                  label="Sites at Risk" 
                  value={`${kpis.criticalSites}`}
                  trend={kpis.criticalSites === 0 ? 'good' : kpis.criticalSites <= 3 ? 'neutral' : 'warn'}
                />
                <KPICard 
                  label="DQ Score" 
                  value={kpis.dqScore ? `${Math.round(kpis.dqScore)}` : '—'}
                  trend={kpis.dqScore >= 85 ? 'good' : kpis.dqScore >= 70 ? 'neutral' : 'warn'}
                />
                <KPICard 
                  label="Screen Fail" 
                  value={kpis.screenFailRate !== null ? `${kpis.screenFailRate}%` : '—'}
                  trend={kpis.screenFailRate === null ? 'neutral' : kpis.screenFailRate <= 25 ? 'good' : kpis.screenFailRate <= 40 ? 'neutral' : 'warn'}
                />
              </motion.div>
            )}

            {allSites.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <WorldMap 
                  sites={allSites}
                  onSiteClick={(site) => handleSiteClick(site.site_id || site.id)}
                  onSiteHover={() => {}}
                  hoveredSite={null}
                  height="h-[320px]"
                  highlightedSiteNames={new Set(attentionItems.map(a => a.name))}
                  needsAttentionSiteIds={new Set(attentionItems.map(a => a.id))}
                />
              </motion.div>
            )}

            {/* Search Section */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="bg-white rounded-3xl p-8 shadow-sm border border-apple-grey-100"
            >
              <div className="text-center mb-6">
                <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-apple-grey-50 rounded-full mb-4">
                  <Sparkles className="w-3.5 h-3.5 text-apple-grey-500" />
                  <span className="text-[11px] font-medium text-apple-tertiary uppercase tracking-wider">AI-Powered Investigation</span>
                </div>
                
                <h1 className="text-2xl font-semibold text-apple-text mb-2">
                  What would you like to investigate?
                </h1>
                
                <p className="text-[13px] text-apple-secondary max-w-md mx-auto">
                  Ask about enrollment, data quality, sites, vendors, or financials.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="relative mb-5">
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g., Why is SITE-074 underperforming?"
                  className="w-full px-5 py-4 pr-14 bg-apple-grey-50 border border-apple-grey-200 rounded-2xl text-[14px] text-apple-text placeholder:text-apple-tertiary focus:outline-none focus:border-apple-grey-400 focus:bg-white transition-all"
                />
                <button
                  type="submit"
                  disabled={!query.trim()}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 w-10 h-10 flex items-center justify-center rounded-xl bg-apple-grey-800 text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-apple-grey-700 transition-all"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>

              <div className="flex flex-wrap justify-center gap-2">
                {QUICK_ACTIONS.map((action) => (
                  <button
                    key={action.label}
                    onClick={() => handleQuickAction(action.label)}
                    className="inline-flex items-center gap-2 px-3.5 py-2 bg-apple-grey-50 border border-apple-grey-100 rounded-xl text-[12px] text-apple-secondary hover:text-apple-text hover:bg-apple-grey-100 hover:border-apple-grey-200 transition-all"
                  >
                    <action.icon className="w-3.5 h-3.5" />
                    {action.label}
                  </button>
                ))}
              </div>

              <div className="text-center mt-4">
                <button
                  onClick={() => setShowExplore(!showExplore)}
                  className="inline-flex items-center gap-1 text-[11px] text-apple-muted hover:text-apple-secondary transition-colors"
                >
                  <span>Explore more</span>
                  <ChevronDown className={`w-3 h-3 transition-transform ${showExplore ? 'rotate-180' : ''}`} />
                </button>
                <AnimatePresence>
                  {showExplore && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="flex flex-wrap justify-center gap-2 pt-3">
                        {EXPLORE_ACTIONS.map((action) => (
                          <button
                            key={action.label}
                            onClick={() => handleQuickAction(action.query)}
                            className="inline-flex items-center gap-2 px-3.5 py-2 bg-apple-grey-50 border border-apple-grey-100 rounded-xl text-[12px] text-apple-secondary hover:text-apple-text hover:bg-apple-grey-100 hover:border-apple-grey-200 transition-all"
                          >
                            <action.icon className="w-3.5 h-3.5" />
                            {action.label}
                          </button>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>

            {attentionItems.length > 0 && (
              <motion.section
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <h2 className="text-[11px] font-semibold text-apple-tertiary uppercase tracking-wider mb-4 text-center">
                  Needs Attention
                </h2>
                <div className="bg-white rounded-2xl shadow-sm border border-apple-grey-100 overflow-hidden divide-y divide-apple-grey-100">
                  {attentionItems.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => handleSiteClick(item.id)}
                      className="w-full flex items-center justify-between p-4 hover:bg-apple-grey-50 transition-all text-left group"
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-2 h-2 rounded-full ${
                          item.type === 'critical' ? 'bg-red-500' : 'bg-amber-500'
                        }`} />
                        <div>
                          <span className="text-[14px] font-medium text-apple-text">{item.name}</span>
                          {item.metric && <p className="text-[11px] text-apple-muted mt-0.5">{item.metric}</p>}
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        {item.value && <span className="text-[12px] font-mono text-apple-secondary">{item.value}</span>}
                        <ChevronRight className="w-4 h-4 text-apple-grey-300 group-hover:text-apple-grey-500 transition-colors" />
                      </div>
                    </button>
                  ))}
                </div>
              </motion.section>
            )}
          </div>
        ) : (
          <div className="space-y-6" ref={resultsRef}>
            {conversationHistory.map((msg, i) => (
              <ConversationMessage 
                key={i} 
                message={msg} 
                resolveText={resolveText}
                onSiteClick={handleSiteClick}
              />
            ))}
            
            {isInvestigating && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-3 p-4 bg-apple-surface border border-apple-border rounded-xl"
              >
                <Loader2 className="w-4 h-4 text-[#5856D6] animate-spin" />
                <span className="text-body text-apple-secondary">
                  {PHASE_LABELS[currentPhase] || 'Processing...'}
                </span>
              </motion.div>
            )}

            {error && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="p-4 bg-red-50 border border-red-200 rounded-xl"
              >
                <p className="text-body text-red-700">{error}</p>
              </motion.div>
            )}

            <form onSubmit={handleSubmit} className="relative mt-8">
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask a follow-up question..."
                disabled={isInvestigating}
                className="w-full px-5 py-4 pr-14 bg-apple-surface border border-apple-border rounded-2xl text-body text-apple-text placeholder:text-apple-secondary/50 focus:outline-none focus:border-apple-text/30 focus:ring-4 focus:ring-apple-text/5 transition-all disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={!query.trim() || isInvestigating}
                className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 flex items-center justify-center rounded-xl bg-apple-text text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-apple-text/90 transition-all"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        )}
      </main>
    </div>
  )
}

function KPICard({ label, value, subvalue, trend }) {
  const dotStyles = {
    good: 'from-emerald-500 to-emerald-400',
    neutral: 'from-amber-500 to-amber-400',
    warn: 'from-red-500 to-red-400',
  }
  const dotStyle = dotStyles[trend] || 'from-apple-grey-400 to-apple-grey-300'
  
  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-apple-grey-100 hover:shadow-md transition-shadow duration-200">
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
    </div>
  )
}

function ConversationMessage({ message, resolveText, onSiteClick }) {
  if (message.role === 'user') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-end"
      >
        <div className="max-w-[80%] px-4 py-3 bg-apple-grey-900 text-white rounded-apple-lg rounded-br-apple-sm">
          <p className="text-body">{message.content}</p>
        </div>
      </motion.div>
    )
  }

  const data = message.content
  const synthesis = data?.synthesis
  const hypotheses = data?.hypotheses || []
  const nbas = data?.next_best_actions || []
  const topHypothesis = hypotheses[0]
  const topAction = nbas.find(n => n.priority === 1) || nbas[0]

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      {synthesis?.executive_summary && (
        <div className="card-elevated p-5">
          <p className="text-body text-apple-text leading-relaxed">
            {resolveText(synthesis.executive_summary)}
          </p>
        </div>
      )}

      {topHypothesis && (
        <div className="card p-4 border-l-[3px] border-l-apple-warning">
          <p className="section-header mb-2">Root Cause</p>
          <p className="text-body text-apple-text">{resolveText(topHypothesis.finding)}</p>
          {topHypothesis.causal_chain && (
            <div className="flex items-center gap-2 mt-3 flex-wrap">
              {topHypothesis.causal_chain.split(/\s*(?:→|->)\s*/).filter(Boolean).map((node, i, arr) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-caption text-apple-secondary bg-apple-grey-100 px-2 py-0.5 rounded-apple-sm">{node.trim()}</span>
                  {i < arr.length - 1 && <span className="text-apple-grey-400">→</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {topAction && (
        <div className="card p-4 border-l-[3px] border-l-apple-accent">
          <div className="flex items-center gap-2 mb-2">
            <p className="section-header">Recommended Action</p>
            {topAction.urgency === 'immediate' && (
              <span className="text-[10px] font-medium text-white bg-apple-grey-800 px-1.5 py-0.5 rounded-full">Now</span>
            )}
          </div>
          <p className="text-body text-apple-text">{resolveText(topAction.action)}</p>
          {topAction.owner && (
            <p className="text-caption text-apple-tertiary mt-2">{topAction.owner}</p>
          )}
        </div>
      )}

      {hypotheses.length > 1 && (
        <p className="text-caption text-apple-tertiary text-center">
          + {hypotheses.length - 1} more findings, {nbas.length - 1} more actions
        </p>
      )}
    </motion.div>
  )
}
