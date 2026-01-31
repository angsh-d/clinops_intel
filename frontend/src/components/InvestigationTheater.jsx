import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, ChevronDown, ExternalLink, Copy, Check } from 'lucide-react'
import { useStore } from '../lib/store'

const PHASES = ['Routing', 'Gathering', 'Analyzing', 'Planning', 'Investigating', 'Finding']

export function InvestigationTheater() {
  const { investigation, setInvestigation } = useStore()
  const [currentPhase, setCurrentPhase] = useState(0)
  const [typedText, setTypedText] = useState('')
  const [showTrace, setShowTrace] = useState(false)
  const [phaseData, setPhaseData] = useState({})
  
  const finalAnswer = `Query spike at ${investigation?.site?.id || 'this site'} is driven by Lab Results and Drug Accountability pages.

Root Cause: Data entry proficiency gap following CRA transition, not a monitoring-triggered spike.

Evidence:
• Lab Results page: 38% of queries (norm: 18%)
• Drug Accountability: 22% of queries (norm: 12%)
• Query rate 2.5x peer average for Academic sites
• No monitoring visit correlation detected

Recommended Action: Targeted training on Lab Results and Drug Accountability CRF completion. Expected 40-50% query reduction within 3-4 weeks based on similar interventions at peer sites.`

  useEffect(() => {
    if (!investigation) return
    
    const delays = [500, 1500, 3000, 4500, 6000, 7500]
    const timers = []
    
    delays.forEach((delay, index) => {
      timers.push(setTimeout(() => {
        setCurrentPhase(index)
        setPhaseData(prev => ({
          ...prev,
          [index]: getPhaseContent(index, investigation)
        }))
      }, delay))
    })
    
    const typingDelay = 8000
    let charIndex = 0
    const typeTimer = setInterval(() => {
      if (charIndex <= finalAnswer.length) {
        setTypedText(finalAnswer.slice(0, charIndex))
        charIndex++
      } else {
        clearInterval(typeTimer)
      }
    }, 15)
    
    return () => {
      timers.forEach(clearTimeout)
      clearInterval(typeTimer)
    }
  }, [investigation])
  
  if (!investigation) return null
  
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
          {investigation.site?.id} · Just now
        </motion.p>
        
        <PhaseIndicator phases={PHASES} currentPhase={currentPhase} />
        
        <div className="mt-8 space-y-4">
          <AnimatePresence mode="popLayout">
            {Object.entries(phaseData).map(([phase, content]) => (
              <PhaseCard key={phase} phase={parseInt(phase)} content={content} />
            ))}
          </AnimatePresence>
        </div>
        
        {currentPhase >= 5 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-8"
          >
            <div className="card p-6 border-l-4 border-l-[#5856D6] relative overflow-hidden">
              <div className="absolute inset-0 opacity-5 ai-gradient-border" />
              
              <h3 className="text-section text-apple-text mb-4">Finding</h3>
              
              <div className="prose prose-sm max-w-none">
                <pre className="whitespace-pre-wrap font-body text-body text-apple-text leading-relaxed bg-transparent p-0 m-0">
                  {typedText}
                  <span className="animate-pulse">|</span>
                </pre>
              </div>
              
              <div className="flex items-center gap-4 mt-6 pt-4 border-t border-apple-border">
                <ConfidenceBadge confidence={92} />
                <span className="text-caption text-apple-secondary">
                  Data Quality Agent · EDC + CTMS · Updated 2h ago
                </span>
              </div>
            </div>
            
            <button
              onClick={() => setShowTrace(!showTrace)}
              className="flex items-center gap-2 mt-4 text-caption text-apple-accent hover:underline"
            >
              <ChevronDown className={`w-4 h-4 transition-transform ${showTrace ? 'rotate-180' : ''}`} />
              {showTrace ? 'Hide reasoning trace' : 'Show full reasoning trace'}
            </button>
            
            <AnimatePresence>
              {showTrace && <ReasoningTrace />}
            </AnimatePresence>
            
            <FollowUpChips />
            
            <ActionButtons />
          </motion.div>
        )}
      </div>
    </motion.div>
  )
}

function PhaseIndicator({ phases, currentPhase }) {
  return (
    <div className="flex items-center justify-center gap-2">
      {phases.map((phase, i) => (
        <div key={phase} className="flex items-center gap-2">
          <motion.div
            initial={{ scale: 0.8 }}
            animate={{ 
              scale: i === currentPhase ? 1.2 : 1,
              backgroundColor: i <= currentPhase ? '#1D1D1F' : '#E5E5E5'
            }}
            className={`w-2 h-2 rounded-full ${i === currentPhase ? 'animate-pulse-slow' : ''}`}
          />
          {i < phases.length - 1 && (
            <div className={`w-8 h-0.5 ${i < currentPhase ? 'bg-apple-text' : 'bg-apple-border'}`} />
          )}
        </div>
      ))}
    </div>
  )
}

