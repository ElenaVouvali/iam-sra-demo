<script setup>
import { computed, ref, reactive, watch, nextTick, onMounted } from 'vue'
import { useAssessment } from '@/composables/useAssessment'
import AsyncState from '@/components/AsyncState.vue'
import SelectField from '@/components/SelectField.vue'
import AssessmentSummary from '@/components/AssessmentSummary.vue'
import { label } from '@/format'
const flow = useAssessment()
const { session, capabilities, expired, ended, jobStatus, boot, operation, working, allowed } = flow
const context = reactive({ perspective: '', role: '', city: '', place: '', function: '' })
const text = ref(''), correction = ref(''), informationQuestion = ref(''), selection = ref(''), scenarioChoice = ref('')
const blurred = reactive({})
const dialog = ref(null), deliberateAction = ref('reset'), heading = ref(null)
const options = (bank) => Object.entries(capabilities.value?.onboarding[bank] || {}).map(([value, title]) => ({ value, label: title }))
const state = computed(() => session.value?.state)
const taskTitle = computed(() => ({
  general_welcome: 'Before we begin', general_context: 'Review your details',
  general_interview: 'Your general interview', scenario_interview: 'The illustrative example',
  general_review: 'Check our interpretation', scenario_review: 'Check our interpretation',
  general_baseline_review: 'Check your general summary', offer: 'Explore an illustrative example?',
  scenario_baseline_review: 'Check your final summary', final_review: 'Check your final summary', final: 'Your evidence summary',
}[state.value] || 'Your interview'))
const contextReady = computed(() => context.perspective && context.role && context.city)
const reviewingSummary = computed(() => ['general_baseline_review', 'scenario_baseline_review', 'final_review', 'final'].includes(state.value))
const error = computed(() => operation.error.value)
function clearDrafts() { Object.keys(blurred).forEach((key) => { blurred[key] = false }); text.value = ''; correction.value = ''; informationQuestion.value = ''; selection.value = ''; context.place = ''; context.function = '' }
watch(() => session.value && `${session.value.id}:${session.value.version}`, async () => {
  if (!session.value) return
  const view = session.value
  if (view.returned_text && !view.busy_job) text.value = view.returned_text
  if (view.state === 'general_context' && view.respondent) Object.assign(context, {
    perspective: view.respondent.perspective, role: view.respondent.stakeholder_category, city: view.respondent.city,
    place: view.respondent.broad_place || '', function: view.respondent.function || '',
  })
  scenarioChoice.value = view.scenario?.id || ''
  await nextTick()
  if (!view.busy_job) heading.value?.focus({ preventScroll: true })
})
async function submit(action, data = {}) {
  clearDrafts()
  await flow.act(action, data)
}
function submitContext() {
  Object.assign(blurred, { perspective: true, role: true, city: true })
  if (!contextReady.value) return
  const data = { ...context, place: context.city === 'other' ? context.place : '', function: context.perspective === 'organisation' ? context.function : '' }
  submit('set_context', data)
}
function submitAnswer(control = 'answer') {
  const value = session.value.question?.format === 'selection' ? selection.value : text.value.trim()
  if (control === 'answer' && !value) { blurred.answer = true; return }
  submit('answer', { text: control === 'answer' ? value : '', control })
}
function askDeliberate(action) { deliberateAction.value = action; dialog.value.showModal() }
async function confirmDeliberate() {
  dialog.value.close(); clearDrafts()
  if (deliberateAction.value === 'reset') { Object.assign(context, { perspective: '', role: '', city: '' }); await flow.reset() }
  else await flow.act('end')
}
onMounted(flow.initialize)
</script>

