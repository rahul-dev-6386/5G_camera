export default function AuthView({ authMode, setAuthMode, authForm, setAuthForm, authError, validationErrors, onSubmit, theme, onToggleTheme, dbStatus }) {
  return (
    <div className="auth-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />
      <div className="auth-grid">
        <div className="auth-intro">
          <p className="section-eyebrow">Smart Campus Control</p>
          <h1>Enterprise monitoring for occupancy, attendance, and network performance.</h1>
          <p className="hero-text">
                 Secure classroom operations in one interface with 5G-ready monitoring, and review occupancy evidence with a cleaner operator workflow.
          </p>
          <div className="feature-list">
            <div className="feature-item">
              <strong>Operational clarity</strong>
              <span>Separate live monitoring, analytics, and review workflows.</span>
            </div>
            <div className="feature-item">
              <strong>Context-based tracking</strong>
              <span>Manage attendance by room and course without mixing sessions.</span>
            </div>
            <div className="feature-item">
              <strong>Audit-ready history</strong>
              <span>Inspect latency and occupancy trends with stored evidence logs.</span>
            </div>
          </div>
        </div>

        <div className="auth-card">
          <div className="auth-toolbar">
            <button type="button" className="secondary-btn compact-btn" onClick={onToggleTheme}>
              {theme === "dark" ? "Light Mode" : "Dark Mode"}
            </button>
            {dbStatus && (
              <div className="db-status-badge">
                <span className={`db-indicator db-${dbStatus.type}`}></span>
                DB: {dbStatus.type === "mongodb" ? (dbStatus.mongodb_connected ? "MongoDB" : "MongoDB (disconnected)") : "Local JSON"}
              </div>
            )}
          </div>
          <p className="section-eyebrow">Secure Access</p>
          <h2 className="auth-heading">Operator sign-in</h2>
          <p className="section-copy">Use your dashboard credentials to continue, or create an operator account for your lab team.</p>
          <div className="segmented-control auth-toggle">
            {["login", "signup"].map((mode) => (
              <button
                key={mode}
                type="button"
                className={authMode === mode ? "segment active" : "segment"}
                onClick={() => setAuthMode(mode)}
              >
                {mode === "login" ? "Login" : "Create account"}
              </button>
            ))}
          </div>
          <form className="auth-form" onSubmit={onSubmit}>
            {authMode === "signup" ? (
              <label className="field">
                <span>Full Name</span>
                <input
                  type="text"
                  value={authForm.fullName}
                  onChange={(event) => setAuthForm((current) => ({ ...current, fullName: event.target.value }))}
                  required
                  className={validationErrors?.fullName ? "input-error" : ""}
                />
                {validationErrors?.fullName ? (
                  <span className="field-error">{validationErrors.fullName}</span>
                ) : null}
              </label>
            ) : null}
            <label className="field">
              <span>Username</span>
              <input
                type="text"
                value={authForm.username}
                onChange={(event) => setAuthForm((current) => ({ ...current, username: event.target.value }))}
                required
                className={validationErrors?.username ? "input-error" : ""}
              />
              {validationErrors?.username ? (
                <span className="field-error">{validationErrors.username}</span>
              ) : null}
            </label>
            <label className="field">
              <span>Password</span>
              <input
                type="password"
                value={authForm.password}
                onChange={(event) => setAuthForm((current) => ({ ...current, password: event.target.value }))}
                required
                className={validationErrors?.password ? "input-error" : ""}
              />
              {validationErrors?.password ? (
                <span className="field-error">{validationErrors.password}</span>
              ) : null}
              {authMode === "signup" ? (
                <span className="field-hint">
                  Min 8 chars with uppercase, lowercase, and digit
                </span>
              ) : null}
            </label>
            {authError ? <div className="error-banner">{authError}</div> : null}
            <button type="submit" className="primary-btn wide-btn">
              {authMode === "login" ? "Open Dashboard" : "Create Operator Account"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
