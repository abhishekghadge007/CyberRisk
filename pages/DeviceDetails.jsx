
import { useEffect, useState } from 'react'
import { NavLink, useParams } from 'react-router-dom'
import {
  Activity,
  Monitor,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  CheckCircle,
  Clock,
  RefreshCw,
} from 'lucide-react'

import api from '../../services_api'
import { Badge, Panel, Metric, PageTitle } from '../components/UI'

function severityStyle(severity) {
  const value = String(severity || '').toLowerCase()

  if (value === 'critical') {
    return 'border-rose-500/30 bg-rose-500/10 text-rose-300'
  }
  if (value === 'high') {
    return 'border-orange-500/30 bg-orange-500/10 text-orange-300'
  }
  if (value === 'medium') {
    return 'border-amber-500/30 bg-amber-500/10 text-amber-300'
  }
  if (value === 'low') {
    return 'border-blue-500/30 bg-blue-500/10 text-blue-300'
  }

  return 'border-slate-600 bg-slate-800 text-slate-300'
}

function statusStyle(status) {
  const value = String(status || '').toLowerCase()

  if (value.includes('resolved') || value.includes('implemented')) {
    return 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
  }

  if (value.includes('open') || value.includes('not implemented')) {
    return 'border-rose-500/30 bg-rose-500/10 text-rose-300'
  }

  if (value.includes('partial') || value.includes('progress')) {
    return 'border-amber-500/30 bg-amber-500/10 text-amber-300'
  }

  return 'border-slate-600 bg-slate-800 text-slate-300'
}

function InfoValue({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
      <p className="text-xs muted">{label}</p>
      <p className="mt-2 break-words text-sm font-semibold text-white">
        {value === null || value === undefined || value === ''
          ? '—'
          : String(value)}
      </p>
    </div>
  )
}

function getArray(data, keys = []) {
  if (Array.isArray(data)) return data

  for (const key of keys) {
    if (Array.isArray(data?.[key])) return data[key]
  }

  return []
}

