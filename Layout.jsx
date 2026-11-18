
import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard, Boxes, ShieldAlert, Gauge, Monitor, BrainCircuit,
  Target, FileText, Settings as SettingsIcon, Bell, Menu, X, ShieldCheck,
  Activity,
} from 'lucide-react'

const nav = [
  ['Overview', '/', LayoutDashboard],
  ['Asset Inventory', '/assets', Boxes],
  ['Vulnerabilities', '/vulnerabilities', ShieldAlert],
  ['Risk Assessment', '/risk', Gauge],
  ['Monitoring', '/monitoring', Monitor],
  ['AI Prediction', '/prediction', BrainCircuit],
  ['Investment Optimization', '/optimization', Target],
  ['API Activity', '/api-activity', Activity],
  ['Reports', '/reports', FileText],
  ['Settings', '/settings', SettingsIcon],
]

function Layout() {
  const [mobile, setMobile] = useState(false)

  return (
    <div className="min-h-screen bg-[#080d18] text-slate-200">
      {mobile && (
        <button
          onClick={() => setMobile(false)}
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
          aria-label="Close menu"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-800 bg-[#0c1422] transition-transform lg:translate-x-0 ${
          mobile ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-20 items-center gap-3 border-b border-slate-800 px-6">
          <div className="rounded-xl bg-teal-400/10 p-2.5 text-teal-300">
            <ShieldCheck size={24} />
          </div>

          <div>
            <p className="text-lg font-bold text-white">
              Cyber<span className="text-teal-400">Risk</span>
            </p>
            <p className="text-[10px] uppercase tracking-[.2em] text-slate-500">
              Risk intelligence
            </p>
          </div>

          <button
            className="ml-auto lg:hidden"
            onClick={() => setMobile(false)}
            aria-label="Close navigation"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-4 pt-6">
          <p className="px-3 pb-3 text-[10px] font-bold uppercase tracking-[.18em] text-slate-500">
            Workspace
          </p>

          <nav className="space-y-1">
            {nav.map(([label, path, Icon]) => (
              <NavLink
                key={path}
                to={path}
                end={path === '/'}
                onClick={() => setMobile(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium ${
                    isActive
                      ? 'bg-teal-400/10 text-teal-300'
                      : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                  }`
                }
              >
                <Icon size={17} />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="mt-auto p-4">
          <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
            <p className="text-xs font-semibold text-teal-300">
              Risk intelligence
            </p>
            <p className="mt-2 text-xs leading-5 text-slate-500">
              Monitor assets, analyze security findings, assess cyber risk
              and optimize security investments.
            </p>
          </div>

          <p className="mt-4 text-center text-[10px] text-slate-600">
            CYBERRISK PLATFORM
          </p>
        </div>
      </aside>

      <main className="min-h-screen lg:pl-64">
        <header className="sticky top-0 z-20 flex h-20 items-center justify-between border-b border-slate-800 bg-[#080d18]/90 px-5 backdrop-blur-xl md:px-8">
          <div className="flex items-center gap-3">
            <button
              className="lg:hidden"
              onClick={() => setMobile(true)}
              aria-label="Open navigation"
            >
              <Menu size={21} />
            </button>

            <div>
              <p className="text-xs muted">CyberRisk / Workspace</p>
              <p className="mt-1 font-semibold text-white">
                Security platform
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden items-center gap-2 rounded-full border border-slate-800 px-3 py-2 text-xs text-slate-400 sm:flex">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              Connected workspace
            </span>

            <button
              className="rounded-xl border border-slate-800 p-2.5 text-slate-400"
              aria-label="Notifications"
              title="Notifications"
            >
              <Bell size={18} />
            </button>

            <div
              className="grid h-9 w-9 place-items-center rounded-full bg-teal-400/15 text-xs font-bold text-teal-300"
              title="CyberRisk"
            >
              CR
            </div>
          </div>
        </header>

        <div className="mx-auto max-w-[1600px] p-5 md:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

export default Layout
