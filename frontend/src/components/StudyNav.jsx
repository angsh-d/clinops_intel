import { useNavigate, useParams } from 'react-router-dom'
import { MapPin, Command } from 'lucide-react'
import { useStore } from '../lib/store'

const NAV_ITEMS = [
  { path: '', label: 'Brief' },
  { path: '/overview', label: 'Overview' },
  { path: '/sites', label: 'Sites' },
  { path: '/vendors', label: 'Vendors' },
  { path: '/financials', label: 'Financials' },
  { path: '/signals', label: 'Signals' },
  { path: '/directives', label: 'Directives' },
  { path: '/history', label: 'History' },
]

export function StudyNav({ active }) {
  const navigate = useNavigate()
  const { studyId: urlStudyId } = useParams()
  const { toggleCommand, studyData, currentStudyId } = useStore()
  const studyId = urlStudyId || currentStudyId
  const basePath = `/study/${studyId}`

  const enrolled = studyData.enrolled || 0
  const target = studyData.target || 0
  const progress = target > 0 ? Math.round((enrolled / target) * 100) : 0
  const totalSites = studyData.totalSites || studyData.total_sites || 0
  const countries = studyData.countries?.length || 0

  return (
    <header className="sticky top-0 z-50 glass border-b border-apple-border">
      <div className="px-5 py-3 flex items-center justify-between gap-4">
        {/* Left: Logo + Home */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <button onClick={() => navigate('/')} className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <img src="/saama_logo.svg" alt="Saama" className="h-6" />
            <div className="w-px h-5 bg-apple-border" />
            <span className="text-body font-medium text-apple-text">DSP</span>
          </button>
        </div>

        {/* Center: Study KPI strip */}
        <div className="flex items-center gap-5 text-caption">
          <span className="font-medium text-apple-text">{studyData.studyId || currentStudyId}</span>
          <span className="text-apple-secondary">{studyData.phase || ''}</span>
          <div className="flex items-center gap-2">
            <div className="w-24 h-1.5 bg-apple-border rounded-full overflow-hidden">
              <div className="h-full bg-apple-text rounded-full transition-all" style={{ width: `${progress}%` }} />
            </div>
            <span className="font-mono text-apple-text">{enrolled}/{target}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <MapPin className="w-3 h-3 text-apple-secondary" />
            <span className="text-apple-secondary">{totalSites} sites</span>
            <span className="text-apple-secondary/40 mx-0.5">/</span>
            <span className="text-apple-secondary">{countries} ctry</span>
          </div>
        </div>

        {/* Right: Nav */}
        <nav className="flex items-center gap-1 flex-shrink-0">
          {NAV_ITEMS.map((item) => {
            const isActive = active === item.label.toLowerCase()
            return (
              <button
                key={item.path}
                onClick={() => navigate(`${basePath}${item.path}`)}
                className={`px-3 py-1.5 text-caption rounded-lg transition-all ${
                  isActive
                    ? 'text-apple-text bg-apple-surface font-medium'
                    : 'text-apple-secondary hover:text-apple-text hover:bg-apple-surface'
                }`}
              >
                {item.label}
              </button>
            )
          })}
          <button
            onClick={toggleCommand}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-apple-surface border border-apple-border rounded-lg text-caption text-apple-secondary hover:text-apple-text hover:border-apple-text/20 transition-all ml-2"
          >
            <Command className="w-3 h-3" />
            <span>K</span>
          </button>
        </nav>
      </div>
    </header>
  )
}
