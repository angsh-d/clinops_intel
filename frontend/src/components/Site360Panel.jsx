import { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { 
  Users, FileSearch, Shield, Calendar, Activity,
  ChevronRight, ArrowRight
} from 'lucide-react'
import { getSiteDetail, getSiteMetadata } from '../lib/api'

const DIMENSIONS = [
  { key: 'enrollment', label: 'Enrollment', icon: Users },
  { key: 'dataQuality', label: 'Data Quality', icon: FileSearch },
  { key: 'monitoring', label: 'Monitoring', icon: Calendar },
  { key: 'integrity', label: 'Integrity', icon: Shield },
  { key: 'operations', label: 'Operations', icon: Activity }
]

function CompactRadar({ dimensions, size = 200 }) {
  const center = size / 2
  const radius = (size / 2) - 30
  const numPoints = DIMENSIONS.length
  
  const points = useMemo(() => {
    return DIMENSIONS.map((dim, i) => {
      const angle = (Math.PI * 2 * i) / numPoints - Math.PI / 2
      const value = dimensions[dim.key]?.score || 0
      const normalizedValue = Math.min(100, Math.max(0, value)) / 100
      return {
        key: dim.key,
        label: dim.label,
        angle,
        x: center + Math.cos(angle) * radius * normalizedValue,
        y: center + Math.sin(angle) * radius * normalizedValue,
        labelX: center + Math.cos(angle) * (radius + 18),
        labelY: center + Math.sin(angle) * (radius + 18),
        gridX: center + Math.cos(angle) * radius,
        gridY: center + Math.sin(angle) * radius,
        score: value
      }
    })
  }, [dimensions, center, radius, numPoints])

  const pathData = points.map((p, i) => 
    `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`
  ).join(' ') + ' Z'

  return (
    <svg width={size} height={size} className="mx-auto">
      {[0.33, 0.66, 1].map(level => (
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
          strokeWidth="1"
          className="text-neutral-200"
        />
      ))}
      
      <motion.path
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        d={pathData}
        fill="rgba(0,0,0,0.04)"
        stroke="rgba(0,0,0,0.5)"
        strokeWidth="1.5"
      />
      
      {points.map((p, i) => (
        <g key={`label-${p.key}`}>
          <motion.circle
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2 + i * 0.05, duration: 0.2 }}
            cx={p.x}
            cy={p.y}
            r={4}
            className="fill-neutral-800"
          />
          <text
            x={p.labelX}
            y={p.labelY}
            textAnchor="middle"
            dominantBaseline="middle"
            className="text-[9px] fill-neutral-500"
          >
            {p.label}
          </text>
        </g>
      ))}
    </svg>
  )
}

function ScoreRing({ score, size = 100 }) {
  const status = score >= 75 ? 'good' : score >= 50 ? 'fair' : 'poor'
  const strokeColor = status === 'good' ? '#22c55e' : status === 'fair' ? '#f59e0b' : '#ef4444'
  const r = (size - 8) / 2
  const circumference = 2 * Math.PI * r

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size/2}
          cy={size/2}
          r={r}
          fill="none"
          stroke="#f5f5f5"
          strokeWidth="6"
        />
        <motion.circle
          cx={size/2}
          cy={size/2}
          r={r}
          fill="none"
          stroke={strokeColor}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference * (1 - score / 100) }}
          transition={{ duration: 1, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-semibold text-neutral-900">{Math.round(score)}</span>
      </div>
    </div>
  )
}

function DimensionRow({ dim, data }) {
  const Icon = dim.icon
  const score = data?.score || 0
  const status = score >= 75 ? 'good' : score >= 50 ? 'fair' : 'poor'
  
  return (
    <div className="flex items-center gap-4 py-3 border-b border-neutral-100 last:border-0">
      <Icon className="w-4 h-4 text-neutral-400" />
      <span className="flex-1 text-sm text-neutral-700">{dim.label}</span>
      <div className="flex items-center gap-2">
        <div className="w-24 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
          <motion.div 
            className={`h-full rounded-full ${
              status === 'good' ? 'bg-green-500' : 
              status === 'fair' ? 'bg-amber-500' : 'bg-red-500'
            }`}
            initial={{ width: 0 }}
            animate={{ width: `${score}%` }}
            transition={{ duration: 0.6, delay: 0.2 }}
          />
        </div>
        <span className="text-xs font-medium text-neutral-500 w-8 text-right">{Math.round(score)}</span>
      </div>
    </div>
  )
}

function MetricPill({ label, value, trend }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-neutral-50 rounded-lg">
      <span className="text-xs text-neutral-500">{label}</span>
      <span className="text-xs font-medium text-neutral-800">{value}</span>
      {trend && (
        <span className={`text-[10px] ${trend === 'up' ? 'text-red-500' : 'text-green-500'}`}>
          {trend === 'up' ? '↑' : '↓'}
        </span>
      )}
    </div>
  )
}

