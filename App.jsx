import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './layout/Layout'
import Overview from './pages/Overview'
import Assets from './pages/Assets'
import DeviceDetails from './pages/DeviceDetails'
import Vulnerabilities from './pages/Vulnerabilities'
import Risk from './pages/Risk'
import Monitoring from './pages/Monitoring'
import Optimization from './pages/Optimization'
import APIActivity from './pages/APIActivity'
import Reports from './pages/Reports'
import Settings from './pages/Settings'
import LivePrediction from './pages/Prediction'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Overview />} />
        <Route path="/assets" element={<Assets />} />
        <Route path="/assets/:assetId" element={<DeviceDetails />} />
        <Route path="/vulnerabilities" element={<Vulnerabilities />} />
        <Route path="/risk" element={<Risk />} />
        <Route path="/monitoring" element={<Monitoring />} />
        <Route path="/prediction" element={<LivePrediction />} />
        <Route path="/optimization" element={<Optimization />} />
        <Route path="/api-activity" element={<APIActivity />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}