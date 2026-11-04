<script setup>
import { computed, onMounted, ref } from 'vue'
import { useAssessment } from '@/composables/useAssessment'
const flow = useAssessment({ mode: 'chat', depth: 'short', assisted: new URLSearchParams(location.search).get('assisted') === '1' })
const { session, capabilities, boot, operation, working, ended: sessionEnded } = flow
const chat = computed(() => session.value?.chat)
const draft = ref(''), notice = ref(''), endDialog = ref(null), ending = ref(false)
const ended = computed(() => chat.value?.stage === 'ended')
async function send() {
 if (!draft.value.trim() || working.value) return
 const submitted = draft.value
 const ok = await flow.act('chat_message', { text: submitted })
 if (ok && !session.value?.preview && draft.value === submitted) draft.value = ''
 if (!session.value) return
 notice.value = ok ? 'Response ready below.' : 'Your draft is retained. Please check the error.'
}
async function confirmCleaned() {
 const ok = await flow.act('confirm_cleaned', { preview_id: session.value.preview.id })
 if (ok && !session.value?.preview) draft.value = ''
}
async function start() {
 await flow.initialize()
 if (boot.state.value === 'ready' && !session.value) await flow.act('new')
}
async function endSession() {
 endDialog.value.close()
 ending.value = true
 const ok = await flow.act('end')
 ending.value = false
 if (ok) {
  draft.value = ''
  notice.value = 'This temporary session has ended. Downloaded copies remain with you.'
 }
}
async function restart() {
 if (working.value) return
 const ok = session.value ? await flow.reset() : await flow.act('new')
 if (ok) draft.value = ''
}
onMounted(start)
</script>

