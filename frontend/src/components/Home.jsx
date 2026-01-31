import { motion } from 'framer-motion'
import { Activity, ArrowRight, Users, Database, Brain, Shield } from 'lucide-react'
import { useStore } from '../lib/store'

const studies = [
  {
    id: 'M14-359',
    name: 'M14-359',
    title: 'Veliparib + Carboplatin/Paclitaxel in Advanced NSCLC',
    phase: 'Phase 3',
    status: 'active',
    enrolled: 420,
    target: 595,
    sites: 149,
    countries: 5,
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

const features = [
  {
    icon: Brain,
    title: 'Autonomous AI Agents',
    description: 'PRPA cognitive loop for deep operational investigation'
  },
  {
    icon: Activity,
    title: 'Real-time Signals',
    description: 'Continuous monitoring of enrollment, data quality, and compliance'
  },
  {
    icon: Database,
    title: 'Cross-domain Correlation',
    description: 'Unified view across EDC, CTMS, IRT, and safety systems'
  },
  {
    icon: Shield,
    title: 'Actionable Insights',
    description: 'Evidence-based recommendations with full reasoning traces'
  }
]

export function Home() {
  const { setView, setStudyData } = useStore()

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
    setView('pulse')
  }

  return (
    <div className="min-h-screen bg-apple-bg">
      <Header />
      <Hero />
      <Features />
      <StudySelector studies={studies} onSelect={handleStudySelect} />
      <Footer />
    </div>
  )
}

function Header() {
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
          <a href="#features" className="text-body text-apple-secondary hover:text-apple-text transition-colors">
            Features
          </a>
        </nav>
      </div>
    </header>
  )
}

function Hero() {
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
            detect data quality issues, and deliver actionable recommendations.
          </p>
          
          <div className="flex items-center justify-center gap-4">
            <a 
              href="#studies"
              className="button-primary inline-flex items-center gap-2"
            >
              View Studies
              <ArrowRight className="w-4 h-4" />
            </a>
            <a 
              href="#features"
              className="button-secondary inline-flex items-center gap-2"
            >
              Learn More
            </a>
          </div>
        </motion.div>
      </div>
    </section>
  )
}

function Features() {
  return (
    <section id="features" className="py-20 px-6 bg-apple-surface border-y border-apple-border">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl font-light text-apple-text mb-4">
            Powered by the PRPA Cognitive Loop
          </h2>
          <p className="text-body text-apple-secondary max-w-xl mx-auto">
            Perceive. Reason. Plan. Act. Reflect. — Autonomous investigation at scale.
          </p>
        </motion.div>
        
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature, i) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="card p-6"
            >
              <div className="w-10 h-10 rounded-xl bg-apple-bg flex items-center justify-center mb-4">
                <feature.icon className="w-5 h-5 text-apple-text" />
              </div>
              <h3 className="text-section text-apple-text mb-2">{feature.title}</h3>
              <p className="text-caption text-apple-secondary">{feature.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
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
      className={`w-full text-left card p-6 transition-all ${
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
      
      {isActive ? (
        <>
          <div className="mb-4">
            <div className="flex justify-between text-caption mb-1">
              <span className="text-apple-secondary">Enrollment</span>
              <span className="font-mono text-apple-text">{study.enrolled} / {study.target}</span>
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
            <span>Updated {study.lastUpdated}</span>
          </div>
        </>
      ) : (
        <div className="text-caption text-apple-secondary">
          {study.lastUpdated}
        </div>
      )}
    </button>
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
