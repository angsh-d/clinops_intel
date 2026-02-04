import { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { useStore } from '../lib/store'
import { getVendorScorecards, getVendorDetail, getVendorComparison } from '../lib/api'
import { StudyNav } from './StudyNav'

export function VendorDashboard() {
  const { toggleCommand, studyData } = useStore()
  const [scorecards, setScorecards] = useState([])
  const [comparison, setComparison] = useState(null)
  const [selectedVendor, setSelectedVendor] = useState(null)
  const [vendorDetail, setVendorDetail] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const [sc, comp] = await Promise.all([
          getVendorScorecards(),
          getVendorComparison(),
        ])
        if (sc?.vendors) setScorecards(sc.vendors)
        if (comp) setComparison(comp)
      } catch (error) {
        console.error('VendorDashboard fetch error:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  useEffect(() => {
    if (!selectedVendor) { setVendorDetail(null); return }
    async function fetchDetail() {
      try {
        const data = await getVendorDetail(selectedVendor.vendor_id)
        setVendorDetail(data)
      } catch (error) {
        console.error('Vendor detail fetch error:', error)
      }
    }
    fetchDetail()
  }, [selectedVendor?.vendor_id])

  if (loading) {
    return (
      <div className="min-h-screen bg-apple-bg flex items-center justify-center">
        <div className="flex items-center gap-3 text-apple-secondary">
          <div className="w-5 h-5 border-2 border-apple-secondary/30 border-t-apple-secondary rounded-full animate-spin" />
          <span className="text-body">Loading Vendor Dashboard...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-apple-bg">
      <StudyNav active="vendors" />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Vendor Cards Grid */}
        <section>
          <h2 className="text-xl font-light text-apple-text mb-4">Vendor Scorecards</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
            {scorecards.map((vendor, i) => (
              <motion.div
                key={vendor.vendor_id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <VendorCard
                  vendor={vendor}
                  selected={selectedVendor?.vendor_id === vendor.vendor_id}
                  onClick={() => setSelectedVendor(selectedVendor?.vendor_id === vendor.vendor_id ? null : vendor)}
                />
              </motion.div>
            ))}
          </div>
        </section>

        {/* Vendor Detail Pane */}
        {vendorDetail && (
          <motion.section
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="overflow-hidden"
          >
            <VendorDetailPane vendor={vendorDetail} onClose={() => setSelectedVendor(null)} />
          </motion.section>
        )}

        {/* KPI Comparison */}
        {comparison?.kpis && (
          <section>
            <h2 className="text-xl font-light text-apple-text mb-4">KPI Comparison</h2>
            <div className="card p-6 overflow-x-auto">
              <table className="w-full text-caption">
                <thead>
                  <tr className="border-b border-apple-border">
                    <th className="text-left p-2 text-apple-secondary font-medium">KPI</th>
                    {comparison.vendor_names?.map(name => (
                      <th key={name} className="text-right p-2 text-apple-secondary font-medium">{name}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {comparison.kpis.map(kpi => (
                    <tr key={kpi.kpi_name} className="border-b border-apple-border/50">
                      <td className="p-2 text-apple-text">{kpi.kpi_name}</td>
                      {kpi.values?.map((val, i) => (
                        <td key={i} className="p-2 text-right font-mono">
                          <span className={
                            val.status === 'Red' ? 'text-apple-critical' :
                            val.status === 'Amber' ? 'text-apple-warning' :
                            'text-apple-text'
                          }>
                            {val.value}
                          </span>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* Milestone Timeline */}
        {scorecards.length > 0 && (
          <section>
            <h2 className="text-xl font-light text-apple-text mb-4">Milestone Timeline</h2>
            <div className="card p-6 space-y-4">
              {scorecards.filter(v => v.milestones?.length > 0).slice(0, 4).map(vendor => (
                <div key={vendor.vendor_id}>
                  <p className="text-caption font-medium text-apple-text mb-2">{vendor.name}</p>
                  <div className="space-y-1.5">
                    {vendor.milestones?.slice(0, 3).map((ms, i) => (
                      <div key={i} className="flex items-center gap-3 text-caption">
                        <div className={`w-2 h-2 rounded-full ${
                          ms.status === 'Completed' ? 'bg-apple-success' :
                          ms.status === 'At Risk' ? 'bg-apple-warning' :
                          ms.status === 'Delayed' ? 'bg-apple-critical' :
                          'bg-apple-secondary/30'
                        }`} />
                        <span className="text-apple-text flex-1">{ms.milestone_name}</span>
                        <span className="text-apple-secondary">{ms.planned_date}</span>
                        {ms.delay_days > 0 && (
                          <span className="text-apple-critical font-mono">+{ms.delay_days}d</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

function VendorCard({ vendor, selected, onClick }) {
  const ragColor = {
    Green: 'border-l-apple-success',
    Amber: 'border-l-apple-warning',
    Red: 'border-l-apple-critical',
  }[vendor.overall_rag] || 'border-l-apple-secondary/30'

  return (
    <button
      onClick={onClick}
      className={`w-full text-left card p-4 border-l-4 ${ragColor} transition-all ${
        selected ? 'ring-2 ring-apple-accent/50' : 'hover:shadow-apple-lg'
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          <p className="text-body font-medium text-apple-text">{vendor.name}</p>
          <p className="text-caption text-apple-secondary">{vendor.vendor_type}</p>
        </div>
        <RagBadge rag={vendor.overall_rag} />
      </div>
      <div className="flex items-center gap-4 text-caption text-apple-secondary">
        <span>{vendor.active_sites} sites</span>
        {vendor.issue_count > 0 && (
          <span className="text-apple-warning">{vendor.issue_count} issues</span>
        )}
      </div>
    </button>
  )
}

function RagBadge({ rag }) {
  const config = {
    Green: { bg: 'bg-apple-success/10', text: 'text-apple-success' },
    Amber: { bg: 'bg-apple-warning/10', text: 'text-apple-warning' },
    Red: { bg: 'bg-apple-critical/10', text: 'text-apple-critical' },
  }[rag] || { bg: 'bg-apple-secondary/10', text: 'text-apple-secondary' }

  return (
    <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${config.bg} ${config.text}`}>
      {rag}
    </span>
  )
}

function VendorDetailPane({ vendor, onClose }) {
  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-section text-apple-text">{vendor.name}</h3>
          <p className="text-caption text-apple-secondary">{vendor.vendor_type} · {vendor.country_hq}</p>
        </div>
        <button onClick={onClose} className="text-caption text-apple-secondary hover:text-apple-text">Close</button>
      </div>

      {vendor.kpi_trends && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {vendor.kpi_trends.map(kpi => (
            <div key={kpi.kpi_name} className="p-3 bg-apple-bg rounded-lg">
              <p className="text-caption text-apple-secondary mb-1">{kpi.kpi_name}</p>
              <p className="font-mono text-data text-apple-text">{kpi.current_value}</p>
              <p className="text-[11px] text-apple-secondary">Target: {kpi.target}</p>
            </div>
          ))}
        </div>
      )}

      {vendor.site_breakdown && (
        <div>
          <h4 className="text-caption font-medium text-apple-secondary uppercase mb-2">Site Breakdown</h4>
          <div className="space-y-1">
            {vendor.site_breakdown.map(site => (
              <div key={site.site_id} className="flex items-center justify-between text-caption py-1">
                <span className="text-apple-text">{site.site_name || site.site_id}</span>
                <span className="text-apple-secondary">{site.role}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
