import { create } from 'zustand'

export const useStore = create((set, get) => ({
  view: 'home',
  setView: (view) => set({ view }),

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
    // Deduplicate: skip if the last phase for this agent has the same phase name and iteration
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

  commandOpen: false,
  setCommandOpen: (open) => set({ commandOpen: open }),
  toggleCommand: () => set((state) => ({ commandOpen: !state.commandOpen })),

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
      useStore.getState().setInvestigation(null)
    }
  })
}
