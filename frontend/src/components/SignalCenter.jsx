import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Bell, Check, X, ChevronDown, Clock } from 'lucide-react'
import { useStore } from '../lib/store'
import { getAlerts, acknowledgeAlert, suppressAlert, getScans } from '../lib/api'
import { StudyNav } from './StudyNav'

const SEVERITY_ORDER = { critical: 0, high: 1, warning: 2, info: 3 }
const SEVERITY_DOT = {
  critical: 'bg-red-500',
  high: 'bg-amber-500',
  warning: 'bg-yellow-500',
  info: 'bg-blue-400',
}
const SEVERITY_BADGE = {
  critical: 'bg-red-50 text-red-700 border-red-200',
  high: 'bg-amber-50 text-amber-700 border-amber-200',
  warning: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  info: 'bg-blue-50 text-blue-600 border-blue-200',
}

const AGENT_LABELS = {
  data_quality: 'Data Quality',
  enrollment_funnel: 'Enrollment',
  clinical_trials_gov: 'Competitive Intel',
  phantom_compliance: 'Data Integrity',
  site_rescue: 'Site Decision',
  vendor_performance: 'Vendor',
  financial_intelligence: 'Financial',
}

export function SignalCenter() {
  const navigate = useNavigate()
  const { currentStudyId, setInvestigation } = useStore()
  const [alerts, setAlertsData] = useState([])
  const [totalAlerts, setTotalAlerts] = useState(0)
  const [scans, setScansData] = useState([])
  const [loading, setLoading] = useState(true)

  // Filters
  const [severityFilter, setSeverityFilter] = useState(new Set(['critical', 'high', 'warning']))
  const [statusFilter, setStatusFilter] = useState('active')
  const [selectedAlerts, setSelectedAlerts] = useState(new Set())
  const [suppressModal, setSuppressModal] = useState(null)

  useEffect(() => {
    async function fetchData() {
      try {
        const [alertsR, scansR] = await Promise.all([
          getAlerts({ limit: 100 }),
          getScans(10),
        ])
        if (alertsR?.alerts) {
          setAlertsData(alertsR.alerts)
          setTotalAlerts(alertsR.total)
        }
        if (Array.isArray(scansR)) setScansData(scansR)
      } catch (error) {
        console.error('SignalCenter fetch error:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const filteredAlerts = useMemo(() => {
    return alerts
      .filter(a => severityFilter.has(a.severity))
      .filter(a => {
        if (statusFilter === 'active') return a.status === 'active'
        if (statusFilter === 'acknowledged') return a.status === 'acknowledged'
        return true
      })
      .sort((a, b) => {
        const sevDiff = (SEVERITY_ORDER[a.severity] || 9) - (SEVERITY_ORDER[b.severity] || 9)
        if (sevDiff !== 0) return sevDiff
        return new Date(b.created_at) - new Date(a.created_at)
      })
  }, [alerts, severityFilter, statusFilter])

  const severityCounts = useMemo(() => {
    const counts = { critical: 0, high: 0, warning: 0, info: 0 }
    alerts.forEach(a => { counts[a.severity] = (counts[a.severity] || 0) + 1 })
    return counts
  }, [alerts])

  const toggleSeverity = (sev) => {
    setSeverityFilter(prev => {
      const next = new Set(prev)
      if (next.has(sev)) next.delete(sev)
      else next.add(sev)
      return next
    })
  }

  const toggleSelect = (id) => {
    setSelectedAlerts(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleAcknowledgeSelected = async () => {
    const ids = [...selectedAlerts]
    const results = await Promise.allSettled(ids.map(id => acknowledgeAlert(id)))
    const succeededIds = new Set()
    results.forEach((r, i) => {
      if (r.status === 'fulfilled') succeededIds.add(ids[i])
      else console.error('Acknowledge error:', r.reason)
    })
    setAlertsData(prev => prev.map(a => succeededIds.has(a.id) ? { ...a, status: 'acknowledged' } : a))
    setSelectedAlerts(new Set())
  }

  const handleSuppress = async (alertId, reason) => {
    try {
      await suppressAlert(alertId, { reason })
      setAlertsData(prev => prev.map(a => a.id === alertId ? { ...a, status: 'suppressed' } : a))
      setSuppressModal(null)
    } catch (error) {
      console.error('Suppress error:', error)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-apple-bg">
        <StudyNav active="signals" />
        <div className="flex items-center justify-center h-64">
          <div className="flex items-center gap-3 text-apple-secondary">
            <div className="w-5 h-5 border-2 border-apple-secondary/30 border-t-apple-secondary rounded-full animate-spin" />
            <span className="text-body">Loading Signal Center...</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-apple-bg">
      <StudyNav active="signals" />

      <div className="max-w-7xl mx-auto px-6 py-8 flex gap-6">
        {/* Signal Feed (2/3) */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-medium text-apple-text">Signal Feed</h2>
            <div className="flex items-center gap-3">
              {/* Status toggle */}
              <div className="flex items-center bg-apple-surface border border-apple-border rounded-lg overflow-hidden">
                {['active', 'acknowledged', 'all'].map(s => (
                  <button
                    key={s}
                    onClick={() => setStatusFilter(s)}
                    className={`px-3 py-1.5 text-caption capitalize transition-colors ${
                      statusFilter === s ? 'bg-apple-text text-white' : 'text-apple-secondary hover:text-apple-text'
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
              {selectedAlerts.size > 0 && (
                <button
                  onClick={handleAcknowledgeSelected}
                  className="px-3 py-1.5 bg-green-50 border border-green-200 rounded-lg text-caption text-green-700 hover:bg-green-100 transition-colors"
                >
                  Acknowledge ({selectedAlerts.size})
                </button>
              )}
            </div>
          </div>

          {/* Alert list */}
          <div className="space-y-2">
            {filteredAlerts.length === 0 && (
              <div className="text-center py-12 text-apple-secondary text-caption">No signals match your filters</div>
            )}
            {filteredAlerts.map(alert => (
              <motion.div
                key={alert.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                className={`p-4 bg-apple-surface border border-apple-border rounded-xl hover:border-apple-text/20 transition-all ${
                  alert.status === 'acknowledged' ? 'opacity-60' : ''
                }`}
              >
                <div className="flex items-start gap-3">
                  {/* Select checkbox */}
                  <button
                    onClick={() => toggleSelect(alert.id)}
                    className={`mt-1 w-4 h-4 rounded border transition-colors flex-shrink-0 ${
                      selectedAlerts.has(alert.id)
                        ? 'bg-apple-text border-apple-text'
                        : 'border-apple-border hover:border-apple-text/40'
                    }`}
                  >
                    {selectedAlerts.has(alert.id) && <Check className="w-3 h-3 text-white mx-auto" />}
                  </button>

                  {/* Severity dot */}
                  <div className={`mt-2 w-2.5 h-2.5 rounded-full flex-shrink-0 ${SEVERITY_DOT[alert.severity] || SEVERITY_DOT.info}`} />

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className="text-[11px] text-apple-secondary">{timeAgo(alert.created_at)}</span>
                      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${SEVERITY_BADGE[alert.severity] || SEVERITY_BADGE.info}`}>
                        {alert.severity}
                      </span>
                      {alert.agent_id && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-50 text-purple-600 border border-purple-200/50">
                          {AGENT_LABELS[alert.agent_id] || alert.agent_id}
                        </span>
                      )}
                    </div>
                    <p className="text-caption text-apple-text leading-relaxed">{alert.summary || alert.message}</p>
                    {alert.site_id && (
                      <button
                        onClick={() => navigate(`/study/${currentStudyId}/sites/${alert.site_id}`)}
                        className="text-[11px] font-mono text-apple-accent hover:underline mt-1"
                      >
                        {alert.site_id}
                      </button>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {alert.status !== 'acknowledged' && (
                      <button
                        onClick={async () => {
                          await acknowledgeAlert(alert.id)
                          setAlertsData(prev => prev.map(a => a.id === alert.id ? { ...a, status: 'acknowledged' } : a))
                        }}
                        className="p-1.5 rounded-lg hover:bg-green-50 text-apple-secondary hover:text-green-600 transition-colors"
                        title="Acknowledge"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                    )}
                    <button
                      onClick={() => setSuppressModal(alert.id)}
                      className="p-1.5 rounded-lg hover:bg-red-50 text-apple-secondary hover:text-red-500 transition-colors"
                      title="Suppress"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => setInvestigation({ question: alert.summary || alert.message, status: 'routing' })}
                      className="p-1.5 rounded-lg hover:bg-blue-50 text-apple-secondary hover:text-blue-600 transition-colors text-[11px] font-medium"
                      title="Investigate"
                    >
                      Investigate
                    </button>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Filters sidebar (1/3) */}
        <div className="w-64 flex-shrink-0 space-y-6">
          {/* Severity filters */}
          <div>
            <h4 className="text-[12px] font-medium text-apple-secondary uppercase tracking-wide mb-3">Severity</h4>
            <div className="space-y-2">
              {['critical', 'high', 'warning', 'info'].map(sev => (
                <button
                  key={sev}
                  onClick={() => toggleSeverity(sev)}
                  className="w-full flex items-center gap-2.5 text-caption py-1"
                >
                  <div className={`w-3.5 h-3.5 rounded border transition-colors ${
                    severityFilter.has(sev) ? 'bg-apple-text border-apple-text' : 'border-apple-border'
                  }`}>
                    {severityFilter.has(sev) && <Check className="w-2.5 h-2.5 text-white mx-auto" />}
                  </div>
                  <div className={`w-2 h-2 rounded-full ${SEVERITY_DOT[sev]}`} />
                  <span className="capitalize text-apple-text flex-1 text-left">{sev}</span>
                  <span className="text-apple-secondary font-mono text-[11px]">({severityCounts[sev]})</span>
                </button>
              ))}
            </div>
          </div>

          {/* Scan history */}
          <div>
            <h4 className="text-[12px] font-medium text-apple-secondary uppercase tracking-wide mb-3">Scan History</h4>
            <div className="space-y-2">
              {scans.slice(0, 5).map(scan => (
                <div key={scan.scan_id} className="flex items-center gap-2 text-caption">
                  <div className={`w-2 h-2 rounded-full ${scan.status === 'completed' ? 'bg-green-500' : scan.status === 'running' ? 'bg-blue-500 animate-pulse' : 'bg-amber-500'}`} />
                  <span className="text-apple-secondary flex-1">{timeAgo(scan.created_at)}</span>
                  <span className="text-[10px] text-apple-secondary">{scan.status === 'completed' ? '\u2713' : scan.status}</span>
                </div>
              ))}
              {scans.length === 0 && (
                <p className="text-caption text-apple-secondary">No scans yet</p>
              )}
            </div>
          </div>

          {/* Total */}
          <div className="p-3 bg-apple-surface rounded-xl border border-apple-border">
            <p className="text-caption text-apple-secondary">Total Alerts</p>
            <p className="text-lg font-mono font-medium text-apple-text">{totalAlerts}</p>
          </div>
        </div>
      </div>

      {/* Suppress Modal */}
      <AnimatePresence>
        {suppressModal && (
          <SuppressModal
            alertId={suppressModal}
            onSuppress={handleSuppress}
            onClose={() => setSuppressModal(null)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}


function SuppressModal({ alertId, onSuppress, onClose }) {
  const [reason, setReason] = useState('')

  return (
    <>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/30 z-50" onClick={onClose}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}
        className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-apple-surface rounded-2xl shadow-apple-lg border border-apple-border p-6 z-50"
      >
        <h3 className="text-body font-medium text-apple-text mb-3">Suppress Alert</h3>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Reason for suppression..."
          className="w-full h-24 px-3 py-2 bg-apple-bg border border-apple-border rounded-xl text-caption text-apple-text placeholder:text-apple-secondary/50 outline-none resize-none"
        />
        <div className="flex items-center gap-3 mt-4 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-caption text-apple-secondary hover:text-apple-text transition-colors">Cancel</button>
          <button
            onClick={() => onSuppress(alertId, reason || 'No reason provided')}
            className="px-4 py-2 bg-red-50 border border-red-200 text-red-700 text-caption font-medium rounded-xl hover:bg-red-100 transition-colors"
          >
            Suppress
          </button>
        </div>
      </motion.div>
    </>
  )
}

function timeAgo(isoStr) {
  if (!isoStr) return ''
  const delta = Date.now() - new Date(isoStr).getTime()
  const mins = Math.floor(delta / 60_000)
  const hours = Math.floor(delta / 3_600_000)
  const days = Math.floor(delta / 86_400_000)
  if (days > 0) return `${days}d ago`
  if (hours > 0) return `${hours}h ago`
  if (mins > 0) return `${mins}m ago`
  return 'Just now'
}
