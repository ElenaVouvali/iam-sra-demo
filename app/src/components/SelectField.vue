<script setup>
// Labelled select (playground .field/.input). Options: strings or {value, label}.
// One option → still shown, pre-selected (spec §7). No options → disabled with the `waiting` hint.
import { computed, useId, watch } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  options: { type: Array, default: () => [] },
  help: { type: String, default: '' },
  waiting: { type: String, default: '' },           // e.g. "Choose a city first"
  placeholder: { type: String, default: '' },        // e.g. "Choose a metric"
  disabled: { type: Boolean, default: false },
  optional: { type: Boolean, default: false },
})
const model = defineModel({ type: String, default: '' })
const id = useId()

const opts = computed(() => props.options.map((o) => (typeof o === 'object' ? o : { value: String(o), label: String(o) })))
const isDisabled = computed(() => props.disabled || opts.value.length === 0)

// Auto-pick a single option; drop a value that no longer exists after an upstream change. An empty list means the
// options are still loading: keep the value, or a selection restored from the URL is wiped before it can match.
watch(opts, (list) => {
  if (list.length === 1 && model.value !== list[0].value) model.value = list[0].value
  else if (list.length && model.value && !list.some((o) => o.value === model.value)) model.value = ''
}, { immediate: true })
</script>

<template>
  <div class="field">
    <label :for="id">{{ label }} <span v-if="optional" class="opt">(optional)</span></label>
    <select :id="id" v-model="model" class="input" :disabled="isDisabled" :aria-describedby="help ? `${id}-help` : undefined">
      <option v-if="isDisabled && waiting" value="">{{ waiting }}</option>
      <option v-else-if="opts.length > 1" value="" disabled>{{ placeholder || `Choose ${label.toLowerCase()}` }}</option>
      <option v-for="o in opts" :key="o.value" :value="o.value">{{ o.label }}</option>
    </select>
    <span v-if="help" :id="`${id}-help`" class="help">{{ help }}</span>
  </div>
</template>
