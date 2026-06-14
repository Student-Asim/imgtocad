import { NavLink, Route, Routes } from 'react-router-dom';
import { LayoutDashboard, ImageUp, TimerReset, PanelsTopLeft } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import GenerateSync from './pages/GenerateSync';
import GenerateAsync from './pages/GenerateAsync';

function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 48 48" fill="none">
              <path
                d="M10 33L24 12L38 33"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M16 33V38H32V33"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M21 25H27"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
              />
            </svg>
          </div>

          <div>
            <p className="eyebrow">AI Floorplan</p>
            <h1>Plan Studio</h1>
          </div>
        </div>

        <nav className="nav">
          <NavLink to="/" end className="nav-link">
            <LayoutDashboard size={18} />
            <span>Dashboard</span>
          </NavLink>

          <NavLink to="/generate" className="nav-link">
            <ImageUp size={18} />
            <span>Generate</span>
          </NavLink>

          <NavLink to="/generate-async" className="nav-link">
            <TimerReset size={18} />
            <span>Async Generate</span>
          </NavLink>
        </nav>

        <div className="sidebar-card">
          <PanelsTopLeft size={18} />
          <p>
            Minimal AI-style dashboard with neutral surfaces, teal accents, and room for debug output.
          </p>
        </div>
      </aside>

      <main className="main-panel">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/generate" element={<GenerateSync />} />
          <Route path="/generate-async" element={<GenerateAsync />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;