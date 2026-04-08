export function TabBar({ tabs, active, onChange, counts = {} }) {
  return (
    <div className="tab-bar" role="tablist">
      {tabs.map(tab => {
        const isActive = active === tab.key
        const count = counts[tab.key]
        return (
          <button
            key={tab.key}
            className={`tab-bar-item ${isActive ? 'tab-bar-item--active' : ''}`}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.key)}
          >
            {tab.icon && tab.icon}
            {tab.label}
            {count != null && (
              <span className="tab-bar-count">{count}</span>
            )}
          </button>
        )
      })}
    </div>
  )
}
