import { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { X, ChevronDown, ChevronRight, ChevronLeft, ExternalLink, Copy, Check, Loader2, Search, ArrowRight, AlertCircle, BarChart3, Lightbulb, ListChecks, FileText, Shield, TrendingUp, Link2, MessageSquare } from 'lucide-react'
import { useStore } from '../lib/store'
import { startInvestigation, connectInvestigationStream, getQueryStatus, submitFollowUp } from '../lib/api'
import { Site360Panel } from './Site360Panel'

const PHASE_LABELS = {
  routing: 'Analyzing Query',
  perceive: 'Gathering Data',
  reason: 'Analyzing',
  plan: 'Planning',
  act: 'Investigating',
  reflect: 'Evaluating',
  adaptive_reroute: 'Cross-Domain Re-routing',
  synthesize: 'Synthesizing',
  complete: 'Complete',
}

function ExecutiveBrief({ synthesis, hypotheses, nbas, onShowFullAnalysis, resolveText }) {
  const topHypothesis = hypotheses?.[0]
  const topAction = nbas?.find(n => n.priority === 1) || nbas?.[0]
  
  const parseInsights = () => {
    const text = synthesis?.executive_summary || ''
    const insights = []
    
    const dollarMatch = text.match(/\$([\d,]+(?:\.\d{2})?)/)
    const percentMatch = text.match(/\(?\+?([\d.]+)%\)?/)
    const daysMatch = text.match(/(\d+)\s*days?\s*overdue/i)
    const enrollMatch = text.match(/enrolling\s+(\d+)\s*(?:vs|of)\s*(\d+)/i)
    const delayCostMatch = text.match(/\$([\d,]+(?:\.\d{2})?)\s*delay\s*cost/i)
    
    if (dollarMatch) {
      insights.push({ value: `$${dollarMatch[1]}`, label: 'Over Plan', type: 'primary' })
    }
    if (percentMatch) {
      insights.push({ value: `+${percentMatch[1]}%`, label: 'Variance', type: 'secondary' })
    }
    if (daysMatch) {
      insights.push({ value: daysMatch[1], label: 'Days Overdue', type: 'secondary' })
    }
    if (enrollMatch) {
      insights.push({ value: `${enrollMatch[1]}/${enrollMatch[2]}`, label: 'Enrolled', type: 'secondary' })
    }
    if (delayCostMatch) {
      insights.push({ value: `$${delayCostMatch[1]}`, label: 'Delay Cost', type: 'secondary' })
    }
    
    return insights.slice(0, 3)
  }
  
  const extractStory = () => {
    const text = synthesis?.executive_summary || ''
    const sentences = text.split(/\.\s+/)
    if (sentences.length <= 1) return { headline: text, detail: null }
    return {
      headline: sentences[0] + '.',
      detail: sentences.slice(1, 2).join('. ') + (sentences[1] ? '.' : '')
    }
  }
  
  const insights = parseInsights()
  const story = extractStory()
  const primaryInsight = insights.find(i => i.type === 'primary')
  const secondaryInsights = insights.filter(i => i.type === 'secondary')
  
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6, ease: [0.25, 0.1, 0.25, 1] }}
      className="max-w-2xl mx-auto px-4"
    >
      {/* Primary Metric - Large hero number */}
      {primaryInsight && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="text-center mb-6"
        >
          <span className="text-[64px] font-semibold tracking-tight text-neutral-900 leading-none">
            {primaryInsight.value}
          </span>
          <p className="text-[14px] text-neutral-400 mt-1">{primaryInsight.label}</p>
        </motion.div>
      )}
      
      {/* Secondary Metrics Row */}
      {secondaryInsights.length > 0 && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.15 }}
          className="flex items-center justify-center gap-8 mb-10"
        >
          {secondaryInsights.map((insight, i) => (
            <div key={i} className="text-center">
              <span className="text-[28px] font-medium text-neutral-700">{insight.value}</span>
              <p className="text-[12px] text-neutral-400 mt-0.5">{insight.label}</p>
            </div>
          ))}
        </motion.div>
      )}
      
      {/* Story - Headline and detail as separate lines */}
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="text-center mb-10 space-y-3"
      >
        <p className="text-[19px] font-medium text-neutral-800 leading-relaxed">
          {resolveText(story.headline)}
        </p>
        {story.detail && (
          <p className="text-[15px] text-neutral-500 leading-relaxed">
            {resolveText(story.detail)}
          </p>
        )}
      </motion.div>
      
      {/* Divider */}
      <div className="w-12 h-px bg-neutral-200 mx-auto mb-10" />
      
      {/* Root Cause */}
      {topHypothesis && (
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="text-center mb-10"
        >
          <p className="text-[12px] font-medium text-neutral-400 uppercase tracking-wide mb-3">Root Cause</p>
          <p className="text-[15px] text-neutral-700 leading-relaxed">
            {resolveText(topHypothesis.finding)}
          </p>
          
          {topHypothesis.causal_chain && (
            <div className="flex items-center justify-center gap-2 mt-4 flex-wrap">
              {topHypothesis.causal_chain.split(/\s*(?:→|->)\s*/).filter(Boolean).map((node, i, arr) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-[12px] text-neutral-500">{node.trim()}</span>
                  {i < arr.length - 1 && (
                    <span className="text-neutral-300">→</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </motion.div>
      )}
      
      {/* Priority Action */}
      {topAction && (
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="bg-neutral-50/80 rounded-xl p-6 mb-8"
        >
          <div className="flex items-center gap-2 mb-2">
            <p className="text-[12px] font-medium text-neutral-400 uppercase tracking-wide">Next Step</p>
            {topAction.urgency === 'immediate' && (
              <span className="text-[10px] font-medium text-neutral-900 bg-neutral-200 px-1.5 py-0.5 rounded">
                Now
              </span>
            )}
          </div>
          <p className="text-[15px] text-neutral-800 leading-relaxed">
            {resolveText(topAction.action)}
          </p>
          {topAction.owner && (
            <p className="text-[12px] text-neutral-400 mt-2">{topAction.owner}</p>
          )}
        </motion.div>
      )}
      
      {/* View More Link */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.5 }}
        className="text-center"
      >
        <button
          onClick={onShowFullAnalysis}
          className="text-[14px] text-blue-600 hover:text-blue-700 transition-colors"
        >
          View {hypotheses?.length || 0} findings and {nbas?.length || 0} actions
        </button>
      </motion.div>
    </motion.div>
  )
}

const AGENT_NAMES = {
  data_quality: 'Data Quality',
  enrollment_funnel: 'Enrollment Funnel',
  clinical_trials_gov: 'Competitive Intelligence',
  phantom_compliance: 'Data Integrity',
  site_rescue: 'Site Decision',
  vendor_performance: 'Vendor Performance',
  financial_intelligence: 'Financial Intelligence',
  conductor: 'Orchestrator',
}

/** Replace SITE-xxx IDs in text with human-readable site names. */
function useResolveText() {
  const { siteNameMap } = useStore()
  return (text) => {
    if (!text || typeof text !== 'string') return text
    return text.replace(/SITE-\d+/g, (id) => {
      const name = siteNameMap[id]
      return name ? `${name} (${id})` : id
    })
  }
}

/** Convert 0-1 confidence float to human-readable label + color. */
function confidenceLabel(value) {
  const pct = Math.round((value || 0) * 100)
  if (pct >= 85) return { text: 'High confidence', color: 'text-green-600', bg: 'bg-green-50 border-green-200' }
  if (pct >= 60) return { text: 'Moderate confidence', color: 'text-amber-600', bg: 'bg-amber-50 border-amber-200' }
  return { text: 'Low confidence', color: 'text-red-500', bg: 'bg-red-50 border-red-200' }
}

export function InvestigationTheater() {
  const navigate = useNavigate()
  const routeParams = useParams()
  const { investigation, setInvestigation, studyData, investigationPhases, addInvestigationPhase, investigationResult, setInvestigationResult, investigationError, setInvestigationError, investigationQueryId, setInvestigationQueryId, currentStudyId } = useStore()
  const resolveText = useResolveText()
  const [loading, setLoading] = useState(true)
  const [showTrace, setShowTrace] = useState(false)
  const [timelineCollapsed, setTimelineCollapsed] = useState(true)
  const [phase, setPhase] = useState(() => investigation?.site ? 'overview' : 'analyzing')
  const [displayMode, setDisplayMode] = useState('brief')
  const [followUpInput, setFollowUpInput] = useState('')
  const [followUpLoading, setFollowUpLoading] = useState(false)
  const [linkCopied, setLinkCopied] = useState(false)
  const wsRef = useRef(null)

  // If navigated directly via /investigate/:queryId, load from backend
  useEffect(() => {
    if (routeParams.queryId && !investigation) {
      setInvestigationQueryId(routeParams.queryId)
      async function loadExisting() {
        try {
          const result = await getQueryStatus(routeParams.queryId)
          if (result.status === 'completed') {
            setInvestigationResult({
              synthesis: result.synthesis,
              agent_outputs: result.agent_outputs,
            })
            setInvestigation({ question: result.question || 'Investigation', status: 'complete' })
            setLoading(false)
          } else if (result.status === 'processing' || result.status === 'pending') {
            setInvestigation({ question: result.question || 'Investigation', status: 'routing' })
            const ws = connectInvestigationStream(routeParams.queryId, {
              onPhase: (msg) => addInvestigationPhase(msg),
              onComplete: (msg) => { setInvestigationResult(msg); setLoading(false) },
              onError: (err) => { setInvestigationError(err); setLoading(false) },
            })
            wsRef.current = ws
          }
        } catch {
          setInvestigationError('Investigation not found')
          setLoading(false)
        }
      }
      loadExisting()
    }
  }, [routeParams.queryId])

  const handleLaunchAnalysis = () => {
    setPhase('analyzing')
  }

  const handleShowFullAnalysis = () => {
    setDisplayMode('full')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleBackToSummary = () => {
    setDisplayMode('brief')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleCopyLink = () => {
    const url = investigationQueryId
      ? `${window.location.origin}/investigate/${investigationQueryId}`
      : window.location.href
    navigator.clipboard.writeText(url)
    setLinkCopied(true)
    setTimeout(() => setLinkCopied(false), 2000)
  }

  const handleFollowUp = async () => {
    if (!followUpInput.trim() || !investigationQueryId) return
    setFollowUpLoading(true)
    try {
      // Close existing WebSocket before starting new follow-up
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      const { query_id } = await submitFollowUp(investigationQueryId, followUpInput.trim())
      setFollowUpInput('')
      setInvestigationQueryId(query_id)
      navigate(`/investigate/${query_id}`, { replace: true })
      // Reset and stream new investigation
      setInvestigation({ question: followUpInput.trim(), status: 'routing' })
      setLoading(true)
      const ws = connectInvestigationStream(query_id, {
        onPhase: (msg) => addInvestigationPhase(msg),
        onComplete: (msg) => { setInvestigationResult(msg); setLoading(false); setFollowUpLoading(false) },
        onError: (err) => { setInvestigationError(err); setLoading(false); setFollowUpLoading(false) },
      })
      wsRef.current = ws
    } catch (error) {
      setInvestigationError(error.message)
      setFollowUpLoading(false)
    }
  }

  useEffect(() => {
    if (!investigation || phase !== 'analyzing') return

    let cancelled = false

    async function launch() {
      setLoading(true)

      try {
        const { query_id } = await startInvestigation(
          investigation.question,
          investigation.site?.id
        )

        if (cancelled) return
        setInvestigationQueryId(query_id)
        // Update URL to be shareable
        navigate(`/investigate/${query_id}`, { replace: true })

        const ws = connectInvestigationStream(query_id, {
          onPhase: (msg) => {
            if (!cancelled) addInvestigationPhase(msg)
          },
          onComplete: (msg) => {
            if (!cancelled) {
              setInvestigationResult(msg)
              setLoading(false)
            }
          },
          onError: (err) => {
            if (!cancelled) {
              setInvestigationError(err)
              setLoading(false)
            }
          },
        })
        wsRef.current = ws
      } catch (error) {
        if (!cancelled) {
          setInvestigationError(error.message)
          setLoading(false)
        }
      }
    }

    launch()

    return () => {
      cancelled = true
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [investigation?.question, investigation?.site?.id, phase])

  const synthesis = investigationResult?.synthesis || {}
  const agentOutputs = investigationResult?.agent_outputs || {}
  const hypotheses = synthesis.cross_domain_findings || []
  const nbas = synthesis.next_best_actions || []
  const isComplete = !!investigationResult

  const singleDomainFindings = synthesis.single_domain_findings || []
  const siteDecision = synthesis.site_decision || null
  const integrityAssessment = synthesis.integrity_assessment || null
  const hasVerdict = !!(siteDecision?.verdict || integrityAssessment?.verdict)

  if (!investigation) return null

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-white z-50 overflow-y-auto"
    >
      {/* Site 360 Overview Phase */}
      {phase === 'overview' && investigation.site && (
        <div className="min-h-full bg-white">
          <div className="sticky top-0 bg-white/95 backdrop-blur-xl border-b border-neutral-100 z-10 px-6 py-5">
            <div className="max-w-4xl mx-auto flex items-center justify-between">
              <button
                onClick={() => { setInvestigation(null); navigate(-1); }}
                className="flex items-center gap-1.5 text-[13px] text-neutral-500 hover:text-neutral-900 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                <span>Back</span>
              </button>
              <div className="text-center">
                <h1 className="text-[17px] font-semibold text-neutral-900 tracking-tight">Investigation Studio</h1>
                <p className="text-[11px] text-neutral-400 uppercase tracking-wider mt-0.5">360° Site Analysis</p>
              </div>
              <div className="w-24" />
            </div>
          </div>
          <Site360Panel
            siteId={investigation.site.id}
            siteName={investigation.site.name}
            question={investigation.question}
            onLaunchAnalysis={handleLaunchAnalysis}
          />
        </div>
      )}

      {/* Analysis Phase - show directly if no site context */}
      {(phase === 'analyzing' || !investigation.site) && (
      <div className="max-w-3xl mx-auto px-6 py-12 bg-white min-h-screen">
        <div className="flex items-center mb-8">
          <button
            onClick={() => {
              if (phase === 'analyzing' && investigation.site) {
                setPhase('overview')
              } else {
                setInvestigation(null);
                navigate(-1);
              }
            }}
            className="flex items-center gap-1.5 text-[13px] text-neutral-500 hover:text-neutral-900 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>{phase === 'analyzing' && investigation.site ? 'Back to Site Overview' : 'Back to Study'}</span>
          </button>
        </div>

        <motion.h1
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="text-[24px] font-semibold text-neutral-900 tracking-tight mb-2 text-center leading-snug"
        >
          "{investigation.question}"
        </motion.h1>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="text-[13px] text-neutral-500 text-center mb-10"
        >
          {investigation.site?.name || investigation.site?.id || 'Study-wide'} · Live Investigation
        </motion.p>

        {investigationError && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
            <p className="text-[14px] text-red-700">{investigationError}</p>
          </div>
        )}

        {/* Live Agent Timeline — collapses once insights start revealing */}
        {timelineCollapsed ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-neutral-50 rounded-xl p-4 flex items-center justify-between cursor-pointer hover:bg-neutral-100 transition-colors"
            onClick={() => setTimelineCollapsed(false)}
          >
            <span className="text-[13px] text-neutral-600">
              {Object.keys(agentOutputs).length > 0
                ? `${Object.keys(agentOutputs).length} agent${Object.keys(agentOutputs).length > 1 ? 's' : ''} completed investigation`
                : 'Investigation complete'}
            </span>
            <span className="text-[12px] text-neutral-900 font-medium hover:underline">Show details</span>
          </motion.div>
        ) : (
          <div>
            <AgentTimeline phases={investigationPhases} loading={loading} reroutedAgents={investigationResult?.adaptive_reroute?.agents_added} />
            {isComplete && (
              <button
                onClick={() => setTimelineCollapsed(true)}
                className="text-[12px] text-neutral-500 hover:text-neutral-900 transition-colors mt-3"
              >
                Hide details
              </button>
            )}
          </div>
        )}

        {/* Adaptive Re-routing Indicator */}
        {isComplete && investigationResult?.adaptive_reroute?.triggered && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 bg-purple-50/60 border border-purple-200/50 rounded-xl px-4 py-3 flex items-start gap-3"
          >
            <div className="w-5 h-5 rounded-full bg-purple-100 flex items-center justify-center shrink-0 mt-0.5">
              <ArrowRight className="w-3 h-3 text-purple-600" />
            </div>
            <div>
              <p className="text-[12px] font-medium text-purple-700">
                Cross-domain re-routing activated
              </p>
              <p className="text-[11px] text-purple-600/70 mt-0.5">
                Added {investigationResult.adaptive_reroute.agents_added.map(a => AGENT_NAMES[a] || a).join(', ')}
                {investigationResult.adaptive_reroute.rationale && (
                  <span> — {investigationResult.adaptive_reroute.rationale}</span>
                )}
              </p>
            </div>
          </motion.div>
        )}

        {/* Executive Brief Mode - Clean consumable summary */}
        {isComplete && displayMode === 'brief' && (
          <div className="mt-10">
            <ExecutiveBrief
              synthesis={synthesis}
              hypotheses={[...hypotheses].sort((a, b) => (b.confidence || 0) - (a.confidence || 0))}
              nbas={nbas}
              onShowFullAnalysis={handleShowFullAnalysis}
              resolveText={resolveText}
            />
          </div>
        )}

        {/* Full Analysis Mode - All sections visible */}
        <AnimatePresence mode="wait">
          {displayMode === 'full' && (
            <motion.div
              key="full-analysis"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              {/* Mode Toggle */}
              <div className="mt-8 flex items-center justify-between">
                <button
                  onClick={handleBackToSummary}
                  className="flex items-center gap-2 text-[13px] font-medium text-neutral-500 hover:text-neutral-900 transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Back to summary
                </button>
                <span className="text-[12px] text-neutral-400">
                  {hypotheses.length} findings · {nbas.length} actions
                </span>
              </div>

              {/* 1. What We Found */}
              {synthesis.signal_detection && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
                  className="mt-8"
                >
                  <div className="bg-neutral-50 rounded-2xl p-6 relative overflow-hidden">
                    <div className="flex items-center gap-2.5 mb-4">
                      <Search className="w-4 h-4 text-neutral-400" />
                      <h3 className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider">What We Found</h3>
                    </div>
                    <p className="text-[15px] text-neutral-900 leading-relaxed">{resolveText(synthesis.signal_detection)}</p>
                  </div>
                </motion.div>
              )}

              {/* 1b. Verdict (site_decision or integrity_assessment) */}
              {hasVerdict && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 0.1, ease: [0.25, 0.46, 0.45, 0.94] }}
                  className="mt-8"
                >
                  {siteDecision?.verdict && <SiteDecisionCard decision={siteDecision} />}
                  {integrityAssessment?.verdict && <IntegrityAssessmentCard assessment={integrityAssessment} />}
                </motion.div>
              )}

              {/* 2. What the Data Shows */}
              {singleDomainFindings.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 0.2, ease: [0.25, 0.46, 0.45, 0.94] }}
                  className="mt-10"
                >
                  <div className="flex items-center gap-2.5 mb-5">
                    <BarChart3 className="w-4 h-4 text-neutral-400" />
                    <h3 className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider">What the Data Shows</h3>
                  </div>
                  <div className="space-y-3">
                    {singleDomainFindings.map((f, i) => (
                      <FindingCard key={`finding-${i}`} finding={f} agentOutput={agentOutputs[f.agent]} resolveText={resolveText} />
                    ))}
                  </div>
                </motion.div>
              )}

              {/* 3. Why This Is Happening */}
              {hypotheses.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
                  className="mt-10"
                >
                  <div className="flex items-center gap-2.5 mb-5">
                    <Lightbulb className="w-4 h-4 text-neutral-400" />
                    <h3 className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider">Why This Is Happening</h3>
                  </div>
                  <div className="space-y-3">
                    {[...hypotheses]
                      .sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
                      .map((h, i) => (
                        <HypothesisCard key={`hyp-${i}`} hypothesis={h} rank={i + 1} />
                      ))}
                  </div>
                </motion.div>
              )}

              {/* 4. What To Do Next */}
              {nbas.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
                  className="mt-10"
                >
                  <NBAPanel actions={nbas} />
                </motion.div>
              )}

              {/* 5. Agent Reasoning Trace */}
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
                className="mt-10"
              >
                <button
                  onClick={() => setShowTrace(!showTrace)}
                  className="flex items-center gap-2 text-[12px] text-neutral-500 hover:text-neutral-900 transition-colors"
                >
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${showTrace ? 'rotate-180' : ''}`} />
                  {showTrace ? 'Hide agent reasoning' : 'View agent reasoning'}
                </button>

                <AnimatePresence>
                  {showTrace && <ReasoningTrace agentOutputs={agentOutputs} reroutedAgents={investigationResult?.adaptive_reroute?.agents_added} />}
                </AnimatePresence>

                <div className="flex items-center gap-4 mt-6 pt-4 border-t border-neutral-100">
                  <span className="text-[12px] text-neutral-500">
                    {synthesis.confidence_assessment || `${Object.keys(agentOutputs).length} agents analyzed`} · Live data
                  </span>
                </div>

                <ActionButtons synthesis={synthesis} onCopyLink={handleCopyLink} linkCopied={linkCopied} />
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Follow-up input — shown after investigation completes */}
        {isComplete && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.6 }}
            className="mt-8 border-t border-neutral-100 pt-6"
          >
            <div className="flex items-center gap-2 mb-3">
              <MessageSquare className="w-4 h-4 text-neutral-400" />
              <span className="text-[12px] font-medium text-neutral-500 uppercase tracking-wide">Follow Up</span>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="text"
                value={followUpInput}
                onChange={(e) => setFollowUpInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleFollowUp()}
                placeholder="Ask a follow-up question about these findings..."
                className="flex-1 bg-neutral-50 border border-neutral-200 rounded-xl px-4 py-3 text-[14px] text-neutral-900 placeholder:text-neutral-400 outline-none focus:border-neutral-400 transition-colors"
                disabled={followUpLoading}
              />
              {followUpInput.trim() && (
                <button
                  onClick={handleFollowUp}
                  disabled={followUpLoading}
                  className="px-4 py-3 bg-neutral-900 text-white rounded-xl text-[14px] font-medium hover:bg-neutral-800 transition-colors disabled:opacity-50"
                >
                  {followUpLoading ? 'Sending...' : 'Ask'}
                </button>
              )}
            </div>
          </motion.div>
        )}

        {/* Loading state when waiting for results */}
        {loading && !investigationError && investigationPhases.length === 0 && (
          <div className="flex flex-col items-center justify-center h-64 mt-10">
            <Loader2 className="w-8 h-8 text-apple-secondary animate-spin mb-4" />
            <p className="text-body text-apple-secondary">Launching investigation...</p>
          </div>
        )}
      </div>
      )}
    </motion.div>
  )
}


/** Confidence badge for inline hypothesis display. */
function ConfidenceBadge({ value }) {
  const pct = Math.round((value || 0) * 100)
  const cls = pct >= 80
    ? 'bg-green-50 text-green-700 border-green-200'
    : pct >= 60
      ? 'bg-amber-50 text-amber-700 border-amber-200'
      : 'bg-red-50 text-red-700 border-red-200'
  return (
    <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${cls}`}>
      {pct}%
    </span>
  )
}

