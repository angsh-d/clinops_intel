import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Activity, ArrowRight, Users, Database, Brain, Shield, X, Search, Lightbulb, Wrench, CheckCircle, Eye, GitMerge, Globe, TrendingUp } from 'lucide-react'
import { useStore } from '../lib/store'

const studies = [
  {
    id: 'M14-359',
    name: 'M14-359',
    title: 'Veliparib + Carboplatin/Paclitaxel in Advanced NSCLC',
    phase: 'Phase 3',
    status: 'active',
    enrolled: 427,
    target: 595,
    sites: 142,
    countries: 20,
    lastUpdated: '2h ago'
  },
  {
    id: 'M15-421',
    name: 'M15-421',
    title: 'Investigational Agent in Metastatic Breast Cancer',
    phase: 'Phase 2',
    status: 'upcoming',
    enrolled: 0,
    target: 280,
    sites: 45,
    countries: 3,
    lastUpdated: 'Starting Q2 2026'
  },
  {
    id: 'M16-088',
    name: 'M16-088',
    title: 'Combination Therapy in Advanced Melanoma',
    phase: 'Phase 1/2',
    status: 'upcoming',
    enrolled: 0,
    target: 120,
    sites: 25,
    countries: 2,
    lastUpdated: 'Starting Q3 2026'
  }
]

const PRPA_PHASES = [
  { icon: Eye, label: 'Perceive', description: 'Gather raw signals via SQL tools across operational tables' },
  { icon: Lightbulb, label: 'Reason', description: 'LLM generates hypotheses from the perceived data' },
  { icon: GitMerge, label: 'Plan', description: 'LLM dynamically selects which tools to invoke next' },
  { icon: Wrench, label: 'Act', description: 'Execute the planned tool invocations against the database' },
  { icon: CheckCircle, label: 'Reflect', description: 'LLM evaluates if the investigation goal is satisfied' },
]

