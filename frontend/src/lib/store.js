import { create } from 'zustand'

export const useStore = create((set, get) => ({
  // Default study ID — used by all study routes
  currentStudyId: 'STUDY-001',
  setCurrentStudyId: (id) => set({ currentStudyId: id }),

  selectedSite: null,
  setSelectedSite: (site) => set({ selectedSite: site }),

  investigation: null,
  setInvestigation: (investigation) => set({
    investigation,
    investigationPhases: [],
    investigationResult: null,
    investigationError: null,
  }),

  // Investigation streaming state
  investigationPhases: [],
  addInvestigationPhase: (phase) => set((state) => {
    const existing = state.investigationPhases
    const last = [...existing].reverse().find(p => p.agent_id === phase.agent_id)
    if (last && last.phase === phase.phase && last.data?.iteration === phase.data?.iteration) {
      return state
    }
    return { investigationPhases: [...existing, phase] }
  }),

  investigationResult: null,
  setInvestigationResult: (result) => set({ investigationResult: result }),

  investigationError: null,
  setInvestigationError: (error) => set({ investigationError: error }),

  // Current investigation query_id for persistence
  investigationQueryId: null,
  setInvestigationQueryId: (id) => set({ investigationQueryId: id }),

  commandOpen: false,
  setCommandOpen: (open) => set({ commandOpen: open }),
  toggleCommand: () => set((state) => ({ commandOpen: !state.commandOpen })),

  commandQuery: '',
  setCommandQuery: (q) => set({ commandQuery: q }),
  openCommandWithQuery: (q) => set({ commandOpen: true, commandQuery: q }),

  activeTheme: null,
  setActiveTheme: (theme) => set({ activeTheme: theme }),
  clearActiveTheme: () => set({ activeTheme: null }),

  // Time lens — global temporal control
  timeLens: '1M',
  setTimeLens: (lens) => set({ timeLens: lens }),

  studyData: {
    enrolled: 0,
    target: 0,
    criticalSites: 0,
    watchSites: 0,
    studyName: '',
    lastUpdated: null
  },
  setStudyData: (data) => set({ studyData: data }),

  sites: [],
  setSites: (sites) => set({ sites }),

  siteNameMap: {},
  setSiteNameMap: (map) => set({ siteNameMap: map }),

  alerts: [],
  setAlerts: (alerts) => set({ alerts })
}))

if (typeof window !== 'undefined') {
  window.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault()
      useStore.getState().toggleCommand()
    }
    if (e.key === 'Escape') {
      useStore.getState().setCommandOpen(false)
      useStore.getState().setSelectedSite(null)
      useStore.getState().clearActiveTheme()
    }
  })
}
