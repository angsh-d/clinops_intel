import { motion } from 'framer-motion'
import { useStore } from '../lib/store'

export function Pulse() {
  const { studyData, setView } = useStore()
  const percentage = Math.round((studyData.enrolled / studyData.target) * 100 * 10) / 10
  
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen flex flex-col items-center justify-center px-6 cursor-pointer"
      onClick={() => setView('constellation')}
    >
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1, duration: 0.5 }}
        className="text-center max-w-2xl"
      >
        <p className="text-caption text-apple-secondary mb-8 tracking-wide uppercase">
          {studyData.studyName}
        </p>
        
        <div className="mb-8">
          <motion.span 
            className="text-hero text-apple-text font-light tracking-tight"
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring', stiffness: 100 }}
          >
            {studyData.enrolled}
          </motion.span>
          <span className="text-hero text-apple-secondary font-light"> / {studyData.target}</span>
        </div>
        
        <div className="relative w-full max-w-md mx-auto mb-8">
          <div className="h-2 bg-apple-border rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-apple-text rounded-full animate-pulse-slow"
              initial={{ width: 0 }}
              animate={{ width: `${percentage}%` }}
              transition={{ delay: 0.4, duration: 1, ease: 'easeOut' }}
            />
          </div>
        </div>
        
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="text-title text-apple-text mb-4"
        >
          {percentage}% enrolled
        </motion.p>
        
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="text-body text-apple-secondary"
        >
          <span className="text-apple-critical">{studyData.criticalSites} sites</span> need attention
          <span className="mx-2">·</span>
          <span className="text-apple-warning">{studyData.watchSites}</span> on watch
        </motion.p>
        
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2 }}
          className="text-caption text-apple-secondary/60 mt-12"
        >
          Click anywhere to explore
        </motion.p>
      </motion.div>
      
      <CommandHint />
    </motion.div>
  )
}

function CommandHint() {
  const { toggleCommand } = useStore()
  
  return (
    <motion.button
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 1.5 }}
      onClick={(e) => {
        e.stopPropagation()
        toggleCommand()
      }}
      className="fixed bottom-8 left-1/2 -translate-x-1/2 flex items-center gap-2 px-4 py-2 
                 bg-apple-surface border border-apple-border rounded-full shadow-apple
                 text-caption text-apple-secondary hover:text-apple-text transition-colors"
    >
      <kbd className="px-1.5 py-0.5 bg-apple-bg rounded text-xs font-mono">⌘K</kbd>
      <span>Ask anything</span>
    </motion.button>
  )
}
