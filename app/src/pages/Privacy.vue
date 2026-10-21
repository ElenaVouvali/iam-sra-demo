<script setup>
import Breadcrumb from '@/components/Breadcrumb.vue'
</script>
<template>
  <div class="wrap">
    <Breadcrumb :items="[{ to: '/', label: 'Tools' }, { label: 'Privacy' }]" />
    <article class="card sra-prose">
      <h1 class="t-title">Privacy and assessment limits</h1>
      <p>IAM-SRA2 is an internal demonstration using synthetic, general descriptions. Do not enter names, private addresses, contact details, credentials, bank details or identifiable medical information.</p>
      <p>Mandatory local screening runs before text is retained or sent to the model. Private details may produce a cleaned preview that needs your explicit confirmation. Sensitive content is withheld. Screening can miss private information and does not guarantee anonymity.</p>
      <p>Interview data stays in server memory. Reset, end, expiry and server restart drop application references; this does not securely erase process memory or downloaded files. The default idle expiry is one hour, with an absolute four-hour limit; operators can configure these limits.</p>
      <p>JSON and JSONL downloads are optional and screened again. Keep exported files private and delete them when no longer needed. Answers and results are never saved in browser storage or URLs.</p>
      <p>Confirmed testimony is self-report, without independent verification. Missing evidence does not establish low readiness. Citizen estimates are provisional; this interview does not establish technical, organisational or overall societal readiness.</p>
      <p>Before real citizen use, the responsible institution must establish its controller contact, purpose, lawful basis, retention policy and rights procedures. These decisions are not supplied by this demonstration.</p>
    </article>
  </div>
</template>
