<script setup>
// "Tools / <name> / Tool" (iamcc-ui layout.css .crumbs). The last item is the current page.
defineProps({ items: { type: Array, required: true } })   // [{ to?, label }]
</script>

<template>
  <nav class="crumbs" aria-label="Breadcrumb">
    <template v-for="(it, i) in items" :key="i">
      <span v-if="i" class="sep" aria-hidden="true">/</span>
      <RouterLink v-if="it.to && i < items.length - 1" :to="it.to">{{ it.label }}</RouterLink>
      <span v-else aria-current="page">{{ it.label }}</span>
    </template>
  </nav>
</template>
