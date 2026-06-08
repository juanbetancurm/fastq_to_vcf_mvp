import { Outlet, Link, useLocation } from 'react-router-dom'

export default function Layout() {
  const { pathname } = useLocation()
  const nav = (path) =>
    `text-sm ${pathname === path ? 'text-blue-600 font-medium' : 'text-gray-600 hover:text-gray-900'}`

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 flex items-center gap-8 h-14">
          <span className="font-semibold text-gray-900 text-sm">IEI Platform</span>
          <Link to="/"       className={nav('/')}>Runs</Link>
          <Link to="/upload" className={nav('/upload')}>New Analysis</Link>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
