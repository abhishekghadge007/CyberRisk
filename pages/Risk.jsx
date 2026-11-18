
import { useCallback, useEffect, useState } from 'react'
import { RefreshCw, ShieldAlert, Calculator } from 'lucide-react'

import api from '../../services_api'
import { Badge, Panel, PageTitle } from '../components/UI'

function Risk() {
  const [organizations, setOrganizations] = useState([])
  const [organizationId, setOrganizationId] = useState('')
  const [assets, setAssets] = useState([])
  const [assetId, setAssetId] = useState('')
  const [assessment, setAssessment] = useState(null)

  const [loadingOrganizations, setLoadingOrganizations] = useState(true)
  const [loadingAssets, setLoadingAssets] = useState(false)
  const [calculating, setCalculating] = useState(false)
  const [error, setError] = useState('')

  // ==========================================
  // LOAD ORGANIZATIONS
  // ==========================================

  const loadOrganizations = useCallback(async () => {
    setLoadingOrganizations(true)
    setError('')

    try {
      const response = await api.get('/organizations/')

      const data = Array.isArray(response.data)
        ? response.data
        : response.data.organizations ||
          response.data.items ||
          response.data.results ||
          []

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
      setError(
        err.response?.data?.detail ||
          'Unable to load organizations.'
      )
      setOrganizations([])
      setOrganizationId('')
    } finally {
      setLoadingOrganizations(false)
    }
  }, [])

  useEffect(() => {
    loadOrganizations()
  }, [loadOrganizations])

  // ==========================================
  // LOAD ASSETS FOR SELECTED ORGANIZATION
  // ==========================================

  const loadAssets = useCallback(async () => {
    if (!organizationId) {
      setAssets([])
      setAssetId('')
      setAssessment(null)
      return
    }

    setLoadingAssets(true)
    setError('')
    setAssessment(null)

    try {
      const response = await api.get('/assets/', {
        params: {
          organization_id: Number(organizationId),
        },
      })

      const data = Array.isArray(response.data)
        ? response.data
        : response.data.assets ||
          response.data.items ||
          response.data.results ||
          []

      // Remove duplicate asset IDs.
      const uniqueAssets = Array.from(
        new Map(
          data.map((asset) => [
            String(asset.asset_id),
            asset,
          ])
        ).values()
      )

      setAssets(uniqueAssets)

      setAssetId((current) =>
        uniqueAssets.some(
          (asset) => String(asset.asset_id) === current
        )
          ? current
          : uniqueAssets.length > 0
            ? String(uniqueAssets[0].asset_id)
            : ''
      )
    } catch (err) {
      setAssets([])
      setAssetId('')
      setError(
        err.response?.data?.detail ||
          'Unable to load organization assets.'
      )
    } finally {
      setLoadingAssets(false)
    }
  }, [organizationId])

  useEffect(() => {
    loadAssets()
  }, [loadAssets])

  // ==========================================
  // CALCULATE RISK
  // ==========================================

  const calculateRisk = async () => {
    if (!assetId || !organizationId) return

    setCalculating(true)
    setError('')
    setAssessment(null)

    try {
      const response = await api.post(
        `/risk-assessments/assets/${assetId}/calculate`
      )

      setAssessment(response.data)
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          'Risk assessment could not be calculated.'
      )
    } finally {
      setCalculating(false)
    }
  }

  // ==========================================
  // ASSESSMENT DATA
  // ==========================================

  const details = assessment?.assessment_details
  const breakdown = details?.risk_breakdown
  const findings = details?.evaluated_findings || []

  const controls =
    details?.security_control_analysis?.evaluated_controls || []

  const score = assessment?.risk_score
  const level = assessment?.risk_level || 'Not Assessed'

  const scoreColor =
    level === 'Critical'
      ? '#fb7185'
      : level === 'High'
        ? '#fb923c'
        : level === 'Moderate' || level === 'Medium'
          ? '#fbbf24'
          : '#34d399'

  const selectedOrganization = organizations.find(
    (organization) =>
      String(organization.organization_id) === organizationId
  )

  // ==========================================
  // UI
  // ==========================================

  return (
    <div className="space-y-6">
      <PageTitle
        title="Risk assessment"
        desc="Calculate explainable asset risk using the CyberRisk backend risk engine."
        extra={
          <button
            onClick={loadOrganizations}
            disabled={loadingOrganizations}
            className="btn-secondary flex items-center gap-2 text-xs"
          >
            <RefreshCw
              size={14}
              className={
                loadingOrganizations ? 'animate-spin' : ''
              }
            />
            Refresh organizations
          </button>
        }
      />

      {error && (
        <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-300">
          {error}
        </div>
      )}

      {/* ORGANIZATION AND ASSET SELECTION */}

      <Panel
        title="Select organization and asset"
        subtitle={
          selectedOrganization
            ? `Organization: ${selectedOrganization.name || selectedOrganization.organization_name || `Organization ${selectedOrganization.organization_id}`}`
            : 'Select an organization to view its assets.'
        }
      >
        <div className="space-y-4">
          <div>
            <label className="mb-2 block text-sm text-slate-400">
              Organization
            </label>

            <select
              className="field w-full"
              value={organizationId}
              onChange={(e) => {
                setOrganizationId(e.target.value)
                setAssets([])
                setAssetId('')
                setAssessment(null)
                setError('')
              }}
              disabled={
                loadingOrganizations ||
                organizations.length === 0
              }
            >
              {loadingOrganizations && (
                <option value="">
                  Loading organizations...
                </option>
              )}

              {!loadingOrganizations &&
                organizations.length === 0 && (
                  <option value="">
                    No organizations available
                  </option>
                )}

              {organizations.map((organization) => (
                <option
                  key={organization.organization_id}
                  value={organization.organization_id}
                >
                  {organization.name ||
                    organization.organization_name ||
                    `Organization ${organization.organization_id}`}
                  {' · ID '}
                  {organization.organization_id}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-4 sm:flex-row">
            <div className="min-w-0 flex-1">
              <label className="mb-2 block text-sm text-slate-400">
                Asset
              </label>

              <select
                className="field w-full"
                value={assetId}
                onChange={(e) => {
                  setAssetId(e.target.value)
                  setAssessment(null)
                }}
                disabled={
                  loadingAssets ||
                  loadingOrganizations ||
                  assets.length === 0
                }
              >
                {loadingAssets && (
                  <option value="">
                    Loading assets...
                  </option>
                )}

                {!loadingAssets &&
                  organizationId &&
                  assets.length === 0 && (
                    <option value="">
                      No assets available for this organization
                    </option>
                  )}

                {assets.map((asset) => (
                  <option
                    key={asset.asset_id}
                    value={asset.asset_id}
                  >
                    {asset.asset_name ||
                      asset.hostname ||
                      asset.ip_address ||
                      `Asset ${asset.asset_id}`}
                    {' · '}
                    {asset.criticality || 'Unclassified'}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={calculateRisk}
                disabled={
                  !assetId ||
                  calculating ||
                  loadingAssets ||
                  loadingOrganizations
                }
                className="btn-primary flex w-full items-center justify-center gap-2 disabled:opacity-50 sm:w-auto"
              >
                <Calculator size={16} />
                {calculating
                  ? 'Calculating...'
                  : 'Calculate risk'}
              </button>
            </div>
          </div>
        </div>
      </Panel>

      {/* RISK ASSESSMENT RESULTS */}

      {assessment && (
        <>
          <div className="grid gap-5 xl:grid-cols-[0.8fr_1.2fr]">
            <Panel
              title="Asset risk score"
              subtitle={
                details?.methodology ||
                'CyberRisk risk assessment'
              }
            >
              <div className="flex flex-col items-center py-5">
                <div
                  className="grid h-44 w-44 place-items-center rounded-full"
                  style={{
                    background:
                      score == null
                        ? '#263244'
                        : `conic-gradient(${scoreColor} ${score * 3.6}deg, #263244 0deg)`,
                  }}
                >
                  <div className="grid h-36 w-36 place-items-center rounded-full bg-[#101827]">
                    <div className="text-center">
                      <p className="text-5xl font-bold text-white">
                        {score ?? '—'}
                      </p>
                      <p className="text-xs text-slate-500">
                        out of 100
                      </p>
                    </div>
                  </div>
                </div>

                <div className="mt-4">
                  <Badge value={level} />
                </div>

                <p className="mt-3 text-center text-sm text-slate-400">
                  {details?.asset?.asset_name ||
                    `Asset ${assessment.asset_id}`}
                </p>
              </div>

              <div className="space-y-3 border-t border-slate-800 pt-4 text-sm">
                <div className="flex justify-between gap-3">
                  <span className="text-slate-500">
                    Assessment ID
                  </span>
                  <b>{assessment.assessment_id}</b>
                </div>

                <div className="flex justify-between gap-3">
                  <span className="text-slate-500">
                    Criticality
                  </span>
                  <b>
                    {details?.asset?.criticality || '—'}
                  </b>
                </div>

                <div className="flex justify-between gap-3">
                  <span className="text-slate-500">
                    Open findings
                  </span>
                  <b>
                    {details?.open_findings_count ?? 0}
                  </b>
                </div>

                <div className="flex justify-between gap-3">
                  <span className="text-slate-500">
                    Control adjustment
                  </span>
                  <b>
                    {breakdown?.security_control_adjustment ?? 0}
                  </b>
                </div>
              </div>
            </Panel>

            <Panel
              title="Risk calculation breakdown"
              subtitle={
                details?.calculation ||
                'Backend calculation'
              }
            >
              <div className="space-y-4">
                {[
                  [
                    'Base risk score',
                    breakdown?.base_risk_score,
                  ],
                  [
                    'Security control adjustment',
                    breakdown?.security_control_adjustment,
                  ],
                  [
                    'Final risk score',
                    breakdown?.final_risk_score,
                  ],
                  [
                    'Exposure factor',
                    details?.factors?.exposure_factor,
                  ],
                  [
                    'Criticality factor',
                    details?.factors?.criticality_factor,
                  ],
                ].map(([label, value]) => (
                  <div
                    key={label}
                    className="flex items-center justify-between gap-3 border-b border-slate-800 pb-3 text-sm"
                  >
                    <span className="text-slate-400">
                      {label}
                    </span>
                    <b className="text-white">
                      {value ?? '—'}
                    </b>
                  </div>
                ))}

                <p className="text-xs leading-5 text-slate-500">
                  {details?.aggregation_method ||
                    'Risk score calculated using evaluated open findings and verified asset-level controls.'}
                </p>
              </div>
            </Panel>
          </div>

          {/* EVALUATED FINDINGS */}

          <Panel
            title="Evaluated risk findings"
            subtitle={`${findings.length} findings included in this assessment`}
          >
            {findings.length === 0 ? (
              <p className="text-sm text-slate-400">
                No valid open risk findings were available for this assessment.
                A numerical risk score may therefore be unavailable.
              </p>
            ) : (
              <div className="space-y-3">
                {findings.map((finding) => (
                  <div
                    key={finding.finding_id}
                    className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <p className="break-words text-sm font-medium text-white">
                        {finding.title}
                      </p>

                      <p className="mt-1 text-xs text-slate-500">
                        Finding #{finding.finding_id}
                        {' · '}
                        {finding.category}
                      </p>
                    </div>

                    <div className="flex shrink-0 items-center gap-3">
                      <Badge value={finding.severity} />

                      <span className="text-sm font-semibold text-white">
                        {finding.adjusted_score ??
                          finding.base_score}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>

          {/* VERIFIED SECURITY CONTROLS */}

          <Panel
            title="Verified security controls"
            subtitle={`${controls.length} verified asset-level controls evaluated`}
          >
            {controls.length === 0 ? (
              <p className="text-sm text-slate-400">
                No verified asset-level security controls were included in this assessment.
              </p>
            ) : (
              <div className="space-y-3">
                {controls.map((control) => (
                  <div
                    key={control.control_id}
                    className="flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900/40 p-4 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div>
                      <p className="text-sm font-medium text-white">
                        {control.control_name}
                      </p>

                      <p className="mt-1 text-xs text-slate-500">
                        {control.control_key}
                        {' · Effectiveness: '}
                        {control.effectiveness_score}%
                      </p>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="text-xs text-slate-400">
                        {control.status}
                      </span>

                      <span className="text-sm font-semibold text-amber-300">
                        +{control.risk_adjustment}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>

          {/* EXCLUDED FINDINGS */}

          {details?.excluded_findings?.length > 0 && (
            <Panel title="Excluded findings">
              <p className="mb-3 text-xs text-slate-500">
                These findings were not included in the numerical assessment.
              </p>

              {details.excluded_findings.map(
                (finding, index) => (
                  <div
                    key={index}
                    className="border-b border-slate-800 py-2 text-sm"
                  >
                    {finding.title ||
                      finding.reason ||
                      JSON.stringify(finding)}
                  </div>
                )
              )}
            </Panel>
          )}
        </>
      )}

      {/* INITIAL STATE */}

      {!assessment &&
        !loadingAssets &&
        !loadingOrganizations && (
          <div className="panel flex flex-col items-center justify-center p-10 text-center">
            <ShieldAlert
              size={32}
              className="text-teal-300"
            />

            <p className="mt-3 font-semibold text-white">
              Ready for risk assessment
            </p>

            <p className="mt-2 max-w-md text-sm text-slate-500">
              Select an organization and asset, then calculate
              its risk to view actual findings, verified
              controls and the explainable risk breakdown.
            </p>
          </div>
        )}
    </div>
  )
}

export default Risk
