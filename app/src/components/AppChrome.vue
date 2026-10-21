<script setup>
// Mode B header + EU footer around every page (iamcc-ui components.md "Chrome"; spec §4).
// "Back to hub" opens the hub tools list in a new tab: there is no /tools/iam-iq hub page yet.
import { toolsLink } from '@/router'
</script>

<template>
  <div class="iq">
    <a class="skip" href="#main">Skip to content</a>
    <header class="tool-header">
      <RouterLink :to="toolsLink" aria-label="IAM-SRA home" style="display: contents">
        <svg class="logo" viewBox="0 0 1781.34 333.04" role="img" aria-label="IAM-CC"><use href="/brand/icons.svg#iamcc-logo" /></svg>
      </RouterLink>
      <span class="divider" aria-hidden="true"></span>
      <span class="name">IAM-SRA</span>
      <a class="back" href="https://hub.iamcc.eu/tools" target="_blank" rel="noopener">Back to hub</a>
    </header>

    <main id="main" tabindex="-1"><slot /></main>

    <footer class="tool-footer">
      <div class="eu">
        <img src="/brand/eu-emblem.svg" alt="Funded by the European Union" />
        <p>Funded by the European Union under Grant Agreement No 101271620. Views and opinions expressed are those of the author(s) only and do not necessarily reflect those of the European Union or the granting authority. Neither the European Union nor the granting authority can be held responsible for them.</p>
      </div>
      <div class="credit">IAM-SRA · <RouterLink to="/privacy">Privacy</RouterLink></div>
    </footer>
  </div>
</template>

<style scoped>
.skip { position: absolute; left: -999rem; }
.skip:focus { left: var(--sp4); top: var(--sp2); z-index: 10; background: var(--c-surface); padding: var(--sp2) var(--sp3); border-radius: var(--r-sm); outline: var(--ring) solid var(--ring-coral); }
main:focus { outline: none; }
</style>
