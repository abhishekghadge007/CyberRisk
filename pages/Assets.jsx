
import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { Activity, Boxes, ShieldAlert, Search, Download } from 'lucide-react'
import api from '../../services_api'
import { Badge, Panel, Metric, PageTitle } from '../components/UI'
import { download } from '../utils/helpers'

function Assets() {
  const [rows, setRows] = useState([])
  const [query, setQuery] = useState('')
  const [organization, setOrganization] = useState('All')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadAssets = async () => {
    setLoading(true)
    setError('')

    try {
      const response = await api.get('/assets/global', {
        params: {
          limit: 500,
          offset: 0,
        },
      })

      const data = response.data

      const assets = Array.isArray(data)
        ? data
        : data?.assets || data?.items || data?.results || []

      setRows(Array.isArray(assets) ? assets : [])
    } catch (err) {
      console.error('Asset inventory loading failed:', err)

      setError(
        err.response?.data?.detail ||
        'Unable to load devices. Check whether the backend is running and the global assets endpoint is available.'
      )

      setRows([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAssets()
  }, [])

  const organizations = [
    ...new Set(
      rows
        .map((asset) => asset.organization_id)
        .filter((id) => id !== null && id !== undefined)
    ),
  ].sort((a, b) => Number(a) - Number(b))

  const filtered = rows.filter((asset) => {
    const searchable = [
      asset.asset_id,
      asset.asset_name,
      asset.hostname,
      asset.ip_address,
      asset.asset_type,
      asset.operating_system,
      asset.owner,
      asset.organization_id,
    ]
      .filter((value) => value !== null && value !== undefined)
      .join(' ')
      .toLowerCase()

    const matchesSearch = searchable.includes(query.trim().toLowerCase())

    const matchesOrganization =
      organization === 'All' ||
      String(asset.organization_id) === organization

    return matchesSearch && matchesOrganization
  })

  const criticalCount = rows.filter(
    (asset) => String(asset.criticality || '').toLowerCase() === 'critical'
  ).length

  const uniqueOrganizations = organizations.length

  const exportCSV = () => {
    if (!filtered.length) return

    const data = [
      [
        'Asset ID',
        'Asset Name',
        'Hostname',
        'Organization ID',
        'Type',
        'Operating System',
        'IP Address',
        'Criticality',
        'Exposure',
        'Owner',
      ],
      ...filtered.map((asset) => [
        asset.asset_id ?? '',
        asset.asset_name ?? '',
        asset.hostname ?? '',
        asset.organization_id ?? '',
        asset.asset_type ?? '',
        asset.operating_system ?? '',
        asset.ip_address ?? '',
        asset.criticality ?? '',
        asset.exposure_level ?? '',
        asset.owner ?? '',
      ]),
    ]

    download('cyberrisk-global-assets.csv', data)
  }

  return (
    <div className="space-y-6">
      <PageTitle
        title="Global Device Inventory"
        desc="View and inspect devices discovered across your registered organizations."
        extra={
          <button
            onClick={loadAssets}
            disabled={loading}
            className="btn-primary flex items-center gap-2 text-xs disabled:opacity-50"
          >
            <Activity size={15} />
            {loading ? 'Refreshing...' : 'Refresh devices'}
          </button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <Metric
          label="Total devices"
          value={loading ? '—' : rows.length}
          detail="Devices registered in the database"
          Icon={Boxes}
        />

        <Metric
          label="Critical devices"
          value={loading ? '—' : criticalCount}
          detail="Devices marked as critical"
          Icon={ShieldAlert}
          tone="rose"
        />

        <Metric
          label="Organizations"
          value={loading ? '—' : uniqueOrganizations}
          detail="Organizations represented in inventory"
          Icon={Activity}
          tone="blue"
        />
      </div>

      <Panel
        title="Registered devices"
        subtitle="Live inventory retrieved from the CyberRisk backend"
        action={
          <button
            onClick={exportCSV}
            disabled={filtered.length === 0 || loading}
            className="btn-secondary flex items-center gap-2 text-xs disabled:opacity-50"
          >
            <Download size={14} />
            Export CSV
          </button>
        }
      >
        <div className="mb-5 grid gap-3 md:grid-cols-[1fr_220px]">
          <div className="relative">
            <Search
              size={16}
              className="absolute left-3 top-3 text-slate-500"
            />

            <input
              className="field pl-9"
              placeholder="Search name, hostname, IP, operating system..."
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>

          <select
            className="field"
            value={organization}
            onChange={(event) => setOrganization(event.target.value)}
          >
            <option value="All">All organizations</option>

            {organizations.map((id) => (
              <option key={id} value={String(id)}>
                Organization {id}
              </option>
            ))}
          </select>
        </div>

        {error && (
          <div className="mb-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
            {error}
          </div>
        )}

        {loading ? (
          <div className="py-12 text-center text-sm muted">
            Loading devices from the database...
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Device</th>
                  <th>IP Address</th>
                  <th>Organization</th>
                  <th>Type</th>
                  <th>Operating System</th>
                  <th>Criticality</th>
                  <th>Exposure</th>
                  <th>Details</th>
                </tr>
              </thead>

              <tbody>
                {filtered.map((asset) => (
                  <tr key={asset.asset_id}>
                    <td>
                      <b className="text-sm text-white">
                        {asset.asset_name ||
                          asset.hostname ||
                          `Asset ${asset.asset_id}`}
                      </b>

                      <p className="text-xs text-slate-500">
                        ID: {asset.asset_id}
                        {asset.hostname ? ` · ${asset.hostname}` : ''}
                      </p>
                    </td>

                    <td className="font-mono text-xs">
                      {asset.ip_address || '—'}
                    </td>

                    <td>
                      <span className="rounded-lg bg-slate-800 px-2 py-1 text-xs">
                        Org {asset.organization_id ?? '—'}
                      </span>
                    </td>

                    <td>{asset.asset_type || '—'}</td>

                    <td>{asset.operating_system || '—'}</td>

                    <td>
                      {asset.criticality ? (
                        <Badge value={asset.criticality} />
                      ) : (
                        '—'
                      )}
                    </td>

                    <td>{asset.exposure_level || '—'}</td>

                    <td>
                      <NavLink
                        to={`/assets/${asset.asset_id}`}
                        className="text-xs font-semibold text-teal-300 hover:text-teal-200"
                      >
                        View device →
                      </NavLink>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {!filtered.length && (
              <p className="py-8 text-center muted">
                {error
                  ? 'Device inventory could not be loaded.'
                  : 'No matching devices found.'}
              </p>
            )}
          </div>
        )}

        <p className="mt-4 text-xs muted">
          Showing {filtered.length} of {rows.length} devices. Select a device
          to inspect its details and scan history.
        </p>
      </Panel>
    </div>
  )
}

export default Assets
