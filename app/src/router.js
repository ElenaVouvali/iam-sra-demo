import { ref } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { toolById } from '@/tools'
import { pageFor } from '@/toolPages'

const routes = [
  { path: '/privacy', component: () => import('@/pages/Privacy.vue'), meta: { title: 'Privacy' } },
  { path: '/', name: 'home', component: () => import('@/pages/Home.vue'), meta: { title: null } },
  { path: '/tools/:id', name: 'tool', component: () => import('@/pages/ToolDetail.vue'),
    beforeEnter: (to) => (toolById(to.params.id) ? true : { name: 'not-found', params: { path: to.path.slice(1).split('/') } }) },
  { path: '/tools/:id/app', name: 'tool-app', component: () => import('@/pages/ToolApp.vue'),
    // Unknown id, detail-only tool, or no page file yet → Not found (never a blank page).
    beforeEnter: (to) => {
      const t = toolById(to.params.id)
      return t && t.hasApp && pageFor(t.id) ? true : { name: 'not-found', params: { path: to.path.slice(1).split('/') } }
    } },
  { path: '/:path(.*)*', name: 'not-found', component: () => import('@/pages/NotFound.vue'), meta: { title: 'Not found' } },
]

// The tools catalogue as last left: its search/filter query and scroll position. The "Tools" breadcrumb and the logo
// link to it, so they return there like Back does. Kept in sessionStorage so a reload of a tool page keeps it too.
const KEY = 'iamsra.catalogue'
let saved = null
try { saved = JSON.parse(sessionStorage.getItem(KEY)) } catch { /* no storage: start fresh */ }
let catalogueY = saved?.y ?? 0
export const toolsLink = ref({ path: '/', query: saved?.query ?? {} })

export const router = createRouter({
  history: createWebHistory(),
  routes,
  // Back restores the scroll position; a link to the catalogue goes back to where it was left; other pages start at the top.
  scrollBehavior: (to, from, back) => back
    || (to.name === 'home' && from.name !== 'home' ? { top: catalogueY } : to.path !== from.path ? { top: 0 } : false),
})

router.beforeEach((to, from) => {
  if (from.name !== 'home' || to.name === 'home') return
  catalogueY = window.scrollY
  toolsLink.value = { path: '/', query: { ...from.query } }
  try { sessionStorage.setItem(KEY, JSON.stringify({ query: from.query, y: catalogueY })) } catch { /* not kept */ }
})

// Titles (spec D3): "<Page> · IAM-SRA | IAM-CC"; home is "IAM-SRA | IAM-CC".
router.afterEach((to) => {
  const tool = to.params.id ? toolById(to.params.id) : null
  const page = tool ? (to.name === 'tool-app' ? `${tool.name} tool` : tool.name) : to.meta.title
  document.title = page ? `${page} · IAM-SRA | IAM-CC` : 'IAM-SRA | IAM-CC'
})
