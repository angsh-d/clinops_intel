import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send, Loader2, ArrowUpDown,
  Sparkles, ChevronDown, ChevronRight,
} from 'lucide-react'

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

export function AssistantPanel({
  conversationHistory,
  isInvestigating,
  currentPhase,
  error,
  query,
  setQuery,
  onSubmit,
  onSiteClick,
  resolveText,
  quickActions,
  exploreActions,
  onQuickAction,
  onNavigate,
  showExplore,
  setShowExplore,
  width = 440,
  onResize,
}) {
  const scrollRef = useRef(null)
  const inputRef = useRef(null)
  const [isDragging, setIsDragging] = useState(false)

  const isIdle = conversationHistory.length === 0 && !isInvestigating

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [conversationHistory, isInvestigating])

  const handleDragStart = useCallback((e) => {
    e.preventDefault()
    setIsDragging(true)
    const handleMove = (ev) => {
      const newWidth = Math.min(800, Math.max(380, window.innerWidth - ev.clientX))
      onResize?.(newWidth)
    }
    const handleUp = () => {
      setIsDragging(false)
      window.removeEventListener('mousemove', handleMove)
      window.removeEventListener('mouseup', handleUp)
    }
    window.addEventListener('mousemove', handleMove)
    window.addEventListener('mouseup', handleUp)
  }, [onResize])

  const lastAssistantMsg = [...conversationHistory].reverse().find(m => m.role === 'assistant')
  const synthesis = lastAssistantMsg?.content?.synthesis
  const displayFormat = synthesis?.display_format || { type: 'narrative' }

  return (
    <div
      className="fixed right-0 top-[57px] bottom-0 z-[60] bg-apple-surface border-l border-apple-divider flex flex-col"
      style={{
        width,
        transition: isDragging ? 'none' : 'width 0.15s ease-out',
      }}
    >
      {/* Drag handle */}
      <div
        className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize z-10 hover:bg-apple-grey-300 transition-colors"
        onMouseDown={handleDragStart}
        style={{ backgroundColor: isDragging ? 'var(--color-apple-grey-400, #9ca3af)' : 'transparent' }}
      />
      {/* Header */}
      <div className="flex items-center px-5 py-3.5 border-b border-apple-divider flex-shrink-0">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-apple-grey-500" />
          <span className="text-[13px] font-semibold text-apple-text">Assistant</span>
        </div>
      </div>

      {isIdle ? (
        /* ── Idle state: search + quick actions + explore ── */
        <div className="flex-1 overflow-y-auto px-5 py-6 space-y-5">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-apple-grey-50 rounded-full mb-3">
              <Sparkles className="w-3.5 h-3.5 text-apple-grey-500" />
              <span className="text-[11px] font-medium text-apple-tertiary uppercase tracking-wider">AI-Powered Investigation</span>
            </div>
            <h2 className="text-[17px] font-semibold text-apple-text mb-1">
              What would you like to investigate?
            </h2>
            <p className="text-[12px] text-apple-secondary">
              Ask about enrollment, data quality, sites, vendors, or financials.
            </p>
          </div>

          <form onSubmit={onSubmit} className="relative">
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., Why is SITE-074 underperforming?"
              className="w-full px-4 py-3.5 pr-12 bg-apple-grey-50 border border-apple-grey-200 rounded-xl text-[13px] text-apple-text placeholder:text-apple-tertiary focus:outline-none focus:border-apple-grey-400 focus:bg-white transition-all"
            />
            <button
              type="submit"
              disabled={!query.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center rounded-lg bg-apple-grey-800 text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-apple-grey-700 transition-all"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>

          <div className="space-y-2">
            {quickActions?.map((action) => (
              <button
                key={action.label}
                onClick={() => onQuickAction?.(action.label)}
                className="w-full flex items-center gap-2.5 px-3.5 py-2.5 bg-apple-grey-50 border border-apple-grey-100 rounded-xl text-[12px] text-apple-secondary hover:text-apple-text hover:bg-apple-grey-100 hover:border-apple-grey-200 transition-all text-left"
              >
                <action.icon className="w-3.5 h-3.5 flex-shrink-0" />
                <span className="leading-snug">{action.label}</span>
              </button>
            ))}
          </div>

          <div>
            <button
              onClick={() => setShowExplore?.(!showExplore)}
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
                  <div className="space-y-2 pt-2">
                    {exploreActions?.map((action) => (
                      <button
                        key={action.label}
                        onClick={() => onNavigate?.(action.navId)}
                        className="w-full flex items-center gap-2.5 px-3.5 py-2.5 bg-apple-grey-50 border border-apple-grey-100 rounded-xl text-[12px] text-apple-secondary hover:text-apple-text hover:bg-apple-grey-100 hover:border-apple-grey-200 transition-all text-left"
                      >
                        <action.icon className="w-3.5 h-3.5 flex-shrink-0" />
                        {action.label}
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      ) : (
        /* ── Active state: conversation + investigation ── */
        <>
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
            {conversationHistory.map((msg, i) => (
              <PanelMessage
                key={i}
                message={msg}
                resolveText={resolveText}
                onSiteClick={onSiteClick}
                displayFormat={i === conversationHistory.length - 1 && msg.role === 'assistant' ? displayFormat : null}
              />
            ))}

            {isInvestigating && (
              <InvestigationProgress currentPhase={currentPhase} />
            )}

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl">
                <p className="text-[12px] text-red-700">{error}</p>
              </div>
            )}
          </div>

          {/* Fixed bottom input */}
          <div className="flex-shrink-0 border-t border-apple-divider p-4">
            <form onSubmit={onSubmit} className="relative">
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask a follow-up..."
                disabled={isInvestigating}
                className="w-full px-4 py-3 pr-12 bg-apple-grey-50 border border-apple-grey-200 rounded-xl text-[13px] text-apple-text placeholder:text-apple-tertiary focus:outline-none focus:border-apple-grey-400 focus:bg-white transition-all disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={!query.trim() || isInvestigating}
                className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center rounded-lg bg-apple-grey-800 text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-apple-grey-700 transition-all"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>
        </>
      )}
    </div>
  )
}


function PanelMessage({ message, resolveText, onSiteClick, displayFormat }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] px-3.5 py-2.5 bg-apple-grey-900 text-white rounded-2xl rounded-br-md">
          <p className="text-[13px] leading-relaxed">{message.content}</p>
        </div>
      </div>
    )
  }

  const data = message.content
  const synthesis = data?.synthesis
  if (!synthesis) return null

  const formatType = displayFormat?.type || 'narrative'

  return (
    <div className="space-y-3">
      {/* Narrative section — always shown for narrative types */}
      {(formatType === 'narrative' || formatType === 'narrative_table' || formatType === 'narrative_chart') && (
        <NarrativeSection
          synthesis={synthesis}
          data={data}
          resolveText={resolveText}
          onSiteClick={onSiteClick}
        />
      )}

      {/* Table section */}
      {(formatType === 'narrative_table' || formatType === 'table') && displayFormat?.table_data && (
        <TableSection
          tableData={displayFormat.table_data}
          onSiteClick={onSiteClick}
        />
      )}

      {/* Chart section */}
      {(formatType === 'narrative_chart') && displayFormat?.chart_data && (
        <ChartSection chartData={displayFormat.chart_data} />
      )}

      {/* For pure table mode, still show executive summary */}
      {formatType === 'table' && (
        <div className="bg-white rounded-xl border border-apple-grey-100 p-4">
          <p className="text-[12px] text-apple-text leading-relaxed">
            {resolveText(synthesis.executive_summary)}
          </p>
        </div>
      )}
    </div>
  )
}


