<script setup>
import { computed, reactive, ref, watch } from 'vue'
import SelectField from './SelectField.vue'
const props = defineProps({ view: Object, allowed: Function, working: Boolean, answers: Array, returnedText: String })
const emit = defineEmits(['action'])
const selected = ref([]), context = ref('general_understanding'), useCase = ref('')
const reuse = reactive({}), answer = ref(''), feedback = ref(''), statement = ref(''), explanation = ref('')
const row = computed(() => props.view?.current)
const levels = computed(() => row.value?.scale || [])
const labels = { not_assessed: 'Not assessed', suggested: 'Awaiting your review', insufficient_evidence: 'Tool abstained', completed: 'Self-assessment recorded', participant_unsure: 'Participant unsure', declined: 'Declined' }
watch(() => props.view?.revision, () => {
  answer.value = ''; feedback.value = ''; statement.value = ''; explanation.value = ''; useCase.value = ''
  if (props.returnedText && row.value?.state === 'collecting') answer.value = props.returnedText
})
function act(name, data = {}) {
  answer.value = ''; feedback.value = ''; explanation.value = ''; useCase.value = ''
  emit('action', name, data)
}
function begin() {
  const linked = Object.fromEntries(selected.value.map((id) => [id, reuse[id] || []]))
  act('select_indicators', { profile: 'citizen', indicator_ids: [...selected.value], context: context.value, use_case: useCase.value, reuse_answers: linked })
}
const reusable = computed(() => (props.answers || []).filter((a) => context.value === 'illustrative_proposal' ? a.stage === 'scenario' : a.stage === 'general'))
</script>

