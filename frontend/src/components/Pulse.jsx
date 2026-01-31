import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Activity, ArrowRight, AlertTriangle, TrendingDown, 
  Brain, Zap, Eye, CheckCircle, ChevronRight, 
  BarChart3, Users, Clock, Sparkles
} from 'lucide-react'
import { useStore } from '../lib/store'
import { getStudySummary, getAttentionSites, getAgentInsights, getAgentActivity } from '../lib/api'

export function Pulse() {
  const { studyData, setStudyData, setView, setSelectedSite, setInvestigation, toggleCommand } = useStore()
  const [expandedInsight, setExpandedInsight] = useState(null)
  const [attentionSites, setAttentionSites] = useState([])
  const [agentInsights, setAgentInsights] = useState([])
  const [agentActivity, setAgentActivity] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const [summary, attention, insights, activity] = await Promise.all([
          getStudySummary(),
          getAttentionSites(),
          getAgentInsights(),
          getAgentActivity()
        ])
        
        if (summary) {
          setStudyData({
            studyId: summary.study_id,
            studyName: summary.study_name,
            enrolled: summary.enrolled,
            target: summary.target,
            totalSites: summary.total_sites,
            activeSites: summary.active_sites,
            countries: summary.countries,
            criticalSites: attention?.critical_count || 0,
            watchSites: attention?.warning_count || 0,
            lastUpdated: summary.last_updated
          })
        }
        
        if (attention?.sites?.length > 0) {
          setAttentionSites(attention.sites)
        }
        
        if (insights?.insights?.length > 0) {
          setAgentInsights(insights.insights)
        }
        
        if (activity?.agents?.length > 0) {
          setAgentActivity(activity.agents)
        }
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error)
      } finally {
        setLoading(false)
      }
    }
    
    fetchData()
  }, [setStudyData])

  const percentage = studyData.target > 0 
    ? Math.round((studyData.enrolled / studyData.target) * 100 * 10) / 10 
    : 0

  return (
    <div className="min-h-screen bg-apple-bg">
      <Header studyData={studyData} onSearch={toggleCommand} onBack={() => setView('home')} />
      
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <EnrollmentHero 
              enrolled={studyData.enrolled} 
              target={studyData.target} 
              percentage={percentage}
              onExplore={() => setView('constellation')}
            />
            
            <ConductorInsights 
              insights={agentInsights}
              expandedInsight={expandedInsight}
              setExpandedInsight={setExpandedInsight}
              onInvestigate={(insight) => setInvestigation({
                question: `Investigate: ${insight.title}`,
                site: { id: insight.sites[0] },
                status: 'routing'
              })}
            />
          </div>
          
          <div className="space-y-6">
            <AgentActivityPanel agents={agentActivity} />
            
            <AttentionRequired 
              sites={attentionSites}
              onSiteClick={(site) => setSelectedSite(site)}
            />
            
            <QuickActions 
              onAsk={toggleCommand}
              onExplore={() => setView('constellation')}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function Header({ studyData, onSearch, onBack }) {
  return (
    <header className="sticky top-0 z-40 glass border-b border-apple-border">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button 
            onClick={onBack}
            className="flex items-center gap-2 text-apple-secondary hover:text-apple-text transition-colors"
          >
            <Activity className="w-5 h-5" />
            <span className="text-section text-apple-text">{studyData.studyName}</span>
          </button>
          <span className="text-caption text-apple-secondary">Phase 3 · NSCLC</span>
        </div>
        
        <button
          onClick={onSearch}
          className="flex items-center gap-2 px-4 py-2 bg-apple-bg border border-apple-border 
                     rounded-full text-caption text-apple-secondary hover:text-apple-text transition-colors"
        >
          <Sparkles className="w-4 h-4" />
          <span>Ask Conductor</span>
          <kbd className="px-1.5 py-0.5 bg-apple-surface rounded text-xs font-mono ml-2">⌘K</kbd>
        </button>
      </div>
    </header>
  )
}

function EnrollmentHero({ enrolled, target, percentage, onExplore }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="card p-8"
    >
      <div className="flex items-start justify-between mb-6">
        <div>
          <p className="text-caption text-apple-secondary mb-2">Study Enrollment</p>
          <div className="flex items-baseline gap-2">
            <span className="text-5xl font-light text-apple-text">{enrolled}</span>
            <span className="text-2xl text-apple-secondary">/ {target}</span>
          </div>
        </div>
        <button
          onClick={onExplore}
          className="flex items-center gap-2 text-caption text-apple-accent hover:underline"
        >
          Explore sites
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
      
      <div className="mb-4">
        <div className="h-3 bg-apple-border rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${percentage}%` }}
            transition={{ duration: 1, ease: 'easeOut' }}
            className="h-full bg-gradient-to-r from-apple-text to-apple-secondary rounded-full"
          />
        </div>
      </div>
      
      <div className="flex items-center justify-between text-caption">
        <span className="text-apple-text font-medium">{percentage}% complete</span>
        <div className="flex items-center gap-4 text-apple-secondary">
          <span className="flex items-center gap-1">
            <Users className="w-3.5 h-3.5" />
            149 active sites
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" />
            Updated 2h ago
          </span>
        </div>
      </div>
    </motion.div>
  )
}

