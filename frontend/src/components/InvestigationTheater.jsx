import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, ChevronDown, ExternalLink, Copy, Check, Loader2 } from 'lucide-react'
import { useStore } from '../lib/store'
import { runInvestigation } from '../lib/api'

const PHASES = ['Routing', 'Gathering', 'Analyzing', 'Planning', 'Investigating', 'Finding']

export function InvestigationTheater() {
  const { investigation, setInvestigation } = useStore()
  const [currentPhase, setCurrentPhase] = useState(0)
  const [typedText, setTypedText] = useState('')
  const [showTrace, setShowTrace] = useState(false)
  const [phaseData, setPhaseData] = useState({})
  const [investigationResult, setInvestigationResult] = useState(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    if (!investigation) return
    
    async function fetchInvestigation() {
      setLoading(true)
      setCurrentPhase(0)
      setTypedText('')
      setPhaseData({})
      
      try {
        const result = await runInvestigation(
          investigation.question,
          investigation.site?.id
        )
        setInvestigationResult(result)
        
        // Animate through phases
        const delays = [500, 1500, 2500, 3500, 4500, 5500]
        const timers = []
        
        result.phases?.forEach((phase, index) => {
          timers.push(setTimeout(() => {
            setCurrentPhase(index)
            setPhaseData(prev => ({
              ...prev,
              [index]: phase.content
            }))
          }, delays[index]))
        })
        
        // Set phase to 5 (Finding) after all phases complete
        const phaseCount = result.phases?.length || 0
        timers.push(setTimeout(() => {
          setCurrentPhase(5)
        }, delays[phaseCount] || 5500))
        
        // Type the final answer
        const finalAnswer = buildFinalAnswer(result)
        const typingDelay = 6000
        let charIndex = 0
        const typeTimer = setInterval(() => {
          if (charIndex <= finalAnswer.length) {
            setTypedText(finalAnswer.slice(0, charIndex))
            charIndex++
          } else {
            clearInterval(typeTimer)
          }
        }, 12)
        
        timers.push(typeTimer)
        
        setLoading(false)
        
        return () => {
          timers.forEach(t => clearTimeout(t) || clearInterval(t))
        }
      } catch (error) {
        console.error('Investigation failed:', error)
        setLoading(false)
      }
    }
    
    fetchInvestigation()
  }, [investigation?.question, investigation?.site?.id])
  
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
        
        {loading ? (
          <div className="flex flex-col items-center justify-center h-64">
            <Loader2 className="w-8 h-8 text-apple-secondary animate-spin mb-4" />
            <p className="text-body text-apple-secondary">Analyzing data...</p>
          </div>
        ) : (
          <>
            <PhaseIndicator phases={PHASES} currentPhase={currentPhase} />
            
            <div className="mt-8 space-y-4">
              <AnimatePresence mode="popLayout">
                {Object.entries(phaseData).map(([phase, content]) => (
                  <PhaseCard key={phase} phase={parseInt(phase)} content={content} />
                ))}
              </AnimatePresence>
            </div>
            
            {currentPhase >= 5 && investigationResult && (
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
                    <ConfidenceBadge confidence={investigationResult.confidence || 88} />
                    <span className="text-caption text-apple-secondary">
                      {investigationResult.agent_id === 'data_quality' ? 'Data Quality Agent' : 'Analysis Agent'} · {investigationResult.finding?.data_sources || 'Database'} · Live data
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
                  {showTrace && <ReasoningTrace result={investigationResult} />}
                </AnimatePresence>
                
                <FollowUpChips />
                
                <ActionButtons />
              </motion.div>
            )}
          </>
        )}
      </div>
    </motion.div>
  )
}

function buildFinalAnswer(result) {
  if (!result?.finding) {
    return "Analysis complete. No significant issues detected."
  }
  
  const { finding } = result
  let answer = finding.summary || "Analysis complete."
  
  if (finding.evidence && finding.evidence.length > 0) {
    answer += "\n\nEvidence:\n"
    finding.evidence.forEach(e => {
      answer += `• ${e}\n`
    })
  }
  
  if (finding.recommendation) {
    answer += `\nRecommended Action: ${finding.recommendation}`
  }
  
  return answer
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
  
  if (!content || !Array.isArray(content)) return null
  
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

function ReasoningTrace({ result }) {
  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      className="overflow-hidden"
    >
      <div className="mt-4 p-4 bg-apple-bg rounded-xl font-mono text-xs text-apple-secondary space-y-2">
        <p>{"{"} "agent": "{result?.agent_id || 'analysis'}", "confidence": {(result?.confidence || 88) / 100} {"}"}</p>
        <p>{"{"} "data_sources": {JSON.stringify(result?.data_sources || ["Database"])} {"}"}</p>
        <p>{"{"} "site_id": "{result?.site_id || 'N/A'}" {"}"}</p>
        <p>{"{"} "phases_completed": {result?.phases?.length || 0} {"}"}</p>
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
