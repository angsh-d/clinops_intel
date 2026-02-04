import { Routes, Route, Navigate } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { Home } from './components/Home'
import { CommandCenter } from './components/CommandCenter'
import { SiteDossier } from './components/SiteDossier'
import { InvestigationTheater } from './components/InvestigationTheater'
import { CommandPalette } from './components/CommandPalette'
import { useStore } from './lib/store'

function App() {
  const { commandOpen } = useStore()

  return (
    <div className="min-h-screen bg-apple-bg">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/study/:studyId" element={<CommandCenter />} />
        <Route path="/study/:studyId/site/:siteId" element={<SiteDossier />} />
        <Route path="/investigate/:queryId" element={<InvestigationTheater />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      <AnimatePresence>
        {commandOpen && <CommandPalette key="command" />}
      </AnimatePresence>
    </div>
  )
}

export default App
