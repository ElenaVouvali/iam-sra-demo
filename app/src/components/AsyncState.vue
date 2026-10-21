<script setup>
// Renders the right state for one async area (spec §7): loading skeleton · empty state · error alert with retry · content.
// <AsyncState :state="r.state.value" :error="r.error.value" empty-title="No results yet" @retry="r.run()">…ready…</AsyncState>
defineProps({
  state: { type: String, required: true },          // idle | loading | ready | empty | error
  error: { type: Object, default: null },
  emptyTitle: { type: String, default: 'No results yet' },
  emptyText: { type: String, default: 'Choose the inputs above to see results.' },
  idleTitle: { type: String, default: 'No results yet' },
  idleText: { type: String, default: 'Choose the inputs above, then run the tool.' },
  lines: { type: Number, default: 3 },
})
defineEmits(['retry'])
</script>

<template>
  <div aria-live="polite">
    <div v-if="state === 'loading'" class="skel" aria-busy="true" aria-label="Loading">
      <i v-for="n in lines" :key="n" :style="{ width: `${[55, 85, 70, 60][(n - 1) % 4]}%` }"></i>
    </div>

    <div v-else-if="state === 'error'" class="alert danger" role="alert">
      <svg class="ico" aria-hidden="true"><use href="/brand/icons.svg#i-err" /></svg>
      <div>
        <b>Couldn't load this</b>
        <p>{{ error?.userMessage || error?.message || 'Something went wrong.' }}</p>
        <button class="btn secondary sm" type="button" style="margin-top: var(--sp2)" @click="$emit('retry')">Try again</button>
      </div>
    </div>

    <div v-else-if="state === 'empty' || state === 'idle'" class="empty">
      <svg class="m" viewBox="0 0 333 333" aria-hidden="true"><use href="/brand/icons.svg#iamcc-mark" /></svg>
      <h3 class="t-card">{{ state === 'empty' ? emptyTitle : idleTitle }}</h3>
      <p class="t-small muted">{{ state === 'empty' ? emptyText : idleText }}</p>
      <slot name="empty-action" />
    </div>

    <slot v-else />
  </div>
</template>
