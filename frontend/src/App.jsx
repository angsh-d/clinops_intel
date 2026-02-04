import { Routes, Route, Navigate } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { Home } from './components/Home'
import { MorningBrief } from './components/MorningBrief'
import { Study360 } from './components/Study360'
import { StudyCommandCenter } from './components/StudyCommandCenter'
import { VendorDashboard } from './components/VendorDashboard'
import { FinancialDashboard } from './components/FinancialDashboard'
import { SignalCenter } from './components/SignalCenter'
import { SiteDossier } from './components/SiteDossier'
import { DirectiveStudio } from './components/DirectiveStudio'
import { InvestigationArchive } from './components/InvestigationArchive'
import { InvestigationTheater } from './components/InvestigationTheater'
import { CommandPalette } from './components/CommandPalette'
import { useStore } from './lib/store'

function App() {
  const { commandOpen } = useStore()

  return (
    <div className="min-h-screen bg-apple-bg">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/study/:studyId" element={<MorningBrief />} />
        <Route path="/study/:studyId/overview" element={<Study360 />} />
        <Route path="/study/:studyId/sites" element={<StudyCommandCenter />} />
        <Route path="/study/:studyId/sites/:siteId" element={<SiteDossier />} />
        <Route path="/study/:studyId/vendors" element={<VendorDashboard />} />
        <Route path="/study/:studyId/financials" element={<FinancialDashboard />} />
        <Route path="/study/:studyId/signals" element={<SignalCenter />} />
        <Route path="/study/:studyId/directives" element={<DirectiveStudio />} />
        <Route path="/study/:studyId/history" element={<InvestigationArchive />} />
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