export function Site360Panel({ siteId, siteName, question, onLaunchAnalysis }) {
  const [loading, setLoading] = useState(true)
  const [siteData, setSiteData] = useState(null)
  const [metadata, setMetadata] = useState(null)

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
    const queryRate = parseFloat(siteData.data_quality_metrics?.find(m => m.label === 'Query Rate')?.value) || 0
    
    const visits = metadata?.monitoring_visits || []
    const recentCritical = visits.slice(0, 3).filter(v => v.critical_findings > 0).length
    const monitoringScore = visits.length > 0 
      ? Math.max(0, 100 - (recentCritical * 20) - (visits[0]?.days_overdue || 0) * 2)
      : 70
    
    const integrityScore = queryRate > 5 ? 50 : queryRate > 3 ? 70 : 90
    
    const cras = metadata?.cra_assignments || []
    const hasActiveCRA = cras.some(c => c.is_current)
    const operationsScore = hasActiveCRA 
      ? Math.max(60, 100 - (cras.length - 1) * 10)
      : 40

    return {
      enrollment: { score: enrollmentPct },
      dataQuality: { score: dqScore },
      monitoring: { score: monitoringScore },
      integrity: { score: integrityScore },
      operations: { score: operationsScore }
    }
  }, [siteData, metadata])

  const overallScore = useMemo(() => {
    const scores = Object.values(dimensions).map(d => d?.score || 0)
    return scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0
  }, [dimensions])

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-neutral-200 border-t-neutral-600 animate-spin" />
          <span className="text-sm text-neutral-500">Loading site profile...</span>
        </div>
      </div>
    )
  }

  const visits = metadata?.monitoring_visits || []
  const currentCRA = metadata?.cra_assignments?.find(a => a.is_current)
  const alertCount = siteData?.alerts?.length || 0

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 overflow-hidden">
        <div className="h-full max-w-4xl mx-auto px-6 py-6 flex flex-col">
          
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-6"
          >
            <h2 className="text-xl font-semibold text-neutral-900 mb-1">{siteName || siteId}</h2>
            <p className="text-sm text-neutral-500">
              {siteData?.country}{siteData?.city ? ` · ${siteData.city}` : ''}
            </p>
          </motion.div>

          <div className="flex-1 grid grid-cols-2 gap-6 min-h-0">
            
            <motion.div 
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-white rounded-2xl border border-neutral-200 p-5 flex flex-col"
            >
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-xs text-neutral-500 uppercase tracking-wide mb-1">Health Score</div>
                  <div className="text-3xl font-semibold text-neutral-900">{Math.round(overallScore)}</div>
                </div>
                <ScoreRing score={overallScore} size={80} />
              </div>
              
              <div className="flex-1 flex items-center justify-center">
                <CompactRadar dimensions={dimensions} size={180} />
              </div>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.15 }}
              className="bg-white rounded-2xl border border-neutral-200 p-5 flex flex-col"
            >
              <div className="text-xs text-neutral-500 uppercase tracking-wide mb-3">Dimensions</div>
              <div className="flex-1">
                {DIMENSIONS.map(dim => (
                  <DimensionRow key={dim.key} dim={dim} data={dimensions[dim.key]} />
                ))}
              </div>
            </motion.div>
          </div>

          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="flex items-center gap-3 mt-5 flex-wrap"
          >
            <MetricPill 
              label="CRA" 
              value={currentCRA ? currentCRA.cra_id : 'Unassigned'} 
            />
            <MetricPill 
              label="Visits (90d)" 
              value={visits.length.toString()} 
            />
            <MetricPill 
              label="Entry Lag" 
              value={siteData?.data_quality_metrics?.find(m => m.label === 'Entry Lag')?.value || '—'} 
            />
            <MetricPill 
              label="Open Queries" 
              value={siteData?.data_quality_metrics?.find(m => m.label === 'Open Queries')?.value || '0'} 
            />
            {alertCount > 0 && (
              <div className="flex items-center gap-2 px-3 py-2 bg-red-50 rounded-lg">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
                <span className="text-xs font-medium text-red-700">{alertCount} active signal{alertCount !== 1 ? 's' : ''}</span>
              </div>
            )}
          </motion.div>

        </div>
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="border-t border-neutral-200 bg-neutral-50 px-6 py-4"
      >
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex-1 pr-6">
            <div className="text-xs text-neutral-500 mb-1">Signal Under Investigation</div>
            <p className="text-sm text-neutral-800 line-clamp-1">{question}</p>
          </div>
          <button
            onClick={onLaunchAnalysis}
            className="flex items-center gap-2 px-6 py-3 bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium rounded-full transition-colors"
          >
            Launch Causal Analysis
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </motion.div>
    </div>
  )
}
