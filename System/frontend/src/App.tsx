import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './layout/Layout'
import { AuthProvider, useAuth } from './auth'
import './App.css'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const DataImport = lazy(() => import('./pages/DataImportV2'))
const ABCAnalysis = lazy(() => import('./pages/ABCAnalysis'))
const PriceCompetitiveness = lazy(() => import('./pages/PriceCompetitiveness'))
const FunnelAnalysis = lazy(() => import('./pages/FunnelAnalysis'))
const InventoryAlert = lazy(() => import('./pages/InventoryAlert'))
const AdsManagement = lazy(() => import('./pages/AdsManagement'))
const StrategyList = lazy(() => import('./pages/StrategyList'))
const DecisionEngine = lazy(() => import('./pages/DecisionEngine'))
const ProfitCalculator = lazy(() => import('./pages/ProfitCalculator'))
const LoginPage = lazy(() => import('./pages/Login'))
const SystemSettings = lazy(() => import('./pages/SystemSettings'))

function PageLoading() {
  return <div style={{ padding: 24 }}>页面加载中...</div>
}

function ProtectedLayout() {
  const { user, loading } = useAuth()
  if (loading) return <div style={{ padding: 24 }}>加载中...</div>
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
          <Route
            path="/login"
            element={
              <Suspense fallback={<PageLoading />}>
                <LoginPage />
              </Suspense>
            }
          />
          <Route path="/" element={<ProtectedLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route
              path="dashboard"
              element={
                <Suspense fallback={<PageLoading />}>
                  <Dashboard />
                </Suspense>
              }
            />
            <Route
              path="import"
              element={
                <Suspense fallback={<PageLoading />}>
                  <DataImport />
                </Suspense>
              }
            />
            <Route
              path="settings"
              element={
                <Suspense fallback={<PageLoading />}>
                  <SystemSettings />
                </Suspense>
              }
            />
            <Route
              path="abc"
              element={
                <Suspense fallback={<PageLoading />}>
                  <ABCAnalysis />
                </Suspense>
              }
            />
            <Route
              path="price"
              element={
                <Suspense fallback={<PageLoading />}>
                  <PriceCompetitiveness />
                </Suspense>
              }
            />
            <Route
              path="funnel"
              element={
                <Suspense fallback={<PageLoading />}>
                  <FunnelAnalysis />
                </Suspense>
              }
            />
            <Route
              path="inventory"
              element={
                <Suspense fallback={<PageLoading />}>
                  <InventoryAlert />
                </Suspense>
              }
            />
            <Route
              path="ads"
              element={
                <Suspense fallback={<PageLoading />}>
                  <AdsManagement />
                </Suspense>
              }
            />
            <Route
              path="strategy"
              element={
                <Suspense fallback={<PageLoading />}>
                  <StrategyList />
                </Suspense>
              }
            />
            <Route
              path="decision"
              element={
                <Suspense fallback={<PageLoading />}>
                  <DecisionEngine />
                </Suspense>
              }
            />
            <Route
              path="profit"
              element={
                <Suspense fallback={<PageLoading />}>
                  <ProfitCalculator />
                </Suspense>
              }
            />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
