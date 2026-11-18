const initialAssets = [
  { id: 'AST-001', name: 'Production Web Server', type: 'Server', owner: 'Infrastructure', criticality: 'Critical', exposure: 'Internet-facing', score: 82 },
  { id: 'AST-002', name: 'Customer Database', type: 'Database', owner: 'Data Team', criticality: 'Critical', exposure: 'Internal', score: 71 },
  { id: 'AST-003', name: 'Employee Workstations', type: 'Endpoint', owner: 'IT Operations', criticality: 'High', exposure: 'Internal', score: 48 },
  { id: 'AST-004', name: 'Corporate VPN Gateway', type: 'Network', owner: 'Network Team', criticality: 'High', exposure: 'Internet-facing', score: 64 },
  { id: 'AST-005', name: 'Development Environment', type: 'Cloud', owner: 'Engineering', criticality: 'Medium', exposure: 'Restricted', score: 29 },
]

const initialVulns = [
  { id: 'VUL-1042', title: 'Outdated OpenSSL library', asset: 'Production Web Server', severity: 'Critical', cvss: 9.8, status: 'Open' },
  { id: 'VUL-1038', title: 'Remote code execution exposure', asset: 'Corporate VPN Gateway', severity: 'High', cvss: 8.6, status: 'In Progress' },
  { id: 'VUL-1029', title: 'Weak database access policy', asset: 'Customer Database', severity: 'High', cvss: 7.8, status: 'Open' },
  { id: 'VUL-1017', title: 'Missing endpoint security update', asset: 'Employee Workstations', severity: 'Medium', cvss: 5.4, status: 'Open' },
  { id: 'VUL-1009', title: 'Unnecessary service enabled', asset: 'Development Environment', severity: 'Low', cvss: 3.1, status: 'Resolved' },
]

const trend = [
  { month: 'Jun', score: 61 },
  { month: 'Jul', score: 57 },
  { month: 'Aug', score: 63 },
  { month: 'Sep', score: 52 },
  { month: 'Oct', score: 48 },
  { month: 'Nov', score: 42 },
]

const events = [
  { time: '10:42:18', type: 'Authentication', message: 'Multiple failed login attempts detected', source: '10.0.4.21', level: 'High' },
  { time: '10:35:02', type: 'Endpoint', message: 'Security agent heartbeat received', source: 'WS-FIN-014', level: 'Info' },
  { time: '10:21:46', type: 'Network', message: 'Unusual outbound traffic observed', source: '192.168.1.44', level: 'Medium' },
  { time: '09:58:11', type: 'Vulnerability', message: 'Critical vulnerability remains unpatched', source: 'WEB-PROD-01', level: 'High' },
]

const initiatives = [
  { id: 1, name: 'Endpoint Detection & Response', category: 'Detection', cost: 18000, reduction: 14 },
  { id: 2, name: 'Patch Management Program', category: 'Prevention', cost: 12000, reduction: 12 },
  { id: 3, name: 'Employee Security Training', category: 'Awareness', cost: 6000, reduction: 7 },
  { id: 4, name: 'Web Application Firewall', category: 'Protection', cost: 15000, reduction: 11 },
]

export { initialAssets, initialVulns, trend, events, initiatives }