import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { useAppStore } from './store/app';
import TraceList from './pages/TraceList';
import TraceDetail from './pages/TraceDetail';
import CostAnalytics from './pages/CostAnalytics';
import DriftMonitor from './pages/DriftMonitor';
import Settings from './pages/Settings';

const navItems = [
  { to: '/traces', label: 'Traces', icon: '⊞' },
  { to: '/analytics', label: 'Cost Analytics', icon: '$' },
  { to: '/drift', label: 'Drift Monitor', icon: '~' },
  { to: '/settings', label: 'Settings', icon: '⚙' },
];

export default function App() {
  const { sidebarOpen, toggleSidebar } = useAppStore();

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? 'w-56' : 'w-14'
        } flex flex-col bg-gray-900 text-gray-100 transition-all duration-200`}
      >
        <div className="flex h-14 items-center justify-between px-3">
          {sidebarOpen && (
            <span className="text-lg font-bold tracking-tight">AgentTrace</span>
          )}
          <button
            onClick={toggleSidebar}
            className="rounded p-1 hover:bg-gray-700"
            aria-label="Toggle sidebar"
          >
            {sidebarOpen ? '\u2190' : '\u2192'}
          </button>
        </div>

        <nav className="mt-4 flex-1 space-y-1 px-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-primary text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`
              }
            >
              <span className="text-base">{item.icon}</span>
              {sidebarOpen && <span>{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-gray-700 p-3 text-xs text-gray-500">
          {sidebarOpen && 'AgentTrace v0.1.0'}
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-gray-50">
        <Routes>
          <Route path="/" element={<Navigate to="/traces" replace />} />
          <Route path="/traces" element={<TraceList />} />
          <Route path="/traces/:traceId" element={<TraceDetail />} />
          <Route path="/analytics" element={<CostAnalytics />} />
          <Route path="/drift" element={<DriftMonitor />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