<template>
  <section class="sra-results" data-testid="indicator-assessment">
    <h3 class="t-section">Citizen indicator self-assessment</h3>
    <p v-if="!view?.available" role="status">{{ view?.notice }}</p>
    <template v-else>
      <p class="sra-notice">{{ view.notice }}</p>
      <details class="sra-disclosure" :open="!row">
        <summary>{{ row ? 'Choose further indicators or change assessment scope' : 'Choose your indicators and scope' }}</summary>
        <form class="sra-form" @submit.prevent="begin">
          <p>You are answering as an individual citizen. Choose one to three issues for this round. This is a partial assessment. Restarting an indicator or changing scope supersedes its previous judgments.</p>
          <fieldset :disabled="working || !allowed('select_indicators')"><legend>Indicators (choose up to three)</legend>
            <label v-for="item in view.coverage" :key="item.indicator_id" class="sra-indicator-option"><input v-model="selected" type="checkbox" :value="item.indicator_id" :disabled="selected.length >= 3 && !selected.includes(item.indicator_id)" /> {{ item.name }}</label>
          </fieldset>
          <SelectField v-model="context" label="What is this discussion about?" :disabled="working" :options="[{ value: 'general_understanding', label: 'General understanding' }, { value: 'illustrative_proposal', label: 'The illustrative example discussed' }, { value: 'actual_experience', label: 'My actual experience' }]" />
          <div class="field"><label for="indicator-context">Use case or context (optional, general description)</label><input id="indicator-context" v-model="useCase" class="input" maxlength="240" :disabled="working" autocomplete="off" /></div>
          <details v-if="reusable.length && selected.length" class="sra-disclosure"><summary>Reuse relevant confirmed answers</summary>
            <p>Link only answers that concern this indicator and context. A linked answer is still checked against the statement; a topic label alone does not establish readiness.</p>
            <fieldset v-for="id in selected" :key="id" :disabled="working"><legend>{{ view.coverage.find((i) => i.indicator_id === id)?.name }}</legend>
              <label v-for="item in reusable" :key="item.id" class="sra-indicator-option"><input :checked="(reuse[id] || []).includes(item.id)" type="checkbox" :disabled="(reuse[id] || []).length >= 3 && !(reuse[id] || []).includes(item.id)" @change="reuse[id] = $event.target.checked ? [...(reuse[id] || []), item.id] : (reuse[id] || []).filter((v) => v !== item.id)" /> {{ item.text }}</label>
            </fieldset>
          </details>
          <button class="btn accent" :disabled="working || !allowed('select_indicators') || !selected.length">Begin selected indicators</button>
        </form>
      </details>
      <template v-if="row">
        <h4 class="t-card">{{ row.name }} · Citizen / CRL</h4>
        <p>{{ row.scope.context.replaceAll('_', ' ') }} · {{ row.scope.use_case }}</p>
        <details class="sra-disclosure"><summary>Definition, assessment criterion and all nine statements</summary>
          <p class="sra-whitespace">{{ row.definition }}</p><p class="sra-whitespace">{{ row.criterion.text }}</p>
          <ol class="bullets"><li v-for="level in levels" :key="level.id"><b>CRL {{ level.level }} · {{ level.label }}</b><p class="sra-whitespace">{{ level.statement }}</p><p class="t-small muted">{{ level.source.sheet }}!{{ level.source.cell }} · Shared row review: {{ level.row_review_status }}</p></li></ol>
          <p class="t-small muted">{{ view.bank.source.document }} · Draft {{ view.bank.bank_version }}. Row review is shared, not a separate approval for each profile.</p>
        </details>
        <div v-if="row.state === 'collecting' && row.question" class="sra-form">
          <p class="t-card" data-testid="indicator-question">{{ row.question.question_text }}</p>
          <p class="sra-notice">Up to {{ row.question_budget }} short questions per indicator. No prior service use is required. You may finish or remain unsure.</p>
          <form class="sra-form" @submit.prevent="act('indicator_answer', { text: answer, control: 'answer' })">
            <div class="field"><label for="indicator-answer">Your indicator answer</label><textarea id="indicator-answer" v-model="answer" class="input sra-textarea" maxlength="2000" autocomplete="off" :disabled="working" /></div>
            <div class="row"><button class="btn accent" :disabled="working || !answer.trim()">Submit indicator answer</button>
              <button v-for="control in ['skip', 'unsure', 'decline']" :key="control" type="button" class="btn secondary sm" :disabled="working" @click="act('indicator_answer', { text: '', control })">{{ {skip:'Skip indicator question', unsure:'Not sure about this question', decline:'Prefer not to answer this question'}[control] }}</button>
            </div>
          </form>
          <button class="btn secondary" :disabled="working" @click="act('indicator_finish')">Finish indicator questions</button>
        </div>
        <div v-if="row.pending" class="sra-form" data-testid="indicator-interpretation">
          <h4 class="t-card">Check the indicator interpretation</h4><p>{{ row.pending.reading.meaning }}</p>
          <p>Check both the meaning and how each excerpt is understood. Correct any mistaken attribution or distinction before confirming.</p>
          <ul class="bullets"><li v-for="(observation, index) in row.pending.reading.observations" :key="index">“{{ observation.quote }}”<p>{{ observation.review_description }}</p><p v-for="ambiguity in observation.ambiguities" :key="ambiguity">Unresolved: {{ ambiguity }}</p></li></ul>
          <button class="btn accent" :disabled="working" @click="act('indicator_confirm')">Confirm indicator interpretation</button>
          <details class="sra-disclosure"><summary>Correct the indicator interpretation</summary><form class="sra-form" @submit.prevent="act('indicator_correct', {text:feedback})"><label for="indicator-feedback">What should we understand differently?</label><textarea id="indicator-feedback" v-model="feedback" class="input sra-textarea" maxlength="1500" :disabled="working" /><button class="btn secondary" :disabled="working || !feedback.trim()">Apply indicator correction</button></form></details>
          <details class="sra-disclosure"><summary>Original indicator answer</summary><p class="sra-whitespace">{{ row.pending.text }}</p></details>
        </div>
        <button v-if="allowed('indicator_suggest')" class="btn secondary" :disabled="working" @click="act('indicator_suggest')">Request draft indicator suggestion</button>
        <section v-if="row.participant" data-testid="participant-indicator-result">
          <h4 class="t-card">Your individual self-assessment</h4>
          <template v-if="row.participant.statement"><p><b>CRL {{ row.participant.statement.level }} · {{ row.participant.statement.label }}</b></p><p class="sra-whitespace">{{ row.participant.statement.statement }}</p></template>
          <p v-else>{{ row.participant.status === 'unsure' ? 'You remain unsure. No level selected.' : 'You declined to give a level.' }}</p>
          <p v-if="row.participant.explanation">{{ row.participant.explanation }}</p>
        </section>
        <details v-if="row.tool" class="sra-disclosure" open data-testid="tool-indicator-result"><summary>Provisional tool suggestion and evidence</summary>
          <p>{{ row.tool.statement ? `Suggested CRL ${row.tool.statement.level} · ${row.tool.statement.label}` : 'The tool abstained: no level suggested.' }}</p>
          <p v-if="row.tool.statement" class="sra-whitespace">{{ row.tool.statement.statement }}</p><p>{{ row.tool.explanation }}</p>
          <ul class="bullets"><li v-for="gap in row.tool.gaps" :key="gap">{{ gap }}</li></ul>
          <details class="sra-disclosure"><summary>Statement matches and supporting excerpts</summary><section v-for="match in row.tool.assessments" :key="match.statement_id"><p>{{ match.statement_id }} · {{ match.status }} · {{ match.reason }}</p><p v-for="cite in match.evidence" :key="cite.evidence_id + cite.quote">“{{ cite.quote }}” ({{ cite.evidence_id }})</p></section></details>
        </details>
        <section v-if="allowed('indicator_review')" class="sra-form" data-testid="indicator-review">
          <h4 class="t-card">Review your level</h4><p>Read the nine statements above before choosing. You do not have to agree with the tool. To add new information, edit an answer first.</p>
          <button v-if="row.tool?.statement" class="btn accent" :disabled="working" @click="act('indicator_review', { choice:'endorse', revision:view.revision, explanation })">Confirm suggested statement</button>
          <form class="sra-form" @submit.prevent="act('indicator_review', { choice:'select', statement_id:statement, revision:view.revision, explanation })">
            <SelectField v-model="statement" label="Your own statement selection" :options="levels.map((s) => ({value:s.id, label:`CRL ${s.level} · ${s.label}`}))" :disabled="working" />
            <div class="field"><label for="indicator-review-explanation">Why does this fit, or why do you disagree? (optional)</label><textarea id="indicator-review-explanation" v-model="explanation" class="input" maxlength="600" autocomplete="off" :disabled="working" /></div>
            <button class="btn secondary" :disabled="working || !statement">Record my selected statement</button>
          </form>
          <div class="row"><button class="btn secondary" :disabled="working" @click="act('indicator_review', { choice:'unsure', revision:view.revision, explanation })">Remain unsure about my level</button><button class="btn secondary" :disabled="working" @click="act('indicator_review', { choice:'decline', revision:view.revision, explanation })">Decline to give a level</button></div>
        </section>
        <details v-if="row.events.some((e) => e.active)" class="sra-disclosure"><summary>Indicator answers, barriers and corrections</summary>
          <section v-for="item in row.events.filter((e) => e.active)" :key="item.id" class="sra-exposure"><p class="sra-whitespace">{{ item.text || item.reading.meaning }}</p><p>{{ item.reading.meaning }}</p><p class="t-small muted">{{ item.information_context }} · Confirmed self-report</p>
            <ul class="bullets"><li v-for="(observation, index) in item.reading.observations" :key="index">“{{ observation.quote }}”<p>{{ observation.review_description }}</p><p v-for="ambiguity in observation.ambiguities" :key="ambiguity">Unresolved: {{ ambiguity }}</p></li></ul>
            <div v-if="item.origin === 'indicator_interview' && allowed('indicator_edit')" class="row"><button class="btn secondary sm" :disabled="working" @click="act('indicator_edit', {event_id:item.id,mode:'answer'})">Edit indicator answer</button><button class="btn secondary sm" :disabled="working" @click="act('indicator_edit', {event_id:item.id,mode:'interpretation'})">Review indicator interpretation</button></div>
          </section>
        </details>
      </template>
      <details class="sra-disclosure" data-testid="indicator-coverage"><summary>Indicator coverage and results</summary>
        <p>Unassessed indicators have no result. Changes after correction show assessment refinement, not demonstrated personal development.</p>
        <ul class="bullets"><li v-for="item in view.coverage" :key="item.indicator_id">{{ item.name }}: {{ labels[item.status] || item.status }}<span v-if="item.participant?.statement"> · Your selection: CRL {{ item.participant.statement.level }}</span><button v-if="item.selected && item.indicator_id !== row?.indicator_id && allowed('indicator_next')" class="btn secondary sm" :disabled="working" @click="act('indicator_next', {indicator_id:item.indicator_id})">Continue {{ item.name }}</button></li></ul>
      </details>
    </template>
  </section>
</template>

<style scoped>
/* Indicator review follows the existing single-column interview layout. */
.sra-indicator-option { display: flex; align-items: start; gap: .5rem; margin: .65rem 0; overflow-wrap: anywhere; }
.sra-indicator-option input { flex: 0 0 auto; margin-top: .3rem; }
fieldset { min-width: 0; padding: .75rem; border: 1px solid var(--line, #ddd); }
</style>
