import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

function manualChunks(id: string): string | undefined {
  if (!id.includes('node_modules')) return undefined

  const normalized = id.replace(/\\/g, '/')

  if (
    normalized.includes('/react/') ||
    normalized.includes('/react-dom/') ||
    normalized.includes('/react-router/') ||
    normalized.includes('/react-router-dom/') ||
    normalized.includes('/scheduler/')
  ) {
    return 'vendor-react'
  }

  if (
    normalized.includes('/antd/') ||
    normalized.includes('/@ant-design/') ||
    normalized.includes('/rc-') ||
    normalized.includes('/@ctrl/tinycolor/') ||
    normalized.includes('/resize-observer-polyfill/')
  ) {
    return 'vendor-antd'
  }

  if (
    normalized.includes('/@mui/') ||
    normalized.includes('/@emotion/')
  ) {
    return 'vendor-mui'
  }

  if (
    normalized.includes('/echarts/') ||
    normalized.includes('/echarts-for-react/') ||
    normalized.includes('/recharts/') ||
    normalized.includes('/d3-')
  ) {
    return 'vendor-charts'
  }

  if (normalized.includes('/xlsx/')) {
    return 'vendor-xlsx'
  }

  if (
    normalized.includes('/axios/') ||
    normalized.includes('/dayjs/') ||
    normalized.includes('/lodash/') ||
    normalized.includes('/zustand/') ||
    normalized.includes('/@tanstack/react-query/') ||
    normalized.includes('/immer/')
  ) {
    return 'vendor-utils'
  }

  return 'vendor-misc'
}

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      output: {
        manualChunks,
      },
    },
  },
})
