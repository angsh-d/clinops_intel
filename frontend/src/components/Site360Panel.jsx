import { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Activity, Users, FileSearch, Shield, Calendar, UserCheck, 
  TrendingUp, TrendingDown, AlertTriangle, CheckCircle2,
  ChevronRight, ChevronDown, ArrowRight
} from 'lucide-react'
import { getSiteDetail, getSiteMetadata } from '../lib/api'

const DIMENSION_CONFIG = {
  enrollment: { 
    label: 'Enrollment', 
    icon: Users, 
    description: 'Patient recruitment progress'
  },
  dataQuality: { 
    label: 'Data Quality', 
    icon: FileSearch, 
    description: 'eCRF accuracy and completeness'
  },
  monitoring: { 
    label: 'Monitoring', 
    icon: Calendar, 
    description: 'Visit compliance and findings'
  },
  integrity: { 
    label: 'Data Integrity', 
    icon: Shield, 
    description: 'Fraud risk indicators'
  },
  operations: { 
    label: 'Operations', 
    icon: Activity, 
    description: 'CRA coverage and responsiveness'
  }
}

function RadarChart({ dimensions, size = 260 }) {
  const center = size / 2
  const radius = (size / 2) - 45
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
        labelX: center + Math.cos(angle) * (radius + 28),
        labelY: center + Math.sin(angle) * (radius + 28),
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
          strokeWidth="0.5"
          className="text-neutral-200"
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
          strokeWidth="0.5"
          className="text-neutral-200"
        />
      ))}
      
      <motion.path
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ duration: 1, ease: "easeOut" }}
        d={pathData}
        fill="rgba(0, 0, 0, 0.04)"
        stroke="rgba(0, 0, 0, 0.5)"
        strokeWidth="1.5"
      />
      
      {points.map((p, i) => {
        const config = DIMENSION_CONFIG[p.key]
        const score = dimensions[p.key]?.score || 0
        const status = score >= 80 ? 'healthy' : score >= 60 ? 'warning' : 'critical'
        const dotColor = status === 'critical' ? '#EF4444' : status === 'warning' ? '#F59E0B' : '#22C55E'
        
        return (
          <g key={`label-${p.key}`}>
            <motion.circle
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2 + i * 0.08, duration: 0.25 }}
              cx={p.x}
              cy={p.y}
              r={4}
              fill={dotColor}
            />
            <text
              x={p.labelX}
              y={p.labelY - 6}
              textAnchor="middle"
              dominantBaseline="middle"
              className="text-[9px] font-medium fill-neutral-400 uppercase tracking-wide"
            >
              {config?.label || p.key}
            </text>
            <text
              x={p.labelX}
              y={p.labelY + 8}
              textAnchor="middle"
              dominantBaseline="middle"
              className="text-[13px] font-semibold fill-neutral-900 tabular-nums"
            >
              {Math.round(score)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

function DimensionRow({ dimension, data, isExpanded, onToggle }) {
  const config = DIMENSION_CONFIG[dimension]
  const Icon = config?.icon || Activity
  const score = data?.score || 0
  const status = score >= 80 ? 'healthy' : score >= 60 ? 'warning' : 'critical'
  
  const statusDot = {
    healthy: 'bg-green-500',
    warning: 'bg-amber-500',
    critical: 'bg-red-500'
  }

  return (
    <div className="border-b border-neutral-100 last:border-b-0">
      <button
        onClick={onToggle}
        className="w-full py-4 px-1 flex items-center gap-4 hover:bg-neutral-50/50 transition-colors"
      >
        <Icon className="w-4 h-4 text-neutral-400 flex-shrink-0" />
        
        <div className="flex-1 text-left">
          <span className="text-[15px] font-medium text-neutral-900">{config?.label}</span>
        </div>
        
        <div className="flex items-center gap-3">
          <div className={`w-2 h-2 rounded-full ${statusDot[status]}`} />
          <span className="text-[15px] font-semibold text-neutral-900 tabular-nums w-8 text-right">
            {Math.round(score)}
          </span>
          <ChevronDown 
            className={`w-4 h-4 text-neutral-300 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          />
        </div>
      </button>
      
      <AnimatePresence>
        {isExpanded && data?.metrics && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-1 pb-4">
              {/* Formula explanation */}
              {data.formula && (
                <div className="bg-neutral-100 rounded-lg p-3 mb-3 font-mono">
                  <div className="text-[10px] text-neutral-500 uppercase tracking-wide mb-1">Formula</div>
                  <p className="text-[12px] text-neutral-700">{data.formula}</p>
                </div>
              )}
              {data.source && (
                <p className="text-[11px] text-neutral-500 mb-3">
                  <span className="font-medium">Calculation:</span> {data.source}
                </p>
              )}
              <div className="grid grid-cols-2 gap-2">
                {data.metrics.map((metric, i) => (
                  <div key={i} className="bg-neutral-50 rounded-lg p-3">
                    <div className="text-[11px] text-neutral-500 uppercase tracking-wide mb-1">{metric.label}</div>
                    <div className="flex items-center gap-2">
                      <span className="text-[17px] font-semibold text-neutral-900 tabular-nums">
                        {metric.value}
                      </span>
                      {metric.trend === 'up' && <TrendingUp className="w-3 h-3 text-red-500" />}
                      {metric.trend === 'down' && <TrendingDown className="w-3 h-3 text-green-500" />}
                    </div>
                    {metric.note && (
                      <div className="text-[10px] text-neutral-400 mt-0.5">{metric.note}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function SiteJourneyMap({ visits, craAssignments }) {
  // Build events list
  const events = []
  
  // Add CRA assignment events
  if (craAssignments && Array.isArray(craAssignments)) {
    craAssignments.forEach(cra => {
      if (cra.start_date) {
        events.push({
          type: 'cra_start',
          date: cra.start_date,
          label: cra.cra_id,
          isCurrent: cra.is_current,
          details: cra.is_current ? 'Current CRA' : 'Previous CRA'
        })
      }
      if (cra.end_date && !cra.is_current) {
        events.push({
          type: 'cra_end',
          date: cra.end_date,
          label: cra.cra_id,
          details: 'CRA transition'
        })
      }
    })
  }
  
  // Add monitoring visit events
  if (visits && Array.isArray(visits)) {
    visits.forEach(visit => {
      if (visit.visit_date) {
        events.push({
          type: 'visit',
          date: visit.visit_date,
          label: visit.visit_type || 'Visit',
          visitType: visit.visit_type,
          findings: visit.findings_count || 0,
          critical: visit.critical_findings || 0
        })
      }
    })
  }
  
  // Sort by date descending (most recent first)
  const allEvents = events.sort((a, b) => new Date(b.date) - new Date(a.date)).slice(0, 8)

  if (allEvents.length === 0) return null

  return (
    <div className="lg:col-span-2">
      <div className="flex items-center gap-2 mb-5">
        <Calendar className="w-4 h-4 text-neutral-400" />
        <h3 className="text-[13px] font-semibold text-neutral-900 uppercase tracking-wide">Site Journey</h3>
        <div className="flex items-center gap-4 ml-auto">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-blue-500" />
            <span className="text-[10px] text-neutral-400">CRA</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-2 rounded-sm bg-neutral-800" />
            <span className="text-[10px] text-neutral-400">On-Site</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-2 rounded-sm bg-neutral-300" />
            <span className="text-[10px] text-neutral-400">Remote</span>
          </div>
        </div>
      </div>
      
      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-[7px] top-3 bottom-3 w-px bg-neutral-200" />
        
        <div className="space-y-0">
          {allEvents.map((event, i) => {
            const isCRA = event.type === 'cra_start' || event.type === 'cra_end'
            const isOnSite = event.visitType?.toLowerCase().includes('on-site') || event.visitType?.toLowerCase().includes('onsite')
            const hasCritical = event.critical > 0
            const hasFindings = event.findings > 0
            
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-start gap-4 py-2 relative"
              >
                {/* Timeline marker */}
                <div className="relative z-10 flex-shrink-0">
                  {isCRA ? (
                    <div className={`w-4 h-4 rounded-full flex items-center justify-center ${
                      event.type === 'cra_start' && event.isCurrent 
                        ? 'bg-blue-500' 
                        : event.type === 'cra_start' 
                          ? 'bg-blue-300' 
                          : 'bg-blue-200'
                    }`}>
                      <UserCheck className="w-2.5 h-2.5 text-white" />
                    </div>
                  ) : (
                    <div className={`w-4 h-4 rounded flex items-center justify-center ${
                      isOnSite ? 'bg-neutral-800' : 'bg-neutral-300'
                    }`}>
                      {hasCritical && <div className="w-1.5 h-1.5 rounded-full bg-red-500" />}
                      {!hasCritical && hasFindings && <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />}
                      {!hasCritical && !hasFindings && <div className="w-1.5 h-1.5 rounded-full bg-green-500" />}
                    </div>
                  )}
                </div>
                
                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`text-[13px] font-medium ${isCRA ? 'text-blue-700' : 'text-neutral-900'}`}>
                      {event.label}
                    </span>
                    {isCRA && event.type === 'cra_start' && event.isCurrent && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 uppercase tracking-wide">Active</span>
                    )}
                    {isCRA && event.type === 'cra_end' && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 uppercase tracking-wide">Transition</span>
                    )}
                    {!isCRA && hasCritical && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-red-100 text-red-700">{event.critical} critical</span>
                    )}
                    {!isCRA && !hasCritical && hasFindings && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">{event.findings} findings</span>
                    )}
                  </div>
                  {event.details && (
                    <p className="text-[11px] text-neutral-400 mt-0.5">{event.details}</p>
                  )}
                </div>
                
                {/* Date */}
                <span className="text-[11px] text-neutral-400 tabular-nums flex-shrink-0">
                  {event.date}
                </span>
              </motion.div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function AlertsList({ alerts }) {
  if (!alerts || alerts.length === 0) return null

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="w-4 h-4 text-neutral-400" />
        <h3 className="text-[13px] font-semibold text-neutral-900 uppercase tracking-wide">Active Signals</h3>
        <span className="ml-auto text-[11px] text-neutral-400 tabular-nums">{alerts.length}</span>
      </div>
      
      <div className="space-y-2">
        {alerts.slice(0, 3).map((alert, i) => {
          const dotColor = alert.severity === 'critical' ? 'bg-red-500' : 
                          alert.severity === 'warning' ? 'bg-amber-500' : 'bg-neutral-400'
          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              className="flex items-start gap-3 py-1"
            >
              <div className={`w-2 h-2 rounded-full mt-1.5 ${dotColor}`} />
              <div className="flex-1">
                <p className="text-[13px] text-neutral-900 leading-snug">{alert.message}</p>
                <p className="text-[11px] text-neutral-400 mt-0.5">{alert.time}</p>
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}

function HealthScore({ dimensions }) {
  const scores = Object.values(dimensions).map(d => d?.score || 0)
  const average = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0
  const status = average >= 80 ? 'healthy' : average >= 60 ? 'warning' : 'critical'
  
  const statusConfig = {
    healthy: { color: 'text-green-500', ring: 'stroke-green-500', label: 'On Track' },
    warning: { color: 'text-amber-500', ring: 'stroke-amber-500', label: 'Needs Attention' },
    critical: { color: 'text-red-500', ring: 'stroke-red-500', label: 'At Risk' }
  }

  const circumference = 2 * Math.PI * 45
  const offset = circumference * (1 - average / 100)

  return (
    <div className="flex flex-col items-center">
      <div className="relative">
        <svg width="100" height="100" className="transform -rotate-90">
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="currentColor"
            strokeWidth="6"
            className="text-neutral-100"
          />
          <motion.circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1, ease: "easeOut" }}
            className={statusConfig[status].ring}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[28px] font-semibold text-neutral-900 tabular-nums">{Math.round(average)}</span>
        </div>
      </div>
      <span className={`text-[13px] font-medium mt-3 ${statusConfig[status].color}`}>
        {statusConfig[status].label}
      </span>
    </div>
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
        formula: 'Score = Randomized ÷ Target × 100',
        source: `${siteData.randomized || 0} patients randomized of ${siteData.target_enrollment || 0} target`,
        metrics: siteData.enrollment_metrics
      },
      dataQuality: {
        score: dqScore,
        formula: 'Score from eCRF data quality metrics',
        source: `Open queries: ${openQueries}, Query rate: ${queryRate.toFixed(1)} per subject`,
        metrics: siteData.data_quality_metrics
      },
      monitoring: {
        score: monitoringScore,
        formula: 'Score = 100 − (Critical findings × 20) − (Overdue days × 2)',
        source: `100 − (${recentCritical} × 20) − (${visits[0]?.days_overdue || 0} × 2) = ${monitoringScore}`,
        metrics: [
          { label: 'Recent Visits', value: `${visits.length}`, note: 'Last 90 days' },
          { label: 'Critical Findings', value: `${visits.reduce((a, v) => a + (v.critical_findings || 0), 0)}` },
          { label: 'Avg Findings/Visit', value: visits.length > 0 ? (visits.reduce((a, v) => a + (v.findings_count || 0), 0) / visits.length).toFixed(1) : '0' },
          { label: 'Overdue Days', value: `${visits[0]?.days_overdue || 0}d` }
        ]
      },
      integrity: {
        score: integrityScore,
        formula: 'Query rate > 5 → 50 (High risk) | > 3 → 70 (Medium) | ≤ 3 → 90 (Low)',
        source: `Query rate ${queryRate.toFixed(1)} per subject → Score ${integrityScore}`,
        metrics: [
          { label: 'Query Rate', value: queryRate.toFixed(1), note: 'per subject' },
          { label: 'Risk Level', value: integrityScore >= 80 ? 'Low' : integrityScore >= 60 ? 'Medium' : 'High' }
        ]
      },
      operations: {
        score: operationsScore,
        formula: hasActiveCRA 
          ? 'Score = 100 − (CRA transitions × 10), min 60' 
          : 'No active CRA = 40',
        source: hasActiveCRA 
          ? `100 − (${Math.max(0, craChanges - 1)} × 10) = ${operationsScore}` 
          : 'No active CRA assigned',
        metrics: [
          { label: 'Active CRA', value: hasActiveCRA ? 'Yes' : 'No' },
          { label: 'CRA Transitions', value: `${Math.max(0, craChanges - 1)}`, note: 'Since site activation' }
        ]
      }
    }
  }, [siteData, metadata])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 rounded-full border-2 border-neutral-200 border-t-neutral-600 animate-spin" />
          <span className="text-[13px] text-neutral-500">Loading site profile</span>
        </div>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-full overflow-y-auto bg-white"
    >
      <div className="max-w-4xl mx-auto px-6 py-10">
        {/* Header */}
        <div className="text-center mb-10">
          <motion.h1 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-[28px] font-semibold text-neutral-900 tracking-tight"
          >
            {siteName || siteId}
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="text-[15px] text-neutral-500 mt-1"
          >
            {siteData?.country}{siteData?.city ? ` · ${siteData.city}` : ''}
          </motion.p>
        </div>

        {/* Signal Banner */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-neutral-50 rounded-2xl p-5 mb-10"
        >
          <div className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider mb-2">
            Signal Under Investigation
          </div>
          <p className="text-[15px] text-neutral-900 leading-relaxed">{question}</p>
        </motion.div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 mb-10">
          {/* Left: Health + Radar */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="flex flex-col items-center"
          >
            <HealthScore dimensions={dimensions} />
            <div className="mt-6">
              <RadarChart dimensions={dimensions} />
            </div>
          </motion.div>

          {/* Right: Dimensions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <div className="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider mb-4">
              Performance by Dimension
            </div>
            <div className="bg-white rounded-xl border border-neutral-200">
              {Object.entries(dimensions).map(([key, data]) => (
                <DimensionRow
                  key={key}
                  dimension={key}
                  data={data}
                  isExpanded={expandedDimension === key}
                  onToggle={() => setExpandedDimension(expandedDimension === key ? null : key)}
                />
              ))}
            </div>
          </motion.div>
        </div>

        {/* Site Journey Timeline */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12 pt-8 border-t border-neutral-100"
        >
          <SiteJourneyMap 
            visits={metadata?.monitoring_visits} 
            craAssignments={metadata?.cra_assignments} 
          />
          <AlertsList alerts={siteData?.alerts} />
        </motion.div>

        {/* Launch Button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="flex justify-center"
        >
          <button
            onClick={onLaunchAnalysis}
            className="group inline-flex items-center gap-3 px-8 py-4 bg-neutral-900 hover:bg-neutral-800 text-white rounded-full text-[15px] font-medium transition-all shadow-lg hover:shadow-xl"
          >
            Launch Causal Analysis
            <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
          </button>
        </motion.div>
      </div>
    </motion.div>
  )
}
