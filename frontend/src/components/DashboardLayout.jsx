import { NavLink, Outlet, useNavigate } from 'react-router-dom'

const navItems = [
  { to: '/patients', label: 'Patients' },
  { to: '/service-requests', label: 'Service Requests' },
  { to: '/conditions', label: 'Conditions' },
  { to: '/medication-requests', label: 'Medications' },
  // { to: '/api-explorer', label: 'API Explorer' },
  { to: '/encounters', label: 'Encounters' },
]

export default function DashboardLayout() {
  const navigate = useNavigate()

  function handleLogout() {
    localStorage.removeItem('access_token')
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex h-screen bg-gray-100 text-gray-800">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 bg-slate-800 text-slate-100 flex flex-col">
        <div className="px-5 py-4 border-b border-slate-700">
          <h1 className="text-lg font-semibold tracking-wide">HIS · HIS</h1>
          <p className="text-xs text-slate-400">FHIR Integration</p>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-slate-600 text-white'
                    : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
          <span className="text-sm text-gray-500">HIS-HIS FHIR Dashboard</span>
          <button
            onClick={handleLogout}
            className="text-sm text-slate-600 hover:text-slate-900 font-medium transition-colors"
          >
            Sign out
          </button>
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
