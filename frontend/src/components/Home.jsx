import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowRight, Users, Brain, X, Database, Shield, TrendingUp, Globe, DollarSign, BarChart3, Search, Eye, Lightbulb, GitMerge, Wrench, CheckCircle } from 'lucide-react'
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
    description: 'Investigates screening volume and velocity, screen failure rates and reason codes, randomization patterns, kit inventory stockouts, and regional enrollment disparities.',
    tools: ['screening_funnel', 'enrollment_velocity', 'screen_failure_pattern', 'regional_comparison', 'kit_inventory', 'kri_snapshot'],
    detects: ['Competing trial enrollment drop', 'Supply-chain disruption to randomization', 'Enrollment stall with excess kit expiry', 'Regional cluster effects'],
  },
  {
    id: 'phantom_compliance',
    name: 'Data Integrity Agent',
    category: 'Advanced',
    description: 'Detects suspiciously perfect data that may indicate fabrication or variance suppression. Cross-references entry lag variance, query aging, monitoring findings, and randomization timing patterns across sites.',
    tools: ['data_variance_analysis', 'timestamp_clustering', 'query_lifecycle_anomaly', 'monitoring_findings_variance', 'site_summary'],
    detects: ['Suppressed variance across multiple domains', 'Unnaturally uniform entry lag timing', 'Zero monitoring findings despite completed visits', 'Artificial query lifecycle uniformity'],
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
    tools: ['budget_variance_analysis', 'cost_per_patient_analysis', 'burn_rate_projection', 'change_order_impact', 'financial_impact_of_delays'],
    detects: ['Budget overruns by category or vendor', 'Cost-per-patient efficiency outliers', 'Burn rate trajectory exceeding budget', 'Change order scope creep patterns'],
  },
]

const ORCHESTRATOR = {
  name: 'Investigation Orchestrator',
  description: 'Semantic LLM-driven router that interprets natural-language queries, decides which agents to invoke, runs them in parallel with isolated database sessions, and synthesizes cross-domain findings into a unified investigation result.',
  steps: [
    { label: 'Route', description: 'LLM analyzes the query and selects which agents to invoke' },
    { label: 'Execute', description: 'Selected agents run in parallel, each with an isolated DB session' },
    { label: 'Synthesize', description: 'Cross-domain findings are merged into root causes and priority actions' },
  ],
}

export function Home() {
  const navigate = useNavigate()
  const { setStudyData, setCurrentStudyId } = useStore()
  const [agentsOpen, setAgentsOpen] = useState(false)
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

            <a
              href="#studies"
              className="button-primary inline-flex items-center gap-2"
            >
              Get Started
              <ArrowRight className="w-4 h-4" />
            </a>
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
              Investigation Orchestrator + 7 specialized agents + PRPA cognitive loop
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
            <div className="grid md:grid-cols-3 gap-4">
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
