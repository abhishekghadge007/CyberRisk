
import { useCallback, useEffect, useRef, useState } from 'react'
import api from '../../services_api'
import { Badge, Panel, PageTitle } from '../components/UI'

const SEVERITIES = ['Critical', 'High', 'Medium', 'Low']

function getErrorMessage(error) {
  return (
    error.response?.data?.detail ||
    error.message ||
    'Something went wrong. Please try again.'
  )
}

function getArray(data, keys = []) {
  if (Array.isArray(data)) return data

  for (const key of keys) {
    if (Array.isArray(data?.[key])) return data[key]
  }

  return []
}

function formatDate(value) {
  if (!value) return '—'

  const date = new Date(value)

  return Number.isNaN(date.getTime())
    ? '—'
    : date.toLocaleString('en-IN')
}

function getCveIds(evidence = {}) {
  const ids = [
    ...(Array.isArray(evidence.cve_ids) ? evidence.cve_ids : []),
    ...(evidence.cve_id ? [evidence.cve_id] : []),
  ]

  return [...new Set(ids.filter(Boolean))]
}

function Vulnerabilities() {
  const [organizations, setOrganizations] = useState([])
  const [organizationId, setOrganizationId] = useState('')
  const [targetNetwork, setTargetNetwork] = useState('')

  const [findings, setFindings] = useState([])
  const [assets, setAssets] = useState([])
  const [scanResults, setScanResults] = useState([])

  const [scanId, setScanId] = useState(null)
  const [scanStatus, setScanStatus] = useState('')
  const [analysisSummary, setAnalysisSummary] = useState(null)

  const [loadingOrganizations, setLoadingOrganizations] = useState(true)
  const [loadingFindings, setLoadingFindings] = useState(false)
  const [startingScan, setStartingScan] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)

  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [q, setQ] = useState('')
  const [severity, setSeverity] = useState('All')
  const [sourceFilter, setSourceFilter] = useState('All')

  const cancelPolling = useRef(false)

  // ==========================================
  // LOAD ORGANIZATIONS
  // ==========================================

  const loadOrganizations = useCallback(async () => {
    setLoadingOrganizations(true)

    try {
      const response = await api.get('/organizations/')
      const data = getArray(response.data, [
        'organizations',
        'items',
        'results',
      ])

      setOrganizations(data)

      if (data.length > 0) {
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

          return String(data[0].organization_id)
        })
      } else {
        setOrganizationId('')
      }
    } catch (err) {
      console.error('Organization loading failed:', err)
      setError(`Could not load organizations: ${getErrorMessage(err)}`)
    } finally {
      setLoadingOrganizations(false)
    }
  }, [])

  // ==========================================
  // LOAD FINDINGS AND ASSETS
  // ==========================================

  const loadFindings = useCallback(async () => {
    if (!organizationId) {
      setFindings([])
      setAssets([])
      return
    }

    setLoadingFindings(true)
    setError('')

    try {
      const [findingResponse, assetResponse] = await Promise.all([
        api.get('/risk-findings/', {
          params: { organization_id: organizationId },
        }),
        api.get('/assets/', {
          params: { organization_id: organizationId },
        }),
      ])

      const allFindings = getArray(findingResponse.data, [
        'findings',
        'items',
        'results',
      ])

      // Vulnerability category includes Nmap/NVD and OpenVAS.
      setFindings(
        allFindings.filter(
          (finding) =>
            String(finding.category || '').toLowerCase() === 'vulnerability'
        )
      )

      setAssets(
        getArray(assetResponse.data, ['assets', 'items', 'results'])
      )
    } catch (err) {
      console.error('Vulnerability findings loading failed:', err)
      setError(
        `Could not load vulnerability findings: ${getErrorMessage(err)}`
      )
    } finally {
      setLoadingFindings(false)
    }
  }, [organizationId])

  useEffect(() => {
    loadOrganizations()

    return () => {
      cancelPolling.current = true
    }
  }, [loadOrganizations])

  useEffect(() => {
    setFindings([])
    setAssets([])
    setScanResults([])
    setScanId(null)
    setAnalysisSummary(null)

    if (organizationId) {
      loadFindings()
    }
  }, [organizationId, loadFindings])

  // ==========================================
  // ASSET NAME
  // ==========================================

  const getAssetName = (assetId, evidence) => {
    const asset = assets.find(
      (item) => String(item.asset_id) === String(assetId)
    )

    if (asset) {
      return (
        asset.asset_name ||
        asset.hostname ||
        asset.ip_address ||
        `Asset ${assetId}`
      )
    }

    return (
      evidence?.host_ip ||
      evidence?.ip_address ||
      (assetId ? `Asset ${assetId}` : 'Unknown asset')
    )
  }

  // ==========================================
  // VULNERABILITY ANALYSIS
  // ==========================================

  const wait = (milliseconds) =>
    new Promise((resolve) => setTimeout(resolve, milliseconds))

  const runVulnerabilityAnalysis = async (currentScanId) => {
    setAnalyzing(true)
    setMessage(
      'Scan completed. Checking discovered software against NVD and CISA KEV...'
    )

    try {
      const response = await api.post(
        `/scans/${currentScanId}/analyze-vulnerabilities`,
        {},
        { timeout: 0 }
      )

      setAnalysisSummary(response.data)
      setMessage(response.data.message || 'Vulnerability analysis completed.')

      await loadFindings()
    } catch (err) {
      console.error('Vulnerability analysis failed:', err)
      setError(
        `The network scan completed, but vulnerability analysis failed: ${getErrorMessage(err)}`
      )
    } finally {
      setAnalyzing(false)
    }
  }

  // ==========================================
  // START NMAP SCAN
  // ==========================================

  const startScan = async () => {
    if (!organizationId) {
      setError('Please select an organization.')
      return
    }

    if (!targetNetwork.trim()) {
      setError('Please enter a target IP address or network range.')
      return
    }

    cancelPolling.current = false
    setError('')
    setMessage('')
    setAnalysisSummary(null)
    setScanResults([])
    setScanId(null)
    setScanStatus('queued')
    setStartingScan(true)

    try {
      const response = await api.post('/scans/start', {
        organization_id: Number(organizationId),
        target_network: targetNetwork.trim(),
      })

      const newScanId = response.data.scan_id

      if (!newScanId) {
        throw new Error('The backend did not return a scan ID.')
      }

      setScanId(newScanId)
      setScanStatus(response.data.status || 'queued')
      setMessage(`Scan #${newScanId} has been queued.`)

      let completedScan = false

      for (let attempt = 0; attempt < 240; attempt += 1) {
        if (cancelPolling.current) return

        await wait(2000)

        if (cancelPolling.current) return

        const statusResponse = await api.get(`/scans/${newScanId}`)
        const currentStatus = String(
          statusResponse.data.status || ''
        ).toLowerCase()

        setScanStatus(currentStatus)

        if (currentStatus === 'completed') {
          completedScan = true
          break
        }

        if (currentStatus === 'failed') {
          throw new Error(
            statusResponse.data.error_message || 'The network scan failed.'
          )
        }
      }

      if (!completedScan) {
        throw new Error(
          'The scan is taking longer than expected. Check its status in Scan History.'
        )
      }

      const resultsResponse = await api.get(`/scans/${newScanId}/results`)

      setScanResults(
        getArray(resultsResponse.data, ['results', 'items'])
      )

      await runVulnerabilityAnalysis(newScanId)
    } catch (err) {
      console.error('Scan workflow failed:', err)
      setError(`Scan workflow: ${getErrorMessage(err)}`)
      setMessage('')
    } finally {
      setStartingScan(false)
    }
  }

  // ==========================================
  // FILTER FINDINGS
  // ==========================================

  const filteredFindings = findings.filter((finding) => {
    const findingSeverity = String(finding.severity || '').toLowerCase()
    const selectedSeverity = severity.toLowerCase()
    const evidence = finding.evidence || {}

    const assetName = getAssetName(finding.asset_id, evidence)
    const cveIds = getCveIds(evidence)

    const source = String(finding.source || 'Unknown')

    const matchesSeverity =
      severity === 'All' || findingSeverity === selectedSeverity

    const matchesSource =
      sourceFilter === 'All' ||
      source.toLowerCase() === sourceFilter.toLowerCase()

    const searchText = [
      finding.title,
      finding.description,
      finding.finding_id,
      finding.asset_id,
      assetName,
      source,
      ...cveIds,
      evidence.product,
      evidence.ip_address,
      evidence.host_ip,
      evidence.oid,
      evidence.port,
    ]
      .filter((value) => value !== null && value !== undefined)
      .join(' ')
      .toLowerCase()

    return (
      matchesSeverity &&
      matchesSource &&
      searchText.includes(q.trim().toLowerCase())
    )
  })

  // ==========================================
  // SUMMARY
  // ==========================================

  const severityCounts = SEVERITIES.reduce((counts, item) => {
    counts[item] = findings.filter(
      (finding) =>
        String(finding.severity || '').toLowerCase() === item.toLowerCase()
    ).length

    return counts
  }, {})

  const openCount = findings.filter(
    (finding) => String(finding.status || '').toLowerCase() === 'open'
  ).length

  const kevCount = findings.filter(
    (finding) => finding.evidence?.known_exploited === true
  ).length

  const openvasCount = findings.filter(
    (finding) =>
      String(finding.source || '').toLowerCase() === 'openvas'
  ).length

  const nmapCount = findings.filter((finding) =>
    ['nmap', 'nvd', 'cisa kev', 'vulnerability analysis'].includes(
      String(finding.source || '').toLowerCase()
    )
  ).length

  const getStatusColor = (status) => {
    const value = String(status || '').toLowerCase()

    if (value === 'completed') return 'text-emerald-400'
    if (value === 'failed') return 'text-red-400'
    if (value === 'running') return 'text-blue-400'
    if (value === 'queued') return 'text-amber-400'

    return 'text-slate-400'
  }

  // ==========================================
  // UI
  // ==========================================

  return (
    <div className="space-y-6">
      <PageTitle
        title="Vulnerability management"
        desc="Discover network services, identify potential CVEs and review Nmap/NVD and OpenVAS vulnerability findings."
      />

      {/* NETWORK SCAN */}

      <Panel
        title="Network vulnerability scan"
        subtitle="Scan an authorized private network and analyze discovered software versions."
      >
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Organization
            </label>

            <select
              className="field"
              value={organizationId}
              onChange={(event) => {
                setOrganizationId(event.target.value)
                setError('')
                setMessage('')
              }}
              disabled={loadingOrganizations || startingScan}
            >
              <option value="">
                {loadingOrganizations
                  ? 'Loading organizations...'
                  : 'Select organization'}
              </option>

              {organizations.map((organization) => (
                <option
                  key={organization.organization_id}
                  value={organization.organization_id}
                >
                  {organization.name ||
                    organization.organization_name ||
                    `Organization #${organization.organization_id}`}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Target IP / Network
            </label>

            <input
              className="field"
              value={targetNetwork}
              onChange={(event) => setTargetNetwork(event.target.value)}
              placeholder="Example: 192.168.1.0/24"
              disabled={startingScan}
            />
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            className="btn-primary"
            onClick={startScan}
            disabled={
              startingScan ||
              analyzing ||
              loadingOrganizations ||
              !organizationId
            }
          >
            {startingScan
              ? 'Scanning...'
              : analyzing
                ? 'Analyzing...'
                : 'Start Vulnerability Scan'}
          </button>

          <button
            type="button"
            className="btn-secondary"
            onClick={loadFindings}
            disabled={loadingFindings || !organizationId}
          >
            {loadingFindings ? 'Refreshing...' : 'Refresh Findings'}
          </button>
        </div>

        <p className="mt-3 text-xs text-slate-500">
          Only scan systems and private networks that you own or have explicit
          permission to assess. Your backend applies its own target validation
          and scan-size restrictions.
        </p>

        {error && (
          <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {message && (
          <div className="mt-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">
            {message}
          </div>
        )}

        {scanId && (
          <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 rounded-lg bg-slate-900/60 p-4 text-sm">
            <span>
              Scan ID: <b className="text-white">#{scanId}</b>
            </span>

            <span>
              Status:{' '}
              <b className={getStatusColor(scanStatus)}>
                {scanStatus || 'Unknown'}
              </b>
            </span>

            {analyzing && (
              <span className="text-amber-300">
                CVE analysis in progress...
              </span>
            )}
          </div>
        )}
      </Panel>

      {/* SUMMARY CARDS */}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
        {[
          { label: 'Total Findings', value: findings.length },
          { label: 'Open Findings', value: openCount },
          { label: 'Critical', value: severityCounts.Critical },
          { label: 'High', value: severityCounts.High },
          { label: 'OpenVAS Findings', value: openvasCount },
          { label: 'Known Exploited', value: kevCount },
        ].map((item) => (
          <div className="panel p-4" key={item.label}>
            <p className="text-xs muted">{item.label}</p>
            <p className="mt-2 text-2xl font-bold text-white">
              {item.value}
            </p>
          </div>
        ))}
      </div>

      {/* SOURCE SUMMARY */}

      <Panel
        title="Vulnerability data sources"
        subtitle="Vulnerability findings grouped by their recorded source."
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
            <p className="text-sm text-slate-400">Nmap / NVD</p>
            <p className="mt-2 text-2xl font-bold text-white">
              {nmapCount}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Potential vulnerability matches from network discovery and CVE enrichment.
            </p>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
            <p className="text-sm text-slate-400">OpenVAS</p>
            <p className="mt-2 text-2xl font-bold text-white">
              {openvasCount}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Findings imported from OpenVAS XML reports.
            </p>
          </div>
        </div>
      </Panel>

      {/* DISCOVERED SERVICES */}

      <Panel
        title="Discovered network services"
        subtitle={
          scanId
            ? `Results from scan #${scanId}`
            : 'Start a scan to discover hosts, ports and software versions.'
        }
      >
        {scanResults.length === 0 ? (
          <p className="py-6 text-center text-sm text-slate-500">
            No scan results to display yet.
          </p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>IP Address</th>
                  <th>Hostname</th>
                  <th>Port</th>
                  <th>Service</th>
                  <th>Product</th>
                  <th>Version</th>
                  <th>State</th>
                </tr>
              </thead>

              <tbody>
                {scanResults.map((result) => (
                  <tr key={result.result_id}>
                    <td className="font-medium text-white">
                      {result.ip_address || '—'}
                    </td>
                    <td>{result.hostname || '—'}</td>
                    <td>
                      {result.port
                        ? `${result.port}/${result.protocol || 'tcp'}`
                        : '—'}
                    </td>
                    <td>{result.service_name || '—'}</td>
                    <td>{result.product || '—'}</td>
                    <td>{result.version || '—'}</td>
                    <td>{result.state || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      {/* VULNERABILITY FINDINGS */}

      <Panel
        title="Detected vulnerability findings"
        subtitle="Nmap/NVD-enriched and OpenVAS-imported vulnerability findings."
      >
        <div className="mb-4 grid gap-3 md:grid-cols-[1fr_170px_170px]">
          <input
            className="field"
            placeholder="Search CVE, product, asset, IP or source..."
            value={q}
            onChange={(event) => setQ(event.target.value)}
          />

          <select
            className="field"
            value={severity}
            onChange={(event) => setSeverity(event.target.value)}
          >
            {['All', ...SEVERITIES].map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>

          <select
            className="field"
            value={sourceFilter}
            onChange={(event) => setSourceFilter(event.target.value)}
          >
            <option value="All">All sources</option>
            <option value="OpenVAS">OpenVAS</option>
            <option value="Nmap">Nmap</option>
            <option value="NVD">NVD</option>
          </select>
        </div>

        {loadingFindings ? (
          <p className="py-6 text-center text-sm text-slate-400">
            Loading vulnerability findings...
          </p>
        ) : filteredFindings.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">
            No vulnerability findings match your filters.
          </p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Finding / CVE</th>
                  <th>Source</th>
                  <th>Asset</th>
                  <th>Product / Port</th>
                  <th>Severity</th>
                  <th>CVSS</th>
                  <th>KEV</th>
                  <th>Status</th>
                  <th>Detected</th>
                </tr>
              </thead>

              <tbody>
                {filteredFindings.map((finding) => {
                  const evidence = finding.evidence || {}
                  const cveIds = getCveIds(evidence)

                  return (
                    <tr key={finding.finding_id}>
                      <td>
                        <b className="text-white">
                          {cveIds.length > 0
                            ? cveIds.join(', ')
                            : finding.title}
                        </b>

                        <p className="mt-1 text-xs text-slate-500">
                          Finding #{finding.finding_id}
                        </p>

                        {finding.description && (
                          <p className="mt-1 max-w-xs text-xs text-slate-500">
                            {finding.description}
                          </p>
                        )}
                      </td>

                      <td>
                        <Badge value={finding.source || 'Unknown'} />
                      </td>

                      <td>
                        {getAssetName(finding.asset_id, evidence)}
                        {(evidence.host_ip || evidence.ip_address) && (
                          <p className="text-xs text-slate-500">
                            {evidence.host_ip || evidence.ip_address}
                          </p>
                        )}
                      </td>

                      <td>
                        {evidence.product ||
                        evidence.nvt_name ||
                        finding.title?.replace(/^OpenVAS:\s*/i, '') ||
                        '—'}

                        {(evidence.port || evidence.detected_version) && (
                          <p className="text-xs text-slate-500">
                            {evidence.port
                              ? `Port ${evidence.port}`
                              : ''}
                            {evidence.port && evidence.detected_version
                              ? ' · '
                              : ''}
                            {evidence.detected_version
                              ? `Version ${evidence.detected_version}`
                              : ''}
                          </p>
                        )}
                      </td>

                      <td>
                        <Badge value={finding.severity || 'Unknown'} />
                      </td>

                      <td>{evidence.cvss_score ?? '—'}</td>

                      <td>
                        {evidence.known_exploited === true ? (
                          <span className="font-semibold text-red-400">
                            Yes
                          </span>
                        ) : (
                          <span className="text-slate-400">
                            Not confirmed
                          </span>
                        )}
                      </td>

                      <td>
                        <Badge value={finding.status || 'Unknown'} />
                      </td>

                      <td className="text-xs">
                        {formatDate(
                          finding.detected_at || finding.created_at
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        <p className="mt-3 text-xs text-slate-500">
          CVSS is shown only when supplied in finding evidence. Potential CVE
          matches require validation; a version match alone does not establish
          exploitability. KEV status is shown as not confirmed unless explicitly
          recorded by the backend.
        </p>
      </Panel>

      {/* ANALYSIS SUMMARY */}

      {analysisSummary && (
        <Panel
          title="Latest vulnerability analysis"
          subtitle={`Analysis summary for scan #${analysisSummary.scan_id}`}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg bg-slate-900/60 p-4">
              <p className="text-xs muted">Analyzed products</p>
              <p className="mt-2 text-2xl font-bold text-white">
                {analysisSummary.analyzed_products ?? 0}
              </p>
            </div>

            <div className="rounded-lg bg-slate-900/60 p-4">
              <p className="text-xs muted">
                Potential vulnerabilities saved
              </p>
              <p className="mt-2 text-2xl font-bold text-white">
                {analysisSummary.potential_vulnerabilities ?? 0}
              </p>
            </div>
          </div>

          <p className="mt-4 text-sm text-slate-400">
            {analysisSummary.message || 'Analysis completed.'}
          </p>
        </Panel>
      )}
    </div>
  )
}

export default Vulnerabilities
