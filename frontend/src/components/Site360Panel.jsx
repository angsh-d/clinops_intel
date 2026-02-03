import { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Activity, Users, FileSearch, Shield, Calendar, UserCheck, 
  TrendingUp, TrendingDown, AlertTriangle, CheckCircle2, Clock,
  ChevronRight, BarChart3, Zap, Target
} from 'lucide-react'
import { getSiteDetail, getSiteMetadata } from '../lib/api'

const DIMENSION_CONFIG = {
  enrollment: { 
    label: 'Enrollment', 
    icon: Users, 
    color: '#34C759',
    description: 'Patient recruitment progress'
  },
  dataQuality: { 
    label: 'Data Quality', 
    icon: FileSearch, 
    color: '#5856D6',
    description: 'eCRF accuracy and completeness'
  },
  monitoring: { 
    label: 'Monitoring', 
    icon: Calendar, 
    color: '#FF9500',
    description: 'Visit compliance and findings'
  },
  integrity: { 
    label: 'Data Integrity', 
    icon: Shield, 
    color: '#AF52DE',
    description: 'Fraud risk indicators'
  },
  operations: { 
    label: 'Operations', 
    icon: Activity, 
    color: '#007AFF',
    description: 'CRA coverage and responsiveness'
  }
}

function RadarChart({ dimensions, size = 280 }) {
  const center = size / 2
  const radius = (size / 2) - 40
  const numPoints = Object.keys(dimensions).length
  
  const points = useMemo(() => {
    const keys = Object.keys(dimensions)
    return keys.map((key, i) => {
      const angle = (Math.PI * 2 * i) / numPoints - Math.PI / 2
      const value = dimensions[key]?.score || 0
      const normalizedValue = Math.min(100, Math.max(0, value)) / 100
      return {
        key,
        angle,
        x: center + Math.cos(angle) * radius * normalizedValue,
        y: center + Math.sin(angle) * radius * normalizedValue,
        labelX: center + Math.cos(angle) * (radius + 25),
        labelY: center + Math.sin(angle) * (radius + 25),
        gridX: center + Math.cos(angle) * radius,
        gridY: center + Math.sin(angle) * radius,
      }
    })
  }, [dimensions, center, radius, numPoints])

  const pathData = points.map((p, i) => 
    `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`
  ).join(' ') + ' Z'

  const gridLevels = [0.25, 0.5, 0.75, 1]

  return (
    <svg width={size} height={size} className="mx-auto">
      {gridLevels.map(level => (
        <polygon
          key={level}
          points={points.map(p => {
            const x = center + Math.cos(p.angle) * radius * level
            const y = center + Math.sin(p.angle) * radius * level
            return `${x},${y}`
          }).join(' ')}
          fill="none"
          stroke="currentColor"
          strokeWidth="1"
          className="text-apple-border/40"
        />
      ))}
      
      {points.map(p => (
        <line
          key={`axis-${p.key}`}
          x1={center}
          y1={center}
          x2={p.gridX}
          y2={p.gridY}
          stroke="currentColor"
          strokeWidth="1"
          className="text-apple-border/30"
        />
      ))}
      
      <defs>
        <linearGradient id="radarGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#5856D6" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#AF52DE" stopOpacity="0.3" />
        </linearGradient>
      </defs>
      
      <motion.path
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ duration: 1.2, ease: "easeOut" }}
        d={pathData}
        fill="url(#radarGradient)"
        stroke="url(#radarGradient)"
        strokeWidth="2"
        className="drop-shadow-lg"
      />
      
      {points.map((p, i) => {
        const config = DIMENSION_CONFIG[p.key]
        const score = dimensions[p.key]?.score || 0
        return (
          <g key={`label-${p.key}`}>
            <motion.circle
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.3 + i * 0.1, duration: 0.3 }}
              cx={p.x}
              cy={p.y}
              r={6}
              fill={config?.color || '#5856D6'}
              className="drop-shadow-md"
            />
            <text
              x={p.labelX}
              y={p.labelY}
              textAnchor="middle"
              dominantBaseline="middle"
              className="text-[10px] font-medium fill-apple-secondary"
            >
              {config?.label || p.key}
            </text>
            <text
              x={p.labelX}
              y={p.labelY + 12}
              textAnchor="middle"
              dominantBaseline="middle"
              className="text-[11px] font-semibold fill-apple-text"
            >
              {Math.round(score)}%
            </text>
          </g>
        )
      })}
    </svg>
  )
}

