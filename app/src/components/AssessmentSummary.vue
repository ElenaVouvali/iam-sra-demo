<script setup>
import { label } from '@/format'
defineProps({ summary: { type: Object, required: true } })
</script>
<template>
  <div class="sra-summary">
    <p class="t-small muted">{{ summary.note }}</p>
    <section v-for="section in summary.sections" :key="section.section">
      <h3 class="t-card">{{ label(section.section) }}</h3>
      <ul v-if="section.observations.length" class="bullets">
        <li v-for="(observation, index) in section.observations" :key="index">{{ observation.interpretation }}</li>
      </ul>
      <p v-else class="t-small muted">Not established in this interview. No limitation in capability is inferred.</p>
    </section>
  </div>
</template>
