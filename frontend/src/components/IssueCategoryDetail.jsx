import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowLeft, TrendingUp, TrendingDown, Minus, MapPin,
  Loader2, ChevronRight, Sparkles
} from 'lucide-react'
import { getIssueCategoryDetail } from '../lib/api'

const ease = [0.25, 0.46, 0.45, 0.94]

const TREND_MAP = {
  improving: { icon: TrendingUp, color: 'text-apple-success', bgColor: 'bg-apple-success/10', label: 'Improving' },
  stable: { icon: Minus, color: 'text-apple-grey-500', bgColor: 'bg-apple-grey-100', label: 'Stable' },
  deteriorating: { icon: TrendingDown, color: 'text-apple-critical', bgColor: 'bg-apple-critical/10', label: 'At Risk' },
}

const DIMENSION_LABELS = {
  data_quality: 'Data Quality',
  enrollment: 'Enrollment',
  compliance: 'Compliance',
  operational: 'Operational',
  integrity: 'Integrity',
}

function dimensionBarColor(v) {
  if (v > 0.6) return 'bg-apple-grey-800'
  if (v > 0.3) return 'bg-apple-grey-500'
  return 'bg-apple-grey-300'
}

function severityDot(severity) {
  return severity === 'critical' ? 'bg-apple-grey-800' : 'bg-apple-grey-500'
}

function statusDot(status) {
  return status === 'critical' ? 'bg-apple-grey-800' : status === 'warning' ? 'bg-apple-grey-500' : 'bg-apple-grey-300'
}

function priorityStyle(priority) {
  return priority === 'immediate'
    ? 'bg-apple-grey-800 text-white'
    : priority === 'short_term'
      ? 'bg-apple-grey-200 text-apple-grey-700'
      : 'bg-apple-grey-100 text-apple-tertiary'
}

/* ── Skeleton shimmer for premium loading state ─────────────────────────── */
function Skeleton({ className }) {
  return <div className={`animate-pulse rounded-lg bg-apple-grey-200/60 ${className}`} />
}

