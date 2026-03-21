import { defineConfig, splitVendorChunkPlugin } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

function manualChunks(id: string): string | undefined {
  if (!id.includes('node_modules')) return undefined

  if (id.includes('/react/') || id.includes('react-dom') || id.includes('react-router')) {
    return 'vendor-react'
  }
  if (
    id.includes('/antd/') ||
    id.includes('@ant-design') ||
    id.includes('/rc-')
  ) {
    return 'vendor-antd'
  }
  if (
    id.includes('/@mui/') ||
    id.includes('/@emotion/')
  ) {
    return 'vendor-mui'
  }
  if (
    id.includes('/echarts') ||
    id.includes('echarts-for-react') ||
    id.includes('/recharts/')
  ) {
    return 'vendor-charts'
  }
  if (id.includes('/xlsx/')) {
    return 'vendor-xlsx'
  }
  if (
    id.includes('/axios/') ||
    id.includes('/dayjs/') ||
    id.includes('/lodash/') ||
    id.includes('/zustand/') ||
    id.includes('@tanstack/react-query')
  ) {
    return 'vendor-utils'
  }
  return 'vendor-misc'
}

export default defineConfig({
  plugins: [react(), splitVendorChunkPlugin()],
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
