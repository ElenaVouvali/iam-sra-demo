<script setup>
import { computed, reactive, ref, watch } from 'vue'
import SelectField from './SelectField.vue'
const props = defineProps({ view:Object, allowed:Function, working:Boolean, answers:Array, returnedText:String, onboarding:Object })
const emit = defineEmits(['action'])
const profiles = [{value:'citizen',label:'Myself—as a citizen or resident'},{value:'organisational',label:'An organisation or team'},{value:'technical',label:'A technology or system I work with'}]
const setup = reactive({ profile:'',discussion_choice:'general',use_case:'',city:'other',area:'',stakeholder_role:'withheld',discussion_status:'proposal',organisation_or_unit:'',responsibilities:'',technical_object:'',object_version:'',intended_environment:'',component_scope:'unsure',likert_enabled:false,materials_or_service:'',use_case_purpose:'',origin_destination_types_or_unknown:'',significant_unknowns:'',scenario_id:null })
const scope = reactive({ availability:'ready_to_discuss',organisation_or_unit:'',responsibilities:'',technical_object:'',object_version:'',intended_environment:'',component_scope:'unsure' })
const contextEditing=ref(false), linked=ref([]), caseId=ref('')
const selected=ref([]), reuse=reactive({}), answer=ref(''), feedback=ref(''), statement=ref(''), explanation=ref(''), scopeOpen=ref(false)
const row=computed(()=>props.view?.current)
const levels=computed(()=>row.value?.scale || [])
// Presentation labels only. Source names, questions and scoring remain unchanged.
const topicNames=['Local transport planning','Places and infrastructure','Energy and emissions','Costs and funding','Access to healthcare deliveries','Traffic and connections','Noise','Visual impact','Feeling safe and protecting privacy','Safety and security','Wind and landing areas','Sharing airspace','Who benefits and who is affected','Awareness and trust','Learning and skills']
const topicNumber=computed(()=>props.view?.coverage?.findIndex((i)=>i.indicator_id===row.value?.indicator_id)+1)
const topicName=computed(()=>topicNames[topicNumber.value-1] || row.value?.name)
const completedCount=computed(()=>props.view?.coverage?.filter((i)=>i.participant).length || 0)
const nextTopic=computed(()=>props.view?.coverage?.find((i,index)=>index>=topicNumber.value && i.selected && !i.participant))
const profileLabel=computed(()=>profiles.find((p)=>p.value===props.view?.profile)?.label || 'Profile assessment')
const sourceScaleVisible=computed(()=>row.value?.information?.some((i)=>i.kind==='scale'))
watch(()=>setup.discussion_choice,()=>{if(setup.discussion_choice==='service' && !['proposal','pilot','operational','unsure'].includes(setup.discussion_status))setup.discussion_status='proposal'})
const labels={not_assessed:'Not assessed',suggested:'Awaiting your review',insufficient_evidence:'Tool abstained',completed:'Self-assessment recorded',participant_unsure:'Participant unsure',respondent_unsure:'Unsure about the question',declined:'Declined',skipped:'Skipped',outside_role:'Outside role',no_technical_object_identified:'No relevant technical object',not_applicable_explained:'Not applicable',superseded:'Scope revised'}
watch(()=>props.view?.revision,()=>{answer.value='';feedback.value='';statement.value='';explanation.value='';if(props.returnedText && row.value?.state==='collecting')answer.value=props.returnedText})
watch(()=>[row.value?.indicator_id, row.value?.state==='scope'],()=>{
 if(row.value) for(const key of Object.keys(scope)) scope[key]=row.value.scope[key] || (key==='availability'?'ready_to_discuss':key==='component_scope'?'unsure':'')
 scopeOpen.value=row.value?.state==='scope'
},{immediate:true})
function act(name,data={}) {
 answer.value='';feedback.value='';explanation.value=''
 const free=['use_case','area','organisation_or_unit','responsibilities','technical_object','object_version','intended_environment','materials_or_service','use_case_purpose','origin_destination_types_or_unknown','significant_unknowns']
 if(['start_assessment','select_indicators'].includes(name))for(const key of free)setup[key]=''
 if(name==='indicator_scope')for(const key of ['organisation_or_unit','responsibilities','technical_object','object_version','intended_environment'])scope[key]=''
 emit('action',name,data)
}
function goBack(){
 if(contextEditing.value){contextEditing.value=false;return}
 if(!viewHasPreviousStep()){openContext();return}
 act('indicator_back')
}
function viewHasPreviousStep(){
 return props.view.report_finished || props.view.navigation_back_available || (row.value && (row.value.pending || row.value.events?.some((e)=>e.active) || row.value.state==='complete'))
}
function openContext(){
 for(const key of Object.keys(setup))if(props.view.scope?.[key]!==undefined)setup[key]=props.view.scope[key]
 setup.profile=props.view.profile
 setup.city=props.view.scope?.respondent_context?.city || 'other'
 setup.stakeholder_role=props.view.scope?.respondent_context?.stakeholder_category || 'withheld'
 setup.scenario_id=props.view.scope?.scenario_id || null
 setup.discussion_choice=props.view.scope?.discussion_choice || (props.view.scope?.context==='illustrative_proposal'?'example':'service')
 for(const key of ['materials_or_service','use_case_purpose','origin_destination_types_or_unknown','significant_unknowns'])setup[key]=props.view.scope?.use_case_card?.[key] || ''
 contextEditing.value=true
}
const chosenExample=computed(()=>props.view?.illustrative_options?.find((s)=>s.id===setup.scenario_id))
const setupReady=computed(()=>setup.profile && setup.city && (setup.discussion_choice==='general' || (setup.discussion_choice==='service' && setup.use_case.trim()) || (setup.discussion_choice==='example' && setup.scenario_id)))
function start(){
 if(!setupReady.value)return
 const data={...setup,discussion_status:setup.discussion_choice==='general'?'general':setup.discussion_choice==='example'?'illustrative':setup.discussion_status,
  use_case:setup.discussion_choice==='service'?setup.use_case:'',scenario_id:setup.discussion_choice==='example'?setup.scenario_id:null}
 // Retain existing detail on an unchanged scope; do not carry it into a different discussion.
 const previousChoice=props.view.scope?.discussion_choice || (props.view.scope?.context==='illustrative_proposal'?'example':'service')
 if(!contextEditing.value || previousChoice!==setup.discussion_choice)for(const key of ['materials_or_service','use_case_purpose','origin_destination_types_or_unknown','significant_unknowns'])data[key]=''
 if(props.view.entry_possible)act('start_assessment',data)
 else{
  const {profile,use_case,area,discussion_choice,discussion_status,organisation_or_unit,responsibilities,technical_object,object_version,intended_environment,component_scope,likert_enabled,scenario_id}=data
  act('select_indicators',{profile,use_case,area,discussion_choice,discussion_status,organisation_or_unit,responsibilities,technical_object,object_version,intended_environment,component_scope,likert_enabled,scenario_id,indicator_ids:props.view.selected_indicator_ids,
   context:discussion_status==='illustrative'?'illustrative_proposal':['pilot','operational'].includes(discussion_status)?'actual_experience':'general_understanding',
   use_case_fields:Object.fromEntries(['materials_or_service','use_case_purpose','origin_destination_types_or_unknown','significant_unknowns'].map((key)=>[key,data[key]]))})
 }
 contextEditing.value=false
}
function begin(){act('select_indicators',{profile:setup.profile || props.view.profile,indicator_ids:[...selected.value],context:props.view.scope?.context || 'general_understanding',use_case:props.view.scope?.use_case || setup.use_case,reuse_answers:Object.fromEntries(selected.value.map((id)=>[id,reuse[id]||[]]))})}
const bankOptions=(name)=>Object.entries(props.onboarding?.[name] || {}).map(([value,label])=>({value,label}))
</script>