function LoadingSkeleton({ studyId, navigate }) {
  return (
    <div className="min-h-screen bg-apple-bg">
      <header className="sticky top-0 z-50 bg-apple-surface/80 backdrop-blur-xl border-b border-apple-divider">
        <div className="max-w-5xl mx-auto px-6 py-3 flex items-center gap-4">
          <button onClick={() => navigate(`/study/${studyId}`)} className="button-icon">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="h-5 w-px bg-apple-divider" />
          <Skeleton className="h-5 w-48" />
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-6 py-5 space-y-5">
        {/* Context card skeleton */}
        <div className="bg-white rounded-2xl p-4 shadow-apple-sm border border-apple-grey-100">
          <Skeleton className="h-4 w-full mb-2" />
          <Skeleton className="h-4 w-3/4 mb-3" />
          <div className="flex gap-2">
            <Skeleton className="h-5 w-20 rounded-full" />
            <Skeleton className="h-5 w-24 rounded-full" />
            <Skeleton className="h-5 w-28 rounded-full" />
          </div>
        </div>
        {/* Analysis skeleton */}
        <div className="bg-white rounded-2xl p-4 shadow-apple-sm border border-apple-grey-100">
          <div className="flex items-center gap-2 mb-3">
            <Skeleton className="h-4 w-4 rounded" />
            <Skeleton className="h-4 w-36" />
          </div>
          <Skeleton className="h-4 w-full mb-2" />
          <Skeleton className="h-4 w-5/6" />
        </div>
        {/* Sites grid skeleton */}
        <div>
          <Skeleton className="h-3 w-28 mb-3" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[0, 1, 2, 3].map(i => (
              <div key={i} className="bg-white rounded-2xl p-4 shadow-apple-sm border border-apple-grey-100">
                <Skeleton className="h-5 w-40 mb-2" />
                <Skeleton className="h-3 w-28 mb-3" />
                <Skeleton className="h-8 w-16 mb-3" />
                <div className="space-y-1.5">
                  <Skeleton className="h-1.5 w-full rounded-full" />
                  <Skeleton className="h-1.5 w-full rounded-full" />
                  <Skeleton className="h-1.5 w-full rounded-full" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}


export function IssueCategoryDetail() {
  const navigate = useNavigate()
  const { studyId, categoryIndex } = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    getIssueCategoryDetail(categoryIndex)
      .then(d => { if (!cancelled) setData(d) })
      .catch(e => { if (!cancelled) setError(e.message) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [categoryIndex])

  if (loading) return <LoadingSkeleton studyId={studyId} navigate={navigate} />

  if (error || !data) {
    return (
      <div className="min-h-screen bg-apple-bg">
        <header className="sticky top-0 z-50 bg-apple-surface/80 backdrop-blur-xl border-b border-apple-divider">
          <div className="max-w-5xl mx-auto px-6 py-3 flex items-center gap-4">
            <button onClick={() => navigate(`/study/${studyId}`)} className="button-icon">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="h-5 w-px bg-apple-divider" />
            <span className="text-body text-apple-secondary">Category not found</span>
          </div>
        </header>
        <div className="flex items-center justify-center h-64">
          <p className="text-caption text-apple-secondary">{error || 'Category not found'}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-apple-bg">
      {/* ── Frosted Header ───────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 bg-apple-surface/80 backdrop-blur-xl border-b border-apple-divider">
        <div className="max-w-5xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate(`/study/${studyId}`)} className="button-icon">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="h-5 w-px bg-apple-divider" />
            <span className="text-body font-semibold text-apple-text">{data.theme}</span>
          </div>
          <div className="flex items-center gap-3">
            <div className={`w-1.5 h-1.5 rounded-full ${severityDot(data.severity)}`} />
            <span className="text-caption text-apple-tertiary">{data.site_count} sites</span>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-5">
        {/* ── Context ────────────────────────────────────────────────────── */}
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.05, ease }}
          className="mb-5"
        >
          <div className="bg-white rounded-2xl p-4 shadow-apple-sm border border-apple-grey-100">
            <p className="text-[13px] text-apple-secondary leading-relaxed mb-3">{data.description}</p>
            <div className="flex flex-wrap items-center gap-2">
              {data.primary_dimension && (
                <span className="text-[10px] font-mono font-medium px-2.5 py-1 rounded-full bg-apple-grey-100 text-apple-grey-600">
                  {data.primary_dimension}
                </span>
              )}
              {data.key_drivers.map((d, i) => (
                <span key={i} className="text-[10px] px-2.5 py-1 rounded-full bg-apple-grey-50 text-apple-secondary border border-apple-grey-100">
                  {d}
                </span>
              ))}
            </div>
          </div>
        </motion.section>

        {/* ── Root Cause Analysis ─────────────────────────────────────────── */}
        {data.root_cause_analysis && (
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1, ease }}
            className="mb-5"
          >
            <div className="bg-white rounded-2xl shadow-apple-sm border border-apple-grey-100 overflow-hidden">
              <div className="p-4 bg-gradient-to-b from-apple-grey-50/50 to-white">
                <div className="flex items-center gap-2 mb-2.5">
                  <div className="w-7 h-7 rounded-lg bg-apple-ai-start/10 flex items-center justify-center">
                    <Sparkles className="w-3.5 h-3.5 text-apple-ai-start" />
                  </div>
                  <h2 className="text-[13px] font-semibold text-apple-text">Root Cause Analysis</h2>
                </div>
                <p className="text-[13px] text-apple-secondary leading-[1.7]">{data.root_cause_analysis}</p>
              </div>
            </div>
          </motion.section>
        )}

        {/* ── Cross-Site Patterns ──────────────────────────────────────────── */}
        {data.cross_site_patterns?.length > 0 && (
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.15, ease }}
            className="mb-5"
          >
            <h2 className="text-[11px] font-semibold uppercase tracking-wider text-apple-tertiary mb-3">Cross-Site Patterns</h2>
            <div className="bg-white rounded-2xl shadow-apple-sm border border-apple-grey-100 divide-y divide-apple-grey-100">
              {data.cross_site_patterns.map((p, i) => (
                <div key={i} className="px-4 py-3">
                  <div className="flex items-start gap-2.5">
                    <div className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${severityDot(p.severity)}`} />
                    <div className="flex-1">
                      <p className="text-[12px] font-medium text-apple-text leading-relaxed">{p.pattern}</p>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {p.sites.map(sid => (
                          <button
                            key={sid}
                            onClick={() => navigate(`/study/${studyId}/site/${sid}`)}
                            className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-apple-grey-50 text-apple-tertiary hover:bg-apple-grey-200 hover:text-apple-text transition-all duration-150"
                          >
                            {sid}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.section>
        )}

        {/* ── Affected Sites ──────────────────────────────────────────────── */}
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2, ease }}
          className="mb-5"
        >
          <h2 className="text-[11px] font-semibold uppercase tracking-wider text-apple-tertiary mb-3">Affected Sites</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {data.affected_sites.map((site) => {
              const trendInfo = TREND_MAP[site.trend] || TREND_MAP.stable
              const TrendIcon = trendInfo.icon
              return (
                <button
                  key={site.site_id}
                  onClick={() => navigate(`/study/${studyId}/site/${site.site_id}`)}
                  className="bg-white rounded-2xl p-4 shadow-apple-sm border border-apple-grey-100 text-left hover:shadow-apple-md transition-shadow duration-200 group"
                >
                  {/* Header row */}
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2.5">
                      <div className={`w-2 h-2 rounded-full ${statusDot(site.status)}`} />
                      <span className="text-[14px] font-semibold text-apple-text">{site.site_name || site.site_id}</span>
                    </div>
                    <ChevronRight className="w-4 h-4 text-apple-grey-300 group-hover:text-apple-grey-500 transition-colors" />
                  </div>

                  {/* Location */}
                  {(site.country || site.city) && (
                    <div className="flex items-center gap-1.5 text-[11px] text-apple-muted ml-[18px] mb-2.5">
                      <MapPin className="w-3 h-3" />
                      <span>{site.country}{site.city ? ` · ${site.city}` : ''}</span>
                    </div>
                  )}

                  {/* Risk score + trend */}
                  <div className="flex items-end justify-between mb-2.5">
                    <div>
                      <span className="text-[28px] font-light text-apple-text tracking-tight leading-none">
                        {(site.risk_score * 100).toFixed(0)}
                      </span>
                      <span className="text-[11px] text-apple-muted ml-1">risk score</span>
                    </div>
                    <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full ${trendInfo.bgColor}`}>
                      <TrendIcon className={`w-3 h-3 ${trendInfo.color}`} />
                      <span className={`text-[10px] font-medium ${trendInfo.color}`}>{trendInfo.label}</span>
                    </div>
                  </div>

                  {/* Dimension scores */}
                  {Object.keys(site.dimension_scores || {}).length > 0 && (
                    <div className="space-y-1.5 mb-2.5 pt-2.5 border-t border-apple-grey-100">
                      {Object.entries(DIMENSION_LABELS).map(([key, label]) => {
                        const val = site.dimension_scores[key]
                        if (val == null) return null
                        return (
                          <div key={key} className="flex items-center gap-2.5">
                            <span className="text-[10px] text-apple-tertiary w-[76px] text-right flex-shrink-0">{label}</span>
                            <div className="flex-1 h-[3px] bg-apple-grey-100 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all ${dimensionBarColor(val)}`}
                                style={{ width: `${Math.min(val * 100, 100)}%` }}
                              />
                            </div>
                            <span className="text-[9px] font-mono text-apple-muted w-7 text-right flex-shrink-0">{(val * 100).toFixed(0)}</span>
                          </div>
                        )
                      })}
                    </div>
                  )}

                  {/* Key drivers */}
                  {site.key_drivers?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {site.key_drivers.slice(0, 3).map((d, i) => (
                        <span key={i} className="text-[9px] px-2 py-0.5 rounded-full bg-apple-grey-50 text-apple-tertiary border border-apple-grey-100">
                          {d}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Status rationale */}
                  {site.status_rationale && (
                    <p className="text-[11px] text-apple-muted leading-relaxed line-clamp-2">{site.status_rationale}</p>
                  )}
                </button>
              )
            })}
          </div>
        </motion.section>

        {/* ── Prioritized Actions ──────────────────────────────────────────── */}
        {data.prioritized_actions?.length > 0 && (
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.25, ease }}
            className="mb-5"
          >
            <h2 className="text-[11px] font-semibold uppercase tracking-wider text-apple-tertiary mb-3">Prioritized Actions</h2>
            <div className="bg-white rounded-2xl shadow-apple-sm border border-apple-grey-100 divide-y divide-apple-grey-100">
              {data.prioritized_actions.map((a, i) => (
                <div key={i} className="px-4 py-3">
                  <div className="flex items-start gap-3">
                    <span className="w-6 h-6 rounded-md bg-apple-grey-900 text-[11px] font-semibold text-white flex items-center justify-center flex-shrink-0">
                      {i + 1}
                    </span>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[12px] font-semibold text-apple-text">{a.action}</span>
                        <span className={`text-[9px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${priorityStyle(a.priority)}`}>
                          {a.priority.replace('_', ' ')}
                        </span>
                      </div>
                      <p className="text-[11px] text-apple-secondary leading-relaxed mb-2">{a.rationale}</p>
                      <div className="flex flex-wrap gap-1.5">
                        {a.target_sites.map(sid => (
                          <button
                            key={sid}
                            onClick={(e) => { e.stopPropagation(); navigate(`/study/${studyId}/site/${sid}`) }}
                            className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-apple-grey-50 text-apple-tertiary hover:bg-apple-grey-200 hover:text-apple-text transition-all duration-150"
                          >
                            {sid}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.section>
        )}

        {/* ── Provenance Footer ───────────────────────────────────────────── */}
        {data.generated_at && (
          <div className="text-center pb-4">
            <p className="text-[10px] font-mono text-apple-muted">
              Generated {new Date(data.generated_at).toLocaleString()}
            </p>
          </div>
        )}
      </main>
    </div>
  )
}

export default IssueCategoryDetail