const AGENTS = [
  // Operational foundation agents
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
  // Advanced analysis agents
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
  // External intelligence agent
  {
    id: 'clinical_trials_gov',
    name: 'Competitive Intelligence Agent',
    category: 'External',
    description: 'Searches ClinicalTrials.gov for real competing trials near sites with unexplained enrollment decline. Provides external market evidence that internal agents cannot access.',
    tools: ['competing_trial_search', 'site_summary', 'enrollment_velocity'],
    detects: ['Competing NSCLC trials at same facility', 'Geographic clustering of competitor recruitment', 'Temporal alignment of competitor start dates with enrollment drops', 'External market forces vs internal operational causes'],
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
  const { setView, setStudyData } = useStore()
  const [dataModelOpen, setDataModelOpen] = useState(false)
  const [agentsOpen, setAgentsOpen] = useState(false)

  const handleStudySelect = (study) => {
    if (study.status !== 'active') return

    setStudyData({
      studyId: study.id,
      studyName: study.name,
      studyTitle: study.title,
      enrolled: study.enrolled,
      target: study.target,
      criticalSites: 3,
      watchSites: 7,
      lastUpdated: new Date().toISOString()
    })
    setView('study')
  }

  const openAgents = () => setAgentsOpen(true)

  return (
    <div className="min-h-screen bg-apple-bg">
      <Header onDataModel={() => setDataModelOpen(true)} onAgents={openAgents} />
      <Hero onLearnMore={openAgents} />
      <StudySelector studies={studies} onSelect={handleStudySelect} />
      <Footer />
      <AnimatePresence>
        {dataModelOpen && <DataModelModal onClose={() => setDataModelOpen(false)} />}
      </AnimatePresence>
      <AnimatePresence>
        {agentsOpen && <AIAgentsModal onClose={() => setAgentsOpen(false)} />}
      </AnimatePresence>
    </div>
  )
}

function Header({ onDataModel, onAgents }) {
  return (
    <header className="sticky top-0 z-50 glass border-b border-apple-border">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#5856D6] to-[#AF52DE] flex items-center justify-center">
            <Activity className="w-4 h-4 text-white" />
          </div>
          <span className="text-section text-apple-text font-medium">Conductor</span>
        </div>
        <nav className="flex items-center gap-6">
          <a href="#studies" className="text-body text-apple-secondary hover:text-apple-text transition-colors">
            Studies
          </a>
          <button
            onClick={onAgents}
            className="text-body text-apple-secondary hover:text-apple-text transition-colors"
          >
            AI Agents
          </button>
          <button
            onClick={onDataModel}
            className="text-body text-apple-secondary hover:text-apple-text transition-colors"
          >
            Data Model
          </button>
        </nav>
      </div>
    </header>
  )
}

function Hero({ onLearnMore }) {
  return (
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
            detect data integrity risks, recommend site rescue or closure, and deliver actionable recommendations.
          </p>

          <div className="flex items-center justify-center gap-4">
            <a
              href="#studies"
              className="button-primary inline-flex items-center gap-2"
            >
              View Studies
              <ArrowRight className="w-4 h-4" />
            </a>
            <button
              onClick={onLearnMore}
              className="button-secondary inline-flex items-center gap-2"
            >
              Learn More
            </button>
          </div>
        </motion.div>
      </div>
    </section>
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
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-apple-border flex-shrink-0">
          <div>
            <h2 className="text-lg font-medium text-apple-text">Agentic Architecture</h2>
            <p className="text-caption text-apple-secondary mt-0.5">
              Investigation Orchestrator + 5 specialized agents + PRPA cognitive loop
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg hover:bg-apple-border/50 flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4 text-apple-secondary" />
          </button>
        </div>

        {/* Scrollable content */}
        <div className="overflow-y-auto px-6 py-5 space-y-6">
          {/* Orchestrator */}
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

          {/* Agents grouped by category */}
          {['Operational', 'Advanced', 'External'].map((category) => {
            const categoryAgents = AGENTS.filter(a => a.category === category)
            if (categoryAgents.length === 0) return null
            const categoryLabels = {
              Operational: 'Operational Agents',
              Advanced: 'Advanced Analysis Agents',
              External: 'External Intelligence',
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

          {/* PRPA Loop */}
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

function StudySelector({ studies, onSelect }) {
  return (
    <section id="studies" className="py-20 px-6">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl font-light text-apple-text mb-4">
            Your Studies
          </h2>
          <p className="text-body text-apple-secondary">
            Select a study to view its operational intelligence dashboard
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {studies.map((study, i) => (
            <motion.div
              key={study.id}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
            >
              <StudyCard study={study} onSelect={onSelect} />
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}

function StudyCard({ study, onSelect }) {
  const isActive = study.status === 'active'
  const progress = study.target > 0 ? (study.enrolled / study.target) * 100 : 0

  return (
    <button
      onClick={() => onSelect(study)}
      disabled={!isActive}
      className={`w-full h-full text-left card p-6 transition-all flex flex-col ${
        isActive
          ? 'hover:shadow-apple-lg hover:border-apple-text/20 cursor-pointer'
          : 'opacity-60 cursor-not-allowed'
      }`}
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-section text-apple-text font-medium">{study.name}</span>
            <span className={`px-2 py-0.5 rounded-full text-xs ${
              isActive
                ? 'bg-apple-success/10 text-apple-success'
                : 'bg-apple-border text-apple-secondary'
            }`}>
              {study.phase}
            </span>
          </div>
          <p className="text-caption text-apple-secondary line-clamp-2">{study.title}</p>
        </div>
        {isActive && (
          <ArrowRight className="w-5 h-5 text-apple-secondary flex-shrink-0" />
        )}
      </div>

      <div className="flex-1" />

      <div className="mb-4">
        <div className="flex justify-between text-caption mb-1">
          <span className="text-apple-secondary">Enrollment</span>
          <span className="font-mono text-apple-text">
            {isActive ? `${study.enrolled} / ${study.target}` : `0 / ${study.target}`}
          </span>
        </div>
        <div className="h-1.5 bg-apple-border rounded-full overflow-hidden">
          <div
            className="h-full bg-apple-text rounded-full"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      <div className="flex items-center gap-4 text-caption text-apple-secondary">
        <div className="flex items-center gap-1">
          <Users className="w-3.5 h-3.5" />
          <span>{study.sites} sites</span>
        </div>
        <span>·</span>
        <span>{study.countries} countries</span>
        <span>·</span>
        <span>{isActive ? `Updated ${study.lastUpdated}` : study.lastUpdated}</span>
      </div>
    </button>
  )
}

const DATA_MODEL = [
  {
    domain: 'Study Configuration',
    tables: [
      { name: 'study_config', description: 'Trial master record (phase, target enrollment, countries)', rows: '1', source: 'Sponsor (digital protocol / USDM)' },
      { name: 'study_arms', description: 'Randomization arms (ARM_A, ARM_B)', rows: '2', source: 'Sponsor (digital protocol / USDM)' },
      { name: 'stratification_factors', description: 'Stratification scheme (Gender, ECOG)', rows: '2', source: 'Sponsor (digital protocol / USDM)' },
      { name: 'visit_schedule', description: 'Planned visit windows and timing', rows: '10', source: 'Sponsor (digital protocol / USDM)' },
      { name: 'visit_activities', description: 'Activities required at each visit', rows: '80', source: 'Sponsor (digital protocol / USDM)' },
      { name: 'eligibility_criteria', description: 'Inclusion/exclusion rules', rows: '25', source: 'Sponsor (digital protocol / USDM)' },
      { name: 'screen_failure_reason_codes', description: 'Taxonomy of screening failure reasons', rows: '15', source: 'Sponsor (protocol-derived codelist)' },
      { name: 'sites', description: '142 trial sites across 20 countries', rows: '142', source: 'CRO upload (site status listing)' },
      { name: 'cra_assignments', description: 'CRA-to-site assignments with date ranges', rows: '172', source: 'CRO upload (CRA staffing roster)' },
    ]
  },
  {
    domain: 'Enrollment Funnel',
    tables: [
      { name: 'screening_log', description: 'Per-subject screening outcome (Passed/Failed/Withdrawn)', rows: '598', source: 'CRO upload (screening listing)' },
      { name: 'randomization_log', description: 'Subjects randomized to treatment arms', rows: '404', source: 'IRT vendor upload (randomization listing)' },
      { name: 'enrollment_velocity', description: 'Weekly screened/failed/randomized counts per site', rows: '9,173', source: 'CRO upload (weekly enrollment report)' },
      { name: 'randomization_events', description: 'Event-level randomization outcomes and delays', rows: '404', source: 'IRT vendor upload (event log extract)' },
      { name: 'depot_shipments', description: 'Drug shipments from depot to site', rows: '1,630', source: 'IRT vendor upload (shipment log)' },
    ]
  },
  {
    domain: 'EDC & Data Quality',
    tables: [
      { name: 'subject_visits', description: 'Planned vs actual visit dates per subject', rows: '3,165', source: 'CRO upload (visit completion listing)' },
      { name: 'ecrf_entries', description: 'eCRF page submissions with entry lag and completeness', rows: '18,553', source: 'CRO upload (eCRF entry status extract)' },
      { name: 'queries', description: 'Data queries \u2014 type, status, age, triggered_by', rows: '15,256', source: 'CRO upload (query management listing)' },
      { name: 'data_corrections', description: 'Field-level corrections linked to queries', rows: '3,245', source: 'CRO upload (data correction audit log)' },
    ]
  },
  {
    domain: 'Drug Supply',
    tables: [
      { name: 'drug_kit_types', description: 'Kit definitions (formulation, shelf life, storage)', rows: '4', source: 'IRT vendor upload (kit configuration)' },
      { name: 'depots', description: 'Regional distribution centers', rows: '8', source: 'IRT vendor upload (depot master)' },
      { name: 'kit_inventory', description: 'Biweekly site-level inventory snapshots', rows: '17,824', source: 'IRT vendor upload (inventory snapshot)' },
    ]
  },
  {
    domain: 'Monitoring & Risk',
    tables: [
      { name: 'monitoring_visits', description: 'CRA visit records (on-site/remote), findings', rows: '1,238', source: 'CRO upload (monitoring visit report)' },
      { name: 'overdue_actions', description: 'Follow-up actions from monitoring findings', rows: '294', source: 'CRO upload (monitoring action item tracker)' },
      { name: 'kri_snapshots', description: 'Monthly KRI values per site (10 metrics, Green/Amber/Red)', rows: '21,250', source: 'Derived (computed from operational data)' },
    ]
  },
]

function DataModelModal({ onClose }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] flex items-start justify-center pt-16 px-4 pb-8"
    >
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.97 }}
        transition={{ type: 'spring', damping: 30, stiffness: 400 }}
        className="relative w-full max-w-5xl max-h-[calc(100vh-8rem)] bg-apple-surface border border-apple-border rounded-2xl shadow-apple-lg overflow-hidden flex flex-col"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-apple-border flex-shrink-0">
          <div>
            <h2 className="text-lg font-medium text-apple-text">CODM Data Model</h2>
            <p className="text-caption text-apple-secondary mt-0.5">
              24 tables · ~93,500 rows · Joined via site_id and subject_id
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg hover:bg-apple-border/50 flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4 text-apple-secondary" />
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-4 space-y-6">
          {DATA_MODEL.map((group) => (
            <div key={group.domain}>
              <h3 className="text-sm font-medium text-apple-text mb-3">{group.domain}</h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-caption text-apple-secondary border-b border-apple-border">
                    <th className="pb-2 pr-4 font-medium w-[180px]">Table</th>
                    <th className="pb-2 pr-4 font-medium">Description</th>
                    <th className="pb-2 pr-4 font-medium w-[150px]">Source</th>
                    <th className="pb-2 font-medium text-right w-[70px]">Rows</th>
                  </tr>
                </thead>
                <tbody>
                  {group.tables.map((t) => (
                    <tr key={t.name} className="border-b border-apple-border/50">
                      <td className="py-2 pr-4 font-mono text-xs text-[#5856D6]">{t.name}</td>
                      <td className="py-2 pr-4 text-apple-secondary">{t.description}</td>
                      <td className="py-2 pr-4 text-xs text-apple-secondary">{t.source}</td>
                      <td className="py-2 text-right font-mono text-xs text-apple-text">{t.rows}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}

          <div className="pb-2">
            <h3 className="text-sm font-medium text-apple-text mb-2">Join Paths</h3>
            <p className="text-caption text-apple-secondary leading-relaxed">
              <span className="font-mono text-xs text-[#5856D6]">site_id</span> is the primary join key across all domains.
              Patient-level data links through <span className="font-mono text-xs text-[#5856D6]">subject_id</span> across
              {' '}screening_log &rarr; randomization_log &rarr; subject_visits &rarr; ecrf_entries &rarr; queries &rarr; data_corrections.
            </p>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

function Footer() {
  return (
    <footer className="py-8 px-6 border-t border-apple-border">
      <div className="max-w-6xl mx-auto flex items-center justify-between text-caption text-apple-secondary">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4" />
          <span>Conductor · Clinical Operations Intelligence</span>
        </div>
        <span>Powered by Agentic AI</span>
      </div>
    </footer>
  )
}
