<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAssessment } from '@/composables/useAssessment'
const flow = useAssessment({ mode: 'chat', depth: 'short', assisted: new URLSearchParams(location.search).get('assisted') === '1' })
const { session, boot, operation, working, inferenceStatus, ended: sessionEnded } = flow
const chat = computed(() => session.value?.chat)
const draft = ref(''), feedbackDraft = ref(''), notice = ref(''), endDialog = ref(null), ending = ref(false)
const ended = computed(() => chat.value?.stage === 'ended')
const introducedSession = ref(null), conversationStart = ref(null)
const introduction = computed(() => chat.value?.messages.find((m) => m.act === 'introduction'))
const showIntroduction = computed(() => introduction.value && !sessionEnded.value
 && introducedSession.value !== session.value?.id && !chat.value.messages.some((m) => m.role === 'respondent'))
const conversationMessages = computed(() => chat.value?.messages.filter((m) => m.act !== 'introduction') || [])
const choiceDisplay = computed(() => {
 const options = chat.value?.response_options || []
 const message = conversationMessages.value.filter((m) => m.role === 'assistant').at(-1)
 if (!options.length || !message) return { options: [], questionId: null, prompt: '' }
 const inlineList = options.map((o, i) => `${i === options.length - 1 ? 'or ' : ''}${o.value}. ${o.label}`).join(', ')
 const lines = message.text.replace(inlineList, '').replace(/:\s*\./g, '.').split('\n'), hidden = new Set()
 const optionLine = (line) => line.match(/^([A-E])(?:\.\s+|\s+—\s+)(.*)$/)
 const cards = options.map((option) => {
  const index = lines.findIndex((line) => {
   const match = optionLine(line)
   return match?.[1] === option.value && match[2].trim() === option.label
  })
  if (index < 0) return option
  hidden.add(index)
  const description = []
  for (let i = index + 1; i < lines.length && lines[i].trim() && !optionLine(lines[i]); i++) {
   description.push(lines[i]); hidden.add(i)
  }
  return { ...option, description: description.join('\n') }
 })
 return { options: cards, questionId: message.id,
  prompt: lines.filter((_, i) => !hidden.has(i)).join('\n').replace(/\n{3,}/g, '\n\n').trim() }
})
const responseOptions = computed(() => choiceDisplay.value.options)
const selectedChoice = ref('')
const longWait = ref(false)
let longWaitTimer = null
watch(working, (busy) => {
 clearTimeout(longWaitTimer); longWait.value = false
 if (busy) longWaitTimer = setTimeout(() => { longWait.value = true }, 30000)
})
onBeforeUnmount(() => clearTimeout(longWaitTimer))
watch(() => `${session.value?.id}:${chat.value?.messages.at(-1)?.id}`, () => {
 selectedChoice.value = ''
})
async function beginConversation() {
 introducedSession.value = session.value.id
 await nextTick()
 conversationStart.value?.focus()
}
async function sendChoice() {
 if (!selectedChoice.value || working.value || !responseOptions.value.some((o) => o.value === selectedChoice.value)) return
 const ok = await flow.act('chat_message', { text: selectedChoice.value })
 notice.value = ok ? 'Response ready below.' : 'Your selection is retained. Please check the error.'
}
async function send() {
 if (!draft.value.trim() || working.value) return
 const submitted = draft.value
 const ok = await flow.act('chat_message', { text: submitted })
 if (ok && !session.value?.preview && draft.value === submitted) draft.value = ''
 if (!session.value) return
 notice.value = ok ? 'Response ready below.' : 'Your draft is retained. Please check the error.'
}
async function submitFeedback() {
 if (working.value || chat.value?.reviewer_feedback) return
 const ok = await flow.act('chat_feedback', { text: feedbackDraft.value })
 if (ok) notice.value = feedbackDraft.value.trim() ? 'Thank you. Your feedback was recorded separately.' : 'Feedback skipped.'
}
async function sendControl(text) {
 if (!working.value) await flow.act('chat_message', { text })
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
 if (ok) { draft.value = ''; introducedSession.value = null }
}
onMounted(start)
</script>