function PhaseCard({ phase, content }) {
  const titles = ['Routing', 'Gathering Data', 'Analyzing', 'Investigation Plan', 'Investigating', 'Finding']
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="card p-4"
    >
      <h4 className="text-caption text-apple-secondary uppercase tracking-wide mb-2">
        {titles[phase]}
      </h4>
      <div className="text-body text-apple-text space-y-1">
        {content.map((line, i) => (
          <motion.p
            key={i}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: i * 0.1 }}
            className="flex items-center gap-2"
          >
            {line.done !== undefined && (
              <span className={line.done ? 'text-apple-success' : 'text-apple-secondary'}>
                {line.done ? '✓' : '●'}
              </span>
            )}
            {line.text}
          </motion.p>
        ))}
      </div>
    </motion.div>
  )
}

function getPhaseContent(phase, investigation) {
  const site = investigation?.site?.id || 'SITE-012'
  
  switch (phase) {
    case 0:
      return [{ text: `Routing to Data Quality specialist — this question is about query patterns. Confidence: 97%` }]
    case 1:
      return [
        { text: 'Querying eCRF entry data... 847 records', done: true },
        { text: 'Querying query history... 312 queries', done: true },
        { text: 'Checking CRA assignment history... 2 assignments', done: true },
        { text: 'Loading monitoring visit log...', done: false }
      ]
    case 2:
      return [
        { text: '1. CRA training gap — query concentration on Lab Results and AE pages suggests proficiency issue' },
        { text: '2. Monitoring spike — recent visit may have triggered query burst' },
        { text: '3. Site complexity — academic high-volume site' }
      ]
    case 3:
      return [
        { text: '(1) Check CRF page distribution of queries' },
        { text: '(2) Cross-reference monitoring visit dates' },
        { text: '(3) Compare with peer sites of similar profile' },
        { text: '(4) Examine CRA assignment timeline' }
      ]
    case 4:
      return [
        { text: 'Step 1: Lab Results 38%, Drug Accountability 22%, AE 18% → Concentration confirmed', done: true },
        { text: 'Step 2: Last visit 42 days ago, no triggered queries → Monitoring spike ruled out', done: true },
        { text: 'Step 3: 2.5x average for similar Academic sites → Genuinely anomalous', done: true },
        { text: 'Step 4: Single CRA since activation → CRA change ruled out', done: true }
      ]
    default:
      return []
  }
}

function ConfidenceBadge({ confidence }) {
  const filled = Math.round(confidence / 10)
  
  return (
    <div className="flex items-center gap-1.5">
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
      <span className="text-caption text-apple-secondary">{confidence}%</span>
    </div>
  )
}

function ReasoningTrace() {
  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      className="overflow-hidden"
    >
      <div className="mt-4 p-4 bg-apple-bg rounded-xl font-mono text-xs text-apple-secondary space-y-2">
        <p>{"{"} "agent": "data_quality", "confidence": 0.92 {"}"}</p>
        <p>{"{"} "data_sources": ["EDC", "CTMS"], "records_analyzed": 1159 {"}"}</p>
        <p>{"{"} "hypotheses_tested": 3, "hypotheses_rejected": 2 {"}"}</p>
        <p>{"{"} "primary_signal": "query_concentration", "pages": ["Lab Results", "Drug Accountability"] {"}"}</p>
        <p>{"{"} "peer_comparison": {"{"} "site_type": "Academic", "ratio": 2.5 {"}"} {"}"}</p>
      </div>
    </motion.div>
  )
}

function FollowUpChips() {
  const chips = [
    'Show query trend over time',
    'Other sites with similar patterns?',
    'Impact on database readiness?',
    'Generate site action report'
  ]
  
  return (
    <div className="flex flex-wrap gap-2 mt-6">
      {chips.map((chip) => (
        <button
          key={chip}
          className="px-3 py-1.5 bg-apple-bg border border-apple-border rounded-full 
                     text-caption text-apple-secondary hover:text-apple-text hover:border-apple-text/30 transition-colors"
        >
          {chip}
        </button>
      ))}
    </div>
  )
}

function ActionButtons() {
  const [copied, setCopied] = useState(false)
  
  const handleCopy = () => {
    navigator.clipboard.writeText('Investigation summary copied')
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
