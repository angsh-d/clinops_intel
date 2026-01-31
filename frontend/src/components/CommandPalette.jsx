import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, ArrowRight, AlertCircle, TrendingUp, Users } from 'lucide-react'
import { useStore } from '../lib/store'
import { getAttentionSites } from '../lib/api'

const suggestions = [
  { icon: AlertCircle, text: 'Which sites need attention?', category: 'Alerts' },
  { icon: TrendingUp, text: 'Show enrollment trends', category: 'Enrollment' },
  { icon: Users, text: 'Sites behind on enrollment', category: 'Sites' },
  { icon: AlertCircle, text: 'Data quality issues this week', category: 'Data Quality' },
  { icon: TrendingUp, text: 'Screen failure analysis', category: 'Enrollment' }
]

export function CommandPalette() {
  const { setCommandOpen, setInvestigation, setSelectedSite, setView } = useStore()
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [recentSites, setRecentSites] = useState([])
  const inputRef = useRef(null)
  
  useEffect(() => {
    async function fetchRecentSites() {
      try {
        const data = await getAttentionSites()
        if (data?.sites) {
          setRecentSites(data.sites.slice(0, 5).map(s => ({
            id: s.site_id,
            status: s.severity,
            finding: s.issue
          })))
        }
      } catch (error) {
        console.error('Failed to fetch recent sites:', error)
      }
    }
    fetchRecentSites()
  }, [])
  
  const filteredSuggestions = query
    ? suggestions.filter(s => s.text.toLowerCase().includes(query.toLowerCase()))
    : suggestions
  
  const filteredSites = query
    ? recentSites.filter(s => s.id.toLowerCase().includes(query.toLowerCase()))
    : recentSites
  
  const allItems = [...filteredSuggestions, ...filteredSites]
  
  useEffect(() => {
    inputRef.current?.focus()
  }, [])
  
  useEffect(() => {
    setSelectedIndex(0)
  }, [query])
  
  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex(i => Math.min(i + 1, allItems.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex(i => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      handleSelect(allItems[selectedIndex])
    }
  }
  
  const handleSelect = (item) => {
    if ('text' in item) {
      setInvestigation({ question: item.text, status: 'routing' })
    } else {
      setView('constellation')
      setSelectedSite(item)
    }
    setCommandOpen(false)
  }
  
  const handleSubmit = () => {
    if (query.trim()) {
      setInvestigation({ question: query, status: 'routing' })
      setCommandOpen(false)
    }
  }
  
  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50"
        onClick={() => setCommandOpen(false)}
      />
      
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: -20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: -20 }}
        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
        className="fixed top-[20%] left-1/2 -translate-x-1/2 w-full max-w-xl z-50"
      >
        <div className="bg-apple-surface rounded-2xl shadow-apple-lg border border-apple-border overflow-hidden">
          <div className="flex items-center gap-3 px-4 py-3 border-b border-apple-border">
            <Search className="w-5 h-5 text-apple-secondary" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about any site, metric, or operational question..."
              className="flex-1 bg-transparent text-body text-apple-text placeholder:text-apple-secondary/50 outline-none"
            />
            {query && (
              <button
                onClick={handleSubmit}
                className="p-1.5 bg-apple-accent rounded-full text-white hover:opacity-90 transition-opacity"
              >
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
          
          <div className="max-h-[400px] overflow-y-auto">
            {filteredSuggestions.length > 0 && (
              <div className="p-2">
                <p className="px-2 py-1 text-caption text-apple-secondary uppercase tracking-wide">
                  Suggestions
                </p>
                {filteredSuggestions.map((suggestion, i) => (
                  <SuggestionItem
                    key={suggestion.text}
                    suggestion={suggestion}
                    isSelected={selectedIndex === i}
                    onSelect={() => handleSelect(suggestion)}
                    onHover={() => setSelectedIndex(i)}
                  />
                ))}
              </div>
            )}
            
            {filteredSites.length > 0 && (
              <div className="p-2 border-t border-apple-border">
                <p className="px-2 py-1 text-caption text-apple-secondary uppercase tracking-wide">
                  Recent Sites
                </p>
                {filteredSites.map((site, i) => (
                  <SiteItem
                    key={site.id}
                    site={site}
                    isSelected={selectedIndex === filteredSuggestions.length + i}
                    onSelect={() => handleSelect(site)}
                    onHover={() => setSelectedIndex(filteredSuggestions.length + i)}
                  />
                ))}
              </div>
            )}
            
            {query && allItems.length === 0 && (
              <div className="p-8 text-center">
                <p className="text-body text-apple-secondary">No results found</p>
                <p className="text-caption text-apple-secondary/70 mt-1">
                  Press Enter to investigate "{query}"
                </p>
              </div>
            )}
          </div>
          
          <div className="px-4 py-2 border-t border-apple-border bg-apple-bg/50">
            <div className="flex items-center justify-between text-caption text-apple-secondary">
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 bg-apple-surface rounded text-xs">↑↓</kbd>
                  navigate
                </span>
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 bg-apple-surface rounded text-xs">↵</kbd>
                  select
                </span>
              </div>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-apple-surface rounded text-xs">esc</kbd>
                close
              </span>
            </div>
          </div>
        </div>
      </motion.div>
    </>
  )
}

function SuggestionItem({ suggestion, isSelected, onSelect, onHover }) {
  const Icon = suggestion.icon
  
  return (
    <button
      onClick={onSelect}
      onMouseEnter={onHover}
      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
        isSelected ? 'bg-apple-accent text-white' : 'hover:bg-apple-bg text-apple-text'
      }`}
    >
      <Icon className={`w-4 h-4 ${isSelected ? 'text-white' : 'text-apple-secondary'}`} />
      <span className="flex-1 text-left text-body">{suggestion.text}</span>
      <span className={`text-caption ${isSelected ? 'text-white/70' : 'text-apple-secondary'}`}>
        {suggestion.category}
      </span>
    </button>
  )
}

function SiteItem({ site, isSelected, onSelect, onHover }) {
  const statusColors = {
    critical: 'bg-apple-critical',
    warning: 'bg-apple-warning',
    healthy: 'bg-apple-success'
  }
  
  return (
    <button
      onClick={onSelect}
      onMouseEnter={onHover}
      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
        isSelected ? 'bg-apple-accent text-white' : 'hover:bg-apple-bg text-apple-text'
      }`}
    >
      <div className={`w-2 h-2 rounded-full ${statusColors[site.status]}`} />
      <span className="font-medium text-body">{site.id}</span>
      <span className={`flex-1 text-left text-caption ${isSelected ? 'text-white/70' : 'text-apple-secondary'}`}>
        {site.finding}
      </span>
    </button>
  )
}
