import { useEffect, useState } from 'react'
import { Activity, Target, ShieldCheck, ShieldAlert } from 'lucide-react'
import api from '../../services_api'
import { Metric, Panel, PageTitle } from '../components/UI'

function APIActivity() {
  const [source, setSource] = useState('Swagger UI')
  const [summary, setSummary] = useState(null)
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadActivity = async () => {
    setLoading(true)
    setError('')

    try {
      const [summaryResponse, logsResponse] = await Promise.all([
        api.get('/api-activity/summary', {
          params: { source },
        }),
        api.get('/api-activity/logs', {
          params: { source, limit: 100 },
        }),
      ])

      setSummary(summaryResponse.data)
      setLogs(logsResponse.data)
    } catch (err) {
      console.error('API activity loading failed:', err)

      setError(
        err.response?.data?.detail ||
        'Unable to load API activity. Check whether the backend is running.'
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadActivity()
  }, [source])

  const formatDate = (value) => {
    if (!value) return '—'

    return new Date(value).toLocaleString('en-IN', {
      dateStyle: 'medium',
      timeStyle: 'medium',
    })
  }

  const statusClass = (code) => {
    if (code >= 200 && code < 400) {
      return 'bg-emerald-500/15 text-emerald-300'
    }

    if (code >= 400) {
      return 'bg-rose-500/15 text-rose-300'
    }

    return 'bg-slate-500/15 text-slate-300'
  }

  return (
    <div className="space-y-6">
      <PageTitle
        title="API Activity Monitoring"
        desc="Track API endpoint usage, Swagger testing activity and request performance."
        extra={
          <button
            onClick={loadActivity}
            disabled={loading}
            className="btn-primary flex items-center gap-2 text-xs disabled:opacity-50"
          >
            <Activity size={15} />
            {loading ? 'Refreshing...' : 'Refresh activity'}
          </button>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium text-white">Request source</p>
          <p className="mt-1 text-xs muted">
            Select which API requests you want to inspect.
          </p>
        </div>

        <select
          className="field w-full sm:max-w-xs"
          value={source}
          onChange={(e) => setSource(e.target.value)}
        >
          <option value="Swagger UI">Swagger UI</option>
          <option value="ReDoc">ReDoc</option>
          <option value="Other">Other / Frontend</option>
        </select>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
          {error}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          label="Total API requests"
          value={summary?.total_requests ?? '—'}
          detail="Recorded requests"
          Icon={Activity}
        />

        <Metric
          label="Unique endpoints tested"
          value={summary?.unique_endpoints ?? '—'}
          detail="Distinct observed URL paths"
          Icon={Target}
          tone="blue"
        />

        <Metric
          label="Successful requests"
          value={summary?.successful_requests ?? '—'}
          detail="HTTP status 200–399"
          Icon={ShieldCheck}
        />

        <Metric
          label="Failed requests"
          value={summary?.failed_requests ?? '—'}
          detail="HTTP status 400 and above"
          Icon={ShieldAlert}
          tone="rose"
        />
      </div>

      <Panel
        title="API request history"
        subtitle={`Latest recorded requests from ${source}`}
      >
        {loading ? (
          <div className="py-12 text-center text-sm muted">
            Loading API activity...
          </div>
        ) : logs.length === 0 ? (
          <div className="py-12 text-center">
            <Activity className="mx-auto mb-3 text-slate-500" size={35} />
            <p className="text-sm font-medium text-white">
              No API requests found
            </p>
            <p className="mt-2 text-xs muted">
              Execute an API endpoint in Swagger UI and refresh this page.
            </p>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Endpoint</th>
                  <th>Method</th>
                  <th>Status</th>
                  <th>Response time</th>
                  <th>Source</th>
                  <th>Timestamp</th>
                </tr>
              </thead>

              <tbody>
                {logs.map((log) => (
                  <tr key={log.log_id}>
                    <td>
                      <code className="text-xs text-teal-300">
                        {log.endpoint}
                      </code>
                      <p className="mt-1 text-[10px] text-slate-500">
                        Request ID: {log.log_id}
                      </p>
                    </td>

                    <td>
                      <span className="rounded-md bg-slate-800 px-2 py-1 text-xs font-semibold text-white">
                        {log.method}
                      </span>
                    </td>

                    <td>
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusClass(log.status_code)}`}
                      >
                        {log.status_code}
                      </span>
                    </td>

                    <td className="font-medium">
                      {log.response_time_ms ?? '—'} ms
                    </td>

                    <td className="text-xs muted">
                      {log.source}
                    </td>

                    <td className="text-xs muted">
                      {formatDate(log.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <p className="mt-4 text-xs muted">
          Showing up to 100 most recent requests. API activity dashboard
          requests are excluded from tracking to prevent counting itself.
        </p>
      </Panel>
    </div>
  )
}

export default APIActivity