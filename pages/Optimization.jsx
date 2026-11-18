
import { useCallback, useEffect, useState } from 'react'
import { Target, RefreshCw, Monitor, Building2 } from 'lucide-react'
import api from '../../services_api'
import { Panel, PageTitle } from '../components/UI'

function getArray(data, keys = []) {
  if (Array.isArray(data)) return data

  for (const key of keys) {
    if (Array.isArray(data?.[key])) return data[key]
  }

  return []
}

function getErrorMessage(error) {
  const detail = error.response?.data?.detail

  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join(', ')
  }

  return detail || error.message || 'Something went wrong. Please try again.'
}

function Optimization() {
  const [organizations, setOrganizations] = useState([])
  const [organizationId, setOrganizationId] = useState('')

  const [assets, setAssets] = useState([])
  const [assetId, setAssetId] = useState('')
  const [scope, setScope] = useState('organization')

  const [budget, setBudget] = useState(100000)

  const [loadingOrganizations, setLoadingOrganizations] = useState(true)
  const [loadingAssets, setLoadingAssets] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [loading, setLoading] = useState(false)

  const [error, setError] = useState('')
  const [recommendationError, setRecommendationError] = useState('')
  const [result, setResult] = useState(null)
  const [recommendations, setRecommendations] = useState([])
  const [history, setHistory] = useState([])

  const selectedOrganization = organizations.find(
    (organization) =>
      String(organization.organization_id) === String(organizationId)
  )

  const selectedAsset = assets.find(
    (asset) => String(asset.asset_id) === String(assetId)
  )

  const money = (value) =>
    new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(Number(value || 0))

  const loadOrganizations = useCallback(async () => {
    setLoadingOrganizations(true)
    setError('')

    try {
      const response = await api.get('/organizations/')

      const data = getArray(response.data, [
        'organizations',
        'items',
        'results',
      ])

      setOrganizations(data)

      setOrganizationId((current) => {
        if (
          current &&
          data.some(
            (organization) =>
              String(organization.organization_id) === String(current)
          )
        ) {
          return current
        }

        // No organization ID is hard-coded. Use the first API result only
        // when the current selection is no longer available.
        return String(data[0]?.organization_id ?? '')
      })
    } catch (err) {
      console.error('Could not load organizations:', err)
      setError(`Could not load organizations: ${getErrorMessage(err)}`)
    } finally {
      setLoadingOrganizations(false)
    }
  }, [])

  const loadAssets = useCallback(async () => {
    if (!organizationId) {
      setAssets([])
      setAssetId('')
      return
    }

    setLoadingAssets(true)

    try {
      const response = await api.get('/assets/', {
        params: {
          organization_id: Number(organizationId),
          limit: 500,
          offset: 0,
        },
      })

      const data = getArray(response.data, [
        'assets',
        'items',
        'results',
      ])

      setAssets(data)

      setAssetId((current) => {
        if (
          current &&
          data.some((asset) => String(asset.asset_id) === String(current))
        ) {
          return current
        }

        return ''
      })
    } catch (err) {
      console.error('Could not load organization assets:', err)
      setAssets([])
      setAssetId('')
      setError(`Could not load assets: ${getErrorMessage(err)}`)
    } finally {
      setLoadingAssets(false)
    }
  }, [organizationId])

  const loadHistory = useCallback(async () => {
    if (!organizationId) {
      setHistory([])
      return
    }

    setLoadingHistory(true)

    try {
      const response = await api.get(
        `/optimization/history/${organizationId}`
      )

      setHistory(
        getArray(response.data, ['history', 'items', 'results'])
      )
    } catch (err) {
      console.error('Could not load optimization history:', err)
      setHistory([])
    } finally {
      setLoadingHistory(false)
    }
  }, [organizationId])

  useEffect(() => {
    loadOrganizations()
  }, [loadOrganizations])

  useEffect(() => {
    if (!organizationId) {
      setAssets([])
      setAssetId('')
      setHistory([])
      return
    }

    setResult(null)
    setRecommendations([])
    setRecommendationError('')
    setError('')

    loadAssets()
    loadHistory()
  }, [organizationId, loadAssets, loadHistory])

  const runOptimization = async () => {
    if (!organizationId) {
      setError('Please select an organization.')
      return
    }

    if (!budget || Number(budget) <= 0) {
      setError('Please enter a valid investment budget.')
      return
    }

    if (scope === 'asset' && !assetId) {
      setError('Please select a device for individual-device optimization.')
      return
    }

    setLoading(true)
    setError('')
    setRecommendationError('')
    setResult(null)
    setRecommendations([])

    let runData

    try {
      const requestBody = {
        organization_id: Number(organizationId),
        asset_id: scope === 'asset' ? Number(assetId) : null,
        available_budget: Number(budget),
      }

      const response = await api.post(
        '/optimization/run',
        requestBody
      )

      runData = response.data
      setResult(runData)
    } catch (err) {
      console.error('Optimization failed:', err)
      setError(`Optimization failed: ${getErrorMessage(err)}`)
      setLoading(false)
      return
    }

    const runId = runData.run_id || runData.optimization_run_id

    if (runId) {
      try {
        const recommendationResponse = await api.get(
          `/optimization/recommendations/${runId}`
        )

        setRecommendations(
          getArray(recommendationResponse.data, [
            'recommendations',
            'items',
            'results',
          ])
        )
      } catch (err) {
        console.error('Could not load recommendations:', err)
        setRecommendationError(
          `Optimization completed, but recommendations could not be loaded: ${getErrorMessage(err)}`
        )
      }
    } else {
      setRecommendationError(
        'The optimization completed, but the backend did not return a run ID.'
      )
    }

    await loadHistory()
    setLoading(false)
  }

  const riskBefore = result?.estimated_risk_before ?? 0
  const riskAfter = result?.estimated_risk_after ?? 0
  const totalInvestment = result?.total_investment ?? 0

  const riskReduction =
    result?.estimated_risk_reduction ??
    result?.risk_reduction ??
    Math.max(0, Number(riskBefore) - Number(riskAfter))

  const resultScope =
    result?.optimization_scope ||
    (result?.asset_id ? 'Individual device' : 'Organization-wide')

  const resultAssetName =
    result?.asset_name ||
    (result?.asset_id ? `Asset ${result.asset_id}` : null)

  return (
    <div className="space-y-6">
      <PageTitle
        title="Investment optimization"
        desc="AI-assisted security investment planning using predictive risk priorities and OR-Tools."
      />

      <div className="grid gap-5 xl:grid-cols-[1fr_1fr]">
        <Panel
          title="Investment configuration"
          subtitle="Choose an organization, optimization scope and investment budget."
        >
          <label className="mb-2 block text-sm font-medium text-slate-300">
            Select organization
          </label>

          <select
            className="field w-full"
            value={organizationId}
            onChange={(event) => setOrganizationId(event.target.value)}
            disabled={loadingOrganizations || loading}
          >
            <option value="">
              {loadingOrganizations
                ? 'Loading organizations...'
                : 'Select an organization'}
            </option>

            {organizations.map((organization) => (
              <option
                key={organization.organization_id}
                value={organization.organization_id}
              >
                {organization.name ||
                  organization.organization_name ||
                  `Organization ${organization.organization_id}`}
                {' (ID: '}
                {organization.organization_id}
                {')'}
              </option>
            ))}
          </select>

          {selectedOrganization && (
            <div className="mt-3 rounded-lg border border-slate-700 bg-slate-900/50 p-3">
              <p className="text-xs muted">Selected organization</p>
              <p className="mt-1 font-semibold text-white">
                {selectedOrganization.name ||
                  selectedOrganization.organization_name ||
                  `Organization ${selectedOrganization.organization_id}`}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Organization ID: {organizationId}
              </p>
            </div>
          )}

          <label className="mb-3 mt-5 block text-sm font-medium text-slate-300">
            Optimization scope
          </label>

          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => {
                setScope('organization')
                setResult(null)
                setRecommendations([])
                setRecommendationError('')
                setError('')
              }}
              disabled={loading}
              className={`rounded-xl border p-4 text-left transition ${
                scope === 'organization'
                  ? 'border-teal-400 bg-teal-500/10 text-teal-300'
                  : 'border-slate-700 bg-slate-900/40 text-slate-300'
              }`}
            >
              <Building2 size={21} className="mb-2" />
              <p className="text-sm font-semibold">Entire organization</p>
              <p className="mt-1 text-xs muted">
                Optimize across all assets
              </p>
            </button>

            <button
              type="button"
              onClick={() => {
                setScope('asset')
                setResult(null)
                setRecommendations([])
                setRecommendationError('')
                setError('')
              }}
              disabled={loading}
              className={`rounded-xl border p-4 text-left transition ${
                scope === 'asset'
                  ? 'border-teal-400 bg-teal-500/10 text-teal-300'
                  : 'border-slate-700 bg-slate-900/40 text-slate-300'
              }`}
            >
              <Monitor size={21} className="mb-2" />
              <p className="text-sm font-semibold">Individual device</p>
              <p className="mt-1 text-xs muted">
                Optimize one selected asset
              </p>
            </button>
          </div>

          {scope === 'asset' && (
            <div className="mt-5">
              <label className="mb-2 block text-sm font-medium text-slate-300">
                Select device / asset
              </label>

              <select
                className="field w-full"
                value={assetId}
                onChange={(event) => {
                  setAssetId(event.target.value)
                  setResult(null)
                  setRecommendations([])
                  setRecommendationError('')
                  setError('')
                }}
                disabled={loadingAssets || loading || !organizationId}
              >
                <option value="">
                  {loadingAssets
                    ? 'Loading devices...'
                    : 'Select a device'}
                </option>

                {assets.map((asset) => (
                  <option
                    key={asset.asset_id}
                    value={asset.asset_id}
                  >
                    {asset.asset_name ||
                      asset.hostname ||
                      asset.ip_address ||
                      `Asset ${asset.asset_id}`}
                    {' (ID: '}
                    {asset.asset_id}
                    {')'}
                  </option>
                ))}
              </select>

              {selectedAsset && (
                <div className="mt-3 rounded-lg border border-slate-700 bg-slate-900/50 p-3">
                  <p className="text-xs muted">Selected device</p>
                  <p className="mt-1 font-semibold text-white">
                    {selectedAsset.asset_name ||
                      selectedAsset.hostname ||
                      selectedAsset.ip_address ||
                      `Asset ${selectedAsset.asset_id}`}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Asset ID: {selectedAsset.asset_id}
                    {selectedAsset.asset_type
                      ? ` • ${selectedAsset.asset_type}`
                      : ''}
                  </p>
                </div>
              )}

              {!loadingAssets && assets.length === 0 && organizationId && (
                <p className="mt-2 text-xs text-amber-300">
                  No assets were found for this organization.
                </p>
              )}
            </div>
          )}

          <label className="mb-2 mt-5 block text-sm muted">
            Available security budget (₹)
          </label>

          <input
            type="number"
            min="1"
            value={budget}
            onChange={(event) => setBudget(event.target.value)}
            className="field w-full"
            placeholder="Enter budget in INR"
            disabled={loading}
          />

          <p className="mt-2 text-lg font-bold text-teal-300">
            {money(budget)}
          </p>

          <button
            onClick={runOptimization}
            disabled={
              loading ||
              loadingOrganizations ||
              loadingAssets ||
              !organizationId ||
              !budget ||
              Number(budget) <= 0 ||
              (scope === 'asset' && !assetId)
            }
            className="btn-primary mt-5 w-full disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading
              ? 'Optimizing investments...'
              : 'Run OR-Tools optimization'}
          </button>

          <button
            onClick={loadOrganizations}
            disabled={loadingOrganizations || loading}
            className="btn-secondary mt-3 flex w-full items-center justify-center gap-2"
          >
            <RefreshCw size={15} />
            {loadingOrganizations ? 'Refreshing...' : 'Refresh organizations'}
          </button>

          {error && (
            <p className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">
              {error}
            </p>
          )}
        </Panel>

        <Panel
          title="Optimization results"
          subtitle={
            result
              ? `${resultScope}${resultAssetName ? ` • ${resultAssetName}` : ''}`
              : selectedOrganization
                ? `Results for ${selectedOrganization.name ||
                  selectedOrganization.organization_name ||
                  `Organization ${selectedOrganization.organization_id}`}`
                : 'Results returned by the backend optimization engine'
          }
        >
          {!result ? (
            <div className="py-10 text-center">
              <Target className="mx-auto mb-3 text-slate-500" size={36} />
              <p className="text-sm muted">
                Choose your optimization scope, set your budget and run
                optimization to see recommended investments.
              </p>
            </div>
          ) : (
            <div className="space-y-5">
              <div>
                <p className="text-xs muted">
                  Total recommended investment
                </p>
                <p className="mt-1 text-3xl font-bold text-white">
                  {money(totalInvestment)}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl border border-slate-700 p-4">
                  <p className="text-xs muted">Risk before</p>
                  <p className="mt-1 text-2xl font-bold">
                    {riskBefore}
                  </p>
                </div>

                <div className="rounded-xl border border-slate-700 p-4">
                  <p className="text-xs muted">Risk after</p>
                  <p className="mt-1 text-2xl font-bold text-teal-300">
                    {riskAfter}
                  </p>
                </div>
              </div>

              <div className="rounded-xl border border-teal-500/20 bg-teal-500/5 p-4">
                <p className="text-sm muted">
                  Estimated risk reduction
                </p>
                <p className="mt-1 text-3xl font-bold text-teal-300">
                  {riskReduction} points
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl border border-slate-700 p-3">
                  <p className="text-xs muted">Remaining budget</p>
                  <p className="mt-1 font-semibold text-white">
                    {money(result.remaining_budget)}
                  </p>
                </div>

                <div className="rounded-xl border border-slate-700 p-3">
                  <p className="text-xs muted">Solver status</p>
                  <p className="mt-1 font-semibold text-teal-300">
                    {result.solver_status || '—'}
                  </p>
                </div>
              </div>

              <div className="rounded-lg border border-slate-700 bg-slate-900/40 p-3">
                <p className="text-xs muted">Optimization scope</p>
                <p className="mt-1 font-semibold text-white">
                  {resultScope}
                </p>

                {resultAssetName && (
                  <p className="mt-1 text-sm muted">
                    Device: {resultAssetName}
                    {result.asset_id ? ` (ID: ${result.asset_id})` : ''}
                  </p>
                )}

                <p className="mt-1 text-xs muted">
                  Organization: {result.organization_id ?? organizationId}
                </p>

                <p className="mt-1 text-xs muted">
                  Run ID: {result.run_id || result.optimization_run_id || 'Not returned'}
                </p>
              </div>

              {result.predictive_prioritization && (
                <div className="rounded-xl border border-slate-700 p-3">
                  <p className="text-sm font-semibold text-white">
                    Predictive prioritization
                  </p>
                  <div className="mt-2 grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <p className="muted">Risk outlook</p>
                      <p className="mt-1 text-slate-200">
                        {result.predictive_prioritization.organization_outlook || '—'}
                      </p>
                    </div>
                    <div>
                      <p className="muted">Data sufficiency</p>
                      <p className="mt-1 text-slate-200">
                        {result.predictive_prioritization.data_sufficiency || '—'}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </Panel>
      </div>

      {result && (
        <Panel
          title="Recommended security investments"
          subtitle="Investments selected by the optimization engine."
        >
          {recommendationError && (
            <p className="mb-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-300">
              {recommendationError}
            </p>
          )}

          {recommendations.length === 0 ? (
            <p className="py-6 text-sm muted">
              No investment recommendations were returned for this run.
            </p>
          ) : (
            <div className="space-y-3">
              {recommendations.map((item, index) => (
                <div
                  key={
                    item.recommendation_id ||
                    item.investment_id ||
                    index
                  }
                  className="rounded-xl border border-slate-700 p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-white">
                        {item.investment_name ||
                          item.name ||
                          `Investment ${item.investment_id || index + 1}`}
                      </p>

                      <p className="mt-1 text-sm muted">
                        {item.description ||
                          'Recommended security investment'}
                      </p>
                    </div>

                    <span className="text-sm font-bold text-teal-300">
                      {money(
                        item.recommended_amount ??
                          item.amount ??
                          item.estimated_cost ??
                          item.cost
                      )}
                    </span>
                  </div>

                  <p className="mt-3 text-xs muted">
                    Estimated risk reduction:{' '}
                    {item.expected_risk_reduction ?? '—'} points
                  </p>

                  {item.priority_weight != null && (
                    <p className="mt-2 text-xs muted">
                      Predictive priority weight: {item.priority_weight}
                    </p>
                  )}

                  {Array.isArray(item.priority_reasons) &&
                    item.priority_reasons.length > 0 && (
                      <div className="mt-3 rounded-lg bg-slate-900/50 p-3">
                        <p className="mb-2 text-xs font-semibold text-slate-300">
                          Priority reasons
                        </p>
                        <ul className="list-disc space-y-1 pl-4 text-xs muted">
                          {item.priority_reasons.map((reason, reasonIndex) => (
                            <li key={reasonIndex}>{reason}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                </div>
              ))}
            </div>
          )}

          <p className="mt-4 text-xs text-slate-500">
            Predicted risk reductions are model estimates, not guaranteed
            improvements in actual security risk.
          </p>
        </Panel>
      )}

      <Panel
        title="Optimization history"
        subtitle={
          selectedOrganization
            ? `Previous optimization runs for ${selectedOrganization.name ||
                  selectedOrganization.organization_name ||
                  `Organization ${selectedOrganization.organization_id}`}`
            : 'Previous investment optimization runs'
        }
      >
        {loadingHistory ? (
          <p className="py-6 text-center text-sm muted">
            Loading optimization history...
          </p>
        ) : history.length === 0 ? (
          <p className="py-6 text-sm muted">
            No optimization history is available for this organization yet.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-700 text-slate-400">
                  <th className="p-3">Run ID</th>
                  <th className="p-3">Scope</th>
                  <th className="p-3">Device</th>
                  <th className="p-3">Budget</th>
                  <th className="p-3">Investment</th>
                  <th className="p-3">Risk before</th>
                  <th className="p-3">Risk after</th>
                  <th className="p-3">Reduction</th>
                </tr>
              </thead>

              <tbody>
                {history.map((item, index) => {
                  const itemScope =
                    item.optimization_scope ||
                    (item.asset_id ? 'Individual device' : 'Organization-wide')

                  return (
                    <tr
                      key={item.run_id || index}
                      className="border-b border-slate-800"
                    >
                      <td className="p-3">
                        #{item.run_id ?? '—'}
                      </td>
                      <td className="p-3">
                        {itemScope}
                      </td>
                      <td className="p-3">
                        {item.asset_name ||
                          (item.asset_id ? `Asset ${item.asset_id}` : 'All assets')}
                      </td>
                      <td className="p-3">
                        {money(item.available_budget)}
                      </td>
                      <td className="p-3">
                        {money(item.total_investment)}
                      </td>
                      <td className="p-3">
                        {item.estimated_risk_before ?? '—'}
                      </td>
                      <td className="p-3">
                        {item.estimated_risk_after ?? '—'}
                      </td>
                      <td className="p-3 text-teal-300">
                        {item.risk_reduction ??
                          (
                            Number(item.estimated_risk_before || 0) -
                            Number(item.estimated_risk_after || 0)
                          )} points
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <p className="text-xs text-slate-500">
        Organization-wide optimization evaluates the selected organization's
        assets. Individual-device optimization evaluates only the selected
        device. Predictive priorities use available risk findings, verified
        control gaps and predictive signals. Risk reductions are estimates,
        not guarantees.
      </p>
    </div>
  )
}

export default Optimization