/** Single-domain finding card with collapsible provenance from agent output. */
function FindingCard({ finding, agentOutput, resolveText }) {
  const [showEvidence, setShowEvidence] = useState(false)

  // Extract provenance: the agent's raw findings + reasoning trace action results
  // Filter to only show findings relevant to the sites in this finding card
  const allAgentFindings = agentOutput?.findings || []
  const targetSiteIds = new Set(finding.site_ids || [])
  const agentFindings = targetSiteIds.size > 0
    ? allAgentFindings.filter(af => {
        const afSite = af.site_id || ''
        // Include if finding matches a target site, or has no site (study-level finding)
        return targetSiteIds.has(afSite) || !afSite
      })
    : allAgentFindings

  const trace = agentOutput?.reasoning_trace || []
  const actionResults = trace
    .filter(t => t.phase === 'act' || t.phase === 'act_done')
    .flatMap(t => t.results || t.data?.action_results || [])
    .filter(r => r.tool_name && r.success)

  const hasEvidence = agentFindings.length > 0 || actionResults.length > 0

  return (
    <div className="bg-white border border-neutral-200 rounded-xl p-5 hover:border-neutral-300 transition-colors">
      <div className="flex items-center gap-2 flex-wrap mb-2">
        <span className="text-[10px] font-semibold tracking-wider text-neutral-400 uppercase">
          {AGENT_NAMES[finding.agent] || finding.agent}
        </span>
        {finding.site_ids?.length > 0 && (
          <>
            <span className="w-1 h-1 rounded-full bg-neutral-300" />
            <span className="text-[11px] text-neutral-500">
              {finding.site_ids.map(id => resolveText(id)).join(', ')}
            </span>
          </>
        )}
      </div>
      <p className="text-[14px] text-neutral-900 leading-relaxed">{resolveText(finding.finding)}</p>
      {finding.recommendation && (
        <p className="text-[12px] text-neutral-500 mt-2 italic">{resolveText(finding.recommendation)}</p>
      )}

      {/* Provenance toggle */}
      {hasEvidence && (
        <>
          <button
            onClick={() => setShowEvidence(v => !v)}
            className="mt-3 flex items-center gap-1.5 text-[11px] font-medium text-neutral-500 hover:text-neutral-900 transition-colors"
          >
            <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${showEvidence ? 'rotate-180' : ''}`} />
            <span>Supporting evidence ({agentFindings.length} findings, {actionResults.length} queries)</span>
          </button>

          <AnimatePresence>
            {showEvidence && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="mt-2.5 space-y-2">
                  {/* Agent findings with data points */}
                  {agentFindings.map((af, j) => {
                    const afFinding = af.finding || af.summary || af.text
                    if (!afFinding) return null
                    return (
                      <div key={j} className="pl-3 border-l-2 border-apple-accent/30">
                        {af.site_id && (
                          <span className="text-[10px] font-medium text-apple-accent">{resolveText(af.site_id)}</span>
                        )}
                        <p className="text-xs text-apple-text leading-relaxed">{resolveText(afFinding)}</p>
                        {af.root_cause && (
                          <p className="text-[11px] text-apple-secondary mt-0.5">
                            <span className="font-medium">Root cause:</span> {resolveText(af.root_cause)}
                          </p>
                        )}
                        {af.causal_chain && (
                          <CausalChainFlow chain={af.causal_chain} />
                        )}
                        {af.evidence_quality && (
                          <span className={`inline-block mt-1 text-[10px] font-medium px-2 py-0.5 rounded-full border ${
                            af.evidence_quality === 'strong' ? 'bg-green-50 text-green-600 border-green-200' :
                            af.evidence_quality === 'moderate' ? 'bg-amber-50 text-amber-600 border-amber-200' :
                            'bg-gray-50 text-gray-500 border-gray-200'
                          }`}>
                            {af.evidence_quality} evidence
                          </span>
                        )}
                      </div>
                    )
                  })}

                  {/* SQL queries executed */}
                  {actionResults.length > 0 && (
                    <div className="pt-2 border-t border-apple-border/40">
                      <p className="text-[10px] font-semibold text-apple-secondary uppercase tracking-wider mb-1.5">Data sources queried</p>
                      <div className="space-y-1">
                        {actionResults.map((r, k) => (
                          <div key={k} className="flex items-center gap-2 text-xs">
                            <span className="text-green-500">&#10003;</span>
                            <span className="font-medium text-apple-text">{r.tool_name?.replace(/_/g, ' ')}</span>
                            {r.row_count > 0 && (
                              <span className="text-apple-secondary">&mdash; {r.row_count} rows</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}
    </div>
  )
}


/** Expandable reasoning detail for a single iteration of one agent. */
function ReasoningDetail({ phases }) {
  const resolveText = useResolveText()
  const reasonDone = phases.find(p => p.phase === 'reason_done')
  const planDone = phases.find(p => p.phase === 'plan_done')
  const actDone = phases.find(p => p.phase === 'act_done')
  const reflectDone = phases.find(p => p.phase === 'reflect_done')

  const hypotheses = reasonDone?.data?.hypotheses || []
  const planSteps = planDone?.data?.plan_steps || []
  const actionResults = actDone?.data?.action_results || []
  const reflection = reflectDone?.data

  if (hypotheses.length === 0 && planSteps.length === 0 && actionResults.length === 0 && !reflection) {
    return null
  }

  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="overflow-hidden"
    >
      <div className="mt-2.5 space-y-2.5">
        {/* Hypotheses */}
        {hypotheses.length > 0 && (
          <div className="pl-3 border-l-2 border-purple-200">
            <p className="text-[11px] font-semibold text-purple-600 uppercase tracking-wider mb-1.5">
              Hypotheses ({hypotheses.length})
            </p>
            <div className="space-y-1.5">
              {hypotheses.map((h, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-[10px] font-bold text-purple-500 mt-0.5 shrink-0">{h.id}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-xs text-apple-text leading-snug">{resolveText(h.description)}</p>
                      <ConfidenceBadge value={h.confidence} />
                    </div>
                    {h.causal_chain && <CausalChainFlow chain={h.causal_chain} />}
                    {h.site_ids?.length > 0 && (
                      <p className="text-[10px] text-apple-secondary mt-0.5">
                        Sites: {h.site_ids.map(id => resolveText(id)).join(', ')}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Plan */}
        {planSteps.length > 0 && (
          <div className="pl-3 border-l-2 border-blue-200">
            <p className="text-[11px] font-semibold text-blue-600 uppercase tracking-wider mb-1.5">
              Plan
            </p>
            <div className="space-y-1">
              {planSteps.map((s, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <span className="text-[10px] font-mono text-blue-500 mt-0.5 shrink-0">{i + 1}.</span>
                  <span className="text-apple-text">
                    <span className="font-medium">{s.tool_name}</span>
                    {s.purpose && <span className="text-apple-secondary"> — {s.purpose}</span>}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action results */}
        {actionResults.length > 0 && (
          <div className="pl-3 border-l-2 border-green-200">
            <p className="text-[11px] font-semibold text-green-600 uppercase tracking-wider mb-1.5">
              Investigation
            </p>
            <div className="space-y-1">
              {actionResults.map((r, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <span className={r.success ? 'text-green-500' : 'text-red-400'}>
                    {r.success ? '✓' : '✗'}
                  </span>
                  <span className="font-medium text-apple-text">{r.tool_name}</span>
                  {r.row_count > 0 && (
                    <span className="text-apple-secondary">— {r.row_count} rows</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Reflection */}
        {reflection && (
          <div className={`pl-3 border-l-2 ${reflection.goal_satisfied ? 'border-green-400' : 'border-amber-300'}`}>
            <div className="flex items-center gap-2">
              <span className={`text-xs font-medium ${reflection.goal_satisfied ? 'text-green-600' : 'text-amber-600'}`}>
                {reflection.goal_satisfied ? '✓ Goal satisfied' : '✗ Not satisfied'}
              </span>
              {reflection.findings_count > 0 && (
                <span className="text-[10px] text-apple-secondary">— {reflection.findings_count} findings</span>
              )}
            </div>
            {!reflection.goal_satisfied && reflection.iteration_focus && (
              <p className="text-[11px] text-apple-secondary mt-0.5">
                Next focus: {reflection.iteration_focus}
              </p>
            )}
            {!reflection.goal_satisfied && reflection.remaining_gaps?.length > 0 && (
              <p className="text-[11px] text-apple-secondary mt-0.5">
                Gaps: {reflection.remaining_gaps.join(', ')}
              </p>
            )}
          </div>
        )}
      </div>
    </motion.div>
  )
}


function AgentTimeline({ phases, loading, reroutedAgents }) {
  const reroutedSet = useMemo(() => new Set(reroutedAgents || []), [reroutedAgents])
  const [expandedIterations, setExpandedIterations] = useState({})

  const prpaOrder = ['perceive', 'reason', 'plan', 'act', 'reflect']
  const prpaLabels = { perceive: 'Gather', reason: 'Analyze', plan: 'Plan', act: 'Investigate', reflect: 'Evaluate' }
  // _done phases are detail payloads, not display phases
  const donePhases = new Set(['perceive_done', 'reason_done', 'plan_done', 'act_done', 'reflect_done'])

  // Group phases by agent
  const agentPhases = useMemo(() => {
    const grouped = {}
    for (const p of phases) {
      const agent = p.agent_id || 'conductor'
      if (!grouped[agent]) grouped[agent] = []
      grouped[agent].push(p)
    }
    return grouped
  }, [phases])

  // Build iteration structure per PRPA agent
  const agentIterations = useMemo(() => {
    const result = {}
    for (const [agent, agentPhs] of Object.entries(agentPhases)) {
      const isPRPA = agentPhs.some(p => prpaOrder.includes(p.phase))
      if (!isPRPA) continue
      const iterations = {}
      for (const p of agentPhs) {
        const iter = p.data?.iteration || 1
        if (!iterations[iter]) iterations[iter] = []
        iterations[iter].push(p)
      }
      const iterKeys = Object.keys(iterations).map(Number).sort((a, b) => a - b)
      result[agent] = { iterations, iterKeys }
    }
    return result
  }, [phases])

  // Details collapsed by default - no auto-expand

  if (phases.length === 0 && !loading) return null

  function toggleIteration(agent, iteration) {
    const key = `${agent}-${iteration}`
    setExpandedIterations(prev => {
      const current = prev[key] ?? false
      return { ...prev, [key]: !current }
    })
  }

  return (
    <div className="space-y-2.5">
      {Object.entries(agentPhases).map(([agent, agentPhs]) => {
        const isPRPA = agentPhs.some(p => prpaOrder.includes(p.phase))
        const latestPhase = agentPhs.filter(p => !donePhases.has(p.phase)).at(-1)?.phase

        if (!isPRPA) {
          // Conductor / non-PRPA agents — keep simple display
          return (
            <motion.div
              key={agent}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="card p-4"
            >
              <div className="flex items-center justify-between mb-2.5">
                <span className="text-caption font-medium text-apple-text">
                  {AGENT_NAMES[agent] || agent}
                  {reroutedSet.has(agent) && (
                    <span className="ml-2 text-[9px] font-semibold text-purple-600 bg-purple-50 border border-purple-200/60 px-1.5 py-0.5 rounded-full uppercase tracking-wider">cross-domain</span>
                  )}
                </span>
                {loading && latestPhase && (
                  <span className="flex items-center gap-1.5 text-xs text-apple-accent">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    {PHASE_LABELS[latestPhase] || latestPhase}
                  </span>
                )}
              </div>
              <div className="space-y-1">
                {agentPhs.filter(p => !donePhases.has(p.phase)).map((p, i) => (
                  <p key={i} className="text-caption text-apple-secondary">
                    {PHASE_LABELS[p.phase] || p.phase}
                    {p.data?.query && ` — "${p.data.query}"`}
                    {p.data?.agents && ` — ${p.data.agents.join(', ')}`}
                    {p.phase === 'adaptive_reroute' && p.data?.additional_agents && (
                      <span> — adding {p.data.additional_agents.map(a => AGENT_NAMES[a] || a).join(', ')}</span>
                    )}
                    {p.phase === 'adaptive_reroute' && p.data?.rationale && (
                      <span className="block text-[11px] text-apple-secondary/70 mt-0.5">{p.data.rationale}</span>
                    )}
                  </p>
                ))}
              </div>
            </motion.div>
          )
        }

        const { iterations, iterKeys } = agentIterations[agent] || { iterations: {}, iterKeys: [] }
        const maxIter = iterKeys[iterKeys.length - 1] || 1

        return (
          <motion.div
            key={agent}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="card p-4"
          >
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-caption font-medium text-apple-text">
                {AGENT_NAMES[agent] || agent}
                {reroutedSet.has(agent) && (
                  <span className="ml-2 text-[9px] font-semibold text-purple-600 bg-purple-50 border border-purple-200/60 px-1.5 py-0.5 rounded-full uppercase tracking-wider">cross-domain</span>
                )}
              </span>
              {loading && latestPhase && (
                <span className="flex items-center gap-1.5 text-xs text-apple-accent">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  {PHASE_LABELS[latestPhase] || latestPhase}
                </span>
              )}
            </div>

            <div className="space-y-3">
              {iterKeys.map(iter => {
                const iterPhases = iterations[iter]
                const displayPhases = iterPhases.filter(p => !donePhases.has(p.phase))
                const completedPhases = new Set(displayPhases.map(p => p.phase))
                const iterLatest = displayPhases.at(-1)?.phase
                const isLatestIter = iter === maxIter
                const iterHasReasoning = iterPhases.some(p => donePhases.has(p.phase))
                const key = `${agent}-${iter}`
                const isExpanded = expandedIterations[key] ?? false

                return (
                  <div key={iter}>
                    {/* Iteration label (only if multi-iteration) */}
                    {iterKeys.length > 1 && (
                      <p className="text-[10px] font-semibold text-apple-secondary/60 uppercase tracking-wider mb-1.5">
                        Round {iter}
                      </p>
                    )}

                    {/* PRPA pills */}
                    <div className="flex items-center gap-1">
                      {prpaOrder.map((step, i) => {
                        const done = completedPhases.has(step)
                        const active = iterLatest === step && loading && isLatestIter
                        return (
                          <div key={step} className="flex items-center gap-1">
                            <div
                              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                                done
                                  ? 'bg-apple-text text-white'
                                  : active
                                    ? 'bg-apple-accent/15 text-apple-accent animate-pulse'
                                    : 'bg-apple-border/40 text-apple-secondary/60'
                              }`}
                            >
                              {prpaLabels[step]}
                            </div>
                            {i < prpaOrder.length - 1 && (
                              <div className={`w-3 h-px ${done ? 'bg-apple-text/40' : 'bg-apple-border'}`} />
                            )}
                          </div>
                        )
                      })}
                    </div>

                    {/* Expandable reasoning detail */}
                    {iterHasReasoning && (
                      <>
                        <button
                          onClick={() => toggleIteration(agent, iter)}
                          className="flex items-center gap-1 mt-1.5 text-[11px] text-apple-secondary hover:text-apple-text transition-colors"
                        >
                          <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`} />
                          {isExpanded ? 'Hide reasoning' : 'Show reasoning'}
                        </button>
                        <AnimatePresence>
                          {isExpanded && <ReasoningDetail phases={iterPhases} />}
                        </AnimatePresence>
                      </>
                    )}
                  </div>
                )
              })}
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}


function HypothesisCard({ hypothesis, rank }) {
  const [expanded, setExpanded] = useState(false)
  const resolveText = useResolveText()
  const { siteNameMap } = useStore()
  const conf = confidenceLabel(hypothesis.confidence)

  const resolveSiteName = (id) => siteNameMap[id] || id

  return (
    <div className="card p-5 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2.5 mb-2">
            <span className="w-6 h-6 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-[11px] font-bold shrink-0">
              {rank}
            </span>
            {hypothesis.site_ids?.length > 0 && (
              <span className="text-xs text-apple-secondary font-medium">
                {hypothesis.site_ids.map(resolveSiteName).join(', ')}
              </span>
            )}
          </div>
          <p className="text-body font-medium text-apple-text leading-snug">{resolveText(hypothesis.finding)}</p>
          {hypothesis.causal_chain && (
            <CausalChainFlow chain={hypothesis.causal_chain} />
          )}
        </div>
        <span className={`text-[11px] font-medium px-2.5 py-1 rounded-full border shrink-0 ${conf.bg} ${conf.color}`}>
          {conf.text}
        </span>
      </div>

      {hypothesis.actual_interpretation && hypothesis.actual_interpretation !== hypothesis.finding && (
        <div className="mt-4 p-3.5 bg-apple-bg/80 rounded-xl">
          {hypothesis.naive_interpretation && (
            <p className="text-xs text-apple-secondary/70 mb-1.5 leading-relaxed">
              <span className="line-through">{hypothesis.naive_interpretation}</span>
            </p>
          )}
          <p className="text-caption text-apple-text leading-relaxed">{hypothesis.actual_interpretation}</p>
        </div>
      )}

      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs text-apple-secondary hover:text-apple-text mt-3 transition-colors"
      >
        <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`} />
        {expanded ? 'Hide supporting evidence' : 'View supporting evidence'}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-3 pt-3 border-t border-apple-border/50 space-y-3">
              {hypothesis.hypothesis_test && (
                <div className="text-xs leading-relaxed">
                  <span className="font-medium text-apple-text">How we tested this: </span>
                  <span className="text-apple-secondary">{resolveText(hypothesis.hypothesis_test)}</span>
                </div>
              )}
              <TemporalEvidenceBar evidence={hypothesis.confirming_evidence} />
              {hypothesis.confirming_evidence?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-green-600 mb-1.5">Supporting evidence</p>
                  {hypothesis.confirming_evidence.map((e, i) => (
                    <p key={i} className="text-xs text-apple-secondary pl-3 border-l-2 border-green-200 mb-1.5 leading-relaxed">{resolveText(e)}</p>
                  ))}
                </div>
              )}
              {hypothesis.refuting_evidence?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-red-500 mb-1.5">Contradicting evidence</p>
                  {hypothesis.refuting_evidence.map((e, i) => (
                    <p key={i} className="text-xs text-apple-secondary pl-3 border-l-2 border-red-200 mb-1.5 leading-relaxed">{resolveText(e)}</p>
                  ))}
                </div>
              )}
              {hypothesis.recommended_action && (
                <div className="pt-2.5 border-t border-apple-border/50">
                  <p className="text-xs font-medium text-apple-text">Suggested action</p>
                  <p className="text-xs text-apple-secondary mt-0.5 leading-relaxed">{resolveText(hypothesis.recommended_action)}</p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}


function NBAPanel({ actions }) {
  const resolveText = useResolveText()
  const urgencyColors = {
    immediate: 'bg-red-50 text-red-600 border-red-200',
    this_week: 'bg-amber-50 text-amber-600 border-amber-200',
    this_month: 'bg-blue-50 text-blue-600 border-blue-200',
  }

  return (
    <div>
      <div className="flex items-center gap-2.5 mb-4">
        <div className="w-7 h-7 rounded-lg bg-green-50 flex items-center justify-center">
          <ListChecks className="w-3.5 h-3.5 text-green-600" />
        </div>
        <h3 className="text-sm font-semibold text-apple-text tracking-tight">What To Do Next</h3>
      </div>
      <div className="space-y-2.5">
        {[...actions]
          .sort((a, b) => (a.priority || 99) - (b.priority || 99))
          .map((nba, i) => (
            <div key={i} className="card p-4 flex gap-4 hover:shadow-sm transition-shadow">
              <div className="shrink-0 w-7 h-7 rounded-full bg-apple-text text-white flex items-center justify-center text-xs font-bold">
                {nba.priority || i + 1}
              </div>
              <div className="flex-1">
                <p className="text-body font-medium text-apple-text leading-snug">{resolveText(nba.action)}</p>
                {nba.rationale && (
                  <p className="text-caption text-apple-secondary mt-1 leading-relaxed">{resolveText(nba.rationale)}</p>
                )}
                <div className="flex items-center gap-2.5 mt-2.5">
                  {nba.urgency && (
                    <span className={`text-[11px] font-medium px-2.5 py-0.5 rounded-full border ${urgencyColors[nba.urgency] || 'bg-gray-50 text-gray-600 border-gray-200'}`}>
                      {nba.urgency.replace('_', ' ')}
                    </span>
                  )}
                  {nba.owner && (
                    <span className="text-xs text-apple-secondary">{nba.owner}</span>
                  )}
                </div>
                {nba.expected_impact && (
                  <p className="text-xs text-apple-accent mt-1.5 leading-relaxed">{resolveText(nba.expected_impact)}</p>
                )}
              </div>
            </div>
          ))}
      </div>
    </div>
  )
}


function CausalChainFlow({ chain }) {
  const nodes = chain.split(/\s*(?:→|->)\s*/).filter(Boolean)
  if (nodes.length === 0) return null

  return (
    <div className="flex flex-wrap items-center gap-1.5 mt-3">
      {nodes.map((node, i) => (
        <div key={i} className="flex items-center gap-1.5">
          <span className="px-3 py-1.5 bg-purple-50 text-purple-700 text-[11px] font-medium rounded-full border border-purple-200/60">
            {node.trim()}
          </span>
          {i < nodes.length - 1 && (
            <ChevronRight className="w-3 h-3 text-apple-secondary/40 shrink-0" />
          )}
        </div>
      ))}
    </div>
  )
}


function TemporalEvidenceBar({ evidence }) {
  if (!evidence || evidence.length === 0) return null

  const pattern = /(?:from\s+)?(\d+(?:\.\d+)?)\s*(%|d|days?|hrs?|hours?|wks?|weeks?)\s*(?:to|→|->)\s*(\d+(?:\.\d+)?)\s*(%|d|days?|hrs?|hours?|wks?|weeks?)?/i
  const pairs = []

  for (const e of evidence) {
    const match = e.match(pattern)
    if (match) {
      const before = parseFloat(match[1])
      const after = parseFloat(match[3])
      const unit = match[4] || match[2] || ''
      if (before > 0 || after > 0) {
        pairs.push({ before, after, unit })
      }
    }
  }

  if (pairs.length === 0) return null

  return (
    <div className="space-y-2.5 mb-2">
      <p className="text-xs font-medium text-apple-text">Before vs. after</p>
      {pairs.map((p, i) => {
        const max = Math.max(p.before, p.after)
        const beforePct = max > 0 ? (p.before / max) * 100 : 0
        const afterPct = max > 0 ? (p.after / max) * 100 : 0
        const worsened = p.after > p.before

        return (
          <div key={i} className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-apple-secondary w-12 text-right shrink-0">Before</span>
              <div className="flex-1 h-3.5 bg-apple-border/20 rounded-full overflow-hidden">
                <div
                  className="h-full bg-green-400/60 rounded-full transition-all"
                  style={{ width: `${Math.max(beforePct, 4)}%` }}
                />
              </div>
              <span className="text-[11px] text-apple-secondary w-16 shrink-0">{p.before}{p.unit}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-apple-secondary w-12 text-right shrink-0">After</span>
              <div className="flex-1 h-3.5 bg-apple-border/20 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${worsened ? 'bg-red-400/60' : 'bg-amber-400/60'}`}
                  style={{ width: `${Math.max(afterPct, 4)}%` }}
                />
              </div>
              <span className="text-[11px] text-apple-secondary w-16 shrink-0">{p.after}{p.unit}</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}


function summarizeTrace(trace) {
  if (!trace || trace.length === 0) return null
  const iterations = new Set(trace.map(s => s.iteration).filter(Boolean)).size || 1
  const toolCalls = trace.filter(s => s.phase === 'act').reduce((sum, s) => sum + (s.results_count || 0), 0)
  const satisfied = trace.some(s => s.goal_satisfied === true)
  const parts = []
  if (iterations > 1) parts.push(`${iterations} rounds`)
  else parts.push('1 round')
  if (toolCalls > 0) parts.push(`${toolCalls} queries`)
  if (satisfied) parts.push('complete')
  return parts.join(' · ')
}

function ReasoningTrace({ agentOutputs, reroutedAgents }) {
  const resolveText = useResolveText()
  const reroutedSet = useMemo(() => new Set(reroutedAgents || []), [reroutedAgents])
  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      className="overflow-hidden"
    >
      <div className="mt-4 space-y-3">
        {Object.entries(agentOutputs).map(([agentId, output]) => {
          const traceSummary = summarizeTrace(output.reasoning_trace)

          return (
            <div key={agentId} className={`p-4 bg-apple-bg/80 rounded-xl border ${reroutedSet.has(agentId) ? 'border-purple-200/60' : 'border-apple-border/40'}`}>
              <div className="flex items-center justify-between mb-2.5">
                <p className="text-caption font-medium text-apple-text">
                  {AGENT_NAMES[agentId] || agentId}
                  {reroutedSet.has(agentId) && (
                    <span className="ml-2 text-[9px] font-semibold text-purple-600 bg-purple-50 border border-purple-200/60 px-1.5 py-0.5 rounded-full uppercase tracking-wider">cross-domain</span>
                  )}
                  {output.severity && (
                    <span className={`ml-2 text-[10px] font-medium px-2 py-0.5 rounded-full ${
                      output.severity === 'critical' ? 'bg-red-50 text-red-600' :
                      output.severity === 'warning' ? 'bg-amber-50 text-amber-600' :
                      output.severity === 'high' ? 'bg-orange-50 text-orange-600' :
                      'bg-green-50 text-green-600'
                    }`}>
                      {output.severity}
                    </span>
                  )}
                </p>
                {traceSummary && (
                  <span className="text-[11px] text-apple-secondary">{traceSummary}</span>
                )}
              </div>

              {output.findings?.length > 0 && (
                <div className="space-y-2">
                  {output.findings.map((f, i) => {
                    if (typeof f === 'string') {
                      return <p key={i} className="text-sm text-apple-text leading-relaxed">{resolveText(f)}</p>
                    }
                    const site = f.site_id
                    const finding = f.finding || f.summary || f.text
                    const interpretation = f.actual_interpretation
                    const naive = f.naive_interpretation
                    if (!finding) return null
                    return (
                      <div key={i} className="space-y-1">
                        {site && (
                          <span className="text-xs font-medium text-apple-accent">{resolveText(site)}</span>
                        )}
                        <p className="text-sm text-apple-text leading-relaxed">{resolveText(finding)}</p>
                        {naive && interpretation && (
                          <div className="p-2.5 bg-white/60 rounded-lg mt-1">
                            <p className="text-xs text-apple-secondary/70 line-through">{resolveText(naive)}</p>
                            <p className="text-xs text-apple-text mt-1">{resolveText(interpretation)}</p>
                          </div>
                        )}
                        {!naive && interpretation && (
                          <p className="text-xs text-apple-secondary italic">{resolveText(interpretation)}</p>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}

              {(!output.findings || output.findings.length === 0) && output.summary && (
                <p className="text-sm text-apple-text leading-relaxed">{output.summary}</p>
              )}
            </div>
          )
        })}
      </div>
    </motion.div>
  )
}


function SiteDecisionCard({ decision }) {
  const resolveText = useResolveText()
  const verdictConfig = {
    rescue: { label: 'Rescue', color: 'text-green-700', bg: 'bg-green-50', border: 'border-green-400', icon: TrendingUp },
    close: { label: 'Close', color: 'text-red-700', bg: 'bg-red-50', border: 'border-red-400', icon: AlertCircle },
    watch: { label: 'Watch', color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-400', icon: AlertCircle },
  }
  const v = verdictConfig[decision.verdict] || verdictConfig.watch
  const Icon = v.icon

  return (
    <div className={`card p-6 border-l-4 ${v.border} relative overflow-hidden`}>
      <div className="flex items-center gap-2.5 mb-3">
        <div className={`w-7 h-7 rounded-lg ${v.bg} flex items-center justify-center`}>
          <Icon className={`w-3.5 h-3.5 ${v.color}`} />
        </div>
        <h3 className="text-sm font-semibold text-apple-text tracking-tight">The Verdict</h3>
      </div>
      <div className="flex items-center gap-3 mb-3">
        <span className={`text-lg font-bold ${v.color} uppercase tracking-wide`}>{v.label}</span>
        <span className="text-body text-apple-secondary">
          {resolveText(decision.site_name || decision.site_id)}
        </span>
      </div>
      <p className="text-body text-apple-text/90 leading-relaxed mb-4">{resolveText(decision.rationale)}</p>
      <div className="grid md:grid-cols-2 gap-3">
        {decision.rescue_indicators?.length > 0 && (
          <div className="p-3 bg-green-50/60 rounded-lg">
            <p className="text-xs font-semibold text-green-700 mb-1.5">Rescue indicators</p>
            {decision.rescue_indicators.map((ind, i) => (
              <p key={i} className="text-xs text-apple-secondary leading-relaxed pl-2 border-l-2 border-green-200 mb-1">{resolveText(ind)}</p>
            ))}
          </div>
        )}
        {decision.close_indicators?.length > 0 && (
          <div className="p-3 bg-red-50/60 rounded-lg">
            <p className="text-xs font-semibold text-red-600 mb-1.5">Close indicators</p>
            {decision.close_indicators.map((ind, i) => (
              <p key={i} className="text-xs text-apple-secondary leading-relaxed pl-2 border-l-2 border-red-200 mb-1">{resolveText(ind)}</p>
            ))}
          </div>
        )}
      </div>
      {decision.recommended_actions?.length > 0 && (
        <div className="mt-3 pt-3 border-t border-apple-border/50">
          <p className="text-xs font-semibold text-apple-text mb-1.5">Next steps</p>
          {decision.recommended_actions.map((a, i) => (
            <p key={i} className="text-xs text-apple-secondary leading-relaxed mb-0.5">{i + 1}. {resolveText(a)}</p>
          ))}
        </div>
      )}
    </div>
  )
}

function IntegrityAssessmentCard({ assessment }) {
  const resolveText = useResolveText()
  const verdictConfig = {
    genuine: { label: 'Genuine', color: 'text-green-700', bg: 'bg-green-50', border: 'border-green-400' },
    suspicious: { label: 'Suspicious', color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-400' },
    critical_risk: { label: 'Critical Risk', color: 'text-red-700', bg: 'bg-red-50', border: 'border-red-400' },
  }
  const v = verdictConfig[assessment.verdict] || verdictConfig.suspicious

  return (
    <div className={`card p-6 border-l-4 ${v.border} relative overflow-hidden`}>
      <div className="flex items-center gap-2.5 mb-3">
        <div className={`w-7 h-7 rounded-lg ${v.bg} flex items-center justify-center`}>
          <Shield className={`w-3.5 h-3.5 ${v.color}`} />
        </div>
        <h3 className="text-sm font-semibold text-apple-text tracking-tight">Integrity Assessment</h3>
      </div>
      <div className="flex items-center gap-3 mb-3">
        <span className={`text-lg font-bold ${v.color} uppercase tracking-wide`}>{v.label}</span>
        <span className="text-body text-apple-secondary">
          {resolveText(assessment.site_name || assessment.site_id)}
        </span>
      </div>
      <p className="text-body text-apple-text/90 leading-relaxed mb-4">{resolveText(assessment.rationale)}</p>
      {assessment.domains_with_suppressed_variance?.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {assessment.domains_with_suppressed_variance.map((domain, i) => (
            <span key={i} className={`text-[11px] font-medium px-2.5 py-1 rounded-full border ${v.bg} ${v.color}`}>
              {domain}
            </span>
          ))}
        </div>
      )}
      {assessment.recommended_actions?.length > 0 && (
        <div className="mt-3 pt-3 border-t border-apple-border/50">
          <p className="text-xs font-semibold text-apple-text mb-1.5">Recommended audit steps</p>
          {assessment.recommended_actions.map((a, i) => (
            <p key={i} className="text-xs text-apple-secondary leading-relaxed mb-0.5">{i + 1}. {resolveText(a)}</p>
          ))}
        </div>
      )}
    </div>
  )
}

function ActionButtons({ synthesis, onCopyLink, linkCopied }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    const text = [
      synthesis?.executive_summary,
      synthesis?.cross_domain_findings?.map(h => `- ${h.finding}`).join('\n'),
      synthesis?.next_best_actions?.map(a => `${a.priority}. ${a.action}`).join('\n'),
    ].filter(Boolean).join('\n\n')

    navigator.clipboard.writeText(text || 'No synthesis available')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex gap-3 mt-6">
      <button className="button-primary flex items-center gap-2 rounded-xl">
        <ExternalLink className="w-4 h-4" />
        Export Report
      </button>
      <button onClick={handleCopy} className="button-secondary flex items-center gap-2 rounded-xl">
        {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
        {copied ? 'Copied' : 'Copy'}
      </button>
      <button onClick={onCopyLink} className="button-secondary flex items-center gap-2 rounded-xl">
        {linkCopied ? <Check className="w-4 h-4" /> : <Link2 className="w-4 h-4" />}
        {linkCopied ? 'Link Copied' : 'Share Link'}
      </button>
    </div>
  )
}
