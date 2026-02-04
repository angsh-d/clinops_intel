import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Search, Clock, ChevronRight } from 'lucide-react'
import { useStore } from '../lib/store'
import { getAgentFindings } from '../lib/api'
import { StudyNav } from './StudyNav'

const AGENT_LABELS = {
  data_quality: 'Data Quality',
  enrollment_funnel: 'Enrollment',
  clinical_trials_gov: 'Competitive Intel',
  phantom_compliance: 'Data Integrity',
  site_rescue: 'Site Decision',
  vendor_performance: 'Vendor',
  financial_intelligence: 'Financial',
}

const SEVERITY_BADGE = {
  critical: 'bg-red-50 text-red-700 border-red-200',
  high: 'bg-amber-50 text-amber-700 border-amber-200',
  warning: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  info: 'bg-blue-50 text-blue-600 border-blue-200',
}

export function InvestigationArchive() {
  const navigate = useNavigate()
  const { currentStudyId, siteNameMap } = useStore()
  const [findings, setFindings] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [agentFilter, setAgentFilter] = useState(null)

  useEffect(() => {
    async function fetchAll() {
      try {
        // Fetch findings from all agents
        const agentIds = Object.keys(AGENT_LABELS)
        const results = await Promise.allSettled(
          agentIds.map(id => getAgentFindings(id, 50))
        )
        const allFindings = []
        results.forEach((r, i) => {
          if (r.status === 'fulfilled' && Array.isArray(r.value)) {
            r.value.forEach(f => allFindings.push({ ...f, agent_id: agentIds[i] }))
          }
        })
        // Sort by date descending
        allFindings.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        setFindings(allFindings)
      } catch (error) {
        console.error('Archive fetch error:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchAll()
  }, [])

  const filtered = findings.filter(f => {
    if (agentFilter && f.agent_id !== agentFilter) return false
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      const summary = (f.summary || '').toLowerCase()
      const siteId = (f.site_id || '').toLowerCase()
      return summary.includes(q) || siteId.includes(q)
    }
    return true
  })

  function timeAgo(isoStr) {
    if (!isoStr) return ''
    const delta = Date.now() - new Date(isoStr).getTime()
    const hours = Math.floor(delta / 3_600_000)
    const days = Math.floor(delta / 86_400_000)
    if (days > 0) return `${days}d ago`
    if (hours > 0) return `${hours}h ago`
    return 'Just now'
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-apple-bg">
        <StudyNav active="history" />
        <div className="flex items-center justify-center h-64">
          <div className="flex items-center gap-3 text-apple-secondary">
            <div className="w-5 h-5 border-2 border-apple-secondary/30 border-t-apple-secondary rounded-full animate-spin" />
            <span className="text-body">Loading Investigation Archive...</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-apple-bg">
      <StudyNav active="history" />

      <main className="max-w-4xl mx-auto px-6 py-8">
        <h2 className="text-xl font-medium text-apple-text mb-6">Investigation Archive</h2>

        {/* Search + filters */}
        <div className="flex items-center gap-3 mb-6">
          <div className="flex-1 flex items-center gap-2 bg-apple-surface border border-apple-border rounded-xl px-3 py-2">
            <Search className="w-4 h-4 text-apple-secondary" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search findings..."
              className="flex-1 bg-transparent text-caption text-apple-text placeholder:text-apple-secondary/50 outline-none"
            />
          </div>
          <div className="flex items-center gap-1 bg-apple-surface border border-apple-border rounded-xl overflow-hidden">
            <button
              onClick={() => setAgentFilter(null)}
              className={`px-3 py-2 text-caption transition-colors ${
                !agentFilter ? 'bg-apple-text text-white' : 'text-apple-secondary hover:text-apple-text'
              }`}
            >
              All
            </button>
            {Object.entries(AGENT_LABELS).map(([id, label]) => (
              <button
                key={id}
                onClick={() => setAgentFilter(agentFilter === id ? null : id)}
                className={`px-2 py-2 text-[11px] transition-colors ${
                  agentFilter === id ? 'bg-apple-text text-white' : 'text-apple-secondary hover:text-apple-text'
                }`}
              >
                {label.split(' ')[0]}
              </button>
            ))}
          </div>
        </div>

        {/* Results count */}
        <p className="text-caption text-apple-secondary mb-4">{filtered.length} findings</p>

        {/* Findings list */}
        <div className="space-y-2">
          {filtered.map((f, i) => (
            <motion.div
              key={f.id || i}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(i * 0.02, 0.3) }}
              className="bg-apple-surface border border-apple-border rounded-xl p-4 hover:border-apple-text/20 transition-all"
            >
              <div className="flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1.5">
                    <span className="text-[11px] text-apple-secondary flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {timeAgo(f.created_at)}
                    </span>
                    {f.severity && (
                      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${SEVERITY_BADGE[f.severity] || SEVERITY_BADGE.info}`}>
                        {f.severity}
                      </span>
                    )}
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-50 text-purple-600 border border-purple-200/50">
                      {AGENT_LABELS[f.agent_id] || f.agent_id}
                    </span>
                    {f.site_id && (
                      <button
                        onClick={() => navigate(`/study/${currentStudyId}/sites/${f.site_id}`)}
                        className="text-[10px] font-mono text-apple-accent hover:underline"
                      >
                        {siteNameMap[f.site_id] || f.site_id}
                      </button>
                    )}
                  </div>
                  <p className="text-caption text-apple-text leading-relaxed">{f.summary}</p>
                  {f.root_cause && (
                    <p className="text-[11px] text-apple-secondary mt-1">
                      <span className="font-medium text-apple-text">Root cause:</span> {f.root_cause}
                    </p>
                  )}
                </div>
              </div>
            </motion.div>
          ))}

          {filtered.length === 0 && (
            <div className="text-center py-12 text-apple-secondary text-caption">
              No findings match your search
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
