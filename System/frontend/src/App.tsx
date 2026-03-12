import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './layout/Layout'
import Dashboard from './pages/Dashboard'
import DataImport from './pages/DataImportV2'
import ABCAnalysis from './pages/ABCAnalysis'
import PriceCompetitiveness from './pages/PriceCompetitiveness'
import FunnelAnalysis from './pages/FunnelAnalysis'
import InventoryAlert from './pages/InventoryAlert'
import AdsManagement from './pages/AdsManagement'
import StrategyList from './pages/StrategyList'
import DecisionEngine from './pages/DecisionEngine'
import ProfitCalculator from './pages/ProfitCalculator'
import LoginPage from './pages/Login'
import SystemSettings from './pages/SystemSettings'
import { AuthProvider, useAuth } from './auth'
import './App.css'

function ProtectedLayout() {
  const { user, loading } = useAuth()
  if (loading) return <div style={{ padding: 24 }}>Loading...</div>
  if (!user) return <Navigate to="/login" replace />
  return <Layout />
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<ProtectedLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="import" element={<DataImport />} />
            <Route path="settings" element={<SystemSettings />} />
            <Route path="abc" element={<ABCAnalysis />} />
            <Route path="price" element={<PriceCompetitiveness />} />
            <Route path="funnel" element={<FunnelAnalysis />} />
            <Route path="inventory" element={<InventoryAlert />} />
            <Route path="ads" element={<AdsManagement />} />
            <Route path="strategy" element={<StrategyList />} />
            <Route path="decision" element={<DecisionEngine />} />
            <Route path="profit" element={<ProfitCalculator />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
