import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Activity, ArrowRight, AlertTriangle, AlertCircle, MapPin, Command } from 'lucide-react'
import { useStore } from '../lib/store'
import { getSitesOverview } from '../lib/api'
import { WorldMap } from './WorldMap'

const INTELLIGENCE_SIGNALS = [
  {
    id: 'chain-4',
    severity: 'warning',
    chain: 'Chain 4',
    siteName: 'Aichi Cancer Center Hospital',
    country: 'Japan',
    title: 'High Screen Failures Despite Clean Data',
    description: 'Screen failure rate is 3.5x study average while data quality scores rank in the top 5% across all eCRF domains.',
    query: 'Why does Aichi Cancer Center Hospital have high screen failures but excellent data?',
  },
  {
    id: 'chain-3',
    severity: 'critical',
    chain: 'Chain 3',
    siteName: 'California Cancer Associates for Research and Excellence',
    country: 'USA',
    title: 'Hidden Data Quality Debt After Monitoring Gap',
    description: '5-month monitoring gap left 75 open queries averaging 120+ days unresolved. Open Query Age KRI has been Red since April 2025.',
    query: 'Analyze query backlog trends at California Cancer Associates',
  },
  {
    id: 'chain-6',
    severity: 'critical',
    chain: 'Chain 6',
    siteName: 'Highlands Oncology Group',
    country: 'USA',
    title: 'Enrollment Velocity Declining',
    description: 'Screening volume dropped over 90% after week 35 with no corresponding data quality or compliance flags.',
    query: 'Why has enrollment declined at Highlands Oncology Group?',
  },
  {
    id: 'chain-2',
    severity: 'critical',
    chain: 'Chain 2',
    siteName: 'Canterbury District Health Board',
    country: 'New Zealand',
    title: 'Repeated Kit Stockouts Disrupting Randomization',
    description: 'Two complete kit stockouts (Mar and Jun 2025) drove all inventory to zero, with a randomization delay event during the supply gap.',
    query: 'Why is Canterbury District Health Board experiencing supply disruptions and randomization delays?',
  },
  {
    id: 'chain-7',
    severity: 'warning',
    chain: 'Chain 7',
    siteName: 'CRU Hungary Egeszsegugyi Kft.',
    country: 'Hungary',
    title: 'Suspiciously Perfect Metrics',
    description: 'Zero open queries, 99.5% completeness, 1-day entry lag with near-zero variance across all KRIs.',
    query: 'Is CRU Hungary\'s perfect data quality genuine or is the data too good to be true?',
  },
  {
    id: 'chain-9',
    severity: 'critical',
    chain: 'Chain 9',
    siteName: 'Highlands Oncology Group',
    country: 'USA',
    title: 'Site Viability Decision Needed',
    description: 'Enrollment stalled after week 35 with competing trials nearby. Rescue investment vs closure decision required.',
    query: 'Should we rescue or close Highlands Oncology Group?',
  },
]

const HIGHLIGHTED_SITE_NAMES = new Set(
  INTELLIGENCE_SIGNALS.map(s => s.siteName)
)

export function StudyDashboard() {
  const { setView, studyData, setInvestigation, setSelectedSite, setSites, setSiteNameMap, toggleCommand } = useStore()
  const [sites, setSitesLocal] = useState([])
  const [hoveredSite, setHoveredSite] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchSites() {
      try {
        const data = await getSitesOverview()
        if (data?.sites) {
          setSitesLocal(data.sites)
          setSites(data.sites)
          const nameMap = {}
          for (const s of data.sites) {
            if (s.site_name) nameMap[s.site_id] = s.site_name
          }
          setSiteNameMap(nameMap)
        }
      } catch (error) {
        console.error('Failed to fetch sites:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchSites()
  }, [])

  const handleScenarioClick = (scenario) => {
    setInvestigation({ question: scenario.query, status: 'routing' })
  }

  const handleSiteClick = (site) => {
    setSelectedSite(site)
  }

  const mapSites = sites.map(s => ({
    id: s.site_id,
    name: s.site_name,
    country: s.country,
    status: s.status || 'healthy',
    enrollmentPercent: s.enrollment_percent || 0,
  }))

  return (
    <div className="min-h-screen bg-apple-bg">
      <Header setView={setView} toggleCommand={toggleCommand} />
      <StudyContextBar study={studyData} />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-10">
        <MapSection
          sites={mapSites}
          hoveredSite={hoveredSite}
          onSiteHover={setHoveredSite}
          onSiteClick={handleSiteClick}
          loading={loading}
          siteCount={sites.length}
          countryCount={studyData.countries || 20}
          highlightedSiteNames={HIGHLIGHTED_SITE_NAMES}
        />

        <IntelligenceSignals
          signals={INTELLIGENCE_SIGNALS}
          onClick={handleScenarioClick}
        />
      </main>
    </div>
  )
}

function Header({ setView, toggleCommand }) {
  return (
    <header className="sticky top-0 z-50 glass border-b border-apple-border">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => setView('home')} className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#5856D6] to-[#AF52DE] flex items-center justify-center">
              <Activity className="w-4 h-4 text-white" />
            </div>
            <span className="text-section text-apple-text font-medium">Conductor</span>
          </button>
        </div>
        <nav className="flex items-center gap-6">
          <button
            onClick={() => setView('pulse')}
            className="text-body text-apple-secondary hover:text-apple-text transition-colors"
          >
            Pulse
          </button>
          <button
            onClick={() => setView('constellation')}
            className="text-body text-apple-secondary hover:text-apple-text transition-colors"
          >
            Sites
          </button>
          <button
            onClick={toggleCommand}
            className="inline-flex items-center gap-2 px-3 py-1.5 bg-apple-surface border border-apple-border rounded-lg text-body text-apple-secondary hover:text-apple-text hover:border-apple-text/20 transition-all"
          >
            <Command className="w-3.5 h-3.5" />
            <span>Ask Conductor</span>
            <kbd className="ml-1 px-1.5 py-0.5 bg-apple-bg rounded text-xs font-mono">K</kbd>
          </button>
        </nav>
      </div>
    </header>
  )
}