<template>
 <article class="chat wrap" data-testid="chat-conversation">
  <header><h1>Let's talk about drones</h1><p>A conversation about healthcare deliveries, your experience and what matters to you.</p></header>
  <section v-if="showIntroduction" class="introduction" aria-labelledby="chat-welcome-title" data-testid="chat-introduction">
   <h2 id="chat-welcome-title">Before we begin</h2>
   <p>{{ introduction.text }}</p>
   <p v-if="operation.error.value" role="alert">{{ operation.error.value.userMessage }}</p>
   <RouterLink to="/privacy">Full privacy and retention details</RouterLink>
   <div class="row"><button class="btn accent" :disabled="working" @click="beginConversation">Continue to the conversation</button><button class="btn secondary" :disabled="working" @click="endDialog.showModal()">Leave and clear session</button></div>
  </section>
  <template v-else>
  <p v-if="inferenceStatus?.mode === 'on_demand'" role="status">
   <template v-if="inferenceStatus.state === 'loading'">Preparing your response…</template>
   <template v-else-if="inferenceStatus.state === 'unavailable'">I could not prepare a response just now. Your earlier answers are safe; please try again shortly.</template>
   <template v-else></template>
  </p>
  <p v-if="chat?.completion?.partial" role="status">This is a partial interview. Unexplored or uncertain points do not automatically lower readiness.</p>
  <p v-if="chat?.completion?.evidence_sufficiency === 'unassessed'" role="status">This interview ended without a readiness assessment.</p>
  <details class="sra-disclosure"><summary>Privacy, help and conversation options</summary>
   <p>Please avoid names, contact details and sensitive information. This AI-assisted research prototype screens messages before processing. Your words are self-reports; generated interpretations and results are provisional.</p>
   <p>Progress and wording preferences are held temporarily in memory. Download a copy to keep them. Saving, cross-day resume and contact follow-up are unavailable. Nothing here enables training.</p>
   <p>You can type “I don't know”, “skip this question”, “stop”, “simplify”, “go back”, “keep it short”, “more detail”, or ask to change topic. You do not need to remember commands; ordinary language is welcome. To see two alternative wordings, ask “show two ways of asking that”. English is the tested language.</p>
   <button v-if="chat?.profile === 'citizen' && chat?.depth_selection && chat?.stage === 'conversation'" class="btn secondary sm" :disabled="working" @click="flow.act('chat_message', { text: chat?.depth === 'extended' ? 'keep it short' : 'extended conversation' })">{{ chat?.depth === 'extended' ? 'Use short citizen interview (~20 min)' : 'Use extended citizen interview (~35 min)' }}</button>
   <p v-if="chat?.assisted">Facilitator mode: type the respondent's own words. Do not supply answers for them. This assistance is recorded in the report.</p>
   <RouterLink to="/privacy">Full privacy and retention details</RouterLink>
   <div class="row"><button v-if="chat && !ended" class="btn secondary sm" :disabled="working" @click="sendControl('pause')">Pause</button><button v-if="chat && !ended && chat.stage==='conversation'" class="btn secondary sm" :disabled="working" @click="sendControl('skip this question')">Skip this question</button><button v-if="chat && !ended" class="btn secondary sm" :disabled="working" @click="sendControl('stop')">Finish with a partial record</button><button class="btn secondary sm" :disabled="working" @click="restart">New conversation</button><button v-if="session" class="btn secondary sm" :disabled="ending || working" @click="endDialog.showModal()">End and clear session</button></div>
  </details>
  <p v-if="sessionEnded" role="status">Your temporary session has ended. Downloaded copies remain with you.</p>
  <p v-if="boot.state.value === 'loading'" role="status">Opening the conversation…</p>
  <div v-if="boot.error.value" role="alert"><p>{{ boot.error.value.userMessage }}</p><button class="btn secondary" @click="start">Retry opening</button></div>
  <div v-if="operation.error.value" role="alert"><p>{{ operation.error.value.userMessage }} Earlier answers are retained.</p><button class="btn secondary" :disabled="working" @click="session?.retry_draft ? flow.retry() : flow.act('refresh')">{{ session?.retry_draft ? 'Retry this response' : 'Refresh conversation' }}</button></div>
  <ol v-if="chat" ref="conversationStart" tabindex="-1" class="messages" aria-label="Conversation">
   <li v-for="message in conversationMessages" :key="message.id" :class="message.role">
    <b>{{ message.role === 'assistant' ? 'AI assistant' : 'You' }}</b>
  <section v-if="chat?.suggestion && ['result_review', 'assessment_gap'].includes(message.act)" aria-label="Provisional summary"><h2>Provisional summary</h2><p v-if="chat.suggestion.level"><b>Provisional {{ {citizen:'CRL',organisational:'ORL',technical:'TRL'}[chat.profile] }} {{ chat.suggestion.level }} · {{ chat.suggestion.anchor?.label }}</b></p><p v-else>No numeric level is suggested. You can comment, remain uncertain or finish without a score.</p><p>{{ chat.suggestion.explanation }}</p><p>{{ chat.suggestion.boundary }}</p><details v-if="chat.suggestion.citations?.length"><summary>Supporting words and uncertainty</summary><div v-for="citation in chat.suggestion.citations" :key="citation.evidence_id+ citation.quote">“{{ citation.quote }}”</div></details></section>
    <p>{{ message.id === choiceDisplay.questionId ? choiceDisplay.prompt : message.text }}</p>
    <p v-if="message.resource?.id === 'easa_basics'"><a :href="message.resource.url" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer">{{ message.resource.label }}</a></p>
  <section v-if="(message.scale || chat?.scale) && ['scale_disclosure', 'methodology'].includes(message.act)" aria-label="Scale disclosure"><h2>Readiness scale</h2><p>This prototype scale supports a provisional summary of your self-reported situation. It does not independently verify your answers.</p><ol><li v-for="anchor in (message.scale || chat.scale).anchors" :key="anchor.level"><b>{{ anchor.level }} · {{ anchor.label }}</b><p>{{ anchor.description }}</p></li></ol></section>

   </li>
  </ol>
  <section v-if="chat?.pending_comparison" aria-label="Optional wording preference">
   <p v-for="(variant, index) in chat.pending_comparison.variants" :key="variant.response_id"><b>{{ index + 1 }}.</b> {{ variant.text }}</p>
  </section>
  <section v-if="chat?.summary?.length" aria-label="Your evidence summary"><h2>A few points from your words</h2><p>These are selected original passages. Your full conversation remains above and in the download. Please correct anything missing or misunderstood.</p><blockquote v-for="item in chat.summary" :key="item.evidence_id">{{ item.quote }}</blockquote></section>
  <section v-if="chat?.initial_suggestion" aria-label="Initial provisional result"><h2>Initial result · review pending</h2><p>{{ chat.initial_suggestion.level ? `Initial provisional level ${chat.initial_suggestion.level}` : 'The initial result was an abstention.' }}</p><p>{{ chat.initial_suggestion.explanation }}</p><p>Additional information has been recorded separately. This has not been reassessed.</p></section>
  <section v-if="chat?.participant_review" aria-label="Your review"><h2>Your review</h2><p>{{ chat.participant_review.text }}</p><p>{{ chat.participant_review.status === 'agreed' ? 'You explicitly agreed with the provisional result.' : chat.participant_review.status === 'completed_without_numeric_result' ? 'Completed without a numeric result.' : 'Review pending. Your view and additional evidence are recorded separately; the initial result is unchanged.' }}</p></section>
  <div v-if="session?.preview" class="alert" data-testid="chat-cleaned-preview"><h2>Check the cleaned message</h2><p>Some private details were removed. Use this only if it still says what you meant.</p><p>{{ session.preview.fields.text }}</p><div class="row"><button class="btn secondary" :disabled="working" @click="confirmCleaned">Use cleaned message</button><button class="btn secondary" :disabled="working" @click="flow.act('discard_preview')">Return to editing</button></div></div>
  <details v-if="chat && !ended && !session.preview && responseOptions.length" class="answer-suggestions">
  <summary>Optional quick answers</summary>
  <fieldset class="answer-options" :disabled="working" data-testid="chat-answer-options">
   <legend>Choose your answer</legend>
   <label v-for="option in responseOptions" :key="option.value" class="answer-option" :class="{ selected: selectedChoice === option.value }">
    <input type="radio" name="chat-answer" :value="option.value" :checked="selectedChoice === option.value" @change="selectedChoice = option.value" />
    <span><b>{{ option.value }}.</b> {{ option.label }}<small v-if="option.description" class="option-description">{{ option.description }}</small></span>
   </label>
   <div class="row"><button class="btn accent" type="button" :disabled="working || !selectedChoice" @click="sendChoice">Send selected answer</button></div>
  </fieldset>
  </details>
  <form v-if="chat && !ended && !session.preview" class="composer" @submit.prevent="send">
   <label for="chat-message">Your message <span v-if="responseOptions.length">(or write another answer)</span></label><textarea id="chat-message" v-model="draft" class="input" rows="4" maxlength="1800" aria-describedby="chat-hint" />
   <p id="chat-hint" class="t-small">Write in your own words or ask a question. Enter adds a new line; use Send when ready.</p>
   <button class="btn accent" :disabled="working || !draft.trim()">Send</button>
  </form>
  <section v-if="ended && chat?.participant_review && !chat?.reviewer_feedback" class="composer" aria-label="Optional feedback about the conversation">
   <h2>Optional feedback about this conversation</h2><p>Would you like to tell us whether the questions were clear, repetitive, helpful or difficult to answer? This does not change your interview answers or result.</p>
   <label for="reviewer-feedback">Your feedback (optional)</label><textarea id="reviewer-feedback" v-model="feedbackDraft" class="input" rows="3" maxlength="1200" />
   <div class="row"><button class="btn accent" :disabled="working" @click="submitFeedback">{{ feedbackDraft.trim() ? 'Send feedback' : 'Skip feedback' }}</button></div>
  </section>
  <p v-if="ended && chat?.reviewer_feedback" role="status">{{ chat.reviewer_feedback.provided ? 'Thank you. Your optional feedback is stored separately from the readiness evidence.' : 'Optional feedback skipped.' }}</p>
  <p v-if="working" role="status">{{ longWait ? 'This is taking longer than usual. Your response is still being processed.' : 'Preparing your response…' }}</p>
  <p class="sr-only" role="status" aria-live="polite">{{ notice }}</p>
  <details v-if="session" class="sra-disclosure"><summary>Download a copy</summary><p>This downloads the screened conversation so far, including partial results and any unresolved review.</p><div class="row"><button class="btn secondary" :disabled="working" @click="flow.act('export', { format:'json' })">Download JSON</button><button class="btn secondary" :disabled="working" @click="flow.act('export', { format:'jsonl' })">Download JSONL</button></div></details>
  </template>
  <dialog ref="endDialog" aria-labelledby="chat-end-title"><h2 id="chat-end-title">End this temporary session?</h2><p>Download a copy first if you want to keep it. Ending clears the server session.</p><div class="row"><button class="btn secondary" @click="endDialog.close()">Keep talking</button><button class="btn secondary" :disabled="ending" @click="endSession">End session</button></div></dialog>
 </article>
