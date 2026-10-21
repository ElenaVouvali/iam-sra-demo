<script setup>
// Tool detail /tools/:id (spec §4; hub /tools/iam-compass template; iamcc-ui page-templates.md).
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { TOOLS, toolById } from '@/tools'
import Breadcrumb from '@/components/Breadcrumb.vue'
import { toolsLink } from '@/router'

const route = useRoute()
const tool = computed(() => toolById(route.params.id))
const STATUS = { live: 'Internal demonstration', 'no-data': 'Data coming soon', pending: 'Pending disclosure', 'data-lake': 'Data lake ready' }
const related = computed(() => TOOLS.filter((t) => t.id !== tool.value.id &&
  (t.suite === tool.value.suite || t.domains.some((d) => tool.value.domains.includes(d)))).slice(0, 4))
</script>

<template>
  <div class="wrap">
    <Breadcrumb :items="[{ to: toolsLink, label: 'Tools' }, { label: tool.name }]" />
    <div class="detail-head">
      <h1 class="t-title">{{ tool.name }}</h1>
      <p class="lead">{{ tool.lead }}</p>
      <div class="tags"><span v-for="g in tool.tags" :key="g" class="badge">{{ g }}</span></div>
    </div>

    <div class="detail">
      <div>
        <!-- 2:1 screenshot slot: resolve through src/images.js (spec D8), placeholder when missing -->
        <div class="shot"><svg viewBox="0 0 333 333" width="64" height="64" aria-hidden="true" style="opacity: .25"><use href="/brand/icons.svg#iamcc-mark" /></svg></div>
        <h2 class="t-section" style="margin-top: var(--sp8)">What it does</h2>
        <ul class="bullets t-body" style="margin-top: var(--sp3)"><li v-for="d in tool.does" :key="d">{{ d }}</li></ul>
        <h2 class="t-section" style="margin-top: var(--sp8)">Who it's for</h2>
        <p class="t-body muted" style="margin-top: var(--sp3)">{{ tool.audience }}</p>
      </div>

      <aside class="sidebar">
        <section class="card" aria-labelledby="access">
          <h2 id="access" class="t-card">Access</h2>
          <RouterLink v-if="tool.hasApp && tool.status !== 'pending'" class="btn primary block" :to="`/tools/${tool.id}/app`">Open tool<svg class="ico ico-btn" aria-hidden="true"><use href="/brand/icons.svg#i-ext" /></svg></RouterLink>
          <p v-else class="t-small muted">{{ STATUS[tool.status] }}. The tool page opens when the partner releases it.</p>
          <dl class="facts">
            <dt>Suite</dt><dd>{{ tool.suite }}</dd>
            <dt>Application</dt><dd>{{ tool.partner }}</dd>
            <dt>Status</dt><dd>{{ STATUS[tool.status] }}</dd>
            <dt>Sources and retention</dt><dd>{{ tool.data }}</dd>
          </dl>
        </section>
        <section v-if="related.length" class="card" aria-labelledby="rel">
          <h2 id="rel" class="t-card">Related tools</h2>
          <div v-for="r in related" :key="r.id" class="lrow">
            <div class="tx"><b><RouterLink :to="`/tools/${r.id}`">{{ r.name }}</RouterLink></b><span class="t-small muted">{{ r.suite }}</span></div>
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>
