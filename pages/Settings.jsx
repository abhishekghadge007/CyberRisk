import { useEffect, useState } from 'react'
import { Save, ShieldCheck, Database, Server, Bell } from 'lucide-react'
import { Panel, PageTitle } from '../components/UI'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
const ALERTS_KEY = 'cyberrisk_security_alerts'

function Settings() {
  const [alerts, setAlerts] = useState(true)
  const [saved, setSaved] = useState(false)
  const [apiStatus, setApiStatus] = useState('Checking...')
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem(ALERTS_KEY)

    if (stored !== null) {
      setAlerts(stored === 'true')
    }
  }, [])

  useEffect(() => {
    let active = true

    async function checkBackend() {
      setChecking(true)

      try {
        const response = await fetch(
          `${API_URL.replace(/\/$/, '').replace(/\/api$/, '')}/openapi.json`
        )

        if (!response.ok) {
          throw new Error('Backend unavailable')
        }

        if (active) setApiStatus('Connected')
      } catch {
        if (active) setApiStatus('Unavailable')
      } finally {
        if (active) setChecking(false)
      }
    }

    checkBackend()

    return () => {
      active = false
    }
  }, [])

  const savePreferences = () => {
    localStorage.setItem(ALERTS_KEY, String(alerts))
    setSaved(true)
  }

  return (
    <div className="space-y-6">
      <PageTitle
        title="Settings"
        desc="Manage application preferences and inspect system connectivity."
      />

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Notification preferences" subtitle="Local browser preferences">
          <div className="space-y-5">
            <label className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="rounded-xl bg-teal-400/10 p-2 text-teal-300">
                  <Bell size={19} />
                </div>
                <div>
                  <p className="text-sm font-medium text-white">Security alerts</p>
                  <p className="text-xs text-slate-500">
                    Enable the preference for critical and high-risk alerts.
                  </p>
                </div>
              </div>

              <input
                type="checkbox"
                checked={alerts}
                onChange={(e) => {
                  setAlerts(e.target.checked)
                  setSaved(false)
                }}
                className="h-4 w-4 accent-teal-400"
              />
            </label>

            <button
              onClick={savePreferences}
              className="btn-primary flex items-center gap-2"
            >
              <Save size={15} />
              Save preferences
            </button>

            {saved && (
              <p className="text-xs text-emerald-300">
                Preference saved in this browser.
              </p>
            )}

            <p className="text-xs leading-5 text-slate-500">
              This setting stores your preference locally. It does not yet
              configure email, SMS or push notifications.
            </p>
          </div>
        </Panel>

        <Panel title="Backend connectivity" subtitle="Live connection check">
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <Server size={19} className="text-teal-300" />
                <span className="text-sm text-slate-300">FastAPI backend</span>
              </div>

              <span
                className={`text-xs font-semibold ${
                  apiStatus === 'Connected'
                    ? 'text-emerald-300'
                    : apiStatus === 'Unavailable'
                      ? 'text-rose-300'
                      : 'text-amber-300'
                }`}
              >
                {checking ? 'Checking...' : apiStatus}
              </span>
            </div>

            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <Database size={19} className="text-teal-300" />
                <span className="text-sm text-slate-300">Database</span>
              </div>
              <span className="text-xs text-slate-500">
                PostgreSQL · Via backend
              </span>
            </div>

            <p className="break-all border-t border-slate-800 pt-3 text-xs text-slate-500">
              API: {API_URL}
            </p>
          </div>
        </Panel>

        <Panel title="Security status" subtitle="Application security information">
          <div className="flex items-center gap-3">
            <ShieldCheck size={21} className="text-amber-300" />
            <div>
              <p className="text-sm font-medium text-white">
                Frontend authentication not integrated
              </p>
              <p className="mt-1 text-xs leading-5 text-slate-500">
                Backend authentication capabilities and frontend login
                integration should be verified separately before deployment.
              </p>
            </div>
          </div>
        </Panel>

        <Panel title="System information" subtitle="Application configuration">
          <div className="space-y-3 text-sm">
            <div className="flex justify-between gap-3">
              <span className="text-slate-500">Application</span>
              <b>CyberRisk</b>
            </div>

            <div className="flex justify-between gap-3">
              <span className="text-slate-500">Architecture</span>
              <b>React + FastAPI</b>
            </div>

            <div className="flex justify-between gap-3">
              <span className="text-slate-500">Database</span>
              <b>PostgreSQL</b>
            </div>

            <div className="flex justify-between gap-3">
              <span className="text-slate-500">Optimization</span>
              <b>Google OR-Tools</b>
            </div>

            <div className="flex justify-between gap-3">
              <span className="text-slate-500">Data source</span>
              <b className="text-teal-300">Backend APIs</b>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  )
}

export default Settings
