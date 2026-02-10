import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowRight, Users, Brain, X, Database, Shield, TrendingUp, Globe, DollarSign, BarChart3, Search, Eye, Lightbulb, GitMerge, Wrench, CheckCircle, Layers, Zap, MessageSquare, FileText } from 'lucide-react'
import { useStore } from '../lib/store'
import { getStudySummary } from '../lib/api'

const PRPA_PHASES = [
  { icon: Eye, label: 'Perceive', description: 'Gather raw signals via SQL tools across operational tables' },
  { icon: Lightbulb, label: 'Reason', description: 'LLM generates hypotheses from the perceived data' },
  { icon: GitMerge, label: 'Plan', description: 'LLM dynamically selects which tools to invoke next' },
  { icon: Wrench, label: 'Act', description: 'Execute the planned tool invocations against the database' },
  { icon: CheckCircle, label: 'Reflect', description: 'LLM evaluates if the investigation goal is satisfied' },
]

const AGENTS = [
  {
    id: 'data_quality',
    name: 'Data Quality Agent',
    category: 'Operational',
    description: 'Investigates eCRF entry lags, query burden and aging, data correction patterns, CRA assignment impacts, and monitoring visit compliance across sites.',
    tools: ['entry_lag_analysis', 'query_burden', 'data_correction_analysis', 'cra_assignment_history', 'monitoring_visit_history', 'site_summary'],
    detects: ['CRA transition impact on data quality', 'Monitoring gap hidden debt', 'Query aging drift', 'Correction rate anomalies'],
  },
  {
    id: 'enrollment_funnel',
    name: 'Enrollment Funnel Agent',
    category: 'Operational',
    description: 'Investigates screening volume, screen failure rates, randomization velocity, consent withdrawals, and regional enrollment patterns. Detects competing trials, supply-chain-masked withdrawals, and funnel stage decomposition.',
    tools: ['screening_funnel', 'enrollment_velocity', 'screen_failure_pattern', 'regional_comparison', 'kit_inventory', 'kri_snapshot', 'site_summary'],
    detects: ['Competing trial enrollment drop', 'Supply-chain disruption to randomization', 'Enrollment stall with excess kit expiry', 'Regional cluster effects'],
  },
  {
    id: 'phantom_compliance',
    name: 'Data Integrity Agent',
    category: 'Advanced',
    description: 'Detects data integrity risks including fabrication, batch backfill, and oversight gaps. Analyzes variance suppression, CRA oversight gaps and rubber-stamp patterns, weekday entry clustering, correction provenance anomalies, narrative duplication, and cross-domain inconsistencies.',
    tools: ['data_variance_analysis', 'timestamp_clustering', 'query_lifecycle_anomaly', 'monitoring_findings_variance', 'weekday_entry_pattern', 'cra_oversight_gap', 'cra_portfolio_analysis', 'correction_provenance', 'entry_date_clustering', 'screening_narrative_duplication', 'cross_domain_consistency'],
    detects: ['Suppressed variance across multiple domains', 'Batch backfill and weekday entry clustering', 'CRA rubber-stamping and oversight gaps', 'Narrative duplication and copy-paste patterns', 'Cross-domain metric inconsistencies', 'Correction provenance anomalies'],
  },
  {
    id: 'site_rescue',
    name: 'Site Decision Agent',
    category: 'Advanced',
    description: 'Recommends rescue or closure for underperforming sites by synthesizing enrollment trajectory, screen failure root causes, CRA staffing stability, and supply constraints.',
    tools: ['enrollment_trajectory', 'screen_failure_root_cause', 'supply_constraint_impact', 'screening_funnel', 'cra_assignment_history', 'kit_inventory'],
    detects: ['Fixable vs structural screen failure causes', 'Supply-chain driven consent withdrawals', 'CRA transition recovery potential', 'Enrollment trajectory decline vs recovery signals'],
  },
  {
    id: 'clinical_trials_gov',
    name: 'Competitive Intelligence Agent',
    category: 'External',
    description: 'Searches ClinicalTrials.gov for real competing trials near sites with unexplained enrollment decline. Provides external market evidence that internal agents cannot access.',
    tools: ['competing_trial_search', 'site_summary', 'enrollment_velocity'],
    detects: ['Competing NSCLC trials at same facility', 'Geographic clustering of competitor recruitment', 'Temporal alignment of competitor start dates with enrollment drops', 'External market forces vs internal operational causes'],
  },
  {
    id: 'vendor_performance',
    name: 'Vendor Performance Agent',
    category: 'Operational',
    description: 'Investigates CRO/vendor performance — site activation timelines, query resolution speed, monitoring completion, contractual KPI adherence. Identifies vendor-attributable root causes for operational issues.',
    tools: ['vendor_kpi_analysis', 'vendor_site_comparison', 'vendor_milestone_tracker', 'vendor_issue_log', 'site_summary'],
    detects: ['CRO KPI degradation trends', 'Vendor-attributable monitoring gaps', 'Milestone delays by vendor', 'Issue pattern clustering by vendor'],
  },
  {
    id: 'financial_intelligence',
    name: 'Financial Intelligence Agent',
    category: 'Financial',
    description: 'Investigates budget health, cost efficiency, vendor spending patterns, and financial impact of operational delays. Provides risk-adjusted forecasting and budget reallocation recommendations.',
    tools: ['budget_variance_analysis', 'cost_per_patient_analysis', 'burn_rate_projection', 'change_order_impact', 'financial_impact_of_delays', 'site_summary'],
    detects: ['Budget overruns by category or vendor', 'Cost-per-patient efficiency outliers', 'Burn rate trajectory exceeding budget', 'Change order scope creep patterns'],
  },
  {
    id: 'mvr_analysis',
    name: 'MVR Analysis Agent',
    category: 'Advanced',
    description: 'Analyzes Monitoring Visit Report narratives to detect patterns invisible in structured data: cross-visit finding recurrence (zombie findings), CRA rubber-stamping, PI engagement deterioration, hidden systemic compliance risks, post-gap monitoring debt, and CRA transition quality gaps.',
    tools: ['mvr_narrative_search', 'mvr_cra_portfolio', 'mvr_recurrence_analysis', 'mvr_temporal_pattern', 'mvr_cross_site_comparison'],
    detects: ['Zombie findings recurring despite resolution', 'CRA rubber-stamping with zero findings across visits', 'PI engagement decline correlating with enrollment stall', 'Post-gap monitoring debt accumulation', 'CRA transition quality drops'],
  },
]

