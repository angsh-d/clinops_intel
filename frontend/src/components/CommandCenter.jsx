import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Send, AlertTriangle, TrendingDown, Clock, ChevronRight, 
  Loader2, MapPin, Shield, DollarSign, Users, X, ArrowLeft,
  MessageSquare, Sparkles, BarChart3, Database, Truck, History,
  Activity, FileText, ChevronDown
} from 'lucide-react'
import { useStore } from '../lib/store'
import { 
  getStudySummary, getAttentionSites, startInvestigation, 
  connectInvestigationStream, getQueryStatus, getDataQualityDashboard,
  getEnrollmentDashboard
} from '../lib/api'
import { Site360Panel } from './Site360Panel'

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
  const { setStudyData, siteNameMap, setSiteNameMap } = useStore()
  
  const [studySummary, setStudySummary] = useState(null)
  const [attentionItems, setAttentionItems] = useState([])
  const [kpis, setKpis] = useState(null)
  const [loading, setLoading] = useState(true)
  
  const [query, setQuery] = useState('')
  const [isInvestigating, setIsInvestigating] = useState(false)
  const [currentPhase, setCurrentPhase] = useState(null)
  const [phases, setPhases] = useState([])
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  
  const [selectedSiteId, setSelectedSiteId] = useState(null)
  const [conversationHistory, setConversationHistory] = useState([])
  const [showExplore, setShowExplore] = useState(false)
  
  const inputRef = useRef(null)
  const resultsRef = useRef(null)
  const wsRef = useRef(null)

  useEffect(() => {
    async function loadData() {
      try {
        const [summary, attention, dqData, enrollData] = await Promise.all([
          getStudySummary(),
          getAttentionSites(),
          getDataQualityDashboard().catch(() => null),
          getEnrollmentDashboard().catch(() => null)
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

        setKpis({
          dqScore: dqData?.study_average_dq_score || null,
          criticalSites: attention?.sites?.filter(s => s.risk_level === 'critical').length || 0,
          enrollmentRate: enrollData?.current_weekly_rate || null,
          screenFailRate: enrollData?.screen_failure_rate || null,
        })
      } catch (err) {
        console.error('Failed to load data:', err)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [studyId])

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
      const { query_id } = await startInvestigation(userQuery)
      
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
          setError(err.message || 'Investigation failed')
          setIsInvestigating(false)
        },
      })
    } catch (err) {
      setError(err.message || 'Failed to start investigation')
      setIsInvestigating(false)
    }
  }

  const handleQuickAction = (actionQuery) => {
    setQuery(actionQuery)
    setTimeout(() => handleSubmit(), 50)
  }

  const handleSiteClick = (siteId) => {
    setSelectedSiteId(siteId)
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
  }

  return (
    <div className="min-h-screen bg-apple-bg">
      <header className="sticky top-0 z-50 glass border-b border-apple-border">
        <div className="px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => navigate('/')}
              className="flex items-center gap-2 text-apple-secondary hover:text-apple-text transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <img src="/saama_logo.svg" alt="Saama" className="h-6" />
            </button>
            <div className="w-px h-5 bg-apple-border" />
            <span className="text-body font-medium text-apple-text">{studySummary?.study_id || studyId}</span>
            <span className="text-caption text-apple-secondary">{studySummary?.phase}</span>
          </div>
          
          <div className="flex items-center gap-6 text-caption">
            <div className="flex items-center gap-2">
              <div className="w-20 h-1.5 bg-apple-border rounded-full overflow-hidden">
                <div 
                  className="h-full bg-apple-text rounded-full transition-all" 
                  style={{ width: `${progress}%` }} 
                />
              </div>
              <span className="font-mono text-apple-text">
                {studySummary?.enrolled || 0}/{studySummary?.target || 0}
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-apple-secondary">
              <MapPin className="w-3.5 h-3.5" />
              <span>{studySummary?.total_sites || 0} sites</span>
            </div>
            {conversationHistory.length > 0 && (
              <button
                onClick={clearConversation}
                className="text-apple-secondary hover:text-apple-text transition-colors"
              >
                New chat
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
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
                  value={kpis.screenFailRate ? `${Math.round(kpis.screenFailRate)}%` : '—'}
                  trend={kpis.screenFailRate <= 25 ? 'good' : kpis.screenFailRate <= 40 ? 'neutral' : 'warn'}
                />
              </motion.div>
            )}

            <div className="text-center pt-4">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="inline-flex items-center gap-2 px-4 py-2 bg-apple-surface border border-apple-border rounded-full mb-6"
              >
                <Sparkles className="w-4 h-4 text-[#5856D6]" />
                <span className="text-caption text-apple-secondary">AI-Powered Investigation</span>
              </motion.div>
              
              <motion.h1 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="text-3xl font-light text-apple-text mb-3"
              >
                What would you like to investigate?
              </motion.h1>
              
              <motion.p 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="text-body text-apple-secondary max-w-lg mx-auto"
              >
                Ask about enrollment, data quality, sites, vendors, or financials. 
                I'll analyze across multiple data sources and surface insights.
              </motion.p>
            </div>

            <motion.form 
              onSubmit={handleSubmit}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="relative"
            >
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g., Why is SITE-074 underperforming?"
                className="w-full px-5 py-4 pr-14 bg-apple-surface border border-apple-border rounded-2xl text-body text-apple-text placeholder:text-apple-secondary/50 focus:outline-none focus:border-apple-text/30 focus:ring-4 focus:ring-apple-text/5 transition-all"
              />
              <button
                type="submit"
                disabled={!query.trim()}
                className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 flex items-center justify-center rounded-xl bg-apple-text text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-apple-text/90 transition-all"
              >
                <Send className="w-4 h-4" />
              </button>
            </motion.form>

            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
              className="flex flex-wrap justify-center gap-2"
            >
              {QUICK_ACTIONS.map((action) => (
                <button
                  key={action.label}
                  onClick={() => handleQuickAction(action.label)}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-apple-surface border border-apple-border rounded-full text-caption text-apple-secondary hover:text-apple-text hover:border-apple-text/20 transition-all"
                >
                  <action.icon className="w-3.5 h-3.5" />
                  {action.label}
                </button>
              ))}
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.45 }}
              className="text-center"
            >
              <button
                onClick={() => setShowExplore(!showExplore)}
                className="inline-flex items-center gap-1 text-caption text-apple-secondary hover:text-apple-text transition-colors"
              >
                <span>Explore more</span>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showExplore ? 'rotate-180' : ''}`} />
              </button>
              <AnimatePresence>
                {showExplore && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="flex flex-wrap justify-center gap-2 pt-4">
                      {EXPLORE_ACTIONS.map((action) => (
                        <button
                          key={action.label}
                          onClick={() => handleQuickAction(action.query)}
                          className="inline-flex items-center gap-2 px-4 py-2 bg-apple-surface border border-apple-border rounded-full text-caption text-apple-secondary hover:text-apple-text hover:border-apple-text/20 transition-all"
                        >
                          <action.icon className="w-3.5 h-3.5" />
                          {action.label}
                        </button>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>

            {attentionItems.length > 0 && (
              <motion.section
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
              >
                <h2 className="text-xs font-medium text-apple-secondary uppercase tracking-wide mb-4 text-center">
                  Needs Attention
                </h2>
                <div className="grid gap-3">
                  {attentionItems.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => handleSiteClick(item.id)}
                      className="w-full flex items-center justify-between p-4 bg-apple-surface border border-apple-border rounded-xl hover:border-apple-text/20 transition-all text-left group"
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-2 h-2 rounded-full ${
                          item.type === 'critical' ? 'bg-red-500' : 'bg-amber-500'
                        }`} />
                        <div>
                          <span className="text-body font-medium text-apple-text">{item.name}</span>
                          <p className="text-caption text-apple-secondary">{item.metric}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-caption font-mono text-apple-text">{item.value}</span>
                        <ChevronRight className="w-4 h-4 text-apple-secondary opacity-0 group-hover:opacity-100 transition-opacity" />
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

      <AnimatePresence>
        {selectedSiteId && (
          <Site360Panel 
            siteId={selectedSiteId} 
            onClose={() => setSelectedSiteId(null)}
            onInvestigate={(q) => {
              setQuery(q)
              setSelectedSiteId(null)
              setTimeout(() => handleSubmit(), 50)
            }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

function KPICard({ label, value, subvalue, trend }) {
  const trendColors = {
    good: 'text-emerald-600',
    neutral: 'text-amber-600',
    warn: 'text-red-600',
  }
  
  return (
    <div className="p-4 bg-apple-surface border border-apple-border rounded-xl">
      <p className="text-caption text-apple-secondary mb-1">{label}</p>
      <div className="flex items-baseline gap-1">
        <span className={`text-2xl font-semibold ${trendColors[trend] || 'text-apple-text'}`}>
          {value}
        </span>
        {subvalue && (
          <span className="text-caption text-apple-secondary">{subvalue}</span>
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
        <div className="max-w-[80%] px-4 py-3 bg-apple-text text-white rounded-2xl rounded-br-md">
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
        <div className="p-5 bg-apple-surface border border-apple-border rounded-2xl">
          <p className="text-body text-apple-text leading-relaxed">
            {resolveText(synthesis.executive_summary)}
          </p>
        </div>
      )}

      {topHypothesis && (
        <div className="p-4 bg-amber-50/50 border border-amber-200/50 rounded-xl">
          <p className="text-xs font-medium text-amber-700 uppercase tracking-wide mb-2">Root Cause</p>
          <p className="text-body text-amber-900">{resolveText(topHypothesis.finding)}</p>
          {topHypothesis.causal_chain && (
            <div className="flex items-center gap-2 mt-3 flex-wrap">
              {topHypothesis.causal_chain.split(/\s*(?:→|->)\s*/).filter(Boolean).map((node, i, arr) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-caption text-amber-700 bg-amber-100 px-2 py-0.5 rounded">{node.trim()}</span>
                  {i < arr.length - 1 && <span className="text-amber-400">→</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {topAction && (
        <div className="p-4 bg-blue-50/50 border border-blue-200/50 rounded-xl">
          <div className="flex items-center gap-2 mb-2">
            <p className="text-xs font-medium text-blue-700 uppercase tracking-wide">Recommended Action</p>
            {topAction.urgency === 'immediate' && (
              <span className="text-[10px] font-medium text-white bg-blue-600 px-1.5 py-0.5 rounded">Now</span>
            )}
          </div>
          <p className="text-body text-blue-900">{resolveText(topAction.action)}</p>
          {topAction.owner && (
            <p className="text-caption text-blue-600 mt-2">{topAction.owner}</p>
          )}
        </div>
      )}

      {hypotheses.length > 1 && (
        <p className="text-caption text-apple-secondary text-center">
          + {hypotheses.length - 1} more findings, {nbas.length - 1} more actions
        </p>
      )}
    </motion.div>
  )
}
