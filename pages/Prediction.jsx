
import { useCallback, useEffect, useState } from 'react'
import {
  TrendingUp,
  TrendingDown,
  BrainCircuit,
  Activity,
  RefreshCw,
  AlertTriangle,
  ShieldCheck,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

import api from '../../services_api'
import { Metric, Panel, PageTitle, Badge } from '../components/UI'

function getArray(data, keys = []) {
  if (Array.isArray(data)) return data

  for (const key of keys) {
    if (Array.isArray(data?.[key])) return data[key]
  }

  return []
}

function Prediction() {
  const [organizations, setOrganizations] = useState([])
  const [organizationId, setOrganizationId] = useState('')

  const [analysis, setAnalysis] = useState(null)

  const [loadingOrganizations, setLoadingOrganizations] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [organizationError, setOrganizationError] = useState('')

  // LOAD ORGANIZATIONS
  const loadOrganizations = useCallback(async () => {
    setLoadingOrganizations(true)
    setOrganizationError('')

    try {
      const response = await api.get('/organizations/')

      const data = getArray(response.data, [
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

  // LOAD PREDICTIVE ANALYSIS
  const loadAnalysis = useCallback(async () => {
    if (loadingOrganizations) return

    if (!organizationId) {
      setAnalysis(null)
      setLoading(false)

      if (!organizationError) {
        setError('No organizations are currently available.')
      }

      return
    }

    setLoading(true)
    setError('')

    try {
      const response = await api.get(
        `/organizations/${organizationId}/predictive-analysis`
      )

      setAnalysis(response.data)
    } catch (err) {
      setAnalysis(null)

      setError(
        err.response?.data?.detail ||
          'Unable to load predictive analysis. Check the backend connection.'
      )
    } finally {
      setLoading(false)
    }
  }, [organizationId, loadingOrganizations, organizationError])

  useEffect(() => {
    loadAnalysis()
  }, [loadAnalysis])

  // ANALYSIS ARRAYS
  const assetAnalysis = getArray(analysis?.asset_analysis, [
    'assets',
    'items',
    'results',
  ])

  const emergingSignals = getArray(analysis?.emerging_risk_signals, [
    'signals',
    'items',
    'results',
  ])

  const recommendations = getArray(analysis?.recommendations, [
    'items',
    'results',
  ])

  // RISK METRICS
  const riskScore =
    analysis?.risk_score ??
    analysis?.current_risk_score ??
    analysis?.organization_risk_score

  const outlook =
    analysis?.outlook ||
    analysis?.risk_outlook ||
    'Unavailable'

  const historicalTrend =
    analysis?.historical_trend ||
    analysis?.trend ||
    'Unavailable'

  const dataSufficiency =
    analysis?.data_sufficiency ||
    analysis?.data_quality ||
    'Unavailable'

  const scoreChange =
    analysis?.score_change ??
    analysis?.risk_score_change

  // CHART DATA
  const chartData = assetAnalysis
    .map((asset) => ({
      name:
        asset.asset_name ||
        asset.hostname ||
        `Asset ${asset.asset_id}`,
      score:
        asset.latest_risk_score ??
        asset.risk_score ??
        asset.current_risk_score,
      level: asset.risk_level || asset.latest_risk_level || 'Unknown',
    }))
    .filter(
      (asset) =>
        asset.score !== null &&
        asset.score !== undefined &&
        Number.isFinite(Number(asset.score))
    )
    .map((asset) => ({
      ...asset,
      score: Number(asset.score),
    }))

  const directionIcon =
    String(historicalTrend).toLowerCase().includes('increas')
      ? TrendingUp
      : String(historicalTrend).toLowerCase().includes('decreas')
        ? TrendingDown
        : Activity

  const DirectionIcon = directionIcon

  const selectedOrganization = organizations.find(
    (organization) =>
      String(organization.organization_id) === organizationId
  )

  return (
    <div className="space-y-6">
      <PageTitle
        title="AI risk prediction"
        desc={`Explainable risk trend analysis for ${
          selectedOrganization?.name ||
          selectedOrganization?.organization_name ||
          'your organization'
        }.`}
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
              onClick={loadAnalysis}
              disabled={loading || loadingOrganizations || !organizationId}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-medium text-slate-200 hover:bg-slate-700 disabled:opacity-50"
            >
              <RefreshCw
                size={14}
                className={loading ? 'animate-spin' : ''}
              />
              Refresh analysis
            </button>
          </div>
        }
      />

      <div className="flex items-start gap-3 rounded-xl border border-teal-500/20 bg-teal-500/5 p-4 text-sm text-teal-200">
        <BrainCircuit size={19} className="mt-0.5 shrink-0" />
        <p>
          This module uses an explainable, rule-based predictive analysis
          engine. It evaluates available assessment history, open findings
          and telemetry. It is not a trained machine-learning model, and
          its signals are not guaranteed forecasts.
        </p>
      </div>

      {(error || organizationError) && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-200">
          <AlertTriangle size={18} className="mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">Predictive analysis unavailable</p>
            <p className="mt-1">{organizationError || error}</p>
          </div>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Metric
          label="Current risk score"
          value={loading ? '...' : riskScore ?? 'N/A'}
          detail={`Risk level: ${analysis?.risk_level || analysis?.posture || 'Unavailable'}`}
          Icon={ShieldCheck}
          tone="rose"
        />

        <Metric
          label="Historical trend"
          value={loading ? '...' : historicalTrend}
          detail={
            scoreChange == null
              ? 'Based on available assessment history'
              : `Score change: ${scoreChange > 0 ? '+' : ''}${scoreChange}`
          }
          Icon={DirectionIcon}
          tone="blue"
        />

        <Metric
          label="Predictive outlook"
          value={loading ? '...' : outlook}
          detail="Backend-generated risk outlook"
          Icon={BrainCircuit}
          tone="amber"
        />

        <Metric
          label="Data sufficiency"
          value={loading ? '...' : dataSufficiency}
          detail="Availability of historical and telemetry data"
          Icon={Activity}
          tone="green"
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.3fr_0.7fr]">
        <Panel
          title="Asset-level risk analysis"
          subtitle="Latest available numerical risk scores returned by the predictive engine."
        >
          {loading ? (
            <p className="py-10 text-center text-sm muted">
              Loading asset analysis...
            </p>
          ) : chartData.length === 0 ? (
            <p className="py-10 text-center text-sm muted">
              No numerical asset risk scores are available for comparison.
            </p>
          ) : (
            <>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={chartData}
                    margin={{ top: 10, right: 10, left: 0, bottom: 35 }}
                  >
                    <CartesianGrid
                      stroke="#263244"
                      strokeDasharray="3 3"
                    />
                    <XAxis
                      dataKey="name"
                      stroke="#64748b"
                      angle={-20}
                      textAnchor="end"
                      interval={0}
                      height={65}
                      tick={{ fontSize: 11 }}
                    />
                    <YAxis
                      domain={[0, 100]}
                      stroke="#64748b"
                    />
                    <Tooltip
                      contentStyle={{
                        background: '#111c2c',
                        border: '1px solid #334155',
                        borderRadius: 12,
                      }}
                    />
                    <Bar
                      dataKey="score"
                      name="Risk score"
                      fill="#2dd4bf"
                      radius={[5, 5, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="space-y-2 border-t border-slate-800 pt-4">
                {chartData.map((asset, index) => (
                  <div
                    key={`${asset.name}-${index}`}
                    className="flex items-center justify-between gap-3 text-sm"
                  >
                    <span className="truncate text-slate-300">
                      {asset.name}
                    </span>

                    <div className="flex shrink-0 items-center gap-3">
                      <span className="font-semibold text-white">
                        {asset.score}/100
                      </span>
                      <Badge value={asset.level} />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </Panel>

        <Panel
          title="Analysis coverage"
          subtitle="Available evidence used by the predictive engine."
        >
          {loading ? (
            <p className="py-10 text-center text-sm muted">
              Loading analysis coverage...
            </p>
          ) : !analysis ? (
            <p className="py-10 text-center text-sm muted">
              Analysis information is unavailable.
            </p>
          ) : (
            <div className="space-y-4">
              {[
                ['Total assets', analysis.total_assets],
                ['Assets with history', analysis.assets_with_history],
                ['Assets without history', analysis.assets_without_history],
                ['Open findings', analysis.open_findings_count],
                ['Operational anomalies', analysis.operational_anomaly_count],
                ['Assets with telemetry', analysis.assets_with_telemetry],
                ['Assets without telemetry', analysis.assets_without_telemetry],
                ['Telemetry observations', analysis.telemetry_observation_count],
              ]
                .filter(([, value]) => value !== undefined && value !== null)
                .map(([label, value]) => (
                  <div
                    key={label}
                    className="flex justify-between gap-3 border-b border-slate-800 pb-3 text-sm"
                  >
                    <span className="text-slate-400">{label}</span>
                    <b className="text-white">{value}</b>
                  </div>
                ))}
            </div>
          )}
        </Panel>
      </div>

      <Panel
        title="Emerging risk signals"
        subtitle="Potential risk indicators identified by the backend analysis."
      >
        {loading ? (
          <p className="py-8 text-center text-sm muted">
            Loading emerging signals...
          </p>
        ) : emergingSignals.length === 0 ? (
          <p className="py-8 text-center text-sm muted">
            No emerging risk signals were returned by the analysis.
          </p>
        ) : (
          <div className="space-y-3">
            {emergingSignals.map((signal, index) => (
              <div
                key={signal.finding_id || signal.signal_id || index}
                className="rounded-xl border border-slate-800 bg-slate-900/40 p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-white">
                    {signal.title ||
                      signal.name ||
                      signal.description ||
                      'Emerging risk signal'}
                  </p>

                  <Badge
                    value={
                      signal.severity ||
                      signal.priority ||
                      signal.status ||
                      'Review'
                    }
                  />
                </div>

                {signal.description && signal.title && (
                  <p className="mt-2 text-xs leading-5 text-slate-400">
                    {signal.description}
                  </p>
                )}

                <p className="mt-2 text-xs text-slate-500">
                  {signal.asset_id != null
                    ? `Asset #${signal.asset_id}`
                    : 'Organization-level signal'}
                  {signal.source ? ` · ${signal.source}` : ''}
                </p>
              </div>
            ))}
          </div>
        )}
      </Panel>

      <Panel
        title="Security recommendations"
        subtitle="Actions returned by the predictive analysis engine."
      >
        {loading ? (
          <p className="py-8 text-center text-sm muted">
            Loading recommendations...
          </p>
        ) : recommendations.length === 0 ? (
          <p className="py-8 text-center text-sm muted">
            No recommendations were returned.
          </p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {recommendations.map((recommendation, index) => (
              <div
                key={recommendation.recommendation_id || index}
                className="rounded-xl border border-slate-800 bg-slate-900/40 p-4"
              >
                <div className="mb-2 flex items-center justify-between gap-2">
                  <Badge
                    value={
                      recommendation.priority ||
                      recommendation.severity ||
                      'Recommended'
                    }
                  />

                  {recommendation.asset_id != null && (
                    <span className="text-xs text-slate-500">
                      Asset #{recommendation.asset_id}
                    </span>
                  )}
                </div>

                <p className="text-sm font-semibold text-white">
                  {recommendation.title ||
                    recommendation.recommendation ||
                    recommendation.action ||
                    'Security improvement'}
                </p>

                {recommendation.description && (
                  <p className="mt-2 text-xs leading-5 text-slate-400">
                    {recommendation.description}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </Panel>

      {analysis?.methodology && (
        <Panel title="Methodology">
          <p className="text-sm leading-6 text-slate-400">
            {analysis.methodology}
          </p>

          {analysis.disclaimer && (
            <p className="mt-3 text-xs leading-5 text-slate-500">
              {analysis.disclaimer}
            </p>
          )}
        </Panel>
      )}
    </div>
  )
}

export default Prediction