<template>
 <article class="chat wrap" data-testid="chat-conversation">
  <header><p class="t-small muted">IAM-CC · Research prototype</p><h1>Let's talk about drones</h1><p>A conversation about healthcare deliveries, your experience and what matters to you.</p></header>
  <details class="sra-disclosure"><summary>Privacy, help and conversation options</summary>
   <p>Please avoid names, contact details and sensitive information. This AI-assisted research prototype screens messages before processing. Your words are self-reports; generated interpretations and results are provisional.</p>
   <p>Progress and wording preferences are held temporarily in memory. Download a copy to keep them. Saving, cross-day resume and contact follow-up are unavailable. Nothing here enables training.</p>
   <p>You can type “I don't know”, “skip this question”, “stop”, “simplify”, “go back”, “keep it short”, “more detail”, or ask to change topic. You do not need to remember commands; ordinary language is welcome. To see two alternative wordings, ask “show two ways of asking that”. English is the tested language.</p>
   <p v-if="chat?.assisted">Facilitator mode: type the respondent's own words. Do not supply answers for them. This assistance is recorded in the report.</p>
   <RouterLink to="/privacy">Full privacy and retention details</RouterLink>
   <div class="row"><button class="btn secondary sm" :disabled="working" @click="restart">New conversation</button><button v-if="session" class="btn secondary sm" :disabled="ending" @click="endDialog.showModal()">End and clear session</button></div>
  </details>
  <p v-if="capabilities?.synthetic_fixture || chat?.synthetic" class="alert warning">SYNTHETIC TEST DATA · {{ capabilities?.synthetic_fixture ? 'Fixture conversation; no live assessment.' : 'Authored rehearsal; semantic review required.' }}</p>
  <p v-if="sessionEnded" role="status">Your temporary session has ended. Downloaded copies remain with you.</p>
  <p v-if="boot.state.value === 'loading'" role="status">Opening the conversation…</p>
  <div v-if="boot.error.value" role="alert"><p>{{ boot.error.value.userMessage }}</p><button class="btn secondary" @click="start">Retry opening</button></div>
  <div v-if="operation.error.value" role="alert"><p>{{ operation.error.value.userMessage }}</p><button class="btn secondary" :disabled="working" @click="flow.act('refresh')">Refresh conversation</button></div>
  <ol v-if="chat" class="messages" aria-label="Conversation">
   <li v-for="message in chat.messages" :key="message.id" :class="message.role">
    <b>{{ message.role === 'assistant' ? 'AI assistant' : 'You' }}</b><p>{{ message.text }}</p>
   </li>
  </ol>
  <section v-if="chat?.pending_comparison" aria-label="Optional wording preference">
   <p v-for="(variant, index) in chat.pending_comparison.variants" :key="variant.response_id"><b>{{ index + 1 }}.</b> {{ variant.text }}</p>
  </section>
  <section v-if="chat?.summary?.length" aria-label="Your evidence summary"><h2>A few points from your words</h2><p>These are selected original passages. Your full conversation remains above and in the download. Please correct anything missing or misunderstood.</p><blockquote v-for="item in chat.summary" :key="item.evidence_id">{{ item.quote }}</blockquote></section>
  <section v-if="chat?.scale" aria-label="Scale disclosure"><h2>Readiness scale</h2><p>{{ chat.scale.reference_notice }}</p><ol><li v-for="anchor in chat.scale.anchors" :key="anchor.level"><b>{{ anchor.level }} · {{ anchor.label }}</b><p>{{ anchor.description }}</p><small>PDF pages {{ anchor.source?.pdf_pages?.join(', ') }}</small></li></ol><p>Source: {{ chat.scale.source.document }}. Supplied interview example; prototype interpretation pending partner review.</p></section>
  <section v-if="chat?.suggestion" aria-label="Provisional summary"><h2>Provisional summary</h2><p v-if="chat.suggestion.level"><b>Provisional {{ {citizen:'CRL',organisational:'ORL',technical:'TRL'}[chat.profile] }} {{ chat.suggestion.level }} · {{ chat.suggestion.anchor?.label }}</b></p><p v-else>No overall level suggested.</p><p>{{ chat.suggestion.explanation }}</p><p>{{ chat.suggestion.boundary }}</p><details v-if="chat.suggestion.assessments"><summary>Supporting words and uncertainty</summary><div v-for="assessment in chat.suggestion.assessments" :key="assessment.anchor_id"><p v-for="citation in assessment.citations" :key="citation.evidence_id+ citation.quote">“{{ citation.quote }}”</p></div></details></section>
  <section v-if="chat?.initial_suggestion" aria-label="Initial provisional result"><h2>Initial result · review pending</h2><p>{{ chat.initial_suggestion.level ? `Initial provisional level ${chat.initial_suggestion.level}` : 'The initial result was an abstention.' }}</p><p>{{ chat.initial_suggestion.explanation }}</p><p>Additional information has been recorded separately. This has not been reassessed.</p></section>
  <section v-if="chat?.participant_review" aria-label="Your review"><h2>Your review</h2><p>{{ chat.participant_review.text }}</p><p>Review pending. Your view is recorded separately from the tool result.</p></section>
  <div v-if="session?.preview" class="alert" data-testid="chat-cleaned-preview"><h2>Check the cleaned message</h2><p>Some private details were removed. Use this only if it still says what you meant.</p><p>{{ session.preview.fields.text }}</p><div class="row"><button class="btn secondary" :disabled="working" @click="confirmCleaned">Use cleaned message</button><button class="btn secondary" :disabled="working" @click="flow.act('discard_preview')">Return to editing</button></div></div>
  <form v-if="chat && !ended && !session.preview" class="composer" @submit.prevent="send">
   <label for="chat-message">Your message</label><textarea id="chat-message" v-model="draft" class="input" rows="4" maxlength="1800" aria-describedby="chat-hint" />
   <p id="chat-hint" class="t-small">Write in your own words. Enter adds a new line; use Send when ready.</p>
   <button class="btn accent" :disabled="working || !draft.trim()">Send</button>
  </form>
  <p v-if="working" role="status">The AI is responding. Your words are retained; you can keep reading.</p>
  <p class="sr-only" role="status" aria-live="polite">{{ notice }}</p>
  <details v-if="session" class="sra-disclosure"><summary>Download a copy</summary><p>This downloads the screened conversation so far, including partial results and any unresolved review.</p><div class="row"><button class="btn secondary" :disabled="working" @click="flow.act('export', { format:'json' })">Download JSON</button><button class="btn secondary" :disabled="working" @click="flow.act('export', { format:'jsonl' })">Download JSONL</button></div></details>
  <dialog ref="endDialog" aria-labelledby="chat-end-title"><h2 id="chat-end-title">End this temporary session?</h2><p>Download a copy first if you want to keep it. Ending clears the server session.</p><div class="row"><button class="btn secondary" @click="endDialog.close()">Keep talking</button><button class="btn secondary" :disabled="ending" @click="endSession">End session</button></div></dialog>
 </article>
</template>
<style scoped>
.chat{overflow-wrap:anywhere;max-width:48rem;padding:1.25rem;margin:auto}.chat h1{font-size:clamp(1.65rem,5vw,2.3rem)}.messages{list-style:none;padding:0}.messages li{padding:1rem;margin:1rem 0;border-radius:.75rem;background:var(--c-surface,#f4f6fa);border:1px solid var(--line,#ccc)}.messages .respondent{margin-left:1rem;border-left:4px solid var(--c-accent,#20706b)}.messages p,blockquote{white-space:pre-wrap;overflow-wrap:anywhere}.chat .btn{max-width:100%;white-space:normal;overflow-wrap:anywhere;height:auto;min-height:var(--h);padding-block:.5rem}.composer{display:grid;gap:.5rem}.composer textarea{width:100%;min-height:7rem}.composer button{justify-self:start}.chat button:focus-visible,.chat summary:focus-visible,.chat textarea:focus-visible{outline:3px solid #007d80;outline-offset:3px}.row{flex-wrap:wrap}dialog{max-width:min(32rem,95vw)}
</style>