<template>
  <article class="tool-card sra-assessment" data-testid="assessment">
    <div class="strip"><svg class="ico" aria-hidden="true"><use href="/brand/icons.svg#i-file" /></svg><h1 class="t-card">IAM-SRA2</h1><span class="badge">Draft instrument</span></div>
    <div class="body sra-body">
      <p class="t-body muted">Explore your understanding and participation in innovative air mobility. Interpretations need your confirmation; self-reports are not independently verified.</p>
      <details class="sra-disclosure">
        <summary>About the assessment</summary>
        <div class="sra-prose">
          <h2 class="t-card">Methodology and sources</h2>
          <p>The general interview remains separate from the optional illustrative scenario. Reviewed local source material supports the example and optional information. The existing IAM-SRA2 controller chooses eligible questions and evidence.</p>
          <p>Check each interpretation, correct it when needed, and confirm the final evidence summary. Missing evidence is unknown. Opinions about a proposal and participation in this interview do not establish readiness.</p>
          <p>Any citizen estimate is provisional. Technical, organisational and overall societal readiness remain unavailable.</p>
          <RouterLink to="/privacy">Read privacy and retention details</RouterLink>
        </div>
      </details>
      <AsyncState :state="boot.state.value" :error="boot.error.value" @retry="flow.initialize" idle-title="Interview not opened" idle-text="No interview has been loaded.">
        <div v-if="capabilities?.synthetic_fixture" class="alert warning" role="status"><svg class="ico" aria-hidden="true"><use href="/brand/icons.svg#i-warn" /></svg><p>Synthetic verification fixture. This is not a live semantic assessment.</p></div>
        <div v-if="!capabilities?.readiness.ready" class="alert warning" role="alert"><svg class="ico" aria-hidden="true"><use href="/brand/icons.svg#i-warn" /></svg><div><h2 class="t-card">Assessment unavailable</h2><p>{{ capabilities?.readiness.error.message }}</p><button class="btn secondary" @click="flow.initialize">Check again</button></div></div>
        <template v-else>
          <div v-if="expired" class="alert warning" role="status"><svg class="ico" aria-hidden="true"><use href="/brand/icons.svg#i-warn" /></svg><p>This interview expired or is no longer available. Start a new interview.</p></div>
          <div v-if="ended" class="alert info" role="status"><svg class="ico" aria-hidden="true"><use href="/brand/icons.svg#i-info" /></svg><p>Your server session has ended. Any downloaded files remain with you.</p></div>
          <div v-if="!session" class="empty">
            <h2 class="t-section">{{ expired ? 'Interview expired' : 'No active interview' }}</h2>
            <p class="t-body muted">Use synthetic, general descriptions for this internal demonstration.</p>
            <button class="btn accent" :disabled="working" @click="flow.act('new')">Start interview</button>
          </div>
          <template v-else>
            <div class="sra-task-head"><h2 ref="heading" class="t-section" tabindex="-1">{{ taskTitle }}</h2><span class="badge">{{ session.stage === 'general' ? 'General interview' : session.stage === 'scenario' ? 'Illustrative scenario' : 'Review' }}</span></div>
            <div v-if="working" class="sra-processing" role="status" aria-live="polite"><p>{{ jobStatus === 'queued' ? 'Your action is queued.' : 'Processing your action. You can wait here or return later.' }}</p><div class="skel" aria-busy="true" aria-label="Processing"><i></i><i></i></div></div>
            <div v-if="error" class="alert danger" role="alert"><svg class="ico" aria-hidden="true"><use href="/brand/icons.svg#i-err" /></svg><div><b>{{ error.code === 'session_expired' ? 'Interview expired' : 'Action could not complete' }}</b><p>{{ error.userMessage }}</p><button class="btn secondary" :disabled="operation.state.value === 'loading'" @click="flow.retry">{{ session.retry_draft ? 'Retry step' : 'Refresh interview' }}</button></div></div>
            <div v-if="session.preview" class="sra-preview" data-testid="cleaned-preview">
              <h3 class="t-card">Check the cleaned text</h3><p>{{ session.preview.message }}</p>
              <dl class="facts"><template v-for="(value, key) in session.preview.fields" :key="key"><dt>{{ label(key) }}</dt><dd>{{ value || 'Not supplied' }}</dd></template></dl>
              <div class="row"><button class="btn accent" :disabled="working" @click="submit('confirm_cleaned', { preview_id: session.preview.id })">Confirm cleaned text</button><button class="btn secondary" :disabled="working" @click="submit('discard_preview')">Discard preview</button></div>
            </div>
            <div v-if="!session.preview" :aria-busy="working">
              <div v-if="allowed('set_context')">
                <p class="sra-notice">{{ session.privacy_notice }}</p>
                <form class="sra-form" @submit.prevent="submitContext">
                  <SelectField v-model="context.perspective" label="Are you answering personally or for an organisation?" :options="options('perspectives')" :disabled="working" @focusout="blurred.perspective = true" />
                  <p v-if="blurred.perspective && !context.perspective" class="sra-validation">Choose a perspective.</p>
                  <SelectField v-model="context.role" label="Which role best describes you?" :options="options('stakeholders')" :disabled="working" @focusout="blurred.role = true" />
                  <p v-if="blurred.role && !context.role" class="sra-validation">Choose a role.</p>
                  <SelectField v-model="context.city" label="Which city or region are you answering about?" :options="options('cities')" :disabled="working" @focusout="blurred.city = true" />
                  <p v-if="blurred.city && !context.city" class="sra-validation">Choose a city or region.</p>
                  <div v-if="context.city === 'other'" class="field"><label for="place">Broad city or region (optional)</label><input id="place" v-model="context.place" class="input" maxlength="80" autocomplete="off" :disabled="working" /></div>
                  <div v-if="context.perspective === 'organisation'" class="field"><label for="function">Function or responsibility (optional)</label><input id="function" v-model="context.function" class="input" maxlength="240" autocomplete="off" :disabled="working" /></div>
                  <button class="btn accent" :disabled="working">Begin interview</button>
                </form>
              </div>
              <form v-else-if="allowed('answer') && session.question" class="sra-form" @submit.prevent="submitAnswer()">
                <p class="t-card" data-testid="question">{{ session.question.question_text }}</p>
                <p class="sra-notice">{{ session.privacy_notice }}</p>
                <SelectField v-if="session.question.format === 'selection'" v-model="selection" label="Your answer" :options="Object.entries(session.question.options).map(([value, title]) => ({ value, label: title }))" :disabled="working" />
                <div v-else class="field"><label for="answer">Your answer</label><textarea id="answer" v-model="text" class="input sra-textarea" maxlength="6000" autocomplete="off" :disabled="working" @blur="blurred.answer = true"></textarea></div>
                <p v-if="blurred.answer && !(selection || text.trim())" class="sra-validation">Write or choose an answer, or use Skip.</p>
                <div class="row"><button class="btn accent" :disabled="working">Submit answer</button><button v-for="control in ['skip', 'unsure', 'decline']" :key="control" type="button" class="btn secondary sm" :disabled="working" @click="submitAnswer(control)">{{ { skip: 'Skip', unsure: 'Not sure', decline: 'Prefer not to answer' }[control] }}</button></div>
              </form>
              <div v-else-if="session.pending" class="sra-form" data-testid="interpretation">
                <p class="t-body">{{ session.pending.question?.question_text }}</p>
                <ul v-if="session.pending.interpretations.length" class="bullets"><li v-for="meaning in session.pending.interpretations" :key="meaning">{{ meaning }}</li></ul>
                <p v-else>No clear interpretation was captured. You can correct it before continuing.</p>
                <button v-if="allowed('confirm_answer')" class="btn accent" :disabled="working" @click="submit('confirm_answer')">Confirm interpretation</button>
                <details class="sra-disclosure"><summary>Correct the interpretation</summary><form class="sra-form" @submit.prevent="correction.trim() && submit('correct_interpretation', { text: correction })"><p class="sra-notice">{{ session.privacy_notice }}</p><div class="field"><label for="correction">What should we understand differently?</label><textarea id="correction" v-model="correction" class="input sra-textarea" maxlength="1500" :disabled="working" @blur="blurred.correction = true"></textarea><span v-if="blurred.correction && !correction.trim()" class="sra-validation">Describe the correction.</span></div><button class="btn secondary" :disabled="working || !correction.trim()">Apply correction</button></form></details>
                <details class="sra-disclosure"><summary>Your original answer</summary><p class="sra-whitespace">{{ session.pending.text }}</p></details>
              </div>
              <div v-if="state === 'offer'" class="sra-form">
                <SelectField v-model="scenarioChoice" label="Choose an illustrative example" :options="session.scenarios.map((row) => ({ value: row.id, label: row.title || row.id }))" :disabled="working" />
                <button v-if="scenarioChoice !== session.scenario?.id" class="btn secondary" :disabled="working || !scenarioChoice" @click="submit('select_scenario', { scenario_id: scenarioChoice })">Show example</button>
              </div>
              <section v-if="session.scenario && (state === 'offer' || session.stage === 'scenario')" class="sra-scenario">
                <h3 class="t-card">{{ session.scenario.title }}</h3><p class="sra-whitespace">{{ session.scenario.text }}</p><p class="t-small muted">This is a source-described or hypothetical example. It does not establish a current local service.</p>
                <details class="sra-disclosure"><summary>Unknown details and source</summary><p>{{ session.scenario.unknowns?.join(', ') }}</p><p>{{ session.scenario.source.document }} · {{ session.scenario.source.locator }}</p></details>
              </section>
              <div v-if="state === 'offer'" class="row"><button class="btn accent" :disabled="working || scenarioChoice !== session.scenario?.id" @click="submit('accept_scenario')">Discuss example</button><button class="btn secondary" :disabled="working" @click="submit('decline_scenario')">Decline example</button></div>
              <AssessmentSummary v-if="reviewingSummary" :summary="session.summary" />
              <button v-if="allowed('confirm_general')" class="btn accent" :disabled="working" @click="submit('confirm_general')">Confirm general summary</button>
              <button v-if="allowed('confirm_final')" class="btn accent" :disabled="working" @click="submit('confirm_final')">Confirm final summary</button>
              <details v-if="allowed('ask_information') || session.information.length" class="sra-disclosure" data-testid="information"><summary>Optional information and sources</summary>
                <form v-if="allowed('ask_information')" class="sra-form" @submit.prevent="informationQuestion.trim() && submit('ask_information', { question: informationQuestion })"><p class="sra-notice">{{ session.privacy_notice }}</p><div class="field"><label for="information-question">What would you like to know about this example?</label><input id="information-question" v-model="informationQuestion" class="input" maxlength="300" :disabled="working" autocomplete="off" /></div><button class="btn secondary" :disabled="working || !informationQuestion.trim()">Show sourced information</button></form>
                <section v-for="exposure in session.information" :key="exposure.id" class="sra-exposure"><h3 class="t-card">{{ exposure.kind === 'explanation' ? 'Draft sourced explanation' : 'Illustrative scenario shown' }}</h3><p class="sra-whitespace">{{ exposure.text }}</p><p v-if="exposure.content.notice" class="t-small muted">{{ exposure.content.notice }}</p><div v-for="excerpt in exposure.content.excerpts" :key="excerpt.passage_id" class="t-small muted">{{ excerpt.source.document_title || excerpt.source.document }} · {{ excerpt.source.location || excerpt.source.locator }}</div><p v-if="exposure.acknowledged" class="t-small">Acknowledged as read.</p><button v-else-if="allowed('acknowledge')" class="btn secondary" :disabled="working" @click="submit('acknowledge', { exposure_id: exposure.id })">I have read this</button></section>
                <button v-if="allowed('start_reflection')" class="btn secondary" :disabled="working" @click="submit('start_reflection')">Reflect on information</button>
              </details>
              <details v-if="session.answers.length || session.evidence.length || reviewingSummary" class="sra-disclosure"><summary>Evidence and earlier answers</summary>
                <p class="t-small muted">Prior knowledge and reasoning after supplied information remain separate. Confirmation does not provide external verification.</p>
                <section v-for="answer in session.answers" :key="answer.id" class="sra-exposure"><h3 class="t-card">{{ answer.question_text }}</h3><p class="sra-whitespace">{{ answer.text }}</p><p class="t-small muted">{{ answer.stage === 'general' ? 'General interview' : 'Illustrative scenario' }} · Confirmed self-report</p><button v-if="allowed('edit_answer')" class="btn secondary sm" :disabled="working" @click="submit('edit_answer', { stage: answer.stage, event_id: answer.id })">Edit answer</button></section>
                <ul class="bullets"><li v-for="item in session.evidence" :key="item.evidence_id">{{ item.interpretation }} <span class="t-small muted">({{ label(item.information_context || 'general_baseline') }}, {{ item.external_verification || 'not independently verified' }})</span></li></ul>
              </details>
              <section v-if="state === 'final'" class="sra-results" data-testid="results"><h3 class="t-card">Assessment limits</h3><p>CRL, TRL, ORL and overall SRL are unavailable from this evidence summary. Missing evidence does not establish low readiness.</p>
                <div class="row"><button class="btn secondary" :disabled="working" @click="flow.act('export', { format: 'json' })">Download JSON</button><button class="btn secondary" :disabled="working" @click="flow.act('export', { format: 'jsonl' })">Download JSONL</button></div>
                <details v-if="allowed('provisional_estimate')" class="sra-disclosure"><summary>Optional provisional citizen estimate</summary><p>This draft, unapproved model judgement uses confirmed personal evidence against workbook descriptions. It is not independently verified and may abstain. It does not establish technical, organisational or overall societal readiness.</p><button class="btn secondary" :disabled="working" @click="submit('provisional_estimate')">Request provisional estimate</button><div v-if="session.results.provisional_citizen_estimate"><p class="t-card">Provisional citizen estimate: {{ session.results.provisional_citizen_estimate.crl ?? 'Unavailable' }}</p><p>{{ session.results.provisional_citizen_estimate.explanation }}</p><p class="t-small muted">Draft · Unapproved · Not independently verified</p></div></details>
              </section>
            </div>
            <nav class="sra-controls row" aria-label="Interview controls"><button v-if="allowed('back')" class="btn secondary sm" :disabled="working" @click="submit('back')">Back one step</button><button v-if="allowed('edit_context')" class="btn secondary sm" :disabled="working" @click="submit('edit_context')">Edit details</button><button v-if="allowed('finish')" class="btn secondary sm" :disabled="working" @click="submit('finish')">Finish here</button><button class="btn secondary sm" :disabled="operation.state.value === 'loading' && !session.busy_job" @click="askDeliberate('reset')">Reset interview</button><button class="btn secondary sm" :disabled="working" @click="askDeliberate('end')">End session</button></nav>
          </template>
          <div v-if="!session && error" class="alert danger" role="alert"><svg class="ico" aria-hidden="true"><use href="/brand/icons.svg#i-err" /></svg><p>{{ error.userMessage }}</p></div>
        </template>
      </AsyncState>
      <dialog ref="dialog" class="modal" aria-labelledby="reset-title"><h2 id="reset-title" class="t-card">{{ deliberateAction === 'reset' ? 'Reset this interview?' : 'End this session?' }}</h2><p>Server-held answers will no longer be available in this session. Download any results you want to keep first. Downloaded files remain with you.</p><div class="row"><button class="btn secondary" @click="dialog.close()">Keep interview</button><button class="btn danger" @click="confirmDeliberate">{{ deliberateAction === 'reset' ? 'Confirm reset' : 'Confirm end' }}</button></div></dialog>
    </div>
  </article>
</template>
