
import { useCallback, useEffect, useState } from 'react'
import { FileText, Download, RefreshCw, AlertTriangle } from 'lucide-react'

import api from '../../services_api'
import { download } from '../utils/helpers'
import { PageTitle } from '../components/UI'

function extractArray(data, keys = []) {
  if (Array.isArray(data)) return data

  for (const key of keys) {
    if (Array.isArray(data?.[key])) return data[key]
  }

  return []
}

function isOpenFinding(finding) {
  const status = String(finding.status || 'Open').toLowerCase()

  return !['closed', 'resolved', 'accepted', 'false positive'].includes(status)
}

function getAssetName(asset) {
  return asset.asset_name || asset.name || asset.hostname || ''
}

function Reports() {
  const [organizations, setOrganizations] = useState([])
  const [organizationId, setOrganizationId] = useState('')

  const [assets, setAssets] = useState([])
  const [findings, setFindings] = useState([])
  const [riskSummary, setRiskSummary] = useState(null)

  const [loadingOrganizations, setLoadingOrganizations] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  // Load available organizations
  useEffect(() => {
    let active = true

    async function loadOrganizations() {
      setLoadingOrganizations(true)

      try {
        const response = await api.get('/organizations/')
        const organizationList = extractArray(response.data, [
          'organizations',
          'items',
          'results',
        ])

        if (!active) return

        setOrganizations(organizationList)

        if (organizationList.length > 0) {
          setOrganizationId((currentId) => {
            const existing = organizationList.find(
              (org) => String(org.organization_id ?? org.id) === String(currentId)
            )

            return String(
              existing?.organization_id ??
              existing?.id ??
              organizationList[0].organization_id ??
              organizationList[0].id
            )
          })
        } else {
          setOrganizationId('')
          setError('No organizations are available. Register an organization first.')
        }
      } catch (err) {
        if (active) {
          setError(
            err.response?.data?.detail ||
            'Unable to load organizations. Please check the backend connection.'
          )
        }
      } finally {
        if (active) setLoadingOrganizations(false)
      }
    }

    loadOrganizations()

    return () => {
      active = false
    }
  }, [])

  // Load report data for the selected organization
  const loadReportData = useCallback(async () => {
    if (!organizationId) return

    setLoading(true)
    setError('')

    const results = await Promise.allSettled([
      api.get('/assets/', {
        params: { organization_id: organizationId },
      }),
      api.get('/risk-findings/', {
        params: { organization_id: organizationId },
      }),
      api.get(`/organizations/${organizationId}/risk-summary`),
    ])

    const errors = []

    if (results[0].status === 'fulfilled') {
      setAssets(
        extractArray(results[0].value.data, ['assets', 'items', 'results'])
      )
    } else {
      setAssets([])
      errors.push('Asset inventory')
    }

    if (results[1].status === 'fulfilled') {
      setFindings(
        extractArray(results[1].value.data, ['findings', 'items', 'results'])
      )
    } else {
      setFindings([])
      errors.push('Risk findings')
    }

    if (results[2].status === 'fulfilled') {
      setRiskSummary(results[2].value.data)
    } else {
      setRiskSummary(null)
      errors.push('Organization risk summary')
    }

    if (errors.length > 0) {
      setError(
        `Unable to load: ${errors.join(', ')}. Some reports may be unavailable.`
      )
    }

    setLoading(false)
  }, [organizationId])

  useEffect(() => {
    if (organizationId) {
      setAssets([])
      setFindings([])
      setRiskSummary(null)
      loadReportData()
    }
  }, [loadReportData, refreshKey, organizationId])

  const openFindings = findings.filter(isOpenFinding)

  const selectedOrganization = organizations.find(
    (org) =>
      String(org.organization_id ?? org.id) === String(organizationId)
  )

  const organizationName =
    selectedOrganization?.organization_name ||
    selectedOrganization?.name ||
    riskSummary?.organization_name ||
    `Organization #${organizationId}`

  const exportAssets = () => {
    download('cyberrisk-asset-inventory.csv', [
      [
        'Asset ID',
        'Asset Name',
        'Asset Type',
        'Hostname',
        'IP Address',
        'Operating System',
        'Environment',
        'Owner',
        'Business Unit',
        'Criticality',
        'Exposure Level',
        'Cloud Provider',
      ],
      ...assets.map((asset) => [
        asset.asset_id ?? asset.id ?? '',
        getAssetName(asset),
        asset.asset_type ?? asset.type ?? '',
        asset.hostname ?? '',
        asset.ip_address ?? '',
        asset.operating_system ?? asset.os ?? '',
        asset.environment ?? '',
        asset.owner ?? '',
        asset.business_unit ?? '',
        asset.criticality ?? '',
        asset.exposure_level ?? asset.exposure ?? '',
        asset.cloud_provider ?? '',
      ]),
    ])
  }

  const exportFindings = () => {
    download('cyberrisk-open-findings.csv', [
      [
        'Finding ID',
        'Title',
        'Category',
        'Source',
        'Asset ID',
        'Severity',
        'Likelihood',
        'Impact',
        'Status',
        'Detected At',
      ],
      ...openFindings.map((finding) => [
        finding.finding_id ?? finding.id ?? '',
        finding.title ?? '',
        finding.category ?? '',
        finding.source ?? '',
        finding.asset_id ?? '',
        finding.severity ?? '',
        finding.likelihood ?? '',
        finding.impact ?? '',
        finding.status ?? 'Open',
        finding.detected_at ?? '',
      ]),
    ])
  }

  const exportRiskSnapshot = () => {
    if (!riskSummary) return

    const rows = [
      ['CyberRisk Organization Risk Snapshot'],
      ['Organization', riskSummary.organization_name ?? organizationName],
      ['Organization ID', riskSummary.organization_id ?? organizationId],
      ['Risk Score', riskSummary.risk_score ?? 'Not Assessed'],
      ['Risk Level', riskSummary.risk_level ?? 'Not Assessed'],
      ['Total Assets', riskSummary.total_assets ?? 0],
      ['Assessed Assets', riskSummary.assessed_assets ?? 0],
      ['Unassessed Assets', riskSummary.unassessed_assets ?? 0],
      ['Assessment Coverage (%)', riskSummary.assessment_coverage_percentage ?? 0],
      [],
      [
        'Asset ID',
        'Asset Name',
        'Criticality',
        'Risk Score',
        'Risk Level',
        'Assessment ID',
        'Assessment Date',
        'Assessment Status',
      ],
    ]

    const assessed = riskSummary.asset_risks || []
    const unassessed = riskSummary.unassessed_asset_details || []

    assessed.forEach((asset) => {
      rows.push([
        asset.asset_id ?? '',
        asset.asset_name ?? '',
        asset.criticality ?? '',
        asset.risk_score ?? '',
        asset.risk_level ?? '',
        asset.assessment_id ?? '',
        asset.assessed_at ?? '',
        'Assessed',
      ])
    })

    unassessed.forEach((asset) => {
      rows.push([
        asset.asset_id ?? '',
        asset.asset_name ?? '',
        asset.criticality ?? '',
        '',
        'Not Assessed',
        '',
        '',
        asset.reason ?? 'Not Assessed',
      ])
    })

    download('cyberrisk-organization-risk-snapshot.csv', rows)
  }

  const reports = [
    {
      title: 'Asset inventory report',
      description: 'Live registered assets, ownership, criticality, network and environment details.',
      count: `${assets.length} assets`,
      action: exportAssets,
      disabled: loading || assets.length === 0,
    },
    {
      title: 'Open security findings',
      description: 'Live open vulnerabilities and operational findings with severity and risk details.',
      count: `${openFindings.length} open findings`,
      action: exportFindings,
      disabled: loading || openFindings.length === 0,
    },
    {
      title: 'Organization risk snapshot',
      description: 'Current organization risk score, assessment coverage and assessed or unassessed assets.',
      count: riskSummary
        ? `${riskSummary.assessed_assets ?? 0} assessed assets`
        : 'Unavailable',
      action: exportRiskSnapshot,
      disabled: loading || !riskSummary,
    },
  ]

  return (
    <div className="space-y-6">
      <PageTitle
        title="Reports"
        desc="Generate and export live cybersecurity reports for your organization."
        extra={
          <button
            onClick={() => setRefreshKey((value) => value + 1)}
            disabled={loading || !organizationId}
            className="btn-secondary flex items-center gap-2 text-xs disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh data
          </button>
        }
      />

      {/* Organization selector */}
      <div className="panel flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-white">
            Select organization
          </h3>
          <p className="mt-1 text-xs text-slate-400">
            Reports will be generated for the selected organization.
          </p>
        </div>

        <select
          value={organizationId}
          onChange={(event) => setOrganizationId(event.target.value)}
          disabled={loadingOrganizations || organizations.length === 0}
          className="input-field w-full sm:max-w-xs"
        >
          {organizations.map((org) => {
            const id = org.organization_id ?? org.id
            const name =
              org.organization_name ||
              org.name ||
              `Organization #${id}`

            return (
              <option key={id} value={String(id)}>
                {name} (ID: {id})
              </option>
            )
          })}
        </select>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-200">
          <AlertTriangle size={18} className="mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">Report data warning</p>
            <p className="mt-1 text-amber-200/80">{error}</p>
          </div>
        </div>
      )}

      {loadingOrganizations && (
        <p className="text-sm text-slate-400">
          Loading organizations...
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        {reports.map((report) => (
          <div className="panel p-5" key={report.title}>
            <div className="mb-4 grid h-11 w-11 place-items-center rounded-xl bg-teal-400/10 text-teal-300">
              <FileText size={21} />
            </div>

            <h3 className="font-semibold text-white">{report.title}</h3>

            <p className="mt-2 min-h-16 text-sm text-slate-400">
              {report.description}
            </p>

            <p className="mt-3 text-xs font-medium text-teal-300">
              {loading || loadingOrganizations
                ? 'Loading data...'
                : report.count}
            </p>

            <button
              onClick={report.action}
              disabled={
                loading ||
                loadingOrganizations ||
                !organizationId ||
                report.disabled
              }
              className="btn-secondary mt-5 flex w-full items-center justify-center gap-2 text-xs disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Download size={14} />
              Download CSV
            </button>
          </div>
        ))}
      </div>

      <div className="panel p-5">
        <h3 className="font-semibold text-white">Report information</h3>
        <p className="mt-2 text-sm leading-6 text-slate-400">
          Reports are generated from the currently available backend records
          for {organizationName}. The organization risk snapshot includes
          only valid numerical assessments and explicitly identifies assets
          that remain unassessed. Historical risk trends are not included
          because a verified historical trend export is not currently
          connected to this page.
        </p>
      </div>
    </div>
  )
}

export default Reports
