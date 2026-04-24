import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom'
import DashboardLayout from './components/DashboardLayout'
import RequireAuth from './components/RequireAuth'
import Login from './pages/Login'
import PatientList from './pages/PatientList'
import ServiceRequests from './pages/ServiceRequests'
import Conditions from './pages/Conditions'
import MedicationRequests from './pages/MedicationRequests'
import ApiExplorer from './pages/ApiExplorer'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<RequireAuth />}>
          <Route path="/" element={<DashboardLayout />}>
            <Route index element={<Navigate to="/patients" replace />} />
            <Route path="patients" element={<PatientList />} />
            <Route path="service-requests" element={<ServiceRequests />} />
            <Route path="conditions" element={<Conditions />} />
            <Route path="medication-requests" element={<MedicationRequests />} />
            <Route path="api-explorer" element={<ApiExplorer />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

