import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

function manualChunks(id: string): string | undefined {
  if (!id.includes('node_modules')) return undefined

  const normalized = id.replace(/\\/g, '/')

  if (normalized.includes('/xlsx/')) {
    return 'vendor-xlsx'
  }

  return undefined
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
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks,
      },
    },
  },
})
