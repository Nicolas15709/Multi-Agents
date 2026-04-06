import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useSnapshot } from './useSnapshot'
import { OfficeCustomizer, loadOfficeConfig } from './components/OfficeCustomizer'
import { createCustomAgent, loadCustomAgents, mergeAgents, saveCustomAgents } from './components/agentProfiles'
import { NavSidebar } from './components/NavSidebar'
import { TopBar } from './components/TopBar'
import { ToastContainer, useToasts, useEventToasts } from './components/Toast'

import { OverviewView }   from './components/views/OverviewView'
import { MissionsView }   from './components/views/MissionsView'
import { AgentsView }     from './components/views/AgentsView'
import { TasksView }      from './components/views/TasksView'
import { TimelineView }   from './components/views/TimelineView'
import { TemplatesView }  from './components/views/TemplatesView'
import { SystemView }     from './components/views/SystemView'
import { SettingsView }   from './components/views/SettingsView'

function ViewRouter({ view, onViewChange, ...props }) {
  switch (view) {
    case 'overview':   return <OverviewView  {...props} />
    case 'missions':   return <MissionsView  {...props} />
    case 'agents':     return <AgentsView    {...props} />
    case 'tasks':      return <TasksView     {...props} />
    case 'timeline':   return <TimelineView  {...props} />
    case 'templates':  return <TemplatesView {...props} onViewChange={onViewChange} />
    case 'system':     return <SystemView    {...props} />
    case 'settings':   return <SettingsView  {...props} />
    default:           return <OverviewView  {...props} />
  }
}

export default function App() {
  const { snapshot, status, connection } = useSnapshot()
  const [officeConfig, setOfficeConfig] = useState(() => loadOfficeConfig())
  const [customAgents, setCustomAgents] = useState(() => loadCustomAgents())
  const [showCustomizer, setShowCustomizer] = useState(false)
  const [activeView, setActiveView] = useState('overview')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const { toasts, addToast, dismiss } = useToasts()

  const toggleSidebar = useCallback(() => setSidebarCollapsed(v => !v), [])

  // Loading state
  if (!snapshot) {
    return (
      <div className="loading-screen">
        <div className="loading-brand">{officeConfig.name.toUpperCase()}</div>
        <div style={{ opacity: 0.5, fontSize: '13px' }}>Sincronizando con el sistema...</div>
        {status.error && (
          <div style={{ color: 'var(--danger)', fontSize: '11px', marginTop: '8px' }}>
            Error: {status.error}
          </div>
        )}
      </div>
    )
  }

  const {
    activeMission,
    missions = [],
    agents: runtimeAgents = [],
    tasks = [],
    intakeRequests = [],
    hireRequests = [],
    stream = { events: [], notifications: [] },
    meta = {},
  } = snapshot
  const progress = snapshot?.progress || null
  const agents = mergeAgents(runtimeAgents, customAgents)

  // Toast notifications for runtime events
  useEventToasts(stream.events, addToast)

  function handleCreateAgent(input) {
    setCustomAgents((current) => {
      const next = [...current, createCustomAgent(input, [...agents, ...current])]
      saveCustomAgents(next)
      return next
    })
  }

  const viewProps = {
    activeMission,
    missions,
    agents,
    tasks,
    intakeRequests,
    hireRequests,
    stream,
    progress,
    officeConfig,
    connection,
    onCreateAgent: handleCreateAgent,
  }

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4 }}
        style={{ flexShrink: 0 }}
      >
        <NavSidebar
          officeConfig={officeConfig}
          agents={agents}
          activeMission={activeMission}
          activeView={activeView}
          collapsed={sidebarCollapsed}
          onViewChange={setActiveView}
          onOpenCustomizer={() => setShowCustomizer(true)}
        />
      </motion.div>

      {/* Main Area */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <TopBar
          view={activeView}
          status={status}
          connection={connection}
          sidebarCollapsed={sidebarCollapsed}
          onToggleSidebar={toggleSidebar}
          officeConfig={officeConfig}
          meta={{ agentCount: agents.length, taskCount: tasks.length, missionCount: missions.length, ...meta }}
        />

        <AnimatePresence mode="wait">
          <motion.div
            key={activeView}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minHeight: 0 }}
          >
            <ViewRouter
              view={activeView}
              onViewChange={setActiveView}
              {...viewProps}
            />
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      {/* Office Customizer Modal */}
      <AnimatePresence>
        {showCustomizer && (
          <OfficeCustomizer
            config={officeConfig}
            onSave={cfg => setOfficeConfig(cfg)}
            onClose={() => setShowCustomizer(false)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