</template>
<style scoped>
.introduction p{white-space:pre-wrap}.introduction .row{margin-top:1.25rem}.answer-suggestions{margin:.5rem 0}.answer-suggestions summary{cursor:pointer;color:var(--c-muted,#555)}.answer-options{min-width:0;display:grid;gap:.75rem;padding:1rem;margin:.5rem 0;border:1px solid var(--line,#ccc);border-radius:.75rem}.answer-option{display:flex;align-items:flex-start;gap:.75rem;padding:.85rem;border:1px solid var(--line,#ccc);border-radius:.5rem;cursor:pointer}.answer-option.selected{border-color:var(--c-accent,#20706b);background:var(--c-surface,#f4f6fa)}.answer-option span{min-width:0}.option-description{display:block;margin-top:.35rem;font-size:.95em;line-height:1.5}.answer-option input{flex-shrink:0;margin-top:.25rem}.answer-options legend{font-weight:600}.chat{overflow-wrap:anywhere;max-width:48rem;padding:1.25rem;margin:auto}.chat h1{font-size:clamp(1.65rem,5vw,2.3rem)}.messages{list-style:none;padding:0}.messages li{padding:1rem;margin:1rem 0;border-radius:.75rem;background:var(--c-surface,#f4f6fa);border:1px solid var(--line,#ccc)}.messages .respondent{margin-left:1rem;border-left:4px solid var(--c-accent,#20706b)}.messages p,blockquote{white-space:pre-wrap;overflow-wrap:anywhere}.chat .btn{max-width:100%;white-space:normal;overflow-wrap:anywhere;height:auto;min-height:var(--h);padding-block:.5rem}.composer{display:grid;gap:.5rem}.composer textarea{width:100%;min-height:7rem}.composer button{justify-self:start}.chat button:focus-visible,.chat summary:focus-visible,.chat textarea:focus-visible{outline:3px solid #007d80;outline-offset:3px}.row{flex-wrap:wrap}dialog{max-width:min(32rem,95vw)}
</style>