function DimensionCard({ dimension, data, isExpanded, onToggle }) {
  const config = DIMENSION_CONFIG[dimension]
  const Icon = config?.icon || Activity
  const score = data?.score || 0
  const status = score >= 80 ? 'healthy' : score >= 60 ? 'warning' : 'critical'
  
  const statusColors = {
    healthy: 'bg-apple-success/10 text-apple-success',
    warning: 'bg-apple-warning/10 text-apple-warning',
    critical: 'bg-apple-critical/10 text-apple-critical'
  }

  return (
    <motion.div
      layout
      className="bg-apple-surface rounded-2xl border border-apple-border overflow-hidden"
    >
      <button
        onClick={onToggle}
        className="w-full p-4 flex items-center gap-4 hover:bg-apple-bg/50 transition-colors"
      >
        <div 
          className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ backgroundColor: `${config?.color}15` }}
        >
          <Icon className="w-5 h-5" style={{ color: config?.color }} />
        </div>
        
        <div className="flex-1 text-left">
          <div className="flex items-center gap-2">
            <span className="font-medium text-apple-text">{config?.label}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[status]}`}>
              {Math.round(score)}%
            </span>
          </div>
          <p className="text-xs text-apple-secondary mt-0.5">{config?.description}</p>
        </div>
        
        <ChevronRight 
          className={`w-4 h-4 text-apple-secondary transition-transform ${isExpanded ? 'rotate-90' : ''}`}
        />
      </button>
      
      <AnimatePresence>
        {isExpanded && data?.metrics && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t border-apple-border"
          >
            <div className="p-4 grid grid-cols-2 gap-3">
              {data.metrics.map((metric, i) => (
                <div key={i} className="bg-apple-bg rounded-xl p-3">
                  <div className="text-xs text-apple-secondary mb-1">{metric.label}</div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-lg font-semibold text-apple-text">
                      {metric.value}
                    </span>
                    {metric.trend === 'up' && <TrendingUp className="w-3.5 h-3.5 text-apple-critical" />}
                    {metric.trend === 'down' && <TrendingDown className="w-3.5 h-3.5 text-apple-success" />}
                  </div>
                  {metric.note && (
                    <div className="text-[10px] text-apple-secondary/70 mt-1">{metric.note}</div>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function MonitoringTimeline({ visits }) {
  if (!visits || visits.length === 0) return null

  return (
    <div className="bg-apple-surface rounded-2xl border border-apple-border p-4">
      <div className="flex items-center gap-2 mb-4">
        <Calendar className="w-4 h-4 text-apple-secondary" />
        <h3 className="font-medium text-apple-text">Monitoring Activity</h3>
      </div>
      
      <div className="relative">
        <div className="absolute left-3 top-2 bottom-2 w-px bg-apple-border" />
        
        <div className="space-y-3">
          {visits.slice(0, 4).map((visit, i) => {
            const hasCritical = visit.critical_findings > 0
            const hasFindings = visit.findings_count > 0
            
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="flex items-start gap-3 pl-6 relative"
              >
                <div className={`absolute left-1.5 top-1.5 w-3 h-3 rounded-full border-2 ${
                  hasCritical ? 'bg-apple-critical border-apple-critical' :
                  hasFindings ? 'bg-apple-warning border-apple-warning' :
                  'bg-apple-success border-apple-success'
                }`} />
                
                <div className="flex-1 bg-apple-bg rounded-xl p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-apple-text">
                      {visit.visit_type || 'Monitoring Visit'}
                    </span>
                    <span className="text-xs text-apple-secondary">
                      {visit.visit_date}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-apple-secondary">
                    {visit.findings_count > 0 && (
                      <span className={hasCritical ? 'text-apple-critical' : 'text-apple-warning'}>
                        {visit.findings_count} finding{visit.findings_count !== 1 ? 's' : ''}
                        {hasCritical && ` (${visit.critical_findings} critical)`}
                      </span>
                    )}
                    {visit.findings_count === 0 && (
                      <span className="text-apple-success">No findings</span>
                    )}
                    {visit.days_overdue > 0 && (
                      <span className="text-apple-critical">
                        {visit.days_overdue}d overdue
                      </span>
                    )}
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function CRAPanel({ assignments }) {
  const currentCRA = assignments?.find(a => a.is_current)
  const pastCRAs = assignments?.filter(a => !a.is_current) || []
  
  if (!currentCRA && pastCRAs.length === 0) return null

  return (
    <div className="bg-apple-surface rounded-2xl border border-apple-border p-4">
      <div className="flex items-center gap-2 mb-4">
        <UserCheck className="w-4 h-4 text-apple-secondary" />
        <h3 className="font-medium text-apple-text">CRA Coverage</h3>
      </div>
      
      {currentCRA ? (
        <div className="bg-apple-bg rounded-xl p-3 mb-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-medium text-apple-text">{currentCRA.cra_id}</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-apple-success/10 text-apple-success">
                  Active
                </span>
              </div>
              <div className="text-xs text-apple-secondary mt-1">
                Since {currentCRA.start_date}
              </div>
            </div>
            <CheckCircle2 className="w-5 h-5 text-apple-success" />
          </div>
        </div>
      ) : (
        <div className="bg-apple-warning/10 rounded-xl p-3 mb-3">
          <div className="flex items-center gap-2 text-apple-warning">
            <AlertTriangle className="w-4 h-4" />
            <span className="text-sm font-medium">No active CRA assigned</span>
          </div>
        </div>
      )}
      
      {pastCRAs.length > 0 && (
        <div className="text-xs text-apple-secondary">
          {pastCRAs.length} previous CRA assignment{pastCRAs.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  )
}

function AlertsPanel({ alerts }) {
  if (!alerts || alerts.length === 0) return null

  return (
    <div className="bg-apple-surface rounded-2xl border border-apple-border p-4">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="w-4 h-4 text-apple-warning" />
        <h3 className="font-medium text-apple-text">Active Signals</h3>
        <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-apple-warning/10 text-apple-warning">
          {alerts.length}
        </span>
      </div>
      
      <div className="space-y-2">
        {alerts.slice(0, 3).map((alert, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="flex items-start gap-3 p-2 rounded-xl bg-apple-bg"
          >
            <div className={`w-2 h-2 rounded-full mt-1.5 ${
              alert.severity === 'critical' ? 'bg-apple-critical' :
              alert.severity === 'warning' ? 'bg-apple-warning' :
              'bg-apple-info'
            }`} />
            <div className="flex-1">
              <p className="text-sm text-apple-text">{alert.message}</p>
              <p className="text-xs text-apple-secondary mt-0.5">{alert.time}</p>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

function SignalBanner({ question, siteName }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-r from-[#5856D6]/10 via-[#AF52DE]/10 to-[#5856D6]/10 rounded-2xl p-4 border border-[#5856D6]/20"
    >
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#5856D6] to-[#AF52DE] flex items-center justify-center">
          <Zap className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1">
          <div className="text-xs font-medium text-apple-secondary mb-1">Signal Under Investigation</div>
          <p className="text-sm text-apple-text font-medium">{question}</p>
        </div>
      </div>
    </motion.div>
  )
}

function OverallHealthScore({ dimensions }) {
  const scores = Object.values(dimensions).map(d => d?.score || 0)
  const average = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0
  const status = average >= 80 ? 'healthy' : average >= 60 ? 'warning' : 'critical'
  
  const statusConfig = {
    healthy: { color: 'text-apple-success', bg: 'bg-apple-success', label: 'On Track' },
    warning: { color: 'text-apple-warning', bg: 'bg-apple-warning', label: 'Needs Attention' },
    critical: { color: 'text-apple-critical', bg: 'bg-apple-critical', label: 'At Risk' }
  }

  return (
    <motion.div
      initial={{ scale: 0.95, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className="text-center mb-6"
    >
      <div className="relative inline-block">
        <svg width="120" height="120" className="transform -rotate-90">
          <circle
            cx="60"
            cy="60"
            r="50"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            className="text-apple-border/30"
          />
          <motion.circle
            cx="60"
            cy="60"
            r="50"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={`${2 * Math.PI * 50}`}
            initial={{ strokeDashoffset: 2 * Math.PI * 50 }}
            animate={{ strokeDashoffset: 2 * Math.PI * 50 * (1 - average / 100) }}
            transition={{ duration: 1.2, ease: "easeOut" }}
            className={statusConfig[status].color}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-semibold text-apple-text">{Math.round(average)}</span>
          <span className="text-xs text-apple-secondary">Health Score</span>
        </div>
      </div>
      <div className={`inline-flex items-center gap-1.5 mt-3 px-3 py-1 rounded-full ${statusConfig[status].bg}/10`}>
        <div className={`w-2 h-2 rounded-full ${statusConfig[status].bg}`} />
        <span className={`text-sm font-medium ${statusConfig[status].color}`}>
          {statusConfig[status].label}
        </span>
      </div>
    </motion.div>
  )
}

export function Site360Panel({ siteId, siteName, question, onLaunchAnalysis }) {
  const [loading, setLoading] = useState(true)
  const [siteData, setSiteData] = useState(null)
  const [metadata, setMetadata] = useState(null)
  const [expandedDimension, setExpandedDimension] = useState(null)

  useEffect(() => {
    async function fetchData() {
      setLoading(true)
      try {
        const [detailRes, metadataRes] = await Promise.all([
          getSiteDetail(siteId),
          getSiteMetadata()
        ])
        setSiteData(detailRes)
        const siteMetadata = metadataRes?.sites?.find(s => s.site_id === siteId)
        setMetadata(siteMetadata)
      } catch (error) {
        console.error('Failed to fetch site 360 data:', error)
      } finally {
        setLoading(false)
      }
    }
    if (siteId) fetchData()
  }, [siteId])

  const dimensions = useMemo(() => {
    if (!siteData) return {}
    
    const enrollmentPct = siteData.enrollment_percent || 0
    const dqScore = siteData.data_quality_score || 0
    
    const openQueries = parseInt(siteData.data_quality_metrics?.find(m => m.label === 'Open Queries')?.value) || 0
    const queryRate = parseFloat(siteData.data_quality_metrics?.find(m => m.label === 'Query Rate')?.value) || 0
    
    const visits = metadata?.monitoring_visits || []
    const recentCritical = visits.slice(0, 3).filter(v => v.critical_findings > 0).length
    const monitoringScore = visits.length > 0 
      ? Math.max(0, 100 - (recentCritical * 20) - (visits[0]?.days_overdue || 0) * 2)
      : 70
    
    const integrityScore = queryRate > 5 ? 50 : queryRate > 3 ? 70 : 90
    
    const cras = metadata?.cra_assignments || []
    const hasActiveCRA = cras.some(c => c.is_current)
    const craChanges = cras.length
    const operationsScore = hasActiveCRA 
      ? Math.max(60, 100 - (craChanges - 1) * 10)
      : 40

    return {
      enrollment: {
        score: enrollmentPct,
        metrics: siteData.enrollment_metrics
      },
      dataQuality: {
        score: dqScore,
        metrics: siteData.data_quality_metrics
      },
      monitoring: {
        score: monitoringScore,
        metrics: [
          { label: 'Recent Visits', value: `${visits.length}`, note: 'Last 90 days' },
          { label: 'Critical Findings', value: `${visits.reduce((a, v) => a + (v.critical_findings || 0), 0)}` },
          { label: 'Avg Findings/Visit', value: visits.length > 0 ? (visits.reduce((a, v) => a + (v.findings_count || 0), 0) / visits.length).toFixed(1) : '0' },
          { label: 'Overdue Days', value: `${visits[0]?.days_overdue || 0}d` }
        ]
      },
      integrity: {
        score: integrityScore,
        metrics: [
          { label: 'Query Rate', value: queryRate.toString(), note: 'per subject' },
          { label: 'Risk Level', value: integrityScore >= 80 ? 'Low' : integrityScore >= 60 ? 'Medium' : 'High' }
        ]
      },
      operations: {
        score: operationsScore,
        metrics: [
          { label: 'Active CRA', value: hasActiveCRA ? 'Yes' : 'No' },
          { label: 'CRA Changes', value: `${Math.max(0, craChanges - 1)}`, note: 'Since activation' }
        ]
      }
    }
  }, [siteData, metadata])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex flex-col items-center gap-3">
          <div className="w-12 h-12 rounded-full border-2 border-apple-border border-t-apple-accent animate-spin" />
          <span className="text-sm text-apple-secondary">Loading site profile...</span>
        </div>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-full overflow-y-auto"
    >
      <div className="max-w-5xl mx-auto p-6 space-y-6">
        <SignalBanner question={question} siteName={siteName} />
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-apple-surface rounded-2xl border border-apple-border p-6">
            <h3 className="text-lg font-semibold text-apple-text mb-2 text-center">
              {siteName || siteId}
            </h3>
            <p className="text-sm text-apple-secondary text-center mb-4">
              {siteData?.country}{siteData?.city ? `, ${siteData.city}` : ''}
            </p>
            
            <OverallHealthScore dimensions={dimensions} />
            <RadarChart dimensions={dimensions} />
          </div>
          
          <div className="space-y-3">
            {Object.entries(dimensions).map(([key, data]) => (
              <DimensionCard
                key={key}
                dimension={key}
                data={data}
                isExpanded={expandedDimension === key}
                onToggle={() => setExpandedDimension(expandedDimension === key ? null : key)}
              />
            ))}
          </div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <MonitoringTimeline visits={metadata?.monitoring_visits} />
          <CRAPanel assignments={metadata?.cra_assignments} />
          <AlertsPanel alerts={siteData?.alerts} />
        </div>
        
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onLaunchAnalysis}
          className="w-full py-4 px-6 bg-gradient-to-r from-[#5856D6] to-[#AF52DE] rounded-2xl text-white font-medium flex items-center justify-center gap-3 shadow-lg hover:shadow-xl transition-shadow"
        >
          <Target className="w-5 h-5" />
          Launch Causal Analysis
          <ChevronRight className="w-5 h-5" />
        </motion.button>
      </div>
    </motion.div>
  )
}
