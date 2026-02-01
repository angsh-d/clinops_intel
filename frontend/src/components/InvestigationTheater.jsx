import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, ChevronDown, ChevronRight, ExternalLink, Copy, Check, Loader2, Zap } from 'lucide-react'
import { useStore } from '../lib/store'
import { startInvestigation, connectInvestigationStream } from '../lib/api'

const PHASE_LABELS = {
  routing: 'Signal Detection',
  perceive: 'Perceive',
  reason: 'Reason',
  plan: 'Plan',
  act: 'Act',
  reflect: 'Reflect',
  synthesize: 'Cross-Domain Synthesis',
  complete: 'Complete',
}

const AGENT_NAMES = {
  agent_1: 'Data Quality Agent',
  agent_3: 'Enrollment Funnel Agent',
  conductor: 'Conductor',
}

export function InvestigationTheater() {
  const { investigation, setInvestigation, investigationPhases, addInvestigationPhase, investigationResult, setInvestigationResult, investigationError, setInvestigationError } = useStore()
  const [loading, setLoading] = useState(true)
  const [showTrace, setShowTrace] = useState(false)
  const wsRef = useRef(null)

  useEffect(() => {
    if (!investigation) return

    let cancelled = false

    async function launch() {
      setLoading(true)

      try {
        const { query_id } = await startInvestigation(
          investigation.question,
          investigation.site?.id
        )

        if (cancelled) return

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
  }, [investigation?.question, investigation?.site?.id])

  if (!investigation) return null

  const synthesis = investigationResult?.synthesis || {}
  const agentOutputs = investigationResult?.agent_outputs || {}
  const hypotheses = synthesis.cross_domain_findings || []
  const nbas = synthesis.next_best_actions || []
  const isComplete = !!investigationResult

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-apple-bg/95 backdrop-blur-xl z-50 overflow-y-auto"
    >
      <div className="max-w-3xl mx-auto px-6 py-12">
        <button
          onClick={() => setInvestigation(null)}
          className="absolute top-6 right-6 p-2 hover:bg-apple-border/50 rounded-full transition-colors"
        >
          <X className="w-5 h-5 text-apple-secondary" />
        </button>

        <motion.h1
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="text-title text-apple-text mb-2 text-center"
        >
          "{investigation.question}"
        </motion.h1>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="text-caption text-apple-secondary text-center mb-8"
        >
          {investigation.site?.id || 'Study-wide'} · Live Investigation
        </motion.p>

        {investigationError && (
          <div className="card p-4 border-l-4 border-l-red-500 mb-6">
            <p className="text-body text-red-600">{investigationError}</p>
          </div>
        )}

        {/* Live Agent Timeline */}
        <AgentTimeline phases={investigationPhases} loading={loading} />

        {/* Executive Summary */}
        {isComplete && synthesis.executive_summary && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="card p-5 mt-6 border-l-4 border-l-[#5856D6] relative overflow-hidden"
          >
            <div className="absolute inset-0 opacity-5 ai-gradient-border" />
            <h3 className="text-section text-apple-text mb-3">Executive Summary</h3>
            <p className="text-body text-apple-text leading-relaxed">{synthesis.executive_summary}</p>
            {synthesis.signal_detection && (
              <p className="text-caption text-apple-secondary mt-3 pt-3 border-t border-apple-border">
                <Zap className="w-3 h-3 text-amber-500 inline mr-1 -mt-0.5" />
                {synthesis.signal_detection}
              </p>
            )}
          </motion.div>
        )}

        {/* Causal Hypotheses */}
        {isComplete && hypotheses.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mt-6"
          >
            <h3 className="text-section text-apple-text mb-3">Causal Hypotheses</h3>
            <div className="space-y-3">
              {[...hypotheses]
                .sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
                .map((h, i) => (
                  <HypothesisCard key={i} hypothesis={h} rank={i + 1} />
                ))}
            </div>
          </motion.div>
        )}

        {/* Next Best Actions */}
        {isComplete && nbas.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mt-6"
          >
            <NBAPanel actions={nbas} />
          </motion.div>
        )}

        {/* Single Domain Findings */}
        {isComplete && synthesis.single_domain_findings?.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="mt-6"
          >
            <h3 className="text-section text-apple-text mb-3">Additional Findings</h3>
            <div className="space-y-2">
              {synthesis.single_domain_findings.map((f, i) => (
                <div key={i} className="card p-4">
                  <span className="text-xs font-medium text-apple-accent uppercase">
                    {AGENT_NAMES[f.agent] || f.agent}
                  </span>
                  <p className="text-body text-apple-text mt-1">{f.finding}</p>
                  {f.recommendation && (
                    <p className="text-caption text-apple-secondary mt-1">{f.recommendation}</p>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Reasoning Trace Toggle */}
        {isComplete && (
          <>
            <button
              onClick={() => setShowTrace(!showTrace)}
              className="flex items-center gap-2 mt-6 text-caption text-apple-accent hover:underline"
            >
              <ChevronDown className={`w-4 h-4 transition-transform ${showTrace ? 'rotate-180' : ''}`} />
              {showTrace ? 'Hide agent reasoning' : 'Show full agent reasoning'}
            </button>

            <AnimatePresence>
              {showTrace && <ReasoningTrace agentOutputs={agentOutputs} />}
            </AnimatePresence>

            <div className="flex items-center gap-4 mt-6 pt-4 border-t border-apple-border">
              <span className="text-caption text-apple-secondary">
                {synthesis.confidence_assessment || `${Object.keys(agentOutputs).length} agents · Cross-domain synthesis`} · Live data
              </span>
            </div>

            <ActionButtons synthesis={synthesis} />
          </>
        )}

        {loading && !investigationError && investigationPhases.length === 0 && (
          <div className="flex flex-col items-center justify-center h-64">
            <Loader2 className="w-8 h-8 text-apple-secondary animate-spin mb-4" />
            <p className="text-body text-apple-secondary">Launching investigation...</p>
          </div>
        )}
      </div>
    </motion.div>
  )
}


function AgentTimeline({ phases, loading }) {
  // Group phases by agent
  const agentPhases = {}
  for (const p of phases) {
    const agent = p.agent_id || 'conductor'
    if (!agentPhases[agent]) agentPhases[agent] = []
    agentPhases[agent].push(p)
  }

  const prpaOrder = ['perceive', 'reason', 'plan', 'act', 'reflect']

  if (phases.length === 0 && !loading) return null

  return (
    <div className="space-y-3">
      {Object.entries(agentPhases).map(([agent, agentPhs]) => {
        const isPRPA = agentPhs.some(p => prpaOrder.includes(p.phase))
        const latestPhase = agentPhs[agentPhs.length - 1]?.phase
        const completedPhases = new Set(agentPhs.map(p => p.phase))

        return (
          <motion.div
            key={agent}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="card p-4"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-caption font-medium text-apple-text">
                {AGENT_NAMES[agent] || agent}
              </span>
              {loading && latestPhase && (
                <span className="flex items-center gap-1.5 text-xs text-apple-accent">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  {PHASE_LABELS[latestPhase] || latestPhase}
                </span>
              )}
            </div>

            {isPRPA ? (
              <div className="flex items-center gap-1">
                {prpaOrder.map((step, i) => {
                  const done = completedPhases.has(step)
                  const active = latestPhase === step && loading
                  return (
                    <div key={step} className="flex items-center gap-1">
                      <div
                        className={`px-2 py-0.5 rounded text-xs font-medium transition-all ${
                          done
                            ? 'bg-apple-text text-white'
                            : active
                              ? 'bg-apple-accent/20 text-apple-accent animate-pulse'
                              : 'bg-apple-border/50 text-apple-secondary'
                        }`}
                      >
                        {step.charAt(0).toUpperCase() + step.slice(1)}
                      </div>
                      {i < prpaOrder.length - 1 && (
                        <div className={`w-3 h-0.5 ${done ? 'bg-apple-text' : 'bg-apple-border'}`} />
                      )}
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="space-y-1">
                {agentPhs.map((p, i) => (
                  <p key={i} className="text-caption text-apple-secondary">
                    {PHASE_LABELS[p.phase] || p.phase}
                    {p.data?.query && ` — "${p.data.query}"`}
                    {p.data?.agents && ` — ${p.data.agents.join(', ')}`}
                  </p>
                ))}
              </div>
            )}
          </motion.div>
        )
      })}
    </div>
  )
}


function HypothesisCard({ hypothesis, rank }) {
  const [expanded, setExpanded] = useState(false)
  const confidence = Math.min(100, Math.max(0, Math.round((hypothesis.confidence || 0) * 100)))
  const filled = Math.round(confidence / 10)

  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold text-apple-accent">H{rank}</span>
            {hypothesis.site_ids?.length > 0 && (
              <span className="text-xs text-apple-secondary">
                {hypothesis.site_ids.join(', ')}
              </span>
            )}
          </div>
          <p className="text-body font-medium text-apple-text">{hypothesis.finding}</p>
          {hypothesis.causal_chain && (
            <CausalChainFlow chain={hypothesis.causal_chain} />
          )}
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <ConfidenceBar filled={filled} />
          <span className="text-caption text-apple-secondary w-8">{confidence}%</span>
        </div>
      </div>

      {hypothesis.actual_interpretation && hypothesis.actual_interpretation !== hypothesis.finding && (
        <div className="mt-3 p-3 bg-apple-bg rounded-lg">
          {hypothesis.naive_interpretation && (
            <p className="text-xs text-apple-secondary mb-1">
              <span className="line-through">{hypothesis.naive_interpretation}</span>
            </p>
          )}
          <p className="text-caption text-apple-text">{hypothesis.actual_interpretation}</p>
        </div>
      )}

      <button
        onClick={() => setExpanded(!expanded)}
        className="text-xs text-apple-accent mt-2 hover:underline"
      >
        {expanded ? 'Hide evidence' : 'Show evidence'}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-3 space-y-2">
              {hypothesis.hypothesis_test && (
                <div className="text-xs">
                  <span className="font-medium text-apple-text">Hypothesis test: </span>
                  <span className="text-apple-secondary">{hypothesis.hypothesis_test}</span>
                </div>
              )}
              <TemporalEvidenceBar evidence={hypothesis.confirming_evidence} />
              {hypothesis.confirming_evidence?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-green-600 mb-1">Confirming evidence</p>
                  {hypothesis.confirming_evidence.map((e, i) => (
                    <p key={i} className="text-xs text-apple-secondary pl-3 border-l-2 border-green-300 mb-1">{e}</p>
                  ))}
                </div>
              )}
              {hypothesis.refuting_evidence?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-red-500 mb-1">Refuting evidence</p>
                  {hypothesis.refuting_evidence.map((e, i) => (
                    <p key={i} className="text-xs text-apple-secondary pl-3 border-l-2 border-red-300 mb-1">{e}</p>
                  ))}
                </div>
              )}
              {hypothesis.recommended_action && (
                <div className="pt-2 border-t border-apple-border">
                  <p className="text-xs font-medium text-apple-text">Recommended: </p>
                  <p className="text-xs text-apple-secondary">{hypothesis.recommended_action}</p>
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
  const urgencyColors = {
    immediate: 'bg-red-100 text-red-700 border-red-200',
    this_week: 'bg-amber-100 text-amber-700 border-amber-200',
    this_month: 'bg-blue-100 text-blue-700 border-blue-200',
  }

  return (
    <div>
      <h3 className="text-section text-apple-text mb-3">Next Best Actions</h3>
      <div className="space-y-2">
        {[...actions]
          .sort((a, b) => (a.priority || 99) - (b.priority || 99))
          .map((nba, i) => (
            <div key={i} className="card p-4 flex gap-4">
              <div className="shrink-0 w-7 h-7 rounded-full bg-apple-text text-white flex items-center justify-center text-xs font-bold">
                {nba.priority || i + 1}
              </div>
              <div className="flex-1">
                <p className="text-body font-medium text-apple-text">{nba.action}</p>
                {nba.rationale && (
                  <p className="text-caption text-apple-secondary mt-0.5">{nba.rationale}</p>
                )}
                <div className="flex items-center gap-2 mt-2">
                  {nba.urgency && (
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${urgencyColors[nba.urgency] || 'bg-gray-100 text-gray-600 border-gray-200'}`}>
                      {nba.urgency.replace('_', ' ')}
                    </span>
                  )}
                  {nba.owner && (
                    <span className="text-xs text-apple-secondary">{nba.owner}</span>
                  )}
                </div>
                {nba.expected_impact && (
                  <p className="text-xs text-apple-accent mt-1">{nba.expected_impact}</p>
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
    <div className="flex flex-wrap items-center gap-1 mt-2">
      {nodes.map((node, i) => (
        <div key={i} className="flex items-center gap-1">
          <span className="px-3 py-1.5 bg-apple-accent/10 text-apple-accent text-xs font-medium rounded-full border border-apple-accent/20">
            {node.trim()}
          </span>
          {i < nodes.length - 1 && (
            <ChevronRight className="w-3.5 h-3.5 text-apple-secondary/50 shrink-0" />
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
    <div className="space-y-2 mb-2">
      <p className="text-xs font-medium text-apple-text">Temporal comparison</p>
      {pairs.map((p, i) => {
        const max = Math.max(p.before, p.after)
        const beforePct = max > 0 ? (p.before / max) * 100 : 0
        const afterPct = max > 0 ? (p.after / max) * 100 : 0
        const worsened = p.after > p.before

        return (
          <div key={i} className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs text-apple-secondary w-14 text-right shrink-0">Before</span>
              <div className="flex-1 h-4 bg-apple-border/30 rounded-full overflow-hidden">
                <div
                  className="h-full bg-green-500/70 rounded-full transition-all"
                  style={{ width: `${Math.max(beforePct, 4)}%` }}
                />
              </div>
              <span className="text-xs text-apple-secondary w-16 shrink-0">{p.before}{p.unit}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-apple-secondary w-14 text-right shrink-0">After</span>
              <div className="flex-1 h-4 bg-apple-border/30 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${worsened ? 'bg-red-500/70' : 'bg-amber-500/70'}`}
                  style={{ width: `${Math.max(afterPct, 4)}%` }}
                />
              </div>
              <span className="text-xs text-apple-secondary w-16 shrink-0">{p.after}{p.unit}</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}


function ConfidenceBar({ filled }) {
  return (
    <div className="flex">
      {Array.from({ length: 10 }).map((_, i) => (
        <div
          key={i}
          className={`w-1.5 h-3 ${i < filled ? 'bg-apple-text' : 'bg-apple-border'} ${
            i === 0 ? 'rounded-l' : i === 9 ? 'rounded-r' : ''
          }`}
        />
      ))}
    </div>
  )
}


function ReasoningTrace({ agentOutputs }) {
  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      className="overflow-hidden"
    >
      <div className="mt-4 space-y-4">
        {Object.entries(agentOutputs).map(([agentId, output]) => (
          <div key={agentId} className="p-4 bg-apple-bg rounded-xl">
            <p className="text-caption font-medium text-apple-text mb-3">
              {AGENT_NAMES[agentId] || agentId}
              {output.severity && (
                <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${
                  output.severity === 'critical' ? 'bg-red-100 text-red-700' :
                  output.severity === 'warning' ? 'bg-amber-100 text-amber-700' :
                  'bg-green-100 text-green-700'
                }`}>
                  {output.severity}
                </span>
              )}
            </p>
            {output.summary && (
              <p className="text-sm text-apple-text mb-2">{output.summary}</p>
            )}
            {output.reasoning_trace?.map((step, idx) => (
              <div key={idx} className="border-l-2 border-apple-accent/30 pl-3 mb-2">
                <p className="text-xs font-medium text-apple-accent">{step.phase || step.step || `Step ${idx + 1}`}</p>
                <p className="text-xs text-apple-secondary">{step.detail || step.insight || JSON.stringify(step)}</p>
              </div>
            ))}
            {output.findings?.length > 0 && (
              <div className="mt-2 pt-2 border-t border-apple-border">
                <p className="text-xs font-medium text-apple-text mb-1">Findings:</p>
                {output.findings.map((f, i) => (
                  <p key={i} className="text-xs text-apple-secondary">
                    {typeof f === 'string' ? f : JSON.stringify(f)}
                  </p>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </motion.div>
  )
}


function ActionButtons({ synthesis }) {
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
      <button className="button-primary flex items-center gap-2">
        <ExternalLink className="w-4 h-4" />
        Export Report
      </button>
      <button onClick={handleCopy} className="button-secondary flex items-center gap-2">
        {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
        {copied ? 'Copied' : 'Copy'}
      </button>
    </div>
  )
}
