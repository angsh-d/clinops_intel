import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { useStore } from '../lib/store'
import { getFinancialSummary, getFinancialWaterfall, getFinancialByCountry, getFinancialByVendor, getCostPerPatient } from '../lib/api'
import { StudyNav } from './StudyNav'

export function FinancialDashboard() {
  const { toggleCommand } = useStore()
  const [summary, setSummary] = useState(null)
  const [waterfall, setWaterfall] = useState(null)
  const [byCountry, setByCountry] = useState(null)
  const [byVendor, setByVendor] = useState(null)
  const [costPerPatient, setCostPerPatient] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const [sum, wf, bc, bv, cpp] = await Promise.all([
          getFinancialSummary(),
          getFinancialWaterfall(),
          getFinancialByCountry(),
          getFinancialByVendor(),
          getCostPerPatient(),
        ])
        if (sum) setSummary(sum)
        if (wf) setWaterfall(wf)
        if (bc) setByCountry(bc)
        if (bv) setByVendor(bv)
        if (cpp) setCostPerPatient(cpp)
      } catch (error) {
        console.error('FinancialDashboard fetch error:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-apple-bg flex items-center justify-center">
        <div className="flex items-center gap-3 text-apple-secondary">
          <div className="w-5 h-5 border-2 border-apple-secondary/30 border-t-apple-secondary rounded-full animate-spin" />
          <span className="text-body">Loading Financial Dashboard...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-apple-bg">
      <StudyNav active="financials" />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Budget Summary Bar */}
        {summary && (
          <section>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <BudgetKPI label="Total Budget" value={formatCurrency(summary.total_budget)} />
              <BudgetKPI label="Spent to Date" value={formatCurrency(summary.spent_to_date)} trend={summary.spend_trend} />
              <BudgetKPI label="Remaining" value={formatCurrency(summary.remaining)} />
              <BudgetKPI label="Forecast" value={formatCurrency(summary.forecast_total)} alert={summary.forecast_total > summary.total_budget} />
              <BudgetKPI label="Variance" value={formatPercent(summary.variance_pct)} alert={summary.variance_pct > 5} />
            </div>
          </section>
        )}

        {/* Budget Waterfall */}
        {waterfall && (
          <section>
            <h2 className="text-xl font-light text-apple-text mb-4">Budget Waterfall</h2>
            <div className="card p-6">
              <div className="flex gap-4">
                {waterfall.segments?.map((seg, i) => {
                  const maxVal = Math.max(...waterfall.segments.map(s => Math.abs(s.value)))
                  const heightPct = maxVal > 0 ? (Math.abs(seg.value) / maxVal) * 100 : 0
                  return (
                    <div key={i} className="flex-1 flex flex-col items-center">
                      <span className="text-[11px] font-mono text-apple-text mb-2">{formatCurrencyShort(seg.value)}</span>
                      <div className="w-full h-32 flex items-end">
                        <div
                          className={`w-full rounded-t ${
                            seg.type === 'increase' ? 'bg-amber-400' :
                            seg.type === 'decrease' ? 'bg-emerald-500' :
                            seg.type === 'actual' ? 'bg-blue-500' :
                            'bg-slate-400'
                          }`}
                          style={{ height: `${Math.max(heightPct, 8)}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-apple-secondary text-center mt-2">{seg.label}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          </section>
        )}

        <div className="grid md:grid-cols-2 gap-8">
          {/* Spend by Vendor */}
          {byVendor?.vendors && (
            <section>
              <h2 className="text-xl font-light text-apple-text mb-4">Spend by Vendor</h2>
              <div className="card p-6 space-y-3">
                {byVendor.vendors.map(v => {
                  const pct = byVendor.total > 0 ? (v.amount / byVendor.total) * 100 : 0
                  return (
                    <div key={v.vendor_name}>
                      <div className="flex items-center justify-between text-caption mb-1">
                        <span className="text-apple-text">{v.vendor_name}</span>
                        <span className="font-mono text-apple-secondary">{formatCurrencyShort(v.amount)}</span>
                      </div>
                      <div className="w-full h-2 bg-apple-border rounded-full overflow-hidden">
                        <div className="h-full bg-apple-accent rounded-full" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            </section>
          )}

          {/* Spend by Country */}
          {byCountry?.countries && (
            <section>
              <h2 className="text-xl font-light text-apple-text mb-4">Spend by Country</h2>
              <div className="card p-6 space-y-3">
                {byCountry.countries.slice(0, 8).map(c => {
                  const pct = byCountry.total > 0 ? (c.amount / byCountry.total) * 100 : 0
                  return (
                    <div key={c.country}>
                      <div className="flex items-center justify-between text-caption mb-1">
                        <span className="text-apple-text">{c.country}</span>
                        <span className="font-mono text-apple-secondary">{formatCurrencyShort(c.amount)}</span>
                      </div>
                      <div className="w-full h-2 bg-apple-border rounded-full overflow-hidden">
                        <div className="h-full bg-apple-text/40 rounded-full" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            </section>
          )}
        </div>

        {/* Cost Per Patient Table */}
        {costPerPatient?.sites && (
          <section>
            <h2 className="text-xl font-light text-apple-text mb-4">Site Cost Efficiency</h2>
            <div className="card overflow-x-auto">
              <table className="w-full text-caption">
                <thead>
                  <tr className="border-b border-apple-border bg-apple-surface">
                    <th className="text-left p-3 text-apple-secondary font-medium">Site</th>
                    <th className="text-left p-3 text-apple-secondary font-medium">Country</th>
                    <th className="text-right p-3 text-apple-secondary font-medium">Cost to Date</th>
                    <th className="text-right p-3 text-apple-secondary font-medium">Cost/Screened</th>
                    <th className="text-right p-3 text-apple-secondary font-medium">Cost/Randomized</th>
                    <th className="text-right p-3 text-apple-secondary font-medium">Variance</th>
                  </tr>
                </thead>
                <tbody>
                  {costPerPatient.sites.slice(0, 20).map(site => (
                    <tr key={site.site_id} className="border-b border-apple-border/50 hover:bg-apple-bg">
                      <td className="p-3 text-apple-text">{site.site_name || site.site_id}</td>
                      <td className="p-3 text-apple-secondary">{site.country}</td>
                      <td className="p-3 text-right font-mono">{formatCurrencyShort(site.cost_to_date)}</td>
                      <td className="p-3 text-right font-mono">{formatCurrencyShort(site.cost_per_screened)}</td>
                      <td className="p-3 text-right font-mono">{formatCurrencyShort(site.cost_per_randomized)}</td>
                      <td className={`p-3 text-right font-mono ${
                        site.variance_pct > 10 ? 'text-apple-critical' :
                        site.variance_pct > 5 ? 'text-apple-warning' :
                        'text-apple-text'
                      }`}>
                        {site.variance_pct > 0 ? '+' : ''}{site.variance_pct?.toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}


function BudgetKPI({ label, value, trend, alert }) {
  return (
    <div className={`card p-4 ${alert ? 'border-l-4 border-l-apple-critical' : ''}`}>
      <p className="text-caption text-apple-secondary mb-1">{label}</p>
      <p className={`font-mono text-data ${alert ? 'text-apple-critical' : 'text-apple-text'}`}>{value}</p>
      {trend && (
        <div className="flex items-center gap-1 mt-1">
          {trend === 'up' ? <TrendingUp className="w-3 h-3 text-apple-critical" /> : <TrendingDown className="w-3 h-3 text-apple-success" />}
          <span className="text-[11px] text-apple-secondary">{trend}</span>
        </div>
      )}
    </div>
  )
}

function formatCurrency(val) {
  if (val == null) return '$0'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val)
}

function formatCurrencyShort(val) {
  if (val == null) return '$0'
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`
  if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`
  return `$${val.toFixed(0)}`
}

function formatPercent(val) {
  if (val == null) return '0%'
  return `${val > 0 ? '+' : ''}${val.toFixed(1)}%`
}
