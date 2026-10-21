<script setup>
// /tools/:id/app: chrome + breadcrumb around the tool's own page (src/tools/<id>.vue). The router guard has
// already checked that the tool exists, has a working page, and that the file is there.
import { computed, defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
import { toolById } from '@/tools'
import { pageFor } from '@/toolPages'
import Breadcrumb from '@/components/Breadcrumb.vue'
import { toolsLink } from '@/router'

const route = useRoute()
// route.params is a new object on every navigation, query-only ones included. Key everything off the id string, so
// a filter change in the URL doesn't build a new async component and remount the whole tool page.
const id = computed(() => route.params.id)
const tool = computed(() => toolById(id.value))
const Page = computed(() => defineAsyncComponent(pageFor(id.value)))
</script>

<template>
  <div class="wrap">
    <Breadcrumb :items="[{ to: toolsLink, label: 'Tools' }, { to: `/tools/${tool.id}`, label: tool.name }, { label: 'Tool' }]" />
    <component :is="Page" :key="tool.id" :tool="tool" />
  </div>
</template>
