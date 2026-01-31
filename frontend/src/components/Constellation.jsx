import { useState } from 'react'
import { motion } from 'framer-motion'
import { ArrowLeft, Search, Globe, BarChart3 } from 'lucide-react'
import { useStore } from '../lib/store'
import { WorldMap } from './WorldMap'

const mockSites = Array.from({ length: 50 }, (_, i) => ({
  id: `SITE-${String(i + 1).padStart(3, '0')}`,
  enrollmentPercent: Math.random() * 100,
  dataQualityScore: Math.random() * 100,
  alertCount: Math.floor(Math.random() * 5),
  status: Math.random() > 0.9 ? 'critical' : Math.random() > 0.7 ? 'warning' : 'healthy',
  country: ['USA', 'UK', 'Japan', 'Germany', 'France', 'Canada'][Math.floor(Math.random() * 6)],
  finding: 'Entry lag improving, query backlog elevated'
}))

export function Constellation() {
  const { setView, setSelectedSite, toggleCommand } = useStore()
  const [hoveredSite, setHoveredSite] = useState(null)
  const [activeTab, setActiveTab] = useState('map')
  
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen bg-apple-bg"
    >
      <Header onBack={() => setView('pulse')} onSearch={toggleCommand} />
      
      <div className="px-8 pt-4 pb-8">
        <SummaryBar />
        
        <div className="mt-8 card p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-section text-apple-text">
              {activeTab === 'map' ? 'Global Site Map' : 'Site Constellation'}
            </h2>
            <div className="flex items-center gap-4">
              <ViewToggle activeTab={activeTab} onTabChange={setActiveTab} />
              <div className="flex gap-2">
                <LegendDot color="bg-apple-text" label="Healthy" />
                <LegendDot color="bg-apple-warning" label="Warning" />
                <LegendDot color="bg-apple-critical" label="Critical" />
              </div>
            </div>
          </div>
          
          {activeTab === 'map' ? (
            <WorldMap 
              sites={mockSites}
              onSiteClick={setSelectedSite}
              onSiteHover={setHoveredSite}
              hoveredSite={hoveredSite}
            />
          ) : (
            <div className="relative h-[500px] bg-apple-bg rounded-xl overflow-hidden border border-apple-border">
              <AxisLabels />
              
              <div className="absolute inset-0 p-8">
                {mockSites.map((site) => (
                  <SiteDot
                    key={site.id}
                    site={site}
                    onHover={setHoveredSite}
                    onClick={() => setSelectedSite(site)}
                    isHovered={hoveredSite?.id === site.id}
                  />
                ))}
              </div>
              
              {hoveredSite && <SiteTooltip site={hoveredSite} />}
            </div>
          )}
        </div>
        
        <SiteTable sites={mockSites} onSelect={setSelectedSite} />
      </div>
    </motion.div>
  )
}

function ViewToggle({ activeTab, onTabChange }) {
  return (
    <div className="flex bg-apple-bg rounded-lg p-1 border border-apple-border">
      <button
        onClick={() => onTabChange('map')}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-caption transition-colors ${
          activeTab === 'map' 
            ? 'bg-apple-surface text-apple-text shadow-sm' 
            : 'text-apple-secondary hover:text-apple-text'
        }`}
      >
        <Globe className="w-4 h-4" />
        <span>Map</span>
      </button>
      <button
        onClick={() => onTabChange('scatter')}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-caption transition-colors ${
          activeTab === 'scatter' 
            ? 'bg-apple-surface text-apple-text shadow-sm' 
            : 'text-apple-secondary hover:text-apple-text'
        }`}
      >
        <BarChart3 className="w-4 h-4" />
        <span>Scatter</span>
      </button>
    </div>
  )
}

function Header({ onBack, onSearch }) {
  return (
    <header className="sticky top-0 z-40 glass border-b border-apple-border">
      <div className="px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 -ml-2 hover:bg-apple-bg rounded-full transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-apple-secondary" />
          </button>
          <div>
            <h1 className="text-section text-apple-text">M14-359</h1>
            <p className="text-caption text-apple-secondary">149 active sites · Updated 2h ago</p>
          </div>
        </div>
        
        <button
          onClick={onSearch}
          className="flex items-center gap-2 px-4 py-2 bg-apple-bg border border-apple-border 
                     rounded-full text-caption text-apple-secondary hover:text-apple-text transition-colors"
        >
          <Search className="w-4 h-4" />
          <span>Ask anything</span>
          <kbd className="px-1.5 py-0.5 bg-apple-surface rounded text-xs font-mono ml-2">⌘K</kbd>
        </button>
      </div>
    </header>
  )
}

function SummaryBar() {
  const metrics = [
    { label: 'Enrolled', value: '420 / 595', status: 'healthy' },
    { label: 'Entry Lag', value: '3.2 days', status: 'healthy' },
    { label: 'Open Queries', value: '1,847', status: 'warning' },
    { label: 'Critical Alerts', value: '3', status: 'critical' },
    { label: 'Sites On Track', value: '82%', status: 'healthy' }
  ]
  
  return (
    <div className="flex gap-4 overflow-x-auto pb-2">
      {metrics.map((metric) => (
        <div
          key={metric.label}
          className="flex-shrink-0 card px-5 py-3 cursor-pointer hover:shadow-apple-lg transition-shadow"
        >
          <p className="text-caption text-apple-secondary mb-1">{metric.label}</p>
          <p className={`text-section font-mono ${
            metric.status === 'critical' ? 'text-apple-critical' :
            metric.status === 'warning' ? 'text-apple-warning' :
            'text-apple-text'
          }`}>
            {metric.value}
          </p>
        </div>
      ))}
    </div>
  )
}

