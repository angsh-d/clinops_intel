import { useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { Pulse } from './components/Pulse'
import { Constellation } from './components/Constellation'
import { SiteSheet } from './components/SiteSheet'
import { InvestigationTheater } from './components/InvestigationTheater'
import { CommandPalette } from './components/CommandPalette'
import { useStore } from './lib/store'

function App() {
  const { view, selectedSite, investigation, commandOpen } = useStore()
  
  return (
    <div className="min-h-screen bg-apple-bg">
      <AnimatePresence mode="wait">
        {view === 'pulse' && <Pulse key="pulse" />}
        {view === 'constellation' && <Constellation key="constellation" />}
      </AnimatePresence>
      
      <AnimatePresence>
        {selectedSite && <SiteSheet key="site-sheet" />}
      </AnimatePresence>
      
      <AnimatePresence>
        {investigation && <InvestigationTheater key="investigation" />}
      </AnimatePresence>
      
      <AnimatePresence>
        {commandOpen && <CommandPalette key="command" />}
      </AnimatePresence>
    </div>
  )
}

export default App