function NarrativeSection({ synthesis, data, resolveText, onSiteClick }) {
  const hypotheses = synthesis?.cross_domain_findings || []
  const singleFindings = synthesis?.single_domain_findings || []
  const nbas = synthesis?.next_best_actions || []
  const topAction = nbas.find(n => n.priority === 1) || nbas[0]
  const remainingActions = nbas.filter(a => a !== topAction)
  const [expandedIdx, setExpandedIdx] = useState(0) // auto-expand first finding
  const [showAllActions, setShowAllActions] = useState(false)
  const [showSingleFindings, setShowSingleFindings] = useState(false)

  return (
    <div className="space-y-3">
      {/* Executive summary */}
      {synthesis?.executive_summary && (
        <div className="bg-white rounded-xl border border-apple-grey-100 p-4">
          <p className="text-[12px] text-apple-text leading-relaxed">
            {resolveText(synthesis.executive_summary)}
          </p>
        </div>
      )}

      {/* Cross-domain findings with expandable evidence */}
      {hypotheses.map((hyp, idx) => (
        <div key={idx} className={`bg-white rounded-xl border border-apple-grey-100 ${idx === 0 ? 'border-l-[3px] border-l-amber-400' : ''} overflow-hidden`}>
          <button
            className="w-full p-4 text-left"
            onClick={() => setExpandedIdx(expandedIdx === idx ? null : idx)}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-apple-tertiary mb-1.5">
                  {idx === 0 ? 'Root Cause' : `Finding ${idx + 1}`}
                </p>
                <p className="text-[12px] text-apple-text leading-relaxed">{resolveText(hyp.finding)}</p>
              </div>
              <ChevronDown className={`w-3.5 h-3.5 text-apple-grey-400 flex-shrink-0 mt-1 transition-transform ${expandedIdx === idx ? 'rotate-180' : ''}`} />
            </div>
            {hyp.causal_chain && (
              <div className="flex items-center gap-1.5 mt-2.5 flex-wrap">
                {hyp.causal_chain.split(/\s*(?:->|→)\s*/).filter(Boolean).map((node, i, arr) => (
                  <div key={i} className="flex items-center gap-1.5">
                    <span className="text-[10px] text-apple-secondary bg-apple-grey-100 px-2 py-0.5 rounded-md">{node.trim()}</span>
                    {i < arr.length - 1 && <span className="text-[10px] text-apple-grey-400">→</span>}
                  </div>
                ))}
              </div>
            )}
          </button>
          <AnimatePresence initial={false}>
            {expandedIdx === idx && (
              <motion.div
                key={`evidence-${idx}`}
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <EvidenceDetail hyp={hyp} resolveText={resolveText} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ))}

      {/* Single-domain findings */}
      {singleFindings.length > 0 && (
        <div className="bg-white rounded-xl border border-apple-grey-100 overflow-hidden">
          <button
            className="w-full px-4 py-3 text-left flex items-center justify-between"
            onClick={() => setShowSingleFindings(!showSingleFindings)}
          >
            <p className="text-[10px] font-semibold uppercase tracking-wider text-apple-tertiary">
              Agent Findings ({singleFindings.length})
            </p>
            <ChevronDown className={`w-3.5 h-3.5 text-apple-grey-400 transition-transform ${showSingleFindings ? 'rotate-180' : ''}`} />
          </button>
          <AnimatePresence initial={false}>
            {showSingleFindings && (
              <motion.div
                key="single-findings"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="px-4 pb-3 space-y-2.5 border-t border-apple-grey-50 pt-2.5">
                  {singleFindings.map((sf, i) => (
                    <div key={i} className="text-[11px] text-apple-secondary leading-relaxed border-l-2 border-apple-grey-200 pl-2.5">
                      <span className="text-[9px] font-semibold uppercase tracking-wider text-apple-muted">{sf.agent?.replace(/_/g, ' ')}</span>
                      <p className="mt-0.5">{resolveText(sf.finding)}</p>
                      {sf.recommendation && (
                        <p className="text-[10px] text-apple-tertiary mt-1">{resolveText(sf.recommendation)}</p>
                      )}
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Top action */}
      {topAction && (
        <div className="bg-white rounded-xl border border-apple-grey-100 border-l-[3px] border-l-blue-400 p-4">
          <div className="flex items-center gap-2 mb-1.5">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-apple-tertiary">Recommended Action</p>
            {topAction.urgency === 'immediate' && (
              <span className="text-[9px] font-medium text-white bg-apple-grey-800 px-1.5 py-0.5 rounded-full">Now</span>
            )}
          </div>
          <p className="text-[12px] text-apple-text leading-relaxed">{resolveText(topAction.action)}</p>
          {topAction.rationale && (
            <p className="text-[10px] text-apple-tertiary mt-1.5 leading-relaxed">{resolveText(topAction.rationale)}</p>
          )}
          {topAction.owner && (
            <p className="text-[10px] text-apple-muted mt-1">{topAction.owner}</p>
          )}
        </div>
      )}

      {/* Expandable additional actions */}
      {remainingActions.length > 0 && (
        <div className="bg-white rounded-xl border border-apple-grey-100 overflow-hidden">
          <button
            className="w-full px-4 py-2.5 text-left flex items-center justify-between"
            onClick={() => setShowAllActions(!showAllActions)}
          >
            <p className="text-[10px] font-semibold uppercase tracking-wider text-apple-tertiary">
              {remainingActions.length} more action{remainingActions.length > 1 ? 's' : ''}
            </p>
            <ChevronDown className={`w-3.5 h-3.5 text-apple-grey-400 transition-transform ${showAllActions ? 'rotate-180' : ''}`} />
          </button>
          <AnimatePresence initial={false}>
            {showAllActions && (
              <motion.div
                key="more-actions"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="px-4 pb-3 space-y-3 border-t border-apple-grey-50 pt-2.5">
                  {remainingActions.map((nba, i) => (
                    <div key={i} className="border-l-2 border-blue-300 pl-3">
                      <div className="flex items-center gap-2 mb-0.5">
                        <p className="text-[10px] font-semibold text-apple-tertiary">
                          {nba.priority ? `Priority ${nba.priority}` : `Action ${i + 2}`}
                        </p>
                        {nba.urgency && (
                          <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full ${nba.urgency === 'immediate' ? 'text-white bg-apple-grey-800' : 'text-apple-tertiary bg-apple-grey-100'}`}>
                            {nba.urgency.replace(/_/g, ' ')}
                          </span>
                        )}
                      </div>
                      <p className="text-[12px] text-apple-text leading-relaxed">{resolveText(nba.action)}</p>
                      {nba.rationale && (
                        <p className="text-[10px] text-apple-tertiary mt-1 leading-relaxed">{resolveText(nba.rationale)}</p>
                      )}
                      {nba.owner && (
                        <p className="text-[10px] text-apple-muted mt-0.5">{nba.owner}</p>
                      )}
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  )
}


function EvidenceDetail({ hyp, resolveText }) {
  const confirming = hyp.confirming_evidence || []
  const refuting = hyp.refuting_evidence || []
  const hasInterpretation = hyp.naive_interpretation || hyp.actual_interpretation
  const confidence = hyp.confidence != null ? Math.round(hyp.confidence * 100) : null

  return (
    <div className="px-4 pb-4 pt-1 space-y-3 border-t border-apple-grey-50">
      {/* What we investigated */}
      {hyp.hypothesis_test && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-apple-tertiary mb-1">What we investigated</p>
          <p className="text-[11px] text-apple-secondary pl-3 leading-relaxed">{resolveText(hyp.hypothesis_test)}</p>
        </div>
      )}

      {/* Naive vs Actual interpretation */}
      {hasInterpretation && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-apple-tertiary mb-1.5">Interpretation</p>
          <div className="flex items-stretch gap-2 pl-3">
            {hyp.naive_interpretation && (
              <div className="flex-1 bg-apple-grey-50 rounded-lg p-2.5">
                <p className="text-[9px] font-semibold uppercase tracking-wider text-apple-muted mb-1">Naive reading</p>
                <p className="text-[11px] text-apple-secondary leading-relaxed">{resolveText(hyp.naive_interpretation)}</p>
              </div>
            )}
            {hyp.naive_interpretation && hyp.actual_interpretation && (
              <span className="text-apple-grey-400 self-center text-[14px]">→</span>
            )}
            {hyp.actual_interpretation && (
              <div className="flex-1 bg-apple-grey-50 rounded-lg p-2.5">
                <p className="text-[9px] font-semibold uppercase tracking-wider text-apple-muted mb-1">Actual finding</p>
                <p className="text-[11px] text-apple-text leading-relaxed">{resolveText(hyp.actual_interpretation)}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Confirming evidence */}
      {confirming.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-apple-tertiary mb-1">Confirming evidence</p>
          <ul className="space-y-1 pl-3">
            {confirming.map((e, i) => (
              <li key={i} className="text-[11px] text-apple-secondary leading-relaxed border-l-2 border-emerald-300 pl-2.5">{resolveText(e)}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Refuting evidence */}
      {refuting.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-apple-tertiary mb-1">Refuting evidence</p>
          <ul className="space-y-1 pl-3">
            {refuting.map((e, i) => (
              <li key={i} className="text-[11px] text-apple-secondary leading-relaxed border-l-2 border-red-300 pl-2.5">{resolveText(e)}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Confidence bar */}
      {confidence != null && (
        <div className="pl-3">
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-apple-grey-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-apple-grey-600 rounded-full"
                style={{ width: `${confidence}%` }}
              />
            </div>
            <span className="text-[10px] font-mono text-apple-tertiary">{confidence}%</span>
          </div>
        </div>
      )}
    </div>
  )
}


function TableSection({ tableData, onSiteClick }) {
  const [sortCol, setSortCol] = useState(null)
  const [sortDir, setSortDir] = useState('asc')

  if (!tableData?.headers || !tableData?.rows) return null

  const handleSort = (colIdx) => {
    if (sortCol === colIdx) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortCol(colIdx)
      setSortDir('asc')
    }
  }

  const sortedRows = [...(tableData.rows || [])]
  if (sortCol !== null) {
    sortedRows.sort((a, b) => {
      const va = a[sortCol] ?? ''
      const vb = b[sortCol] ?? ''
      const na = parseFloat(va)
      const nb = parseFloat(vb)
      if (!isNaN(na) && !isNaN(nb)) {
        return sortDir === 'asc' ? na - nb : nb - na
      }
      return sortDir === 'asc'
        ? String(va).localeCompare(String(vb))
        : String(vb).localeCompare(String(va))
    })
  }

  const isSiteId = (val) => typeof val === 'string' && /^SITE-\d+$/.test(val)

  return (
    <div className="bg-white rounded-xl border border-apple-grey-100 overflow-hidden">
      {tableData.title && (
        <div className="px-4 py-2.5 border-b border-apple-grey-100">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-apple-tertiary">{tableData.title}</p>
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="text-[9px] uppercase tracking-wider text-apple-tertiary border-b border-apple-grey-50">
              {tableData.headers.map((h, i) => (
                <th
                  key={i}
                  className="text-left px-3 py-2 font-semibold cursor-pointer hover:text-apple-text transition-colors"
                  onClick={() => handleSort(i)}
                >
                  <span className="inline-flex items-center gap-1">
                    {h}
                    {sortCol === i && (
                      <ArrowUpDown className="w-2.5 h-2.5" />
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-apple-grey-50">
            {sortedRows.map((row, ri) => (
              <tr key={ri} className="hover:bg-apple-grey-50 transition-colors">
                {row.map((cell, ci) => (
                  <td key={ci} className="px-3 py-2 max-w-xs">
                    {isSiteId(cell) ? (
                      <button
                        onClick={() => onSiteClick?.(cell)}
                        className="text-blue-600 hover:underline font-medium"
                      >
                        {cell}
                      </button>
                    ) : (
                      <span className="text-apple-text text-[11px] leading-relaxed whitespace-pre-wrap">{cell ?? '—'}</span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}


function ChartSection({ chartData }) {
  if (!chartData?.labels || !chartData?.values) return null

  const maxVal = Math.max(...chartData.values, 1)
  const isBar = chartData.type !== 'line'

  return (
    <div className="bg-white rounded-xl border border-apple-grey-100 p-4">
      {chartData.title && (
        <p className="text-[10px] font-semibold uppercase tracking-wider text-apple-tertiary mb-3">{chartData.title}</p>
      )}
      {isBar ? (
        <div className="space-y-2">
          {chartData.labels.map((label, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="text-[10px] text-apple-secondary w-20 text-right shrink-0 truncate" title={label}>{label}</span>
              <div className="flex-1 h-5 bg-apple-grey-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-apple-grey-500 rounded-full transition-all"
                  style={{ width: `${(chartData.values[i] / maxVal) * 100}%` }}
                />
              </div>
              <span className="text-[10px] font-mono text-apple-secondary w-12 shrink-0 text-right">
                {chartData.values[i]}{chartData.unit ? ` ${chartData.unit}` : ''}
              </span>
            </div>
          ))}
        </div>
      ) : (
        /* Simple SVG line chart */
        <svg viewBox={`0 0 ${chartData.labels.length * 60} 120`} className="w-full h-32">
          {chartData.values.map((v, i) => {
            const x = i * 60 + 30
            const y = 110 - (v / maxVal) * 90
            const nextV = chartData.values[i + 1]
            const nextX = (i + 1) * 60 + 30
            const nextY = nextV != null ? 110 - (nextV / maxVal) * 90 : null
            return (
              <g key={i}>
                {nextY !== null && (
                  <line x1={x} y1={y} x2={nextX} y2={nextY} stroke="#6b7280" strokeWidth="1.5" />
                )}
                <circle cx={x} cy={y} r="3" fill="#374151" />
                <text x={x} y="118" textAnchor="middle" className="text-[8px] fill-current text-apple-tertiary">{chartData.labels[i]}</text>
              </g>
            )
          })}
        </svg>
      )}
    </div>
  )
}


function InvestigationProgress({ currentPhase }) {
  return (
    <div className="flex items-center gap-3 p-3 bg-apple-grey-50 border border-apple-grey-200 rounded-xl">
      <Loader2 className="w-4 h-4 text-[#5856D6] animate-spin flex-shrink-0" />
      <span className="text-[12px] text-apple-secondary">
        {PHASE_LABELS[currentPhase] || 'Processing...'}
      </span>
    </div>
  )
}
