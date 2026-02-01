import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { X, TrendingUp, TrendingDown, AlertCircle, MessageCircle, Loader2 } from 'lucide-react'
import { useStore } from '../lib/store'
import { getSiteDetail } from '../lib/api'

export function SiteSheet() {
  const { selectedSite, setSelectedSite, setInvestigation } = useStore()
  const [siteData, setSiteData] = useState(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    if (!selectedSite) return
    
    async function fetchSiteData() {
      setLoading(true)
      try {
        const data = await getSiteDetail(selectedSite.id)
        setSiteData(data)
      } catch (error) {
        console.error('Failed to fetch site details:', error)
      } finally {
        setLoading(false)
      }
    }
    
    fetchSiteData()
  }, [selectedSite?.id])
  
  if (!selectedSite) return null
  
  const handleInvestigate = (question) => {
    setInvestigation({
      question,
      site: selectedSite,
      status: 'routing'
    })
  }
  
  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/20 z-40"
        onClick={() => setSelectedSite(null)}
      />
      
      <motion.div
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 30, stiffness: 300 }}
        className="fixed right-0 top-0 bottom-0 w-full max-w-lg bg-apple-surface border-l border-apple-border z-50 overflow-y-auto"
      >
        <div className="sticky top-0 bg-apple-surface/90 backdrop-blur-xl border-b border-apple-border px-6 py-4 flex items-center justify-between z-10">
          <div>
            <h2 className="text-section text-apple-text">{siteData?.site_name || selectedSite.name || selectedSite.id}</h2>
            <p className="text-caption text-apple-secondary">{siteData?.country || selectedSite.country}{siteData?.city ? `, ${siteData.city}` : ''}</p>
          </div>
          <button
            onClick={() => setSelectedSite(null)}
            className="p-2 hover:bg-apple-bg rounded-full transition-colors"
          >
            <X className="w-5 h-5 text-apple-secondary" />
          </button>
        </div>
        
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-6 h-6 text-apple-secondary animate-spin" />
          </div>
        ) : siteData ? (
          <div className="p-6 space-y-6">
            <StatusBadge status={siteData.status} />
            
            <AISummary
              summary={siteData.ai_summary}
              onAsk={() => handleInvestigate(`Why is ${selectedSite.id} showing these metrics?`)}
            />
            
            <DomainCard
              title="Data Quality"
              icon={<TrendingUp className="w-4 h-4" />}
              status={siteData.data_quality_score < 70 ? 'critical' : siteData.data_quality_score < 85 ? 'warning' : 'healthy'}
              summary={`Data quality score: ${Math.round(siteData.data_quality_score)}%`}
              metrics={siteData.data_quality_metrics}
              onInvestigate={() => handleInvestigate(`What caused the data quality issues at ${selectedSite.id}?`)}
            />
            
            <DomainCard
              title="Enrollment"
              icon={<TrendingDown className="w-4 h-4" />}
              status={siteData.enrollment_percent < 50 ? 'warning' : 'healthy'}
              summary={`${Math.round(siteData.enrollment_percent)}% of enrollment target achieved`}
              metrics={siteData.enrollment_metrics}
              onInvestigate={() => handleInvestigate(`Why did enrollment slow at ${selectedSite.id}?`)}
            />
            
            <AlertsSection alerts={siteData.alerts} />
            
            <QuickAsk siteId={selectedSite.id} onAsk={handleInvestigate} />
          </div>
        ) : (
          <div className="flex items-center justify-center h-64 text-apple-secondary">
            Failed to load site data
          </div>
        )}
      </motion.div>
    </>
  )
}

