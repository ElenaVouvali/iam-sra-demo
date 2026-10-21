<script setup>
// Home / tool catalogue (spec §4): search + audience filter chips matching the hub catalogue.
import { computed } from 'vue'
import { TOOLS, AUDIENCES } from '@/tools'
import { useQueryState } from '@/composables/useQueryState'
import { label } from '@/format'

const q = useQueryState({ q: '', audience: '' })
const norm = (s) => s.toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu, '')

const activeAudience = computed(() => AUDIENCES.find((a) => a.id === q.audience))

const shown = computed(() => TOOLS.filter((t) => {
  const matchAudience = !activeAudience.value || t.tags.includes(activeAudience.value.tag)
  const matchSearch = !q.q || norm(`${t.name} ${t.suite} ${t.domains.map(label).join(' ')} ${t.lead} ${t.tags.join(' ')}`).includes(norm(q.q))
  return matchAudience && matchSearch
}))

const statusText = { live: '', 'no-data': 'Data coming soon', pending: 'Pending disclosure', 'data-lake': 'Data lake ready' }
</script>

<template>
  <div class="wrap">
    <div class="hero">
      <div>
        <h1 class="t-title">Societal readiness assessment</h1>
        <p class="t-body muted">Explore understanding, experience and participation through a confirmed evidence summary.</p>
      </div>
    </div>

    <div class="hub-bar">
      <label class="search" style="max-width: 20rem">
        <svg class="ico" aria-hidden="true"><use href="/brand/icons.svg#i-search" /></svg>
        <input v-model.trim="q.q" class="input" type="search" placeholder="Search tools" aria-label="Search tools" />
      </label>
      <div class="row" role="group" aria-label="Audience filter">
        <button class="chipf" type="button" :aria-pressed="!q.audience" @click="q.audience = ''">All</button>
        <button v-for="a in AUDIENCES" :key="a.id" class="chipf" type="button" :aria-pressed="q.audience === a.id" @click="q.audience = a.id">{{ a.label }}</button>
      </div>
    </div>

    <p class="t-small muted" aria-live="polite">{{ shown.length }} {{ shown.length === 1 ? 'tool' : 'tools' }}</p>

    <div v-if="shown.length" class="grid3" style="margin-top: var(--sp4)">
      <article v-for="t in shown" :key="t.id" class="card">
        <div class="img"><svg viewBox="0 0 333 333" aria-hidden="true"><use href="/brand/icons.svg#iamcc-mark" /></svg></div>
        <h2 class="t-card">{{ t.name }}</h2>
        <p class="t-small muted">{{ t.suite }} · {{ t.domains.map(label).join(', ') }}</p>
        <p class="t-small">{{ t.lead }}</p>
        <div class="tags"><span v-for="g in t.tags" :key="g" class="badge">{{ g }}</span>
          <span v-if="statusText[t.status]" class="badge type">{{ statusText[t.status] }}</span></div>
        <div class="actions"><RouterLink class="btn secondary sm" :to="`/tools/${t.id}`">Open tool</RouterLink></div>
      </article>
    </div>
    <div v-else class="empty" style="margin-top: var(--sp4)">
      <h2 class="t-card">No tools match</h2>
      <p class="t-small muted">Try another search, or clear the filter.</p>
      <button class="btn secondary" type="button" @click="Object.assign(q, { q: '', audience: '' })">Clear filter</button>
    </div>
  </div>
</template>
