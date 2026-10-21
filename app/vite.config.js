// Adapted from IAM-IQ. Both modes read the same server-side destination allowlist.
import { readFileSync } from 'node:fs'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
const table = JSON.parse(readFileSync(new URL('./proxy-routes.json', import.meta.url), 'utf8'))
const host = process.env.K8S_HOST || table.defaultHost
const inCluster = process.env.IAMIQ_IN_CLUSTER === '1'
function target(route) {
  const value = process.env[route.targetEnv] || (inCluster ? `http://${route.service}` : `http://${host}:${route.nodePort}`)
  const url = new URL(value)
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.pathname !== '/' || url.search || url.hash) throw new Error('Configure an HTTP backend origin without credentials or path.')
  return url.origin
}
function sendJson(res, status, body) {
  if (res.headersSent) return res.end()
  res.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' })
  res.end(JSON.stringify(body))
}
const proxy = Object.fromEntries(Object.entries(table.routes).map(([tool, route]) => [
  `^/api/${tool}(?:/|$)`, {
    target: target(route), changeOrigin: true, timeout: table.timeoutMs, proxyTimeout: table.timeoutMs,
    rewrite: (path) => path.slice(`/api/${tool}`.length) || '/',
    configure: (p) => p.on('error', (_err, _req, res) => sendJson(res, 502, { error: 'Assessment service is unavailable. Try again shortly.' })),
  },
]))
const unknownApi = {
  name: 'iamsra-unknown-api',
  configurePreviewServer(server) {
    server.middlewares.use((req, res, next) => {
      if (!/^\/api(?:\/|$)/.test(req.url)) return next()
      const tool = req.url.match(/^\/api\/([^/?#]+)/)?.[1]
      if (!Object.hasOwn(table.routes, tool)) return sendJson(res, 404, { error: 'Unknown tool.' })
      next()
    })
  },
  configureServer(server) {
    server.middlewares.use((req, res, next) => {
      if (req.url.startsWith('/assets/')) return sendJson(res, 404, { error: 'Not found.' })
      if (!/^\/api(?:\/|$)/.test(req.url)) return next()
      const tool = req.url.match(/^\/api\/([^/?#]+)/)?.[1]
      if (!Object.hasOwn(table.routes, tool)) return sendJson(res, 404, { error: 'Unknown tool.' })
      next()
    })
  },
}
const serving = { host: process.env.HOST || '127.0.0.1', port: Number(process.env.IAM_SRA_UI_PORT || process.env.PORT || 5001), strictPort: true, proxy }
export default defineConfig({
  plugins: [vue(), unknownApi],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  optimizeDeps: { include: ['vue', 'vue-router'] },
  server: serving, preview: serving,
  build: { outDir: 'dist' },
})