const ORCHESTRATOR = {
  name: 'Investigation Orchestrator',
  description: 'Semantic LLM-driven router that interprets natural-language queries, decides which agents to invoke, runs them in parallel with isolated database sessions, and synthesizes cross-domain findings into a unified investigation result.',
  steps: [
    { label: 'Route', description: 'LLM analyzes the query and selects which agents to invoke' },
    { label: 'Execute', description: 'Selected agents run in parallel, each with an isolated DB session' },
    { label: 'Re-route', description: 'Adaptive re-routing invokes additional agents based on cross-domain followups' },
    { label: 'Synthesize', description: 'Cross-domain findings are merged into root causes and priority actions' },
  ],
}

export function Home() {
  const navigate = useNavigate()
  const { setStudyData, setCurrentStudyId } = useStore()
  const [agentsOpen, setAgentsOpen] = useState(false)
  const [archOpen, setArchOpen] = useState(false)
  const [studies, setStudies] = useState([])
  const [loadingStudies, setLoadingStudies] = useState(true)

  useEffect(() => {
    async function fetchStudies() {
      try {
        const summary = await getStudySummary()
        if (summary) {
          setStudies([{
            id: summary.study_id,
            name: summary.study_name || summary.study_id,
            title: summary.study_title || summary.study_name || summary.study_id,
            phase: summary.phase,
            status: 'active',
            enrolled: summary.enrolled,
            target: summary.target,
            sites: summary.total_sites,
            countries: summary.countries?.length || 0,
            lastUpdated: summary.last_updated,
          }])
        }
      } catch (error) {
        console.error('Failed to fetch studies:', error)
      } finally {
        setLoadingStudies(false)
      }
    }
    fetchStudies()
  }, [])

  const handleStudySelect = (study) => {
    if (study.status !== 'active') return

    setStudyData({
      studyId: study.id,
      studyName: study.name,
      studyTitle: study.title,
      enrolled: study.enrolled,
      target: study.target,
      phase: study.phase,
      totalSites: study.sites,
      countries: Array(study.countries).fill(''),
      lastUpdated: new Date().toISOString()
    })
    setCurrentStudyId(study.id)
    navigate(`/study/${study.id}`)
  }

  return (
    <div className="min-h-screen bg-apple-bg">
      <header className="sticky top-0 z-50 glass border-b border-apple-border">
        <div className="px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/saama_logo.svg" alt="Saama" className="h-7" />
            <div className="w-px h-6 bg-apple-border" />
            <span className="text-section text-apple-text font-medium">Digital Study Platform</span>
          </div>
          <button
            onClick={() => setAgentsOpen(true)}
            className="text-body text-apple-secondary hover:text-apple-text transition-colors"
          >
            AI Agents
          </button>
        </div>
      </header>

      <section className="py-24 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-apple-surface border border-apple-border rounded-full mb-8">
              <span className="w-2 h-2 rounded-full bg-apple-success animate-pulse" />
              <span className="text-caption text-apple-secondary">Agentic AI Platform</span>
            </div>

            <h1 className="text-5xl md:text-6xl font-light text-apple-text tracking-tight mb-6 leading-tight">
              Clinical Operations
              <br />
              <span className="bg-gradient-to-r from-[#5856D6] to-[#AF52DE] bg-clip-text text-transparent">
                Intelligence
              </span>
            </h1>

            <p className="text-xl text-apple-secondary max-w-2xl mx-auto leading-relaxed mb-12">
              Autonomous AI agents that investigate operational signals, diagnose enrollment constraints,
              detect data integrity risks, and deliver actionable recommendations.
            </p>

            <div className="flex items-center justify-center gap-4">
              <a
                href="#studies"
                className="button-primary inline-flex items-center gap-2"
              >
                Get Started
                <ArrowRight className="w-4 h-4" />
              </a>
              <button
                onClick={() => setArchOpen(true)}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-apple-border bg-apple-surface text-sm font-medium text-apple-text hover:bg-apple-border/30 transition-colors"
              >
                <Layers className="w-4 h-4 text-[#5856D6]" />
                Platform Architecture
              </button>
            </div>
          </motion.div>
        </div>
      </section>

      <section id="studies" className="py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="text-center mb-10"
          >
            <h2 className="text-2xl font-light text-apple-text mb-2">Select a Study</h2>
            <p className="text-body text-apple-secondary">Choose a study to begin your investigation</p>
          </motion.div>

          {loadingStudies ? (
            <div className="flex items-center justify-center py-12">
              <div className="flex items-center gap-3 text-apple-secondary">
                <div className="w-5 h-5 border-2 border-apple-secondary/30 border-t-apple-secondary rounded-full animate-spin" />
                <span className="text-body">Loading studies...</span>
              </div>
            </div>
          ) : (
            <div className="grid gap-4">
              {studies.map((study, i) => (
                <motion.button
                  key={study.id}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1 }}
                  onClick={() => handleStudySelect(study)}
                  disabled={study.status !== 'active'}
                  className={`w-full text-left card p-6 transition-all flex items-center justify-between ${
                    study.status === 'active'
                      ? 'hover:shadow-apple-lg hover:border-apple-text/20 cursor-pointer'
                      : 'opacity-60 cursor-not-allowed'
                  }`}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-lg font-medium text-apple-text">{study.name}</span>
                      <span className="px-2 py-0.5 rounded-full text-xs bg-apple-success/10 text-apple-success">
                        {study.phase}
                      </span>
                    </div>
                    <p className="text-body text-apple-secondary mb-4">{study.title}</p>
                    <div className="flex items-center gap-6 text-caption text-apple-secondary">
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-1.5 bg-apple-border rounded-full overflow-hidden">
                          <div
                            className="h-full bg-apple-text rounded-full"
                            style={{ width: `${study.target > 0 ? (study.enrolled / study.target) * 100 : 0}%` }}
                          />
                        </div>
                        <span className="font-mono">{study.enrolled}/{study.target}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Users className="w-3.5 h-3.5" />
                        <span>{study.sites} sites</span>
                      </div>
                      <span>{study.countries} countries</span>
                    </div>
                  </div>
                  <ArrowRight className="w-5 h-5 text-apple-secondary flex-shrink-0" />
                </motion.button>
              ))}
            </div>
          )}
        </div>
      </section>

      <footer className="py-8 px-6 border-t border-apple-border">
        <div className="max-w-4xl mx-auto flex items-center justify-between text-caption text-apple-secondary">
          <span>Saama Technologies</span>
          <span>Clinical Operations Intelligence</span>
        </div>
      </footer>

      <AnimatePresence>
        {agentsOpen && <AIAgentsModal onClose={() => setAgentsOpen(false)} />}
        {archOpen && <PlatformArchitectureModal onClose={() => setArchOpen(false)} />}
      </AnimatePresence>
    </div>
  )
}

