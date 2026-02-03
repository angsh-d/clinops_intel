import { AnimatePresence } from 'framer-motion'
import { Home } from './components/Home'
import { Study360 } from './components/Study360'
import { StudyCommandCenter } from './components/StudyCommandCenter'
import { VendorDashboard } from './components/VendorDashboard'
import { FinancialDashboard } from './components/FinancialDashboard'
import { SiteSheet } from './components/SiteSheet'
import { InvestigationTheater } from './components/InvestigationTheater'
import { CommandPalette } from './components/CommandPalette'
import { useStore } from './lib/store'

function App() {
  const { view, selectedSite, investigation, commandOpen } = useStore()

  return (
    <div className="min-h-screen bg-apple-bg">
      <AnimatePresence mode="wait">
        {view === 'home' && <Home key="home" />}
        {view === 'study360' && <Study360 key="study360" />}
        {view === 'study' && <StudyCommandCenter key="study" />}
        {view === 'vendors' && <VendorDashboard key="vendors" />}
        {view === 'financials' && <FinancialDashboard key="financials" />}
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