function DeviceDetails() {
  const { assetId } = useParams()

  const [asset, setAsset] = useState(null)
  const [history, setHistory] = useState([])
  const [scanDetails, setScanDetails] = useState({})
  const [securityPosture, setSecurityPosture] = useState(null)
  const [findings, setFindings] = useState([])

  const [loading, setLoading] = useState(true)
  const [loadingScan, setLoadingScan] = useState(null)
  const [error, setError] = useState('')
  const [securityError, setSecurityError] = useState('')
  const [findingsError, setFindingsError] = useState('')
  const [scanError, setScanError] = useState('')

  const loadDevice = async () => {
    setLoading(true)
    setError('')
    setSecurityError('')
    setFindingsError('')
    setScanError('')

    try {
      const [assetResponse, historyResponse] = await Promise.all([
        api.get(`/assets/${assetId}`),
        api.get(`/assets/${assetId}/scan-history`),
      ])

      const assetData = assetResponse.data

      setAsset(assetData)
      setHistory(
        getArray(historyResponse.data, ['history', 'scans', 'items', 'results'])
      )
      setScanDetails({})

      const [postureResult, findingsResult] = await Promise.allSettled([
        api.get(`/security-posture/assets/${assetId}`),
        api.get('/risk-findings/', {
          params: {
            organization_id: assetData.organization_id,
            asset_id: assetId,
          },
        }),
      ])

      if (postureResult.status === 'fulfilled') {
        setSecurityPosture(postureResult.value.data)
      } else {
        console.error('Security posture loading failed:', postureResult.reason)
        setSecurityPosture(null)
        setSecurityError(
          postureResult.reason?.response?.data?.detail ||
          'Unable to load security posture.'
        )
      }

      if (findingsResult.status === 'fulfilled') {
        setFindings(
          getArray(findingsResult.value.data, [
            'findings',
            'items',
            'results',
          ])
        )
      } else {
        console.error('Risk findings loading failed:', findingsResult.reason)
        setFindings([])
        setFindingsError(
          findingsResult.reason?.response?.data?.detail ||
          'Unable to load risk findings.'
        )
      }
    } catch (err) {
      console.error('Device details loading failed:', err)
      setError(
        err.response?.data?.detail ||
        'Unable to load device details.'
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDevice()
  }, [assetId])

  const loadScanDetails = async (scanId) => {
    setScanError('')

    if (scanDetails[scanId]) {
      setScanDetails((previous) => {
        const updated = { ...previous }
        delete updated[scanId]
        return updated
      })
      return
    }

    setLoadingScan(scanId)

    try {
      const response = await api.get(`/scans/${scanId}/details`)

      setScanDetails((previous) => ({
        ...previous,
        [scanId]: response.data,
      }))
    } catch (err) {
      console.error('Scan details loading failed:', err)
      setScanError(
        err.response?.data?.detail ||
        `Unable to load details for scan ${scanId}.`
      )
    } finally {
      setLoadingScan(null)
    }
  }

  const formatDate = (value) => {
    if (!value) return '—'

    const date = new Date(value)

    if (Number.isNaN(date.getTime())) return '—'

    return date.toLocaleString('en-IN', {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
  }

  if (loading) {
    return (
      <div className="py-16 text-center text-sm muted">
        Loading device details...
      </div>
    )
  }

  if (error && !asset) {
    return (
      <div className="space-y-4">
        <NavLink
          to="/assets"
          className="text-sm text-teal-300 hover:text-teal-200"
        >
          ← Back to device inventory
        </NavLink>

        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
          {error}
        </div>
      </div>
    )
  }

  if (!asset) return null

  const postureSummary = securityPosture?.summary || {}
  const controls = getArray(securityPosture?.controls)
  const recommendations = getArray(securityPosture?.recommendations)

  const findingCounts = findings.reduce(
    (counts, finding) => {
      const severity = String(finding.severity || '').toLowerCase()

      if (severity in counts) {
        counts[severity] += 1
      }

      return counts
    },
    { critical: 0, high: 0, medium: 0, low: 0 }
  )

  const openFindings = findings.filter(
    (finding) => String(finding.status || '').toLowerCase() === 'open'
  ).length

  return (
    <div className="space-y-6">
      <PageTitle
        title={asset.asset_name || asset.hostname || `Asset ${asset.asset_id}`}
        desc="Device information, security posture, risk findings and historical scan results."
        extra={
          <div className="flex flex-wrap gap-2">
            <button
              onClick={loadDevice}
              disabled={loading}
              className="btn-secondary flex items-center gap-2 text-xs disabled:opacity-50"
            >
              <RefreshCw size={14} />
              Refresh
            </button>

            <NavLink
              to="/assets"
              className="btn-secondary flex items-center gap-2 text-xs"
            >
              ← Back to inventory
            </NavLink>
          </div>
        }
      />

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
          {error}
        </div>
      )}

      {/* DEVICE SUMMARY */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Metric
          label="Asset ID"
          value={asset.asset_id}
          detail={`Organization ${asset.organization_id}`}
          Icon={Monitor}
        />

        <Metric
          label="Recorded scans"
          value={history.length}
          detail="Scans associated with this device"
          Icon={Activity}
          tone="blue"
        />

        <Metric
          label="Criticality"
          value={asset.criticality || 'Unknown'}
          detail="Registered asset classification"
          Icon={ShieldAlert}
          tone="rose"
        />
      </div>

      {/* SECURITY POSTURE */}
      <Panel
        title="Device Security Posture"
        subtitle="Security control implementation and assessment results for this device."
      >
        {securityError ? (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-300">
            <AlertTriangle size={17} className="mr-2 inline" />
            {securityError}
          </div>
        ) : !securityPosture ? (
          <p className="py-6 text-center text-sm muted">
            No security posture data available.
          </p>
        ) : (
          <div className="space-y-5">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {[
                ['Total controls', postureSummary.total_controls ?? 0],
                ['Assessed controls', postureSummary.assessed_controls ?? 0],
                [
                  'Assessment coverage',
                  `${postureSummary.assessment_coverage_percentage ?? 0}%`,
                ],
                [
                  'Implementation',
                  `${postureSummary.implementation_percentage ?? 0}%`,
                ],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="rounded-xl border border-slate-800 bg-slate-900/50 p-4"
                >
                  <p className="text-xs muted">{label}</p>
                  <p className="mt-2 text-2xl font-bold text-white">
                    {value}
                  </p>
                </div>
              ))}
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {[
                ['Implemented', postureSummary.implemented ?? 0, 'text-emerald-300'],
                ['Partially implemented', postureSummary.partially_implemented ?? 0, 'text-amber-300'],
                ['Not implemented', postureSummary.not_implemented ?? 0, 'text-rose-300'],
                ['Unassessed', postureSummary.unassessed_controls ?? 0, 'text-slate-300'],
              ].map(([label, value, color]) => (
                <div
                  key={label}
                  className="rounded-xl border border-slate-800 bg-slate-900/40 p-3"
                >
                  <p className="text-xs muted">{label}</p>
                  <p className={`mt-1 text-xl font-bold ${color}`}>
                    {value}
                  </p>
                </div>
              ))}
            </div>

            <div>
              <div className="mb-2 flex justify-between text-xs">
                <span className="muted">Implementation progress</span>
                <span className="font-semibold text-teal-300">
                  {postureSummary.implementation_percentage ?? 0}%
                </span>
              </div>

              <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full bg-teal-400"
                  style={{
                    width: `${Math.min(
                      100,
                      Math.max(
                        0,
                        Number(postureSummary.implementation_percentage) || 0
                      )
                    )}%`,
                  }}
                />
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
              <p className="text-xs muted">
                Average effectiveness score
              </p>
              <p className="mt-2 text-2xl font-bold text-white">
                {postureSummary.average_effectiveness_score ?? '—'}
                {postureSummary.average_effectiveness_score !== null &&
                postureSummary.average_effectiveness_score !== undefined
                  ? '/100'
                  : ''}
              </p>
            </div>

            <div>
              <h3 className="mb-3 text-sm font-semibold text-white">
                Security Controls
              </h3>

              {controls.length === 0 ? (
                <p className="text-sm muted">
                  No individual control assessments recorded.
                </p>
              ) : (
                <div className="space-y-3">
                  {controls.map((control, index) => (
                    <div
                      key={control.control_id ?? index}
                      className="rounded-xl border border-slate-800 bg-slate-900/40 p-4"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold text-white">
                            {control.control_name || 'Unnamed control'}
                          </p>
                          <p className="mt-1 text-xs muted">
                            {control.control_key || '—'} · {control.category || 'Uncategorized'}
                          </p>
                        </div>

                        <span
                          className={`rounded-full border px-3 py-1 text-xs ${statusStyle(control.status)}`}
                        >
                          {control.status || 'Unknown'}
                        </span>
                      </div>

                      <div className="mt-4 grid gap-3 sm:grid-cols-2">
                        <p className="text-xs muted">
                          Effectiveness score:{' '}
                          <span className="font-semibold text-white">
                            {control.effectiveness_score ?? '—'}
                            {control.effectiveness_score !== null &&
                            control.effectiveness_score !== undefined
                              ? '/100'
                              : ''}
                          </span>
                        </p>

                        <p className="text-xs muted">
                          Last assessed:{' '}
                          <span className="text-slate-200">
                            {formatDate(control.assessed_at)}
                          </span>
                        </p>
                      </div>

                      {control.evidence?.verification_note && (
                        <p className="mt-3 rounded-lg bg-slate-800/70 p-3 text-xs text-slate-300">
                          Evidence: {control.evidence.verification_note}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {recommendations.length > 0 && (
              <div>
                <h3 className="mb-3 text-sm font-semibold text-white">
                  Security Recommendations
                </h3>

                <div className="space-y-2">
                  {recommendations.map((item, index) => (
                    <div
                      key={`${item.control_key || 'recommendation'}-${index}`}
                      className="flex gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4"
                    >
                      <ShieldCheck
                        size={18}
                        className="shrink-0 text-amber-300"
                      />
                      <div>
                        <p className="text-sm font-semibold text-white">
                          {item.control_key || 'Security control'} · {item.priority || 'Normal'} priority
                        </p>
                        <p className="mt-1 text-xs leading-5 text-slate-400">
                          {item.recommendation || 'Review this security control.'}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {securityPosture.methodology && (
              <p className="text-xs leading-5 muted">
                Methodology: {securityPosture.methodology}
              </p>
            )}

            {securityPosture.disclaimer && (
              <p className="text-xs leading-5 text-slate-500">
                {securityPosture.disclaimer}
              </p>
            )}
          </div>
        )}
      </Panel>

      {/* RISK FINDINGS */}
      <Panel
        title="Device Risk Findings"
        subtitle="Risk findings recorded against this device, including operational anomalies and security issues."
      >
        {findingsError ? (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-300">
            <AlertTriangle size={17} className="mr-2 inline" />
            {findingsError}
          </div>
        ) : (
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
              {[
                ['Total findings', findings.length, 'text-white'],
                ['Critical', findingCounts.critical, 'text-rose-300'],
                ['High', findingCounts.high, 'text-orange-300'],
                ['Medium', findingCounts.medium, 'text-amber-300'],
                ['Low', findingCounts.low, 'text-blue-300'],
              ].map(([label, value, color]) => (
                <div
                  key={label}
                  className="rounded-xl border border-slate-800 bg-slate-900/50 p-3"
                >
                  <p className="text-xs muted">{label}</p>
                  <p className={`mt-2 text-2xl font-bold ${color}`}>
                    {value}
                  </p>
                </div>
              ))}
            </div>

            <div className="flex items-center gap-2 text-xs muted">
              <Clock size={14} />
              {openFindings} open findings · {findings.length - openFindings} other statuses
            </div>

            {findings.length === 0 ? (
              <div className="py-8 text-center">
                <CheckCircle
                  size={34}
                  className="mx-auto mb-3 text-emerald-400"
                />
                <p className="text-sm font-semibold text-white">
                  No risk findings returned
                </p>
                <p className="mt-1 text-xs muted">
                  No findings are currently recorded for this device.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {findings.map((finding, index) => (
                  <div
                    key={finding.finding_id ?? index}
                    className="rounded-xl border border-slate-800 bg-slate-900/40 p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-semibold text-white">
                          {finding.title || 'Untitled finding'}
                        </p>
                        <p className="mt-1 text-xs muted">
                          Finding #{finding.finding_id ?? '—'} · {finding.category || 'Uncategorized'}
                        </p>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <span
                          className={`rounded-full border px-3 py-1 text-xs ${severityStyle(finding.severity)}`}
                        >
                          {finding.severity || 'Unknown'}
                        </span>
                        <span
                          className={`rounded-full border px-3 py-1 text-xs ${statusStyle(finding.status)}`}
                        >
                          {finding.status || 'Unknown'}
                        </span>
                      </div>
                    </div>

                    {finding.description && (
                      <p className="mt-3 text-sm leading-6 text-slate-400">
                        {finding.description}
                      </p>
                    )}

                    <div className="mt-4 grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-3">
                      <p className="muted">
                        Source:{' '}
                        <span className="text-slate-200">
                          {finding.source || '—'}
                        </span>
                      </p>

                      <p className="muted">
                        Likelihood:{' '}
                        <span className="text-slate-200">
                          {finding.likelihood ?? '—'}
                        </span>
                      </p>

                      <p className="muted">
                        Impact:{' '}
                        <span className="text-slate-200">
                          {finding.impact ?? '—'}
                        </span>
                      </p>

                      <p className="muted">
                        Detected:{' '}
                        <span className="text-slate-200">
                          {formatDate(finding.created_at)}
                        </span>
                      </p>

                      <p className="muted">
                        Asset ID:{' '}
                        <span className="text-slate-200">
                          {finding.asset_id ?? assetId}
                        </span>
                      </p>
                    </div>

                    {finding.evidence && (
                      <details className="mt-4 rounded-lg border border-slate-800 bg-slate-950/50 p-3">
                        <summary className="cursor-pointer text-xs font-semibold text-teal-300">
                          View finding evidence
                        </summary>
                        <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words text-xs leading-5 text-slate-400">
                          {JSON.stringify(finding.evidence, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Panel>

      {/* DEVICE INFORMATION */}
      <Panel
        title="Device information"
        subtitle="Information stored in the CyberRisk asset inventory"
      >
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {[
            ['Asset name', asset.asset_name],
            ['Hostname', asset.hostname],
            ['IP address', asset.ip_address],
            ['Organization ID', asset.organization_id],
            ['Asset type', asset.asset_type],
            ['Operating system', asset.operating_system],
            ['Environment', asset.environment],
            ['Owner', asset.owner],
            ['Business unit', asset.business_unit],
            ['Cloud provider', asset.cloud_provider],
            ['Exposure level', asset.exposure_level],
            ['Last seen', formatDate(asset.last_seen)],
            ['Created at', formatDate(asset.created_at)],
          ].map(([label, value]) => (
            <InfoValue key={label} label={label} value={value} />
          ))}
        </div>
      </Panel>

      {/* SCAN HISTORY */}
      <Panel
        title="Device scan history"
        subtitle="Every recorded scan that returned results associated with this device"
      >
        {scanError && (
          <div className="mb-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
            {scanError}
          </div>
        )}

        {history.length === 0 ? (
          <div className="py-10 text-center">
            <Activity className="mx-auto mb-3 text-slate-500" size={34} />
            <p className="text-sm text-white">
              No scan history available for this device.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {history.map((scan) => {
              const details = scanDetails[scan.scan_id]

              return (
                <div
                  key={scan.scan_id}
                  className="rounded-xl border border-slate-800 bg-slate-900/40 p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-semibold text-white">
                        Scan #{scan.scan_id}
                      </p>

                      <p className="mt-1 text-xs muted">
                        Target: {scan.target_network || '—'}
                      </p>

                      <p className="mt-1 text-xs muted">
                        Created: {formatDate(scan.created_at)}
                      </p>
                    </div>

                    <div className="text-right">
                      <Badge
                        value={
                          scan.status === 'completed'
                            ? 'Resolved'
                            : scan.status === 'failed'
                              ? 'Critical'
                              : 'Info'
                        }
                      />

                      <p className="mt-2 text-xs muted">
                        {scan.result_count ?? '—'} results
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 pt-3">
                    <p className="text-xs muted">
                      Started: {formatDate(scan.started_at)}
                    </p>

                    <button
                      onClick={() => loadScanDetails(scan.scan_id)}
                      disabled={loadingScan === scan.scan_id}
                      className="text-xs font-semibold text-teal-300 hover:text-teal-200 disabled:opacity-50"
                    >
                      {loadingScan === scan.scan_id
                        ? 'Loading scan...'
                        : details
                          ? 'Hide scan results ↑'
                          : 'View scan results →'}
                    </button>
                  </div>

                  {details && (
                    <div className="mt-4 space-y-3">
                      <div className="rounded-lg bg-slate-800/70 p-3">
                        <p className="text-sm font-semibold text-white">
                          Scan #{details.scan?.scan_id ?? scan.scan_id} results
                        </p>

                        <p className="mt-1 text-xs muted">
                          Total results: {details.total_results ?? '—'}
                        </p>
                      </div>

                      {getArray(details, ['results'])
                        .filter(
                          (result) =>
                            Number(result.asset_id) === Number(assetId)
                        )
                        .map((result) => (
                          <div
                            key={result.result_id}
                            className="rounded-lg border border-slate-700 p-3"
                          >
                            <div className="flex flex-wrap justify-between gap-2">
                              <p className="text-sm font-semibold text-white">
                                {result.service_name || 'Host discovery'}
                              </p>

                              <Badge
                                value={
                                  result.state === 'open' ? 'Open' : 'Info'
                                }
                              />
                            </div>

                            <div className="mt-3 grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-3">
                              <p className="muted">
                                IP: <span className="text-slate-200">{result.ip_address || '—'}</span>
                              </p>

                              <p className="muted">
                                Port: <span className="text-slate-200">{result.port ?? '—'}</span>
                              </p>

                              <p className="muted">
                                Protocol: <span className="text-slate-200">{result.protocol || '—'}</span>
                              </p>

                              <p className="muted">
                                Product: <span className="text-slate-200">{result.product || '—'}</span>
                              </p>

                              <p className="muted">
                                Version: <span className="text-slate-200">{result.version || 'Not detected'}</span>
                              </p>

                              <p className="muted">
                                Hostname: <span className="text-slate-200">{result.hostname || '—'}</span>
                              </p>
                            </div>
                          </div>
                        ))}

                      {getArray(details, ['results']).filter(
                        (result) =>
                          Number(result.asset_id) === Number(assetId)
                      ).length === 0 && (
                        <p className="py-4 text-center text-xs muted">
                          No results for this device in this scan.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </Panel>
    </div>
  )
}

export default DeviceDetails