function AIAgentsModal({ onClose }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] flex items-start justify-center pt-12 px-4 pb-8"
    >
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.97 }}
        transition={{ type: 'spring', damping: 30, stiffness: 400 }}
        className="relative w-full max-w-5xl max-h-[calc(100vh-6rem)] bg-apple-surface border border-apple-border rounded-2xl shadow-apple-lg overflow-hidden flex flex-col"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-apple-border flex-shrink-0">
          <div>
            <h2 className="text-lg font-medium text-apple-text">Agentic Architecture</h2>
            <p className="text-caption text-apple-secondary mt-0.5">
              Investigation Orchestrator + 8 specialized agents + PRPA cognitive loop
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg hover:bg-apple-border/50 flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4 text-apple-secondary" />
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-5 space-y-6">
          <div className="border border-apple-border rounded-xl p-5">
            <div className="flex items-start gap-4 mb-5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#5856D6] to-[#AF52DE] flex items-center justify-center flex-shrink-0">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-sm font-medium text-apple-text">{ORCHESTRATOR.name}</h3>
                <p className="text-caption text-apple-secondary mt-1">{ORCHESTRATOR.description}</p>
              </div>
            </div>
            <div className="grid md:grid-cols-4 gap-4">
              {ORCHESTRATOR.steps.map((step, i) => (
                <div key={step.label} className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-apple-bg border border-apple-border flex items-center justify-center text-xs font-medium text-apple-text">{i + 1}</span>
                  <div>
                    <span className="text-sm font-medium text-apple-text">{step.label}</span>
                    <p className="text-caption text-apple-secondary mt-0.5">{step.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {['Operational', 'Advanced', 'External', 'Financial'].map((category) => {
            const categoryAgents = AGENTS.filter(a => a.category === category)
            if (categoryAgents.length === 0) return null
            const categoryLabels = {
              Operational: 'Operational Agents',
              Advanced: 'Advanced Analysis Agents',
              External: 'External Intelligence',
              Financial: 'Vendor & Financial Intelligence',
            }
            return (
              <div key={category}>
                <h3 className="text-xs font-medium text-apple-secondary uppercase tracking-wide mb-3">
                  {categoryLabels[category]}
                </h3>
                <div className="grid md:grid-cols-2 gap-5">
                  {categoryAgents.map((agent, i) => {
                    const AGENT_ICONS = {
                      data_quality: Database,
                      enrollment_funnel: Users,
                      phantom_compliance: Shield,
                      site_rescue: TrendingUp,
                      clinical_trials_gov: Globe,
                      vendor_performance: BarChart3,
                      financial_intelligence: DollarSign,
                      mvr_analysis: FileText,
                    }
                    const Icon = AGENT_ICONS[agent.id] || Database
                    const isOrphan = categoryAgents.length % 2 === 1 && i === categoryAgents.length - 1

                    return (
                      <div key={agent.id} className={`border border-apple-border rounded-xl p-5 ${isOrphan ? 'md:col-span-2' : ''}`}>
                        <div className="flex items-start gap-4 mb-4">
                          <div className="w-10 h-10 rounded-xl bg-apple-bg flex items-center justify-center flex-shrink-0">
                            <Icon className="w-5 h-5 text-apple-text" />
                          </div>
                          <div>
                            <h3 className="text-sm font-medium text-apple-text">{agent.name}</h3>
                            <p className="text-caption text-apple-secondary mt-1">{agent.description}</p>
                          </div>
                        </div>
                        <div className="mb-4">
                          <span className="text-xs font-medium text-apple-secondary uppercase tracking-wide">Tools</span>
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {agent.tools.map((t) => (
                              <span key={t} className="px-2 py-0.5 rounded-md bg-apple-bg border border-apple-border font-mono text-xs text-apple-secondary">{t}</span>
                            ))}
                          </div>
                        </div>
                        <div>
                          <span className="text-xs font-medium text-apple-secondary uppercase tracking-wide">Detectable Patterns</span>
                          <ul className="mt-2 space-y-1">
                            {agent.detects.map((d) => (
                              <li key={d} className="flex items-start gap-2 text-caption text-apple-secondary">
                                <Search className="w-3.5 h-3.5 text-apple-secondary flex-shrink-0 mt-0.5" />
                                {d}
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}

          <div>
            <h3 className="text-center text-xs font-medium text-apple-secondary uppercase tracking-wide mb-4">
              PRPA Cognitive Loop (max 3 iterations per investigation)
            </h3>
            <div className="flex flex-wrap justify-center gap-3">
              {PRPA_PHASES.map((phase, i) => (
                <div key={phase.label} className="flex items-center gap-3">
                  <div className="border border-apple-border rounded-lg px-4 py-3 flex items-center gap-3 min-w-0">
                    <phase.icon className="w-4 h-4 text-[#5856D6] flex-shrink-0" />
                    <div>
                      <span className="text-sm font-medium text-apple-text">{phase.label}</span>
                      <p className="text-xs text-apple-secondary mt-0.5 max-w-[180px]">{phase.description}</p>
                    </div>
                  </div>
                  {i < PRPA_PHASES.length - 1 && (
                    <ArrowRight className="w-4 h-4 text-apple-border flex-shrink-0 hidden md:block" />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

function ArchTier({ label, color, children, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="relative"
    >
      <div className={`border-l-[3px] ${color} bg-apple-bg/60 rounded-r-lg px-4 py-3`}>
        <div className="text-[10px] font-semibold uppercase tracking-widest text-apple-secondary mb-2">{label}</div>
        {children}
      </div>
    </motion.div>
  )
}

function ArchBox({ children, mono, accent }) {
  return (
    <span className={`inline-flex items-center px-2 py-1 rounded border text-[11px] leading-none ${
      accent
        ? 'border-[#5856D6]/30 bg-[#5856D6]/5 text-[#5856D6] font-medium'
        : mono
          ? 'border-apple-border bg-apple-surface text-apple-text/70 font-mono'
          : 'border-apple-border bg-apple-surface text-apple-secondary font-medium'
    }`}>
      {children}
    </span>
  )
}

function ArchConnector({ dashed }) {
  return (
    <div className="flex justify-center py-0.5">
      <div className={`w-px h-4 ${dashed ? 'border-l border-dashed border-apple-border' : 'bg-apple-border/60'}`} />
    </div>
  )
}

function PlatformArchitectureModal({ onClose }) {
  const [tab, setTab] = useState('logical')

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] flex items-start justify-center pt-6 px-4 pb-6"
    >
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.97 }}
        transition={{ type: 'spring', damping: 30, stiffness: 400 }}
        className="relative w-full max-w-5xl max-h-[calc(100vh-3rem)] bg-apple-surface border border-apple-border rounded-2xl shadow-apple-lg overflow-hidden flex flex-col"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-apple-border flex-shrink-0">
          <div>
            <h2 className="text-lg font-medium text-apple-text">Platform Architecture</h2>
            <div className="flex items-center gap-1 mt-2">
              {[
                { id: 'logical', label: 'Logical Architecture' },
                { id: 'overview', label: 'Architecture Overview' },
              ].map(t => (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all ${
                    tab === t.id
                      ? 'bg-apple-grey-800 text-white'
                      : 'text-apple-secondary hover:text-apple-text hover:bg-apple-grey-100'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg hover:bg-apple-border/50 flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4 text-apple-secondary" />
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-5">
        {tab === 'overview' ? <ArchitectureOverviewTab /> : (
          <>
          {/* System boundary */}
          <div className="border-2 border-apple-border/60 rounded-xl p-4 relative">
            <span className="absolute -top-2.5 left-4 px-2 bg-apple-surface text-[10px] font-semibold uppercase tracking-widest text-apple-secondary">
              System Boundary
            </span>

            <div className="grid grid-cols-[1fr_180px] gap-4">
              {/* ── Main stack (left column) ── */}
              <div className="space-y-0">
                {/* Presentation Tier */}
                <ArchTier label="Presentation Tier" color="border-blue-500" delay={0.03}>
                  <div className="flex items-center gap-2 mb-2">
                    <ArchBox>React 18</ArchBox>
                    <ArchBox>Vite</ArchBox>
                    <ArchBox>Tailwind CSS</ArchBox>
                    <ArchBox>Zustand</ArchBox>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    <ArchBox mono>Command Palette</ArchBox>
                    <ArchBox mono>Investigation Theater</ArchBox>
                    <ArchBox mono>Site Dossier</ArchBox>
                    <ArchBox mono>World Map</ArchBox>
                    <ArchBox mono>Morning Brief</ArchBox>
                    <ArchBox mono>Study 360</ArchBox>
                    <ArchBox mono>Signal Center</ArchBox>
                    <ArchBox mono>Financial Dashboard</ArchBox>
                    <ArchBox mono>Vendor Dashboard</ArchBox>
                  </div>
                </ArchTier>

                <ArchConnector />

                {/* API Tier */}
                <ArchTier label="API Gateway" color="border-emerald-500" delay={0.06}>
                  <div className="flex items-center gap-2 mb-2">
                    <ArchBox>FastAPI</ArchBox>
                    <ArchBox>REST</ArchBox>
                    <ArchBox>WebSocket</ArchBox>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    <ArchBox mono>agents</ArchBox>
                    <ArchBox mono>query</ArchBox>
                    <ArchBox mono>dashboard</ArchBox>
                    <ArchBox mono>alerts</ArchBox>
                    <ArchBox mono>feeds</ArchBox>
                    <ArchBox mono>proactive</ArchBox>
                    <ArchBox mono>ws</ArchBox>
                  </div>
                </ArchTier>

                <ArchConnector />

                {/* Conductor Tier */}
                <ArchTier label="Conductor / Orchestrator" color="border-[#5856D6]" delay={0.09}>
                  <div className="flex items-center gap-1.5 mb-2">
                    <ArchBox accent>Semantic Routing</ArchBox>
                    <ArchBox accent>Parallel Execution</ArchBox>
                    <ArchBox accent>Adaptive Re-routing</ArchBox>
                  </div>
                  <div className="flex items-center gap-2">
                    {['Route', 'Execute', 'Re-route', 'Synthesize'].map((step, i) => (
                      <div key={step} className="flex items-center gap-2">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-[#5856D6]/20 bg-[#5856D6]/5 text-xs font-medium text-[#5856D6]">
                          <span className="w-4 h-4 rounded-full bg-[#5856D6]/10 flex items-center justify-center text-[10px] font-bold">{i + 1}</span>
                          {step}
                        </span>
                        {i < 3 && <ArrowRight className="w-3 h-3 text-apple-border flex-shrink-0" />}
                      </div>
                    ))}
                  </div>
                </ArchTier>

                <ArchConnector />

                {/* Agent Tier */}
                <ArchTier label="Agent Layer — PRPA Cognitive Loop (max 3 iterations)" color="border-orange-500" delay={0.12}>
                  <div className="flex flex-wrap gap-1.5 mb-2.5">
                    {[
                      'Data Quality', 'Enrollment Funnel', 'Vendor Performance',
                      'Data Integrity', 'Site Decision', 'Competitive Intel', 'Financial Intel', 'MVR Analysis'
                    ].map((a) => (
                      <ArchBox key={a} mono>{a}</ArchBox>
                    ))}
                  </div>
                  <div className="flex items-center gap-1">
                    {['Perceive', 'Reason', 'Plan', 'Act', 'Reflect'].map((phase, i) => (
                      <div key={phase} className="flex items-center gap-1">
                        <span className="text-[10px] font-medium text-orange-600/80 bg-orange-500/5 border border-orange-500/15 rounded px-1.5 py-0.5">{phase}</span>
                        {i < 4 && <ArrowRight className="w-2.5 h-2.5 text-apple-border/50" />}
                      </div>
                    ))}
                  </div>
                </ArchTier>

                <ArchConnector />

                {/* Tool Tier — split into SQL tools and MCP */}
                <ArchTier label="Tool Registry — 39 tools, LLM-selected via describe()" color="border-rose-500" delay={0.15}>
                  <div className="grid grid-cols-[1fr_auto] gap-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1.5">
                        <ArchBox>Dynamic Selection</ArchBox>
                        <ArchBox>Self-describing</ArchBox>
                        <ArchBox>Cached Results</ArchBox>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        <ArchBox mono>35 SQL Tools</ArchBox>
                        <ArchBox mono>Vector Search</ArchBox>
                        <ArchBox mono>Trend Projection</ArchBox>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-px h-full border-l border-dashed border-apple-border" />
                      <div className="border border-amber-500/30 bg-amber-500/5 rounded-lg px-3 py-2 text-center">
                        <div className="text-[10px] font-semibold uppercase tracking-wider text-amber-600 mb-1">MCP</div>
                        <ArchBox mono>BioMCP</ArchBox>
                      </div>
                    </div>
                  </div>
                </ArchTier>

                <ArchConnector />

                {/* Data Tier */}
                <ArchTier label="Data Layer" color="border-slate-500" delay={0.18}>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="border border-apple-border rounded-lg px-3 py-2 bg-apple-surface/50">
                      <div className="text-[10px] font-semibold text-apple-secondary mb-1.5">PostgreSQL</div>
                      <div className="space-y-1">
                        <ArchBox mono>38 CODM Tables</ArchBox>
                        <ArchBox mono>10 Governance Tables</ArchBox>
                      </div>
                    </div>
                    <div className="border border-apple-border rounded-lg px-3 py-2 bg-apple-surface/50">
                      <div className="text-[10px] font-semibold text-apple-secondary mb-1.5">ChromaDB</div>
                      <div className="space-y-1">
                        <ArchBox mono>Vector Embeddings</ArchBox>
                        <ArchBox mono>Semantic Search</ArchBox>
                      </div>
                    </div>
                    <div className="border border-apple-border rounded-lg px-3 py-2 bg-apple-surface/50">
                      <div className="text-[10px] font-semibold text-apple-secondary mb-1.5">Cache</div>
                      <div className="space-y-1">
                        <ArchBox mono>L1 In-memory LRU</ArchBox>
                        <ArchBox mono>L2 PostgreSQL</ArchBox>
                      </div>
                    </div>
                  </div>
                </ArchTier>
              </div>

              {/* ── Side panel (right column) ── */}
              <div className="flex flex-col gap-3 pt-1">
                {/* LLM Engine — spans conductor through tools */}
                <motion.div
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 }}
                  className="border border-violet-500/30 bg-violet-500/[0.03] rounded-xl p-3 flex-1"
                >
                  <div className="flex items-center gap-1.5 mb-2">
                    <Zap className="w-3.5 h-3.5 text-violet-500" />
                    <span className="text-[10px] font-semibold uppercase tracking-widest text-violet-500">LLM Engine</span>
                  </div>
                  <div className="space-y-2">
                    <div className="border border-violet-500/15 rounded-md px-2.5 py-1.5 bg-violet-500/5">
                      <div className="text-[10px] font-medium text-violet-600">Primary</div>
                      <div className="text-[11px] font-mono text-apple-text/70">Gemini</div>
                    </div>
                    <div className="border border-violet-500/15 rounded-md px-2.5 py-1.5 bg-violet-500/5">
                      <div className="text-[10px] font-medium text-violet-600">Failover</div>
                      <div className="text-[11px] font-mono text-apple-text/70">Azure OpenAI</div>
                    </div>
                    <div className="border-t border-apple-border/40 pt-2 space-y-1">
                      <div className="text-[10px] text-apple-secondary">FailoverLLMClient</div>
                      <div className="text-[10px] text-apple-secondary">Structured JSON</div>
                      <div className="text-[10px] text-apple-secondary">Temp 0.0</div>
                      <div className="text-[10px] text-apple-secondary">Max Output Tokens</div>
                    </div>
                  </div>
                </motion.div>

                {/* Prompt Management */}
                <motion.div
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.25 }}
                  className="border border-apple-border rounded-xl p-3"
                >
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <MessageSquare className="w-3.5 h-3.5 text-apple-secondary" />
                    <span className="text-[10px] font-semibold uppercase tracking-widest text-apple-secondary">Prompts</span>
                  </div>
                  <div className="text-[10px] text-apple-secondary">
                    External .txt files with runtime {'{'}<span className="font-mono">var</span>{'}'} substitution
                  </div>
                </motion.div>

                {/* Cross-cutting */}
                <motion.div
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.28 }}
                  className="border border-apple-border rounded-xl p-3 space-y-1.5"
                >
                  <div className="flex items-center gap-1.5">
                    <Shield className="w-3.5 h-3.5 text-apple-secondary" />
                    <span className="text-[10px] font-semibold uppercase tracking-widest text-apple-secondary">Cross-cutting</span>
                  </div>
                  <div className="text-[10px] text-apple-secondary">Session Isolation</div>
                  <div className="text-[10px] text-apple-secondary">WebSocket Streaming</div>
                  <div className="text-[10px] text-apple-secondary">Keepalive Protocol</div>
                </motion.div>
              </div>
            </div>
          </div>

          {/* External system — ClinicalTrials.gov */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mt-3 flex items-center justify-center gap-3"
          >
            <div className="flex-1 border-t border-dashed border-apple-border" />
            <div className="flex items-center gap-3">
              <span className="text-[10px] text-apple-secondary uppercase tracking-wider">via BioMCP</span>
              <ArrowRight className="w-3.5 h-3.5 text-amber-500" />
              <div className="border-2 border-dashed border-amber-500/30 bg-amber-500/[0.03] rounded-xl px-4 py-2.5 flex items-center gap-2.5">
                <Globe className="w-4 h-4 text-amber-600" />
                <div>
                  <div className="text-xs font-medium text-apple-text">ClinicalTrials.gov</div>
                  <div className="text-[10px] text-apple-secondary">External API</div>
                </div>
              </div>
            </div>
            <div className="flex-1 border-t border-dashed border-apple-border" />
          </motion.div>
        </>
        )}
        </div>
      </motion.div>
    </motion.div>
  )
}

function ArchOverviewBox({ children, className = '' }) {
  return (
    <div className={`border border-apple-border rounded-lg px-3 py-2.5 bg-apple-surface/60 ${className}`}>
      {children}
    </div>
  )
}

function ArchOverviewArrow({ label, className = '' }) {
  return (
    <div className={`flex flex-col items-center gap-0.5 ${className}`}>
      <div className="w-px h-4 bg-apple-border/60" />
      {label && <span className="text-[9px] text-apple-tertiary">{label}</span>}
      <div className="w-0 h-0 border-l-[3px] border-r-[3px] border-t-[4px] border-l-transparent border-r-transparent border-t-apple-border/60" />
    </div>
  )
}

function ArchitectureOverviewTab() {
  return (
    <div className="space-y-3">
      {/* Dual-path entry points */}
      <div className="grid grid-cols-2 gap-6">
        {/* Left: Proactive */}
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.03 }}>
          <div className="border-2 border-emerald-500/30 rounded-xl p-4 bg-emerald-500/[0.02]">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-emerald-600 mb-2">Proactive Mode</div>
            <p className="text-[11px] text-apple-secondary leading-relaxed">
              Source Systems (EDC, IRT, CTMS, Vendors, Finance, Digital Protocol)
            </p>
          </div>
        </motion.div>

        {/* Right: Reactive */}
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.06 }}>
          <div className="border-2 border-[#5856D6]/30 rounded-xl p-4 bg-[#5856D6]/[0.02]">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-[#5856D6] mb-2">Reactive Mode</div>
            <p className="text-[11px] text-apple-secondary leading-relaxed">
              Natural Language Query from the Command Center
            </p>
          </div>
        </motion.div>
      </div>

      {/* Arrows down */}
      <div className="grid grid-cols-2 gap-6">
        <ArchOverviewArrow />
        <ArchOverviewArrow />
      </div>

      {/* Processing layers */}
      <div className="grid grid-cols-2 gap-6">
        {/* Left: Data Ingestion + Proactive Scan Engine */}
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.09 }} className="space-y-2">
          <ArchOverviewBox>
            <div className="text-[10px] font-semibold uppercase tracking-widest text-apple-secondary mb-1.5">Data Ingestion Layer</div>
            <div className="text-[11px] text-apple-secondary">Normalize vendor feeds → CODM</div>
          </ArchOverviewBox>

          <ArchOverviewArrow />

          <div className="border border-emerald-500/20 rounded-xl p-4 bg-emerald-500/[0.02]">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-emerald-600 mb-3">Proactive Scan Engine</div>
            <div className="space-y-2">
              {[
                { n: '1', label: 'Select Directives', desc: 'User-curated prompt catalog, per agent' },
                { n: '2', label: 'Execute PRPA Loops', desc: 'All agents, isolated DB sessions' },
                { n: '3', label: 'Persist Findings', desc: 'agent_findings + alert_log' },
                { n: '4', label: 'Assemble Briefs', desc: 'LLM cross-agent synthesis' },
              ].map(step => (
                <div key={step.n} className="flex items-start gap-2.5">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-[10px] font-bold text-emerald-600">{step.n}</span>
                  <div>
                    <span className="text-[11px] font-medium text-apple-text">{step.label}</span>
                    <p className="text-[10px] text-apple-tertiary">{step.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Right: Orchestrator Agent */}
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 }} className="space-y-2">
          <div className="border border-[#5856D6]/20 rounded-xl p-4 bg-[#5856D6]/[0.02]">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-[#5856D6] mb-3">Orchestrator Agent</div>
            <div className="text-[11px] text-apple-secondary mb-3">LLM semantic routing — zero keyword matching</div>
            <div className="flex items-center gap-1.5 flex-wrap">
              {['Route', 'Execute', 'Re-route', 'Synthesize'].map((step, i) => (
                <div key={step} className="flex items-center gap-1.5">
                  <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md border border-[#5856D6]/20 bg-[#5856D6]/5 text-[10px] font-medium text-[#5856D6]">
                    <span className="w-3.5 h-3.5 rounded-full bg-[#5856D6]/10 flex items-center justify-center text-[9px] font-bold">{i + 1}</span>
                    {step}
                  </span>
                  {i < 3 && <ArrowRight className="w-2.5 h-2.5 text-apple-border flex-shrink-0" />}
                </div>
              ))}
            </div>
          </div>

          <ArchOverviewArrow />

          {/* Parallel agents */}
          <div className="grid grid-cols-3 gap-2">
            {['Agent A', 'Agent B', 'Agent C'].map(a => (
              <ArchOverviewBox key={a} className="text-center">
                <div className="text-[11px] font-medium text-apple-text">{a}</div>
                <div className="text-[9px] text-apple-tertiary mt-0.5">PRPA loop</div>
                <div className="text-[9px] text-apple-tertiary">isolated DB</div>
              </ArchOverviewBox>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Converge arrows */}
      <div className="grid grid-cols-2 gap-6">
        <ArchOverviewArrow />
        <ArchOverviewArrow />
      </div>

      {/* Shared infrastructure — spans full width */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
        <div className="border-2 border-orange-500/20 rounded-xl p-4 bg-orange-500/[0.02]">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-orange-600 mb-3">Shared Agent & Tool Infrastructure</div>
          <div className="grid grid-cols-3 gap-3">
            <ArchOverviewBox>
              <div className="text-[10px] font-semibold text-apple-secondary mb-1.5">Agent Layer</div>
              <div className="flex flex-wrap gap-1">
                {['Data Quality', 'Enrollment', 'Vendor', 'Integrity', 'Site Rescue', 'Competitive', 'Financial', 'MVR Analysis'].map(a => (
                  <span key={a} className="px-1.5 py-0.5 rounded border border-apple-border bg-apple-surface text-[9px] font-mono text-apple-secondary">{a}</span>
                ))}
              </div>
              <div className="flex items-center gap-1 mt-2">
                {['P', 'R', 'Pl', 'A', 'Rf'].map((p, i) => (
                  <div key={p} className="flex items-center gap-0.5">
                    <span className="text-[9px] font-medium text-orange-600/80 bg-orange-500/5 border border-orange-500/15 rounded px-1 py-0.5">{p}</span>
                    {i < 4 && <span className="text-[8px] text-apple-border">→</span>}
                  </div>
                ))}
              </div>
            </ArchOverviewBox>

            <ArchOverviewBox>
              <div className="text-[10px] font-semibold text-apple-secondary mb-1.5">Tool Registry</div>
              <div className="text-[10px] text-apple-tertiary mb-1">39 tools, LLM-selected via describe()</div>
              <div className="flex flex-wrap gap-1">
                <span className="px-1.5 py-0.5 rounded border border-apple-border bg-apple-surface text-[9px] font-mono text-apple-secondary">35 SQL</span>
                <span className="px-1.5 py-0.5 rounded border border-apple-border bg-apple-surface text-[9px] font-mono text-apple-secondary">Vector</span>
                <span className="px-1.5 py-0.5 rounded border border-amber-500/30 bg-amber-500/5 text-[9px] font-mono text-amber-600">BioMCP</span>
              </div>
            </ArchOverviewBox>

            <ArchOverviewBox>
              <div className="text-[10px] font-semibold text-apple-secondary mb-1.5">CODM Database</div>
              <div className="text-[10px] text-apple-tertiary mb-1">PostgreSQL</div>
              <div className="flex flex-wrap gap-1">
                <span className="px-1.5 py-0.5 rounded border border-apple-border bg-apple-surface text-[9px] font-mono text-apple-secondary">38 CODM</span>
                <span className="px-1.5 py-0.5 rounded border border-apple-border bg-apple-surface text-[9px] font-mono text-apple-secondary">10 Gov</span>
              </div>
            </ArchOverviewBox>
          </div>
        </div>
      </motion.div>

      {/* Cross-Domain Synthesis */}
      <ArchOverviewArrow />

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18 }}>
        <ArchOverviewBox className="text-center">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-apple-secondary mb-1">Cross-Domain Synthesis</div>
          <div className="text-[11px] text-apple-tertiary">LLM merges findings across agents into unified analysis</div>
        </ArchOverviewBox>
      </motion.div>

      {/* Arrows to outputs */}
      <div className="grid grid-cols-2 gap-6">
        <ArchOverviewArrow />
        <ArchOverviewArrow />
      </div>

      {/* Dual outputs */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.21 }} className="grid grid-cols-2 gap-6">
        <div className="border-2 border-emerald-500/20 rounded-xl p-4 bg-emerald-500/[0.02]">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-emerald-600 mb-2">Proactive Output</div>
          <div className="text-[11px] font-medium text-apple-text mb-1.5">Site Intelligence Briefs</div>
          <ul className="space-y-1">
            {['Risk Summary', 'Cross-Domain Correlations', 'Vendor Accountability', 'Recommended Actions', 'Trend Indicators'].map(item => (
              <li key={item} className="flex items-center gap-1.5">
                <div className="w-1 h-1 rounded-full bg-emerald-500" />
                <span className="text-[10px] text-apple-secondary">{item}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="border-2 border-[#5856D6]/20 rounded-xl p-4 bg-[#5856D6]/[0.02]">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-[#5856D6] mb-2">Reactive Output</div>
          <div className="text-[11px] font-medium text-apple-text mb-1.5">Structured Response</div>
          <ul className="space-y-1">
            {['Executive Summary', 'Root Cause Hypotheses', 'Causal Chains', 'Priority Actions', 'Reasoning Trace'].map(item => (
              <li key={item} className="flex items-center gap-1.5">
                <div className="w-1 h-1 rounded-full bg-[#5856D6]" />
                <span className="text-[10px] text-apple-secondary">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </motion.div>

      {/* WebSocket streaming note */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.25 }}
        className="flex items-center justify-center gap-3 pt-1"
      >
        <div className="flex-1 border-t border-dashed border-apple-border" />
        <div className="flex items-center gap-2 px-3 py-1.5 border border-apple-border rounded-lg bg-apple-surface/50">
          <Zap className="w-3 h-3 text-apple-secondary" />
          <span className="text-[10px] text-apple-secondary">WebSocket streaming — real-time phase updates to frontend during reactive investigations</span>
        </div>
        <div className="flex-1 border-t border-dashed border-apple-border" />
      </motion.div>
    </div>
  )
}