function AxisLabels() {
  return (
    <>
      <div className="absolute left-4 top-1/2 -translate-y-1/2 -rotate-90 origin-center">
        <span className="text-caption text-apple-secondary/50">Data Quality Score →</span>
      </div>
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2">
        <span className="text-caption text-apple-secondary/50">Enrollment Progress →</span>
      </div>
    </>
  )
}

function SiteDot({ site, onHover, onClick, isHovered }) {
  const x = site.enrollmentPercent
  const y = 100 - site.dataQualityScore
  const size = 8 + site.alertCount * 4
  
  const colorClass = 
    site.status === 'critical' ? 'bg-apple-critical' :
    site.status === 'warning' ? 'bg-apple-warning' :
    'bg-apple-text'
  
  return (
    <motion.button
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ delay: Math.random() * 0.3 }}
      className={`absolute rounded-full ${colorClass} ${
        site.status === 'critical' ? 'animate-pulse-slow' : ''
      } ${isHovered ? 'ring-4 ring-apple-accent/30' : ''}`}
      style={{
        left: `${x}%`,
        top: `${y}%`,
        width: size,
        height: size,
        transform: 'translate(-50%, -50%)'
      }}
      onMouseEnter={() => onHover(site)}
      onMouseLeave={() => onHover(null)}
      onClick={onClick}
    />
  )
}

function SiteTooltip({ site }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      className="absolute top-4 right-4 card p-4 w-64 z-10"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-section text-apple-text">{site.id}</span>
        <span className={`px-2 py-0.5 rounded-full text-xs text-white ${
          site.status === 'critical' ? 'bg-apple-critical' :
          site.status === 'warning' ? 'bg-apple-warning' :
          'bg-apple-success'
        }`}>
          {site.status}
        </span>
      </div>
      <p className="text-caption text-apple-secondary mb-3">{site.country}</p>
      <div className="space-y-2 text-caption">
        <div className="flex justify-between">
          <span className="text-apple-secondary">Enrollment</span>
          <span className="font-mono">{Math.round(site.enrollmentPercent)}%</span>
        </div>
        <div className="flex justify-between">
          <span className="text-apple-secondary">Data Quality</span>
          <span className="font-mono">{Math.round(site.dataQualityScore)}</span>
        </div>
      </div>
      <p className="mt-3 pt-3 border-t border-apple-border text-caption text-apple-secondary italic">
        "{site.finding}"
      </p>
    </motion.div>
  )
}

function LegendDot({ color, label }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className={`w-2.5 h-2.5 rounded-full ${color}`} />
      <span className="text-caption text-apple-secondary">{label}</span>
    </div>
  )
}

function SiteTable({ sites, onSelect }) {
  const sortedSites = [...sites].sort((a, b) => {
    if (a.status === 'critical' && b.status !== 'critical') return -1
    if (b.status === 'critical' && a.status !== 'critical') return 1
    return b.alertCount - a.alertCount
  }).slice(0, 10)
  
  return (
    <div className="mt-6 card overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="border-b border-apple-border">
            <th className="px-6 py-3 text-left text-caption text-apple-secondary font-medium">Site</th>
            <th className="px-6 py-3 text-left text-caption text-apple-secondary font-medium">Country</th>
            <th className="px-6 py-3 text-right text-caption text-apple-secondary font-medium">Enrollment</th>
            <th className="px-6 py-3 text-right text-caption text-apple-secondary font-medium">Data Quality</th>
            <th className="px-6 py-3 text-right text-caption text-apple-secondary font-medium">Alerts</th>
            <th className="px-6 py-3 text-left text-caption text-apple-secondary font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {sortedSites.map((site) => (
            <tr
              key={site.id}
              onClick={() => onSelect(site)}
              className="border-b border-apple-border last:border-0 hover:bg-apple-bg cursor-pointer transition-colors"
            >
              <td className="px-6 py-4 text-body font-medium">{site.id}</td>
              <td className="px-6 py-4 text-body text-apple-secondary">{site.country}</td>
              <td className="px-6 py-4 text-right font-mono text-data">{Math.round(site.enrollmentPercent)}%</td>
              <td className="px-6 py-4 text-right font-mono text-data">{Math.round(site.dataQualityScore)}</td>
              <td className="px-6 py-4 text-right font-mono text-data">{site.alertCount}</td>
              <td className="px-6 py-4">
                <span className={`inline-flex px-2 py-0.5 rounded-full text-xs text-white ${
                  site.status === 'critical' ? 'bg-apple-critical' :
                  site.status === 'warning' ? 'bg-apple-warning' :
                  'bg-apple-success'
                }`}>
                  {site.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