function ConductorInsights({ insights, expandedInsight, setExpandedInsight, onInvestigate }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="card overflow-hidden"
    >
      <div className="p-6 border-b border-apple-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#5856D6] to-[#AF52DE] flex items-center justify-center">
              <Brain className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="text-section text-apple-text">Conductor Insights</h2>
              <p className="text-caption text-apple-secondary">Proactive findings from AI agents</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-apple-success animate-pulse" />
            <span className="text-caption text-apple-secondary">Live monitoring</span>
          </div>
        </div>
      </div>
      
      <div className="divide-y divide-apple-border">
        {insights.map((insight) => (
          <InsightCard 
            key={insight.id}
            insight={insight}
            isExpanded={expandedInsight === insight.id}
            onToggle={() => setExpandedInsight(expandedInsight === insight.id ? null : insight.id)}
            onInvestigate={() => onInvestigate(insight)}
          />
        ))}
      </div>
    </motion.div>
  )
}

function InsightCard({ insight, isExpanded, onToggle, onInvestigate }) {
  const severityConfig = {
    critical: { bg: 'bg-apple-critical/10', text: 'text-apple-critical', icon: AlertTriangle },
    warning: { bg: 'bg-apple-warning/10', text: 'text-apple-warning', icon: TrendingDown },
    info: { bg: 'bg-apple-info/10', text: 'text-apple-info', icon: Eye }
  }
  const config = severityConfig[insight.severity] || severityConfig.info
  const Icon = config.icon

  return (
    <div className="p-6">
      <button 
        onClick={onToggle}
        className="w-full text-left"
      >
        <div className="flex items-start gap-4">
          <div className={`p-2 rounded-lg ${config.bg}`}>
            <Icon className={`w-4 h-4 ${config.text}`} />
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-caption text-apple-accent font-medium">{insight.agent}</span>
              <span className="text-caption text-apple-secondary">· {insight.timestamp}</span>
            </div>
            <h3 className="text-body text-apple-text font-medium mb-2">{insight.title}</h3>
            <p className="text-caption text-apple-secondary line-clamp-2">{insight.summary}</p>
          </div>
          
          <ChevronRight className={`w-5 h-5 text-apple-secondary transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
        </div>
      </button>
      
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-4 ml-12 space-y-4">
              <div className="p-4 bg-apple-bg rounded-xl">
                <p className="text-caption text-apple-secondary mb-2">Recommendation</p>
                <p className="text-body text-apple-text">{insight.recommendation}</p>
              </div>
              
              <div className="flex items-center gap-6 text-caption">
                <div>
                  <span className="text-apple-secondary">Confidence: </span>
                  <span className="font-mono text-apple-text">{insight.confidence}%</span>
                </div>
                <div>
                  <span className="text-apple-secondary">Impact: </span>
                  <span className="text-apple-text">{insight.impact}</span>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <button
                  onClick={(e) => { e.stopPropagation(); onInvestigate(); }}
                  className="button-primary text-sm py-2"
                >
                  <Zap className="w-4 h-4 mr-2" />
                  Investigate
                </button>
                <button className="button-secondary text-sm py-2">
                  View affected sites
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function AgentActivityPanel({ agents }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="card p-6"
    >
      <div className="flex items-center gap-2 mb-4">
        <Activity className="w-4 h-4 text-apple-accent" />
        <h3 className="text-section text-apple-text">Agent Activity</h3>
      </div>
      
      <div className="space-y-3">
        {agents.map((agent) => (
          <div key={agent.id} className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full ${
              agent.status === 'analyzing' ? 'bg-apple-accent animate-pulse' :
              agent.status === 'monitoring' ? 'bg-apple-success' :
              'bg-apple-secondary'
            }`} />
            <div className="flex-1 min-w-0">
              <p className="text-caption text-apple-text font-medium">{agent.name}</p>
              <p className="text-caption text-apple-secondary truncate">{agent.lastRun}</p>
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  )
}

function AttentionRequired({ sites, onSiteClick }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="card p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-apple-critical" />
          <h3 className="text-section text-apple-text">Attention Required</h3>
        </div>
        <span className="px-2 py-0.5 bg-apple-critical/10 text-apple-critical rounded-full text-xs font-medium">
          {sites.length} sites
        </span>
      </div>
      
      <div className="space-y-2">
        {sites.map((site) => (
          <button
            key={site.site_id}
            onClick={() => onSiteClick({ id: site.site_id, ...site })}
            className="w-full text-left p-3 bg-apple-bg rounded-xl hover:bg-apple-border/50 transition-colors"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-caption text-apple-text font-medium">{site.site_id}</span>
              <span className={`w-2 h-2 rounded-full ${
                site.severity === 'critical' ? 'bg-apple-critical' : 'bg-apple-warning'
              }`} />
            </div>
            <p className="text-caption text-apple-secondary truncate">{site.issue}</p>
            <p className="text-caption text-apple-secondary/70 font-mono">{site.metric}</p>
          </button>
        ))}
      </div>
    </motion.div>
  )
}

function QuickActions({ onAsk, onExplore }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.4 }}
      className="card p-6"
    >
      <h3 className="text-section text-apple-text mb-4">Quick Actions</h3>
      
      <div className="space-y-2">
        <button 
          onClick={onAsk}
          className="w-full flex items-center gap-3 p-3 bg-apple-bg rounded-xl hover:bg-apple-border/50 transition-colors"
        >
          <Sparkles className="w-4 h-4 text-apple-accent" />
          <span className="text-caption text-apple-text">Ask Conductor anything</span>
        </button>
        <button 
          onClick={onExplore}
          className="w-full flex items-center gap-3 p-3 bg-apple-bg rounded-xl hover:bg-apple-border/50 transition-colors"
        >
          <BarChart3 className="w-4 h-4 text-apple-secondary" />
          <span className="text-caption text-apple-text">Explore all sites</span>
        </button>
      </div>
    </motion.div>
  )
}