function StatusBadge({ status }) {
  const config = {
    critical: { bg: 'bg-apple-critical/10', text: 'text-apple-critical', label: 'Needs Attention' },
    warning: { bg: 'bg-apple-warning/10', text: 'text-apple-warning', label: 'On Watch' },
    healthy: { bg: 'bg-apple-success/10', text: 'text-apple-success', label: 'On Track' }
  }
  const { bg, text, label } = config[status] || config.healthy
  
  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full ${bg}`}>
      <div className={`w-2 h-2 rounded-full ${text.replace('text-', 'bg-')}`} />
      <span className={`text-caption font-medium ${text}`}>{label}</span>
    </div>
  )
}

function AISummary({ summary, onAsk }) {
  return (
    <div className="relative pl-4 border-l-2 border-gradient-to-b from-[#5856D6] to-[#AF52DE]">
      <div className="absolute left-0 top-0 bottom-0 w-0.5 ai-gradient-border" />
      <p className="text-body text-apple-text leading-relaxed">{summary}</p>
      <div className="flex items-center gap-2 mt-3">
        <span className="text-caption text-apple-secondary">Conductor Analysis</span>
        <button
          onClick={onAsk}
          className="text-caption text-apple-accent hover:underline"
        >
          Ask why
        </button>
      </div>
    </div>
  )
}

function DomainCard({ title, icon, status, summary, metrics, onInvestigate }) {
  const statusColors = {
    healthy: 'border-apple-success/30',
    warning: 'border-apple-warning/30',
    critical: 'border-apple-critical/30'
  }
  
  return (
    <div className={`card p-5 border-l-4 ${statusColors[status]}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-apple-secondary">{icon}</span>
          <h3 className="text-section text-apple-text">{title}</h3>
        </div>
        <button
          onClick={onInvestigate}
          className="text-caption text-apple-accent hover:underline"
        >
          Investigate
        </button>
      </div>
      
      <p className="text-body text-apple-secondary mb-4">{summary}</p>
      
      <div className="grid grid-cols-3 gap-4">
        {metrics?.map((metric) => (
          <div key={metric.label}>
            <p className="text-caption text-apple-secondary mb-1">{metric.label}</p>
            <p className="font-mono text-data text-apple-text">
              {metric.value}
              {metric.trend === 'up' && <TrendingUp className="inline w-3 h-3 ml-1 text-apple-critical" />}
              {metric.trend === 'down' && <TrendingDown className="inline w-3 h-3 ml-1 text-apple-success" />}
            </p>
            {metric.note && <p className="text-caption text-apple-secondary/70">{metric.note}</p>}
          </div>
        ))}
      </div>
      
      <div className="mt-4 pt-3 border-t border-apple-border">
        <p className="text-caption text-apple-secondary">
          Source: Database · Live data
        </p>
      </div>
    </div>
  )
}

function AlertsSection({ alerts }) {
  if (!alerts || alerts.length === 0) {
    return (
      <div className="space-y-3">
        <h3 className="text-section text-apple-text">Active Alerts</h3>
        <div className="p-3 bg-apple-bg rounded-xl text-center">
          <p className="text-body text-apple-secondary">No active alerts</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="space-y-3">
      <h3 className="text-section text-apple-text">Active Alerts</h3>
      {alerts.map((alert, i) => (
        <div key={i} className="flex items-start gap-3 p-3 bg-apple-bg rounded-xl">
          <AlertCircle className={`w-4 h-4 mt-0.5 ${
            alert.severity === 'critical' ? 'text-apple-critical' :
            alert.severity === 'warning' ? 'text-apple-warning' :
            'text-apple-info'
          }`} />
          <div className="flex-1">
            <p className="text-body text-apple-text">{alert.message}</p>
            <p className="text-caption text-apple-secondary">{alert.time}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

function QuickAsk({ siteId, onAsk }) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-3">
        <MessageCircle className="w-5 h-5 text-apple-secondary" />
        <input
          type="text"
          placeholder={`Ask about ${siteId}...`}
          className="flex-1 bg-transparent text-body placeholder:text-apple-secondary/50 outline-none"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && e.target.value) {
              onAsk(e.target.value)
              e.target.value = ''
            }
          }}
        />
      </div>
    </div>
  )
}