<template>
<section class="sra-results" data-testid="indicator-assessment">
 <button type="button" class="btn secondary sm" :disabled="working || view?.entry_possible" @click="goBack">Back</button>
 <h3 v-if="!view?.entry_possible && !row" class="t-section">Choose what to discuss</h3>
 <p v-if="!view?.available" role="status">{{ view?.notice }}</p>
 <template v-else>

  <form v-if="view.entry_possible || contextEditing" class="sra-form" data-testid="assessment-onboarding" @submit.prevent="start">
   <SelectField v-model="setup.profile" label="Who are you answering for?" :options="profiles" :disabled="working" />
   <SelectField v-model="setup.discussion_choice" label="What would you like to discuss?" :options="[{value:'general',label:'Healthcare drones in general'},{value:'service',label:'A particular service I know about'},{value:'example',label:'An example provided by the tool'}]" :disabled="working" />
   <p>You do not need previous experience to take part.</p>
   <template v-if="setup.discussion_choice==='service'">
    <label for="assessment-use-case">Briefly describe the service</label><p class="t-small muted" id="assessment-service-help">It may be an idea, a planned service, a trial or an existing service. Use general descriptions rather than identifying details.</p><input id="assessment-use-case" v-model="setup.use_case" class="input" maxlength="240" :disabled="working" autocomplete="off" aria-describedby="assessment-service-help" />
    <SelectField v-model="setup.discussion_status" label="What stage is the service at?" :options="[{value:'proposal',label:'Being considered or planned'},{value:'pilot',label:'Being tested'},{value:'operational',label:'Already operating'},{value:'unsure',label:'I’m not sure'}]" :disabled="working" />
    <p class="t-small muted">This records your account, not independently verified service information.</p>
   </template>
   <template v-if="setup.discussion_choice==='example'">
    <SelectField v-model="setup.scenario_id" label="Choose an illustrative example" :options="(view.illustrative_options || []).map((s)=>({value:s.id,label:s.title}))" :disabled="working" />
    <section v-if="chosenExample" data-testid="onboarding-example"><p><b>Illustrative example</b> · {{ chosenExample.source_status || 'Source-described illustration' }} · {{ chosenExample.source_verification || 'Source-described illustration' }}</p><p>{{ chosenExample.text }}</p><p>Unknown: {{ chosenExample.unknowns?.join('; ') }}</p><p>This does not establish a service operating in your city or your prior experience.</p></section>
   </template>
   <SelectField v-model="setup.city" label="Which city or region is this about?" :options="bankOptions('cities')" :disabled="working || contextEditing" />
   <p v-if="contextEditing" class="t-small muted">City and role come from your initial setup. Start a new session to change them.</p>

   <p v-if="setup.profile==='organisational'" class="t-small muted">You can discuss preparedness for a future service. We’ll ask about your organisation or team and relevant responsibilities when needed.</p>
   <p v-if="setup.profile==='technical'" class="t-small muted">A technology may be a concept or prototype. We’ll ask about the relevant object and environment when needed. You can say if these are unknown.</p>
   <details v-if="setup.profile==='citizen'" class="sra-disclosure"><summary>Optional self-report questions</summary><label><input v-model="setup.likert_enabled" type="checkbox" /> Include optional agreement questions. These answers do not become readiness levels.</label></details>
   <button class="btn accent" :disabled="working || !setupReady">{{ view.entry_possible ? 'Start assessment' : 'Confirm changed assessment scope' }}</button><button v-if="contextEditing" type="button" class="btn secondary" @click="contextEditing=false">Keep current scope</button>
  </form>
  <template v-else>
   <details v-if="!view.direct_entry" class="sra-disclosure" :open="!row"><summary>Choose indicators and response capacity</summary>
    <form class="sra-form" @submit.prevent="begin"><SelectField v-model="setup.profile" label="Assessment response capacity" :options="profiles" :disabled="working" />
     <label v-for="item in view.coverage" :key="item.indicator_id" class="sra-indicator-option"><input v-model="selected" type="checkbox" :value="item.indicator_id" />{{ item.name }}</label>
     <label v-if="!view.scope">Use case or context<input v-model="setup.use_case" class="input" maxlength="240" /></label>
     <details v-if="answers?.length" class="sra-disclosure"><summary>Use relevant confirmed answers instead of repeating the opening</summary><p>Explicitly link only answers equivalent to the opening for this indicator and scope. Their content is still assessed; a topic label does not establish a level.</p><fieldset v-for="id in selected" :key="id"><legend>{{ view.coverage.find((i)=>i.indicator_id===id)?.name }}</legend><label v-for="item in answers" :key="item.id" class="sra-indicator-option"><input :checked="(reuse[id]||[]).includes(item.id)" type="checkbox" @change="reuse[id]=$event.target.checked?[...(reuse[id]||[]),item.id]:(reuse[id]||[]).filter((v)=>v!==item.id)" />{{ item.text }}</label></fieldset></details>
     <button class="btn accent" :disabled="working || !allowed('select_indicators') || !selected.length">Begin selected indicators</button>
    </form>
   </details>
   <template v-if="row && !view.report_finished">
    <p class="t-small muted" data-testid="topic-progress">Topic {{ topicNumber }} of {{ view.coverage.length }} available · {{ completedCount }} reviewed</p>
    <h3 class="t-section">{{ topicName }}</h3>
    <p v-if="view.profile==='citizen' && row.state==='collecting'" class="t-small muted">No specialist knowledge is needed. It’s fine to say you don’t know.</p>
    <section v-if="row.scope.illustrative_case" data-testid="indicator-case"><h4 class="t-card">{{ row.scope.illustrative_case.title }}</h4><p>{{ row.scope.illustrative_case.source_status || 'Source illustration' }} · {{ row.scope.illustrative_case.source_verification || 'Source-described illustration' }}</p><details class="sra-disclosure" :open="!row.information.some((e)=>e.kind==='case' && e.already_presented)"><summary>Case text, unknowns and sources</summary><p>{{ row.scope.illustrative_case.text }}</p><p>Unknown: {{ row.scope.illustrative_case.unknowns.join('; ') }}</p><p v-for="r in row.scope.illustrative_case.source_refs || []" :key="r.source_id">{{ r.local_document || r.package_document }} · {{ r.locator }} · {{ r.verification_status }}</p><p>Source illustration, not an actual experience or VR/AR evaluation. Hypothetical reasoning does not establish operational capability or technical validation.</p></details></section>

    <button v-if="allowed('indicator_scope') && view.profile!=='citizen'" class="btn secondary sm" :disabled="working" @click="scopeOpen=!scopeOpen">{{ scopeOpen ? 'Hide scope fields' : 'Review or edit indicator scope' }}</button>
    <form v-if="scopeOpen" class="sra-form" data-testid="indicator-scope" @submit.prevent="act('indicator_scope',{...scope})">
     <p>Confirm responsibility or object for this indicator. Changing it invalidates dependent judgments and evidence.</p>
     <SelectField v-model="scope.availability" label="Scope availability" :options="[{value:'ready_to_discuss',label:'Relevant and ready to discuss'},...(view.profile==='organisational'?[{value:'outside_role',label:'Outside my organisation’s responsibilities'}]:[]),...(view.profile==='technical'?[{value:'no_technical_object_identified',label:'No relevant technical object identified'}]:[]),{value:'not_applicable_explained',label:'Not applicable in this scope'}]" :disabled="working" />
     <template v-if="view.profile==='organisational'"><label for="indicator-unit">Broad unit for this indicator</label><input id="indicator-unit" v-model="scope.organisation_or_unit" class="input" maxlength="240" /><label for="indicator-responsibilities">Responsibilities for this indicator</label><textarea id="indicator-responsibilities" v-model="scope.responsibilities" class="input" maxlength="500" /></template>
     <template v-if="view.profile==='technical'"><label for="indicator-object">Technical object for this indicator</label><input id="indicator-object" v-model="scope.technical_object" class="input" maxlength="240" /><label for="indicator-version">Object version (or unknown)</label><input id="indicator-version" v-model="scope.object_version" class="input" maxlength="100" /><label for="indicator-environment">Intended environment (or unknown)</label><input id="indicator-environment" v-model="scope.intended_environment" class="input" maxlength="240" /><SelectField v-model="scope.component_scope" label="Object scope" :options="['component','system','model','tool','concept','unsure']" /></template>
     <button class="btn accent" :disabled="working">Confirm indicator scope</button>
    </form>
    <button v-if="allowed('indicator_information')" class="btn secondary sm" :disabled="working" @click="act('indicator_information',{kind:'definition'})">What is this topic about?</button>
    <p v-for="item in row.information.filter((i)=>i.kind==='definition')" :key="item.sequence" class="sra-whitespace">{{ item.text }} (Supplied source information)</p>
    <details v-if="allowed('indicator_link')" class="sra-disclosure"><summary>Reuse equivalent confirmed answers for this indicator</summary><p>Only answers from the same profile, object and context are offered. Confirm that the selected words address this opening; the matching step still judges the criterion.</p><label v-for="item in view.reusable_answers" :key="item.id" class="sra-indicator-option"><input v-model="linked" type="checkbox" :value="item.id" :disabled="linked.length>=3 && !linked.includes(item.id)" />{{ item.text }}</label><button class="btn secondary" :disabled="working || !linked.length" @click="act('indicator_link',{answer_ids:[...linked]})">Use selected answers for this opening</button></details>
    <div v-if="row.state==='collecting' && row.question" class="sra-form">
     <p class="t-card" data-testid="indicator-question">{{ row.question.question_text }}</p>
     <form class="sra-form" @submit.prevent="act('indicator_answer',{text:answer,control:'answer'})"><SelectField v-if="row.question.format==='likert'" v-model="answer" label="Optional self-report category" :options="Object.entries(row.question.options).map(([value,label])=>({value,label}))" :disabled="working" /><template v-else><label for="indicator-answer">Your answer</label><textarea id="indicator-answer" v-model="answer" class="input sra-textarea" maxlength="2000" autocomplete="off" :disabled="working" /></template><button class="btn accent" :disabled="working || !answer.trim()">Continue</button></form>
     <div class="row"><button v-for="control in ['skip','unsure']" :key="control" class="btn secondary sm" :disabled="working" @click="act('indicator_answer',{text:'',control})">{{ {skip:'Skip',unsure:'I’m not sure',decline:'Prefer not to answer'}[control] }}</button></div><details class="sra-disclosure"><summary>More answer options</summary><button class="btn secondary sm" :disabled="working" @click="act('indicator_answer',{text:'',control:'decline'})">Prefer not to answer</button><button class="btn secondary sm" :disabled="working" @click="act('indicator_finish')">Finish questions on this topic</button></details>
    </div>
    <details class="sra-disclosure" data-testid="topic-help"><summary>About this topic and optional examples</summary>
     <p>{{ row.name }} · {{ view.scale_name }}</p><p>{{ row.scope_note }}</p>
     <p v-if="row.question" class="t-small muted">{{ row.question.wording_status }} · {{ row.question.questionnaire_version }}. Up to {{ row.question_budget }} open questions.</p>
    <details class="sra-disclosure"><summary>Optional illustrative case for this indicator</summary><p>Your confirmed use case stays primary. A case is optional context, not evidence of your activity or a real organisation/system. Changing it deliberately invalidates this indicator’s dependent answers and judgments.</p><SelectField v-model="caseId" label="Optional case" :options="view.illustrative_options.map((c)=>({value:c.id,label:c.title}))" :disabled="working" /><p v-if="caseId">{{ view.illustrative_options.find((c)=>c.id===caseId)?.source_status }} · {{ view.illustrative_options.find((c)=>c.id===caseId)?.source_verification }}</p><button class="btn secondary" :disabled="working || !caseId || !allowed('indicator_case')" @click="act('indicator_case',{scenario_id:caseId})">Use optional case for this indicator</button><button class="btn secondary" :disabled="working || !row.scope.illustrative_case || !allowed('indicator_case')" @click="act('indicator_case',{scenario_id:null})">Continue without an optional case</button></details>
    </details>
    <div v-if="row.pending" class="sra-form" data-testid="indicator-interpretation"><h4 class="t-card">Did we understand you correctly?</h4><p>{{ row.pending.reading.meaning }}</p><details class="sra-disclosure"><summary>Interpretation details</summary><p>Your original answer is kept; the interpretation can be wrong.</p><ul class="bullets"><li v-for="(o,index) in row.pending.reading.observations" :key="index">“{{ o.quote }}”<p>{{ o.review_description }}</p><p v-for="a in o.ambiguities" :key="a">Unresolved: {{ a }}</p></li></ul><p v-if="!row.pending.reading.observations.length">No observations were extracted. Your full answer is retained for matching; this is not evidence of inability.</p><p v-if="row.pending.reading.follow_up_reason">Possible follow-up gap: {{ row.pending.reading.follow_up_reason }}</p>
     </details><div v-if="row.pending.correction_offer" class="sra-notice">{{ row.pending.correction_offer.notice }} New facts are not yet assessment evidence.</div>
     <button class="btn accent" :disabled="working" @click="act('indicator_confirm')">{{ row.pending.correction_offer ? 'Confirm original answer only' : 'Yes, that’s what I meant' }}</button>
     <details class="sra-disclosure"><summary>Correct the indicator interpretation or add information</summary><form class="sra-form" @submit.prevent="act('indicator_correct',{text:feedback})"><label for="indicator-feedback">What should we understand differently?</label><textarea id="indicator-feedback" v-model="feedback" class="input sra-textarea" maxlength="1500" :disabled="working" /><button class="btn secondary" :disabled="working || !feedback.trim()">Apply indicator correction</button><button type="button" class="btn secondary" :disabled="working || !feedback.trim()" @click="act('indicator_add_information',{text:feedback})">Add this information to my answer</button></form><button v-if="row.pending.correction_offer" class="btn secondary" :disabled="working" @click="act('indicator_add_information',{text:row.pending.correction_offer.text})">Use offered addition and check again</button></details><details class="sra-disclosure"><summary>Original indicator answer</summary><p>{{ row.pending.text }}</p></details>
    </div>
    <p v-if="row.suggestion_error" role="status">{{ row.suggestion_error.notice }}</p>
    <p v-if="row.state==='ready' && !row.tool">Next: request a draft suggestion, or choose your own statement. Unresolved evidence can lead to abstention.</p><button v-if="allowed('indicator_suggest')" class="btn accent" :disabled="working" @click="act('indicator_suggest')">Request draft indicator suggestion</button>
    <section v-if="row.participant" data-testid="participant-indicator-result"><h4 class="t-card">Your individual self-assessment</h4><template v-if="row.participant.statement"><p><b>{{ view.scale_name }} {{ row.participant.statement.level }} · {{ row.participant.statement.label }}</b></p><p>{{ row.participant.statement.statement }}</p></template><p v-else>{{ row.participant.status==='unsure'?'You remain unsure. No level selected.':'You declined to give a level.' }}</p><p>{{ row.participant.explanation }}</p></section>
    <details v-if="row.tool" class="sra-disclosure" open data-testid="tool-indicator-result"><summary>Provisional tool suggestion and evidence</summary><p>{{ row.tool.statement ? `Suggested ${view.scale_name} ${row.tool.statement.level}` : 'The tool abstained: no level suggested.' }}</p><p v-if="row.tool.statement">{{ row.tool.statement.statement }}</p><p>{{ row.tool.explanation }}</p><p v-if="row.tool.alternative_distinction">Alternative considered: {{ row.tool.alternative_statement_id }}. {{ row.tool.alternative_distinction }}</p><ul class="bullets"><li v-for="gap in row.tool.gaps" :key="gap">{{ gap }}</li></ul><details class="sra-disclosure"><summary>Statement matches and supporting excerpts</summary><section v-for="m in row.tool.assessments" :key="m.statement_id"><p>{{ m.statement_id }} · {{ m.status }}</p><p v-for="cite in m.evidence" :key="cite.evidence_id+cite.quote">“{{ cite.quote }}” ({{ cite.evidence_id }})</p></section></details></details>
    <section v-if="allowed('indicator_review')" class="sra-form" data-testid="indicator-review"><h4 class="t-card">Review your level</h4><p>You may disagree or remain unsure. A participant choice is separate from the tool suggestion and is not independent verification.</p><button class="btn secondary" :disabled="working" @click="act('indicator_information',{kind:'scale'})">Read all nine source statements</button><details v-if="sourceScaleVisible" class="sra-disclosure" open><summary>Exact source scale and criterion</summary><p>{{ row.criterion.text }}</p><ol class="bullets"><li v-for="level in levels" :key="level.id"><b>{{ view.scale_name }} {{ level.level }}</b><p>{{ level.statement }}</p><p class="t-small muted">{{ level.source.sheet }}!{{ level.source.cell }} · shared row {{ level.row_review_status }}</p></li></ol><p>{{ view.bank.source.document }} · {{ view.questionnaire.questionnaire_version }}. Draft, not approved.</p></details>
     <template v-if="!['outside_role','no_technical_object_identified','not_applicable_explained'].includes(row.disposition)"><button v-if="row.tool?.statement" class="btn accent" :disabled="working" @click="act('indicator_review',{choice:'endorse',revision:view.revision,explanation})">Confirm suggested statement</button><form class="sra-form" @submit.prevent="act('indicator_review',{choice:'select',statement_id:statement,revision:view.revision,explanation})"><SelectField v-model="statement" label="Your own statement selection" :options="levels.map((s)=>({value:s.id,label:`${view.scale_name} ${s.level} · ${s.label}`}))" :disabled="working" /><label for="indicator-review-explanation">Why does this fit, or why do you disagree? (optional)</label><textarea id="indicator-review-explanation" v-model="explanation" class="input" maxlength="600" /><button class="btn secondary" :disabled="working || !statement">Record my selected statement</button></form></template><div class="row"><button class="btn secondary" :disabled="working" @click="act('indicator_review',{choice:'unsure',revision:view.revision,explanation})">Remain unsure about my level</button><button class="btn secondary" :disabled="working" @click="act('indicator_review',{choice:'decline',revision:view.revision,explanation})">Decline to give a level</button></div>
    </section>
    <details v-if="row.events.some((e)=>e.active)" class="sra-disclosure"><summary>Indicator answers, barriers and corrections</summary><section v-for="item in row.events.filter((e)=>e.active)" :key="item.id"><p>{{ item.text }}</p><p>{{ item.reading.meaning }}</p><p class="t-small muted">{{ item.information_context }} · {{ item.interpretation_status }} · Confirmed self-report</p><div v-if="item.origin==='indicator_interview' && allowed('indicator_edit')" class="row"><button class="btn secondary sm" :disabled="working" @click="act('indicator_edit',{event_id:item.id,mode:'answer'})">Edit indicator answer</button><button class="btn secondary sm" :disabled="working" @click="act('indicator_edit',{event_id:item.id,mode:'interpretation'})">Review indicator interpretation</button></div></section></details>
   </template>
   <section v-if="view.report_finished" data-testid="individual-profile-report"><h4 class="t-card">Your individual indicator profile</h4><p>{{ profileLabel }} · {{ view.scope?.use_case }} · Partial coverage is explicit below. There is no overall numerical score.</p></section>
   <details v-if="view.scope" class="sra-disclosure"><summary>Your context</summary>   <h4 class="t-card">{{ profileLabel }}</h4><button v-if="view.direct_entry && allowed('select_indicators')" class="btn secondary sm" :disabled="working" @click="openContext">Review or change overall assessment scope</button>
   <p v-if="view.scope">{{ view.scope.use_case }} · {{ view.scope.area }}. {{ view.scope.discussion_choice==='general' ? 'General discussion: this label comes from your choice, not a described or verified service.' : view.scope.context==='illustrative_proposal' ? 'Illustrative context, not evidence of prior experience.' : 'Context and service stage are respondent-reported, not independently verified.' }}</p>
   </details>
   <details class="sra-disclosure" :open="view.report_finished" data-testid="indicator-coverage"><summary>{{ view.report_finished ? 'Your results by topic' : 'Choose or review topics' }}</summary><p>You can choose another topic or stop with a partial assessment. Returning to a topic keeps your answers.</p><details v-for="section in view.sections" :key="section.id" class="sra-disclosure" open><summary>{{ section.id.replace('-',' ') }}</summary><ul class="bullets"><li v-for="item in view.coverage.filter((i)=>section.indicator_ids.includes(i.indicator_id))" :key="item.indicator_id">{{ item.name }}: {{ labels[item.status] || item.status }}<p v-if="item.scope && view.profile==='technical'">Object: {{ item.scope.technical_object || 'Not identified' }} · {{ item.scope.object_version || 'Version unknown' }} · {{ item.scope.component_scope }} · {{ item.scope.intended_environment || 'Environment unknown' }}</p><p v-if="item.scope && view.profile==='organisational'">{{ item.scope.organisation_or_unit }} · {{ item.scope.responsibilities }}</p><p v-if="item.suggestion_error">{{ item.suggestion_error.notice }}</p><span v-if="item.answered"> · Answered</span><template v-if="item.participant?.statement"><p><b>Your selection: {{ view.scale_name }} {{ item.participant.statement.level }}</b> {{ item.participant.statement.statement }}</p></template><p v-if="item.tool">Tool: {{ item.tool.statement ? `${view.scale_name} ${item.tool.statement.level}` : 'Abstained' }}. {{ item.tool.explanation }}</p><ul v-if="item.tool?.gaps?.length" class="bullets"><li v-for="gap in item.tool.gaps" :key="gap">{{ gap }}</li></ul><p v-if="item.unconfirmed">An interpretation remains unchecked; it has not been used as evidence.</p><button v-if="item.selected && allowed('indicator_next')" class="btn secondary sm" :disabled="working" @click="act('indicator_next',{indicator_id:item.indicator_id})">{{ item.participant || item.tool ? 'Return to' : 'Continue' }} {{ item.name }}</button></li></ul></details></details>
   <button v-if="nextTopic && row?.participant && !view.report_finished" class="btn accent" :disabled="working || !allowed('indicator_next')" @click="act('indicator_next',{indicator_id:nextTopic.indicator_id})">Next topic</button>
   <button v-if="allowed('complete_assessment') && !view.report_finished" class="btn secondary" :disabled="working" @click="act('complete_assessment')">Finish for now</button>
  </template>
 </template>
</section>
</template>
<style scoped>
.sra-results p,.sra-results li{overflow-wrap:anywhere}.sra-indicator-option{display:flex;align-items:start;gap:.5rem;margin:.65rem 0;overflow-wrap:anywhere}.sra-indicator-option input{flex:0 0 auto;margin-top:.3rem}fieldset{min-width:0;padding:.75rem;border:1px solid var(--line,#ddd)}
</style>
