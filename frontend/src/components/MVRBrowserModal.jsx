import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, FileText, Loader2 } from 'lucide-react'
import { getMVRList, getMVRPdfUrl } from '../lib/api'

export function MVRBrowserModal({ siteId, onClose }) {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedReport, setSelectedReport] = useState(null)

  useEffect(() => {
    getMVRList(siteId)
      .then(data => {
        setReports(data.reports || [])
        if (data.reports?.length > 0) setSelectedReport(data.reports[0])
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [siteId])

  useEffect(() => {
    const handleEsc = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [onClose])

  const pdfUrl = selectedReport?.pdf_filename
    ? getMVRPdfUrl(selectedReport.pdf_filename)
    : null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] flex items-center justify-center"
      >
        {/* Backdrop */}
        <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />

        {/* Modal */}
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          transition={{ type: 'spring', duration: 0.35 }}
          className="relative w-[90vw] h-[85vh] max-w-[1200px] bg-apple-surface rounded-2xl shadow-2xl border border-apple-grey-200 flex overflow-hidden"
        >
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-3 right-3 z-10 w-8 h-8 flex items-center justify-center rounded-lg bg-apple-grey-100 hover:bg-apple-grey-200 transition-colors"
          >
            <X className="w-4 h-4 text-apple-grey-600" />
          </button>

          {/* Left panel: report list */}
          <div className="w-[280px] flex-shrink-0 border-r border-apple-divider flex flex-col">
            <div className="px-4 py-3 border-b border-apple-divider">
              <p className="text-[13px] font-semibold text-apple-text">Monitoring Visit Reports</p>
              <p className="text-[11px] text-apple-tertiary mt-0.5">{siteId} — {reports.length} reports</p>
            </div>
            <div className="flex-1 overflow-y-auto">
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-5 h-5 animate-spin text-apple-tertiary" />
                </div>
              ) : reports.length === 0 ? (
                <p className="text-[12px] text-apple-tertiary text-center py-8">No reports found</p>
              ) : (
                <div className="divide-y divide-apple-grey-50">
                  {reports.map(r => {
                    const isSelected = selectedReport?.id === r.id
                    return (
                      <button
                        key={r.id}
                        onClick={() => setSelectedReport(r)}
                        className={`w-full text-left px-4 py-3 transition-colors ${isSelected ? 'bg-apple-grey-100' : 'hover:bg-apple-grey-50'}`}
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <FileText className="w-3.5 h-3.5 text-apple-grey-400 flex-shrink-0" />
                          <span className="text-[12px] font-medium text-apple-text truncate">
                            {r.visit_type || 'Visit'} #{r.visit_number || '—'}
                          </span>
                        </div>
                        <div className="pl-5.5 space-y-0.5">
                          <p className="text-[11px] text-apple-secondary">{r.visit_date || 'No date'}</p>
                          <div className="flex items-center gap-3 text-[10px] text-apple-tertiary">
                            <span>{r.cra_id}</span>
                            {r.action_required_count > 0 && (
                              <span className="font-medium text-apple-text">{r.action_required_count} actions</span>
                            )}
                            {r.word_count && <span>{r.word_count.toLocaleString()} words</span>}
                          </div>
                          {r.executive_summary && (
                            <p className="text-[10px] text-apple-muted line-clamp-2 mt-1 leading-relaxed">{r.executive_summary}</p>
                          )}
                        </div>
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Right panel: PDF viewer */}
          <div className="flex-1 bg-apple-grey-50 flex items-center justify-center">
            {pdfUrl ? (
              <iframe
                key={pdfUrl}
                src={pdfUrl}
                className="w-full h-full"
                title="MVR PDF"
              />
            ) : (
              <p className="text-[13px] text-apple-tertiary">Select a report to view</p>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
