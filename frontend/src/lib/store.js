import { create } from 'zustand'

export const useStore = create((set, get) => ({
  view: 'home',
  setView: (view) => set({ view }),
  
  selectedSite: null,
  setSelectedSite: (site) => set({ selectedSite: site }),
  
  investigation: null,
  setInvestigation: (investigation) => set({ investigation }),
  
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
