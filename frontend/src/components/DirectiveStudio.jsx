import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Settings, Plus, ChevronDown, ToggleLeft, ToggleRight } from 'lucide-react'
import { useStore } from '../lib/store'
import { getDirectives, toggleDirective, createDirective } from '../lib/api'
import { StudyNav } from './StudyNav'

const AGENT_LABELS = {
  data_quality: 'Data Quality',
  enrollment_funnel: 'Enrollment Funnel',
  clinical_trials_gov: 'Competitive Intelligence',
  phantom_compliance: 'Data Integrity',
  site_rescue: 'Site Decision',
  vendor_performance: 'Vendor Performance',
  financial_intelligence: 'Financial Intelligence',
}

export function DirectiveStudio() {
  const [directives, setDirectives] = useState([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState(null)
  const [showCreate, setShowCreate] = useState(false)

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await getDirectives()
        if (Array.isArray(data)) setDirectives(data)
      } catch (error) {
        console.error('Directives fetch error:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const handleToggle = async (directiveId, currentEnabled) => {
    try {
      const updated = await toggleDirective(directiveId, !currentEnabled)
      setDirectives(prev => prev.map(d =>
        d.directive_id === directiveId ? { ...d, enabled: !currentEnabled } : d
      ))
    } catch (error) {
      console.error('Toggle error:', error)
    }
  }

  const handleCreate = async (newDirective) => {
    try {
      const created = await createDirective(newDirective)
      setDirectives(prev => [...prev, created])
      setShowCreate(false)
    } catch (error) {
      console.error('Create directive error:', error)
    }
  }

  // Group by agent
  const byAgent = {}
  for (const d of directives) {
    const agent = d.agent_id || 'unknown'
    if (!byAgent[agent]) byAgent[agent] = []
    byAgent[agent].push(d)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-apple-bg">
        <StudyNav active="directives" />
        <div className="flex items-center justify-center h-64">
          <div className="flex items-center gap-3 text-apple-secondary">
            <div className="w-5 h-5 border-2 border-apple-secondary/30 border-t-apple-secondary rounded-full animate-spin" />
            <span className="text-body">Loading Directives...</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-apple-bg">
      <StudyNav active="directives" />

      <main className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-xl font-medium text-apple-text">Directive Studio</h2>
            <p className="text-caption text-apple-secondary mt-1">Configure what the AI autonomously investigates during proactive scans</p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-apple-text text-white text-caption font-medium rounded-xl hover:bg-neutral-800 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Create Directive
          </button>
        </div>

        {/* Directives by agent */}
        <div className="space-y-6">
          {Object.entries(byAgent).map(([agentId, agentDirectives]) => (
            <div key={agentId}>
              <h3 className="text-caption font-medium text-apple-secondary uppercase tracking-wide mb-3">
                {AGENT_LABELS[agentId] || agentId}
              </h3>
              <div className="space-y-2">
                {agentDirectives.map(d => (
                  <motion.div
                    key={d.directive_id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-apple-surface border border-apple-border rounded-xl overflow-hidden"
                  >
                    <div className="flex items-center gap-3 px-4 py-3">
                      {/* Toggle */}
                      <button
                        onClick={() => handleToggle(d.directive_id, d.enabled)}
                        className="flex-shrink-0"
                      >
                        {d.enabled ? (
                          <ToggleRight className="w-6 h-6 text-green-500" />
                        ) : (
                          <ToggleLeft className="w-6 h-6 text-neutral-300" />
                        )}
                      </button>

                      {/* Name + description */}
                      <div className="flex-1 min-w-0">
                        <p className={`text-body font-medium ${d.enabled ? 'text-apple-text' : 'text-apple-secondary'}`}>
                          {d.name}
                        </p>
                        <p className="text-caption text-apple-secondary truncate">{d.description}</p>
                      </div>

                      {/* Priority badge */}
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                        d.priority <= 1 ? 'bg-red-50 text-red-600 border-red-200' :
                        d.priority <= 3 ? 'bg-amber-50 text-amber-600 border-amber-200' :
                        'bg-neutral-50 text-neutral-500 border-neutral-200'
                      }`}>
                        P{d.priority}
                      </span>

                      {/* Expand toggle */}
                      <button
                        onClick={() => setExpandedId(expandedId === d.directive_id ? null : d.directive_id)}
                        className="p-1 rounded hover:bg-apple-bg transition-colors"
                      >
                        <ChevronDown className={`w-4 h-4 text-apple-secondary transition-transform ${
                          expandedId === d.directive_id ? 'rotate-180' : ''
                        }`} />
                      </button>
                    </div>

                    {/* Expanded: show prompt text */}
                    <AnimatePresence>
                      {expandedId === d.directive_id && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="overflow-hidden"
                        >
                          <div className="px-4 pb-4 pt-1 border-t border-apple-border/50">
                            <p className="text-[11px] font-medium text-apple-secondary uppercase tracking-wide mb-2">Prompt</p>
                            <pre className="text-[12px] font-mono text-neutral-600 bg-apple-bg rounded-lg p-3 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                              {d.prompt_text || 'Prompt not available'}
                            </pre>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {directives.length === 0 && (
          <div className="text-center py-16 text-apple-secondary">
            <Settings className="w-8 h-8 mx-auto mb-3 opacity-30" />
            <p className="text-body">No directives configured</p>
            <p className="text-caption mt-1">Create your first directive to enable autonomous investigation</p>
          </div>
        )}
      </main>

      {/* Create modal */}
      <AnimatePresence>
        {showCreate && <CreateDirectiveModal onSubmit={handleCreate} onClose={() => setShowCreate(false)} />}
      </AnimatePresence>
    </div>
  )
}


function CreateDirectiveModal({ onSubmit, onClose }) {
  const [form, setForm] = useState({
    directive_id: '',
    agent_id: 'data_quality',
    name: '',
    description: '',
    prompt_text: '',
    priority: 3,
  })
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    if (!form.name || !form.directive_id) return
    setSubmitting(true)
    try {
      await onSubmit(form)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/30 z-50" onClick={onClose}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}
        className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg bg-apple-surface rounded-2xl shadow-apple-lg border border-apple-border p-6 z-50"
      >
        <h3 className="text-body font-medium text-apple-text mb-4">Create New Directive</h3>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-caption text-apple-secondary mb-1 block">ID</label>
              <input
                value={form.directive_id}
                onChange={(e) => setForm(f => ({ ...f, directive_id: e.target.value }))}
                placeholder="e.g. enrollment_gap_scan"
                className="w-full px-3 py-2 bg-apple-bg border border-apple-border rounded-lg text-caption outline-none"
              />
            </div>
            <div>
              <label className="text-caption text-apple-secondary mb-1 block">Agent</label>
              <select
                value={form.agent_id}
                onChange={(e) => setForm(f => ({ ...f, agent_id: e.target.value }))}
                className="w-full px-3 py-2 bg-apple-bg border border-apple-border rounded-lg text-caption outline-none"
              >
                {Object.entries(AGENT_LABELS).map(([id, label]) => (
                  <option key={id} value={id}>{label}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="text-caption text-apple-secondary mb-1 block">Name</label>
            <input
              value={form.name}
              onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="Directive name"
              className="w-full px-3 py-2 bg-apple-bg border border-apple-border rounded-lg text-caption outline-none"
            />
          </div>
          <div>
            <label className="text-caption text-apple-secondary mb-1 block">Description</label>
            <input
              value={form.description}
              onChange={(e) => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="What does this directive investigate?"
              className="w-full px-3 py-2 bg-apple-bg border border-apple-border rounded-lg text-caption outline-none"
            />
          </div>
          <div>
            <label className="text-caption text-apple-secondary mb-1 block">Prompt Text</label>
            <textarea
              value={form.prompt_text}
              onChange={(e) => setForm(f => ({ ...f, prompt_text: e.target.value }))}
              placeholder="Investigation prompt..."
              className="w-full h-28 px-3 py-2 bg-apple-bg border border-apple-border rounded-lg text-caption outline-none resize-none"
            />
          </div>
          <div>
            <label className="text-caption text-apple-secondary mb-1 block">Priority (1=highest)</label>
            <input
              type="number"
              min={1}
              max={10}
              value={form.priority}
              onChange={(e) => setForm(f => ({ ...f, priority: parseInt(e.target.value) || 3 }))}
              className="w-20 px-3 py-2 bg-apple-bg border border-apple-border rounded-lg text-caption outline-none"
            />
          </div>
        </div>
        <div className="flex items-center gap-3 mt-5 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-caption text-apple-secondary hover:text-apple-text">Cancel</button>
          <button
            onClick={handleSubmit}
            disabled={!form.name || !form.directive_id || submitting}
            className="px-4 py-2 bg-apple-text text-white text-caption font-medium rounded-xl hover:bg-neutral-800 transition-colors disabled:opacity-50"
          >
            {submitting ? 'Creating...' : 'Create'}
          </button>
        </div>
      </motion.div>
    </>
  )
}
