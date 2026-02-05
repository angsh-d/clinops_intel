import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { MessageCircle, X, Maximize2, Minimize2, Send, Loader2, Sparkles, Search } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { useStore } from '../lib/store'

const SUGGESTED_QUESTIONS = [
  "What's causing the enrollment issues at this site?",
  "Show me the data quality breakdown for this site",
  "What are the key risks I should address first?",
  "How does this site compare to others in the study?"
]

export function FloatingAssistant({ siteName, siteId }) {
  const navigate = useNavigate()
  const { studyId } = useParams()
  const { currentStudyId } = useStore()
  const effectiveStudyId = studyId || currentStudyId

  const [isOpen, setIsOpen] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const [query, setQuery] = useState('')
  const [activeTab, setActiveTab] = useState('investigate')
  const inputRef = useRef(null)

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  const handleSubmit = () => {
    if (!query.trim()) return
    const contextualQuery = `About ${siteName}: ${query.trim()}`
    navigate(`/study/${effectiveStudyId}?q=${encodeURIComponent(contextualQuery)}`)
  }

  const handleSuggestion = (suggestion) => {
    const contextualQuery = `About ${siteName}: ${suggestion}`
    navigate(`/study/${effectiveStudyId}?q=${encodeURIComponent(contextualQuery)}`)
  }

  return (
    <>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.2, ease: [0.25, 0.46, 0.45, 0.94] }}
            className={`fixed z-50 bg-white rounded-2xl shadow-2xl border border-apple-grey-200 flex flex-col overflow-hidden ${
              isExpanded 
                ? 'bottom-6 right-6 w-[480px] h-[600px]' 
                : 'bottom-6 right-6 w-[380px] h-[480px]'
            }`}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-apple-grey-100 bg-apple-grey-50">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-apple-grey-800 to-apple-grey-600 flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-apple-text">Clinical AI Assistant</h3>
                  <p className="text-[10px] text-apple-tertiary">Powered by multi-agent intelligence</p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button 
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="p-1.5 rounded-lg hover:bg-apple-grey-100 text-apple-tertiary transition-colors"
                >
                  {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                </button>
                <button 
                  onClick={() => setIsOpen(false)}
                  className="p-1.5 rounded-lg hover:bg-apple-grey-100 text-apple-tertiary transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="flex border-b border-apple-grey-100">
              <button
                onClick={() => setActiveTab('reasoning')}
                className={`flex-1 py-2.5 text-xs font-medium flex items-center justify-center gap-1.5 transition-colors ${
                  activeTab === 'reasoning' 
                    ? 'text-apple-text border-b-2 border-apple-grey-800' 
                    : 'text-apple-tertiary hover:text-apple-secondary'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                Reasoning
              </button>
              <button
                onClick={() => setActiveTab('investigate')}
                className={`flex-1 py-2.5 text-xs font-medium flex items-center justify-center gap-1.5 transition-colors ${
                  activeTab === 'investigate' 
                    ? 'text-apple-text border-b-2 border-apple-grey-800' 
                    : 'text-apple-tertiary hover:text-apple-secondary'
                }`}
              >
                <Search className="w-3.5 h-3.5" />
                Investigate
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              <div className="text-center py-8">
                <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-apple-grey-100 flex items-center justify-center">
                  <Sparkles className="w-6 h-6 text-apple-grey-500" />
                </div>
                <h4 className="text-base font-semibold text-apple-text mb-2">How can I help?</h4>
                <p className="text-sm text-apple-secondary max-w-[280px] mx-auto">
                  Ask me anything about {siteName}'s clinical data, safety signals, or operational status.
                </p>
              </div>

              <div className="space-y-2 mt-4">
                {SUGGESTED_QUESTIONS.map((question, i) => (
                  <button
                    key={i}
                    onClick={() => handleSuggestion(question)}
                    className="w-full text-left p-3 rounded-xl bg-apple-grey-50 hover:bg-apple-grey-100 transition-colors group"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm text-apple-text leading-relaxed">{question}</p>
                      <span className="text-[10px] text-apple-tertiary opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap mt-0.5">
                        Agentic
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="p-3 border-t border-apple-grey-100 bg-white">
              <div className="flex items-center gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                  placeholder="Ask a question..."
                  className="flex-1 px-4 py-2.5 text-sm bg-apple-grey-50 border border-apple-grey-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-apple-grey-300 focus:border-transparent placeholder:text-apple-tertiary"
                />
                <button
                  onClick={handleSubmit}
                  disabled={!query.trim()}
                  className="p-2.5 rounded-xl bg-apple-grey-800 text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-apple-grey-700 transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
              <p className="text-[10px] text-apple-muted text-center mt-2">
                Responses may be cached for faster retrieval
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.button
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsOpen(!isOpen)}
        className={`fixed bottom-6 right-6 z-40 w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-colors ${
          isOpen 
            ? 'bg-apple-grey-200 text-apple-grey-600' 
            : 'bg-apple-grey-800 text-white hover:bg-apple-grey-700'
        }`}
      >
        {isOpen ? (
          <X className="w-6 h-6" />
        ) : (
          <MessageCircle className="w-6 h-6" />
        )}
      </motion.button>
    </>
  )
}

export default FloatingAssistant
