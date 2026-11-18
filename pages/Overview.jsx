
import { useCallback, useEffect, useState } from 'react'
import {
  ShieldCheck,
  Boxes,
  ShieldAlert,
  Activity,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react'
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

import api from '../../services_api'
import { Badge, Panel, Metric, PageTitle } from '../components/UI'

const SEVERITY_COLORS = {
  Critical: '#fb7185',
  High: '#fb923c',
  Medium: '#fbbf24',
  Moderate: '#fbbf24',
  Low: '#34d399',
}

const SEVERITY_ORDER = {
  Critical: 4,
  High: 3,
  Medium: 2,
  Moderate: 2,
  Low: 1,
}

function extractArray(data, possibleKeys = []) {
  if (Array.isArray(data)) return data

  for (const key of possibleKeys) {
    if (Array.isArray(data?.[key])) return data[key]
  }

  return []
}

function normalizeSeverity(severity) {
  const value = String(severity || 'Unknown').toLowerCase()

  if (value === 'critical') return 'Critical'
  if (value === 'high') return 'High'
  if (value === 'medium') return 'Medium'
  if (value === 'moderate') return 'Moderate'
  if (value === 'low') return 'Low'

  return 'Unknown'
}

function isOpenFinding(finding) {
  const status = String(finding.status || 'Open').toLowerCase()

  return !['closed', 'resolved', 'accepted', 'false positive'].includes(status)
}

function Overview() {
  const [organizations, setOrganizations] = useState([])
  const [organizationId, setOrganizationId] = useState('')

  const [riskSummary, setRiskSummary] = useState(null)
  const [findings, setFindings] = useState([])

  const [loadingOrganizations, setLoadingOrganizations] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [organizationError, setOrganizationError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  // LOAD ORGANIZATIONS
  const loadOrganizations = useCallback(async () => {
    setLoadingOrganizations(true)
    setOrganizationError('')

    try {
      const response = await api.get('/organizations/')

      const data = extractArray(response.data, [
        'organizations',
        'items',
        'results',
      ])

      setOrganizations(data)

      setOrganizationId((current) =>
        data.some(
          (organization) =>
            String(organization.organization_id) === current
        )
          ? current
          : data.length > 0
            ? String(data[0].organization_id)
            : ''
      )
    } catch (err) {
      setOrganizations([])
      setOrganizationId('')
      setOrganizationError(
        err.response?.data?.detail ||
          'Unable to load organizations.'
      )
    } finally {
      setLoadingOrganizations(false)
    }
  }, [])

  useEffect(() => {
    loadOrganizations()
  }, [loadOrganizations])

  // LOAD DASHBOARD DATA FOR SELECTED ORGANIZATION
  const loadDashboard = useCallback(async () => {
    if (loadingOrganizations) return

    if (!organizationId) {
      setRiskSummary(null)
      setFindings([])
      setLoading(false)

      if (!organizationError) {
        setError('No organizations are currently available.')
      }

      return
    }

    setLoading(true)
    setError('')

    try {
      const results = await Promise.allSettled([
        api.get(`/organizations/${organizationId}/risk-summary`),
        api.get('/risk-findings/', {
          params: {
            organization_id: Number(organizationId),
          },
        }),
      ])

      const errors = []

      if (results[0].status === 'fulfilled') {
        setRiskSummary(results[0].value.data)
      } else {
        setRiskSummary(null)
        errors.push('Organization risk summary')
      }

      if (results[1].status === 'fulfilled') {
        setFindings(
          extractArray(results[1].value.data, [
            'findings',
            'items',
            'results',
          ])
        )
      } else {
        setFindings([])
        errors.push('Risk findings')
      }

      if (errors.length > 0) {
        setError(
          `Unable to load: ${errors.join(' and ')}. Check that the backend is running and the API is accessible.`
        )
      }
    } catch {
      setError(
        'Unable to load dashboard data. Please check your backend connection.'
      )
    } finally {
      setLoading(false)
    }
  }, [organizationId, loadingOrganizations, organizationError])

  useEffect(() => {
    loadDashboard()
  }, [loadDashboard, refreshKey])

  // FINDING CALCULATIONS
  const openFindings = findings.filter(isOpenFinding)

  const severityCounts = {
    Critical: 0,
    High: 0,
    Medium: 0,
    Low: 0,
  }

  openFindings.forEach((finding) => {
    const severity = normalizeSeverity(finding.severity)

    if (severity === 'Critical') severityCounts.Critical += 1
    else if (severity === 'High') severityCounts.High += 1
    else if (severity === 'Medium' || severity === 'Moderate') {
      severityCounts.Medium += 1
    } else if (severity === 'Low') {
      severityCounts.Low += 1
    }
  })

  const findingDistribution = Object.entries(severityCounts).map(
    ([name, value]) => ({
      name,
      value,
      color: SEVERITY_COLORS[name],
    })
  )

  const priorityFindings = [...openFindings]
    .filter((finding) => {
      const severity = normalizeSeverity(finding.severity)
      return severity === 'Critical' || severity === 'High'
    })
    .sort((a, b) => {
      const severityA =
        SEVERITY_ORDER[normalizeSeverity(a.severity)] || 0

      const severityB =
        SEVERITY_ORDER[normalizeSeverity(b.severity)] || 0

      return severityB - severityA
    })
    .slice(0, 3)

  // RISK SUMMARY
  const riskScore = riskSummary?.risk_score
  const riskLevel = riskSummary?.risk_level || 'Not Assessed'
  const totalAssets = riskSummary?.total_assets ?? 0
  const assessedAssets = riskSummary?.assessed_assets ?? 0
  const coverage = riskSummary?.assessment_coverage_percentage ?? 0

  const assetRisks = riskSummary?.highest_risk_assets || []

  const riskTone =
    riskLevel === 'Critical'
      ? 'rose'
      : riskLevel === 'High'
        ? 'amber'
        : riskLevel === 'Moderate'
          ? 'blue'
          : 'green'

  return (
    <div className="space-y-6">
      <PageTitle
        title="Security overview"
        desc={`Live cybersecurity posture for ${riskSummary?.organization_name || organizations.find((org) => String(org.organization_id) === organizationId)?.name || organizations.find((org) => String(org.organization_id) === organizationId)?.organization_name || 'your organization'}.`}
        extra={
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={organizationId}
              onChange={(event) => setOrganizationId(event.target.value)}
              disabled={loadingOrganizations || organizations.length === 0}
              className="max-w-[220px] rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-medium text-slate-200 outline-none focus:border-teal-500 disabled:opacity-50"
            >
              {loadingOrganizations && (
                <option value="">Loading organizations...</option>
              )}

              {!loadingOrganizations && organizations.length === 0 && (
                <option value="">No organizations available</option>
              )}

              {organizations.map((organization) => (
                <option
                  key={organization.organization_id}
                  value={String(organization.organization_id)}
                >
                  {organization.name ||
                    organization.organization_name ||
                    `Organization #${organization.organization_id}`}
                </option>
              ))}
            </select>

            <button
              onClick={() => setRefreshKey((value) => value + 1)}
              disabled={loading || loadingOrganizations || !organizationId}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-medium text-slate-200 transition hover:bg-slate-700 disabled:opacity-50"
            >
              <RefreshCw
                size={14}
                className={loading ? 'animate-spin' : ''}
              />
              Refresh data
            </button>
          </div>
        }
      />

      {(error || organizationError) && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-200">
          <AlertTriangle size={18} className="mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">Dashboard data warning</p>
            <p className="mt-1 text-amber-200/80">
              {organizationError || error}
            </p>
          </div>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          label="Overall risk score"
          value={
            loading
              ? '...'
              : riskScore == null
                ? 'N/A'
                : `${riskScore} / 100`
          }
          detail={`Organization risk level: ${riskLevel}`}
          Icon={ShieldCheck}
          tone={riskTone}
        />

        <Metric
          label="Total assets"
          value={loading ? '...' : totalAssets}
          detail={`${assessedAssets} assets assessed`}
          Icon={Boxes}
          tone="blue"
        />

        <Metric
          label="Open findings"
          value={loading ? '...' : openFindings.length}
          detail={`${severityCounts.Critical} critical · ${severityCounts.High} high`}
          Icon={ShieldAlert}
          tone="rose"
        />

        <Metric
          label="Assessment coverage"
          value={loading ? '...' : `${coverage}%`}
          detail={`${Math.max(totalAssets - assessedAssets, 0)} assets not assessed`}
          Icon={Activity}
          tone="amber"
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
        <Panel
          title="Asset risk overview"
          subtitle="Latest available risk assessments from the organization."
        >
          {loading ? (
            <p className="py-12 text-center text-sm text-slate-500">
              Loading asset risk data...
            </p>
          ) : assetRisks.length === 0 ? (
            <p className="py-12 text-center text-sm text-slate-500">
              No assessed assets are available yet.
            </p>
          ) : (
            <div className="space-y-4">
              {assetRisks.slice(0, 5).map((asset) => (
                <div
                  key={asset.asset_id}
                  className="flex items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-900/40 p-3"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-white">
                      {asset.asset_name}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      Asset #{asset.asset_id} · {asset.criticality} criticality
                    </p>
                  </div>

                  <div className="shrink-0 text-right">
                    <p className="text-sm font-bold text-white">
                      {asset.risk_score}/100
                    </p>
                    <div className="mt-1">
                      <Badge value={asset.risk_level} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {!loading && riskSummary && (
            <div className="mt-4 border-t border-slate-800 pt-4">
              <div className="mb-2 flex justify-between text-xs">
                <span className="text-slate-400">Assessment coverage</span>
                <span className="font-semibold text-white">{coverage}%</span>
              </div>

              <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full bg-teal-400 transition-all"
                  style={{
                    width: `${Math.min(Math.max(Number(coverage), 0), 100)}%`,
                  }}
                />
              </div>

              <p className="mt-2 text-xs text-slate-500">
                Organization score is based only on assets with valid numerical
                assessments.
              </p>
            </div>
          )}
        </Panel>

        <Panel
          title="Open finding distribution"
          subtitle="Live risk findings grouped by severity."
        >
          {loading ? (
            <p className="py-12 text-center text-sm text-slate-500">
              Loading findings...
            </p>
          ) : openFindings.length === 0 ? (
            <p className="py-12 text-center text-sm text-slate-500">
              No open findings are currently available.
            </p>
          ) : (
            <div className="flex items-center gap-2">
              <div className="h-48 w-1/2">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={findingDistribution.filter(
                        (item) => item.value > 0
                      )}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={43}
                      outerRadius={70}
                      paddingAngle={3}
                    >
                      {findingDistribution
                        .filter((item) => item.value > 0)
                        .map((item) => (
                          <Cell key={item.name} fill={item.color} />
                        ))}
                    </Pie>

                    <Tooltip
                      contentStyle={{
                        background: '#111c2c',
                        border: '1px solid #334155',
                        borderRadius: 12,
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="flex-1 space-y-3">
                {findingDistribution.map((item) => (
                  <div
                    key={item.name}
                    className="flex items-center justify-between gap-2 text-xs"
                  >
                    <span className="flex items-center gap-2 text-slate-400">
                      <span
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: item.color }}
                      />
                      {item.name}
                    </span>

                    <b className="text-white">{item.value}</b>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Panel>
      </div>

      <Panel
        title="Priority actions"
        subtitle="Highest-severity open findings requiring attention."
      >
        {loading ? (
          <p className="py-8 text-center text-sm text-slate-500">
            Loading priority findings...
          </p>
        ) : priorityFindings.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">
            No open Critical or High findings are available.
          </p>
        ) : (
          <div className="grid gap-3 md:grid-cols-3">
            {priorityFindings.map((finding, index) => (
              <div
                key={finding.finding_id || index}
                className="rounded-xl border border-slate-800 bg-slate-900/40 p-4"
              >
                <div className="mb-3">
                  <Badge value={normalizeSeverity(finding.severity)} />
                </div>

                <p className="text-sm font-semibold text-white">
                  {finding.title || 'Untitled security finding'}
                </p>

                <p className="mt-2 line-clamp-3 text-xs text-slate-500">
                  {finding.description ||
                    finding.category ||
                    'Review this open security finding and investigate the affected asset.'}
                </p>

                <p className="mt-3 text-xs text-slate-400">
                  Finding #{finding.finding_id ?? 'N/A'}
                  {finding.asset_id != null
                    ? ` · Asset #${finding.asset_id}`
                    : ''}
                </p>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  )
}

export default Overview
