
import { useCallback, useEffect, useState } from 'react'
import {
  Wifi,
  Cpu,
  Activity,
  HardDrive,
  RefreshCw,
  AlertTriangle,
  Server,
} from 'lucide-react'

import api from '../../services_api'
import { Badge, Panel, PageTitle } from '../components/UI'

const ORGANIZATION_ID = 6

function extractArray(data, keys = []) {
  if (Array.isArray(data)) return data

  for (const key of keys) {
    if (Array.isArray(data?.[key])) return data[key]
  }

  return []
}

function getMetricValue(metric, keys) {
  for (const key of keys) {
    const value = metric?.[key]
    if (value !== undefined && value !== null && value !== '') {
      const number = Number(value)
      return Number.isFinite(number) ? number : value
    }
  }

  return null
}

function formatMetric(value, suffix = '') {
  return value == null ? '—' : `${Number(value).toFixed(1)}${suffix}`
}

function getTimestamp(metric) {
  const value =
    metric?.recorded_at ||
    metric?.collected_at ||
    metric?.timestamp ||
    metric?.created_at

  if (!value) return null

  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function formatTime(value) {
  if (!value) return 'Time unavailable'

  return value.toLocaleString()
}

function Monitoring() {
  const [assets, setAssets] = useState([])
  const [metrics, setMetrics] = useState([])
  const [findings, setFindings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  const loadMonitoringData = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const results = await Promise.allSettled([
        api.get('/assets/', {
          params: { organization_id: ORGANIZATION_ID },
        }),
        api.get('/asset-metrics/', {
          params: { organization_id: ORGANIZATION_ID, limit: 100 },
        }),
        api.get('/risk-findings/', {
          params: { organization_id: ORGANIZATION_ID },
        }),
      ])

      const errors = []

      if (results[0].status === 'fulfilled') {
        setAssets(
          extractArray(results[0].value.data, ['assets', 'items', 'results'])
        )
      } else {
        setAssets([])
        errors.push('asset inventory')
      }

      if (results[1].status === 'fulfilled') {
        setMetrics(
          extractArray(results[1].value.data, ['metrics', 'items', 'results'])
        )
      } else {
        setMetrics([])
        errors.push('system telemetry')
      }

      if (results[2].status === 'fulfilled') {
        setFindings(
          extractArray(results[2].value.data, ['findings', 'items', 'results'])
        )
      } else {
        setFindings([])
        errors.push('security findings')
      }

      if (errors.length) {
        setError(`Unable to load ${errors.join(', ')}. Check backend availability and API access.`)
      }
    } catch {
      setError('Unable to load monitoring data. Check your backend connection.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadMonitoringData()
  }, [loadMonitoringData, refreshKey])

  // Keep the newest telemetry record for each asset.
  const latestByAsset = {}

  for (const metric of metrics) {
    const id = metric.asset_id
    if (id == null) continue

    const current = latestByAsset[id]
    const currentTime = getTimestamp(current)
    const newTime = getTimestamp(metric)

    if (
      !current ||
      (newTime && (!currentTime || newTime > currentTime))
    ) {
      latestByAsset[id] = metric
    }
  }

  const monitoredAssets = assets.filter(
    (asset) => latestByAsset[asset.asset_id]
  )

  const latestMetric = monitoredAssets.length
    ? latestByAsset[monitoredAssets[0].asset_id]
    : null

  const cpu = getMetricValue(latestMetric, [
    'cpu_usage',
    'cpu_percent',
    'cpu_usage_percent',
    'cpu',
  ])

  const memory = getMetricValue(latestMetric, [
    'memory_usage',
    'memory_percent',
    'memory_usage_percent',
    'memory',
  ])

  const disk = getMetricValue(latestMetric, [
    'disk_usage',
    'disk_percent',
    'disk_usage_percent',
    'disk',
  ])

  const networkIn = getMetricValue(latestMetric, [
    'network_in',
    'network_in_bytes',
    'network_in_bytes_per_sec',
    'network_received',
  ])

  const networkOut = getMetricValue(latestMetric, [
    'network_out',
    'network_out_bytes',
    'network_out_bytes_per_sec',
    'network_sent',
  ])

  const openFindings = findings.filter((finding) => {
    const status = String(finding.status || 'Open').toLowerCase()
    return !['closed', 'resolved', 'accepted', 'false positive'].includes(status)
  })

  const recentEvents = [...openFindings]
    .sort((a, b) => {
      const dateA = getTimestamp(a)?.getTime() || 0
      const dateB = getTimestamp(b)?.getTime() || 0
      return dateB - dateA
    })
    .slice(0, 10)

  const anomalyCount = openFindings.filter((finding) =>
    String(finding.category || '').toLowerCase().includes('anomal')
  ).length

  const MetricCard = ({ label, value, detail, Icon }) => (
    <div className="panel p-5">
      <div className="flex justify-between gap-2">
        <p className="text-sm muted">{label}</p>
        <Icon className="text-teal-300" size={18} />
      </div>
      <p className="mt-3 text-2xl font-bold text-white">{value}</p>
      <p className="mt-1 text-xs muted">{detail}</p>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageTitle
        title="Continuous monitoring"
        desc="Live endpoint telemetry and security findings collected by the monitoring services."
        extra={
          <button
            onClick={() => setRefreshKey((value) => value + 1)}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-medium text-slate-200 hover:bg-slate-700 disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        }
      />

      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-200">
          <AlertTriangle size={18} className="mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">Monitoring data warning</p>
            <p className="mt-1 text-amber-200/80">{error}</p>
          </div>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Monitored assets"
          value={loading ? '...' : monitoredAssets.length}
          detail={`${assets.length} assets in inventory`}
          Icon={Wifi}
        />

        <MetricCard
          label="CPU utilization"
          value={loading ? '...' : formatMetric(cpu, '%')}
          detail="Latest available telemetry"
          Icon={Cpu}
        />

        <MetricCard
          label="Memory utilization"
          value={loading ? '...' : formatMetric(memory, '%')}
          detail="Latest available telemetry"
          Icon={Activity}
        />

        <MetricCard
          label="Disk utilization"
          value={loading ? '...' : formatMetric(disk, '%')}
          detail="Latest available telemetry"
          Icon={HardDrive}
        />
      </div>

      <Panel
        title="Monitored asset telemetry"
        subtitle="Latest recorded system metrics for each asset with available observations."
      >
        {loading ? (
          <p className="py-8 text-center text-sm muted">
            Loading telemetry...
          </p>
        ) : monitoredAssets.length === 0 ? (
          <p className="py-8 text-center text-sm muted">
            No telemetry records are available. Confirm that the monitoring
            agent is running and sending observations.
          </p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Asset</th>
                  <th>CPU</th>
                  <th>Memory</th>
                  <th>Disk</th>
                  <th>Network in</th>
                  <th>Network out</th>
                  <th>Last observation</th>
                </tr>
              </thead>
              <tbody>
                {monitoredAssets.map((asset) => {
                  const metric = latestByAsset[asset.asset_id]

                  return (
                    <tr key={asset.asset_id}>
                      <td>
                        <div className="font-medium text-white">
                          {asset.asset_name || asset.hostname || `Asset ${asset.asset_id}`}
                        </div>
                        <div className="text-xs muted">
                          Asset #{asset.asset_id}
                        </div>
                      </td>
                      <td>
                        {formatMetric(getMetricValue(metric, [
                          'cpu_usage',
                          'cpu_percent',
                          'cpu_usage_percent',
                          'cpu',
                        ]), '%')}
                      </td>
                      <td>
                        {formatMetric(getMetricValue(metric, [
                          'memory_usage',
                          'memory_percent',
                          'memory_usage_percent',
                          'memory',
                        ]), '%')}
                      </td>
                      <td>
                        {formatMetric(getMetricValue(metric, [
                          'disk_usage',
                          'disk_percent',
                          'disk_usage_percent',
                          'disk',
                        ]), '%')}
                      </td>
                      <td>
                        {formatMetric(getMetricValue(metric, [
                          'network_in',
                          'network_in_bytes',
                          'network_in_bytes_per_sec',
                          'network_received',
                        ]))}
                      </td>
                      <td>
                        {formatMetric(getMetricValue(metric, [
                          'network_out',
                          'network_out_bytes',
                          'network_out_bytes_per_sec',
                          'network_sent',
                        ]))}
                      </td>
                      <td className="text-xs muted">
                        {formatTime(getTimestamp(metric))}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel
        title="Recent security findings"
        subtitle={`${openFindings.length} open findings · ${anomalyCount} operational anomaly findings`}
      >
        {loading ? (
          <p className="py-8 text-center text-sm muted">
            Loading security findings...
          </p>
        ) : recentEvents.length === 0 ? (
          <p className="py-8 text-center text-sm muted">
            No open security findings are available.
          </p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Finding</th>
                  <th>Category</th>
                  <th>Asset</th>
                  <th>Source</th>
                  <th>Severity</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {recentEvents.map((finding, index) => (
                  <tr key={finding.finding_id || index}>
                    <td>
                      <div className="max-w-xs font-medium text-white">
                        {finding.title || 'Untitled finding'}
                      </div>
                      <div className="text-xs muted">
                        #{finding.finding_id ?? 'N/A'}
                      </div>
                    </td>
                    <td>{finding.category || '—'}</td>
                    <td>
                      {finding.asset_id == null
                        ? 'Organization'
                        : `Asset #${finding.asset_id}`}
                    </td>
                    <td>{finding.source || '—'}</td>
                    <td>
                      <Badge value={finding.severity || 'Unknown'} />
                    </td>
                    <td>{finding.status || 'Open'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <div className="flex items-start gap-3 rounded-xl border border-slate-700 bg-slate-900/40 p-4 text-xs leading-5 text-slate-400">
        <Server size={17} className="mt-0.5 shrink-0 text-teal-300" />
        <p>
          Telemetry is displayed only for assets that have recorded observations.
          The monitoring agent currently covers configured endpoints; the
          inventory count does not imply that every organization asset is
          continuously monitored. Operational anomalies are indicators for
          investigation, not proof of an attack.
        </p>
      </div>
    </div>
  )
}

export default Monitoring