function StudyContextBar({ study }) {
  const enrolled = study.enrolled || 0
  const target = study.target || 0
  const progress = target > 0 ? Math.round((enrolled / target) * 100) : 0
  const sites = study.sites || 142
  const countries = study.countries || 20

  return (
    <div className="bg-apple-surface border-b border-apple-border">
      <div className="max-w-7xl mx-auto px-6 py-2.5 flex items-center gap-6 text-caption">
        <span className="font-medium text-apple-text">{study.studyId || study.id}</span>
        <span className="text-apple-secondary">{study.phase || 'Phase 3'}</span>
        <div className="flex items-center gap-2">
          <span className="text-apple-secondary">Enrolled</span>
          <span className="font-mono text-apple-text">{enrolled}/{target}</span>
          <div className="w-16 h-1.5 bg-apple-border rounded-full overflow-hidden">
            <div className="h-full bg-apple-text rounded-full" style={{ width: `${progress}%` }} />
          </div>
          <span className="font-mono text-apple-secondary">{progress}%</span>
        </div>
        <div className="flex items-center gap-1.5">
          <MapPin className="w-3.5 h-3.5 text-apple-secondary" />
          <span className="text-apple-secondary">{sites} sites</span>
          <span className="text-apple-secondary/50 mx-1">/</span>
          <span className="text-apple-secondary">{countries} countries</span>
        </div>
      </div>
    </div>
  )
}

function MapSection({ sites, hoveredSite, onSiteHover, onSiteClick, loading, siteCount, countryCount, highlightedSiteNames }) {
  return (
    <section>
      <div className="flex items-baseline justify-between mb-4">
        <h2 className="text-xl font-light text-apple-text">Global Site Network</h2>
        <span className="text-caption text-apple-secondary">
          {siteCount} sites across {countryCount} countries
        </span>
      </div>
      {loading ? (
        <div className="h-[300px] md:h-[400px] lg:h-[500px] bg-apple-surface rounded-xl border border-apple-border flex items-center justify-center">
          <div className="flex items-center gap-3 text-apple-secondary">
            <div className="w-5 h-5 border-2 border-apple-secondary/30 border-t-apple-secondary rounded-full animate-spin" />
            <span className="text-body">Loading site network...</span>
          </div>
        </div>
      ) : (
        <WorldMap
          sites={sites}
          onSiteClick={onSiteClick}
          onSiteHover={onSiteHover}
          hoveredSite={hoveredSite}
          height="h-[300px] md:h-[400px] lg:h-[500px]"
          highlightedSiteNames={highlightedSiteNames}
        />
      )}
    </section>
  )
}

function IntelligenceSignals({ signals, onClick }) {
  return (
    <section>
      <div className="flex items-baseline justify-between mb-4">
        <h2 className="text-xl font-light text-apple-text">Top Intelligence Signals</h2>
        <span className="text-caption text-apple-secondary">{signals.length} active signals</span>
      </div>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
        {signals.map((signal, i) => (
          <motion.div
            key={signal.id}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="h-full"
          >
            <SignalCard signal={signal} onClick={() => onClick(signal)} />
          </motion.div>
        ))}
      </div>
    </section>
  )
}

function SignalCard({ signal, onClick }) {
  const isCritical = signal.severity === 'critical'

  return (
    <button
      onClick={onClick}
      className="w-full h-full text-left card p-5 flex flex-col gap-3 hover:shadow-apple-lg hover:border-apple-text/20 transition-all group"
    >
      <div className="flex items-center justify-between">
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${
          isCritical
            ? 'bg-apple-critical/10 text-apple-critical'
            : 'bg-apple-warning/10 text-apple-warning'
        }`}>
          {isCritical ? <AlertCircle className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
          {signal.severity}
        </span>
        <span className="text-caption text-apple-secondary">{signal.chain}</span>
      </div>

      <div>
        <p className="text-caption text-apple-secondary">{signal.siteName}, {signal.country}</p>
        <h3 className="text-section text-apple-text font-medium mt-0.5">{signal.title}</h3>
      </div>

      <p className="text-caption text-apple-secondary leading-relaxed flex-1">{signal.description}</p>

      <div className="flex items-center gap-1.5 text-body text-apple-accent group-hover:gap-2.5 transition-all">
        <span>Investigate</span>
        <ArrowRight className="w-4 h-4" />
      </div>
    </button>
  )
}
