export function ViewShell({ title, subtitle, actions, children }) {
  return (
    <div className="view-shell">
      <header className="view-header">
        <div>
          <h1 className="view-title">{title}</h1>
          {subtitle && <p className="view-subtitle">{subtitle}</p>}
        </div>
        {actions && <div className="view-actions">{actions}</div>}
      </header>
      <div className="view-body">{children}</div>
    </div>
  )
}
