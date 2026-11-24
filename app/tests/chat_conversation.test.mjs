/** Vue interaction checks using an in-memory renderer; no browser, sockets or GPU. */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import { compileScript, parse } from '@vue/compiler-sfc'
import * as Vue from 'vue'
globalThis.Document = class Document {}
globalThis.ShadowRoot = class ShadowRoot {}
globalThis.document = Object.assign(new Document(), { activeElement: null })
const { descriptor } = parse(readFileSync(new URL('../src/components/ChatConversation.vue', import.meta.url), 'utf8'))
const compiled = compileScript(descriptor, { id: 'chat-ui-test', inlineTemplate: true,
 templateOptions: { compilerOptions: { hoistStatic: false } } }).content
const intro = 'Thank you for taking part.\n\nYour experiences matter. You can skip, stop or withdraw.\n\nMessages are screened; progress is temporary.'
const roles = ['Citizen', 'Organisation or institution', 'Technology expert or researcher'].map((label, i) => ({ value: 'ABC'[i], label }))
function snapshot(options = roles, resumed = false) {
 return { id: 'synthetic-session', preview: null, chat: { stage: 'conversation', response_options: options,
  messages: [{ id: 'm1', role: 'assistant', act: 'introduction', text: intro },
   ...(resumed ? [{ id: 'm2', role: 'respondent', text: 'An earlier answer.' }] : []),
   { id: 'm3', role: 'assistant', act: 'question', text: 'Which point of view would you like to use?' }], summary: [], completion: {} } }
}
function node(type, text = '') {
 return { type, text, children: [], props: {}, listeners: {}, parent: null, value: '', tagName: type.toUpperCase(),
  getRootNode() { return globalThis.document }, focus() { this.focused = true }, addEventListener(name, fn) { this.listeners[name] = fn }, removeEventListener(name) { delete this.listeners[name] },
  showModal() { this.open = true }, close() { this.open = false } }
}
async function mount(initial = snapshot()) {
 const calls = [], session = Vue.shallowRef(initial)
 const flow = { session, boot: { state: Vue.ref('ready'), error: Vue.ref(null) }, operation: { error: Vue.ref(null) },
  working: Vue.ref(false), ended: Vue.ref(false), inferenceStatus: Vue.ref(null), initialize: async () => {},
  reset: async () => { calls.push({ action: 'reset' }); session.value = snapshot(); return true },
  act: async (action, data) => {
   calls.push({ action, data })
   if (action === 'chat_message') session.value = { ...session.value, chat: { ...session.value.chat, response_options: [],
    messages: [...session.value.chat.messages, { id: 'm4', role: 'respondent', text: data.text },
     { id: 'm5', role: 'assistant', act: 'question', text: 'Which EU city or urban area?' }] } }
   return true
  } }
 const context = vm.createContext({ location: { search: '' }, URLSearchParams })
 const component = new vm.SourceTextModule(compiled, { context })
 const vueModule = new vm.SyntheticModule(Object.keys(Vue), function () {
  for (const [key, value] of Object.entries(Vue)) this.setExport(key, value)
 }, { context })
 const assessment = new vm.SyntheticModule(['useAssessment'], function () { this.setExport('useAssessment', () => flow) }, { context })
 await component.link((name) => name === 'vue' ? vueModule : assessment); await component.evaluate()
 const renderer = Vue.createRenderer({
  createElement: (tag) => node(tag), createText: (text) => node('#text', text), createComment: (text) => node('#comment', text),
  setText: (n, text) => { n.text = text }, setElementText: (n, text) => { n.text = text; n.children = [] },
  parentNode: (n) => n.parent, nextSibling: (n) => n.parent?.children[n.parent.children.indexOf(n) + 1] || null,
  patchProp: (n, key, before, value) => { n.props[key] = value; if (key === 'value') n.value = value },
  insert: (n, parent, anchor = null) => {
   if (n.parent) n.parent.children.splice(n.parent.children.indexOf(n), 1)
   n.parent = parent; const index = anchor ? parent.children.indexOf(anchor) : -1
   if (index < 0) parent.children.push(n); else parent.children.splice(index, 0, n)
  }, remove: (n) => { if (n.parent) n.parent.children.splice(n.parent.children.indexOf(n), 1); n.parent = null },
 })
 const root = node('root'), app = renderer.createApp(component.namespace.default)
 app.component('RouterLink', { props: ['to'], setup: (props, { slots }) => () => Vue.h('a', { href: props.to }, slots.default?.()) })
 app.mount(root); await Vue.nextTick()
 const all = () => { const out = []; const visit = (n) => { out.push(n); n.children.forEach(visit) }; visit(root); return out }
 const text = (n = root) => n.text + n.children.map((child) => text(child)).join(' ')
 const button = (label) => all().find((n) => n.type === 'button' && text(n).includes(label))
 const click = async (n) => { assert.ok(n); await n.props.onClick(); await Vue.nextTick() }
 return { flow, calls, all, text, button, click, unmount: () => app.unmount() }
}
test('full introduction is separate until Continue, without submitting an answer', async () => {
 const ui = await mount()
 try {
  assert.ok(ui.text().includes(intro)); assert.ok(!ui.text().includes('Which point of view'))
  assert.equal(ui.all().filter((n) => n.type === 'input' || n.type === 'textarea').length, 0)
  await ui.click(ui.button('Continue to the conversation'))
  assert.ok(!ui.text().includes(intro)); assert.ok(ui.text().includes('Which point of view'))
  assert.equal(ui.all().filter((n) => n.props.type === 'radio').length, 3)
  assert.equal(ui.all().filter((n) => n.type === 'textarea').length, 0)
  assert.equal(ui.calls.length, 0); assert.ok(ui.all().find((n) => n.type === 'ol').focused)
 } finally { ui.unmount() }
})
test('perspective selection uses the current chat action, then restores free text', async () => {
 const ui = await mount()
 try {
  await ui.click(ui.button('Continue to the conversation')); assert.ok(ui.button('Send selected answer').props.disabled)
  ui.all().find((n) => n.props.type === 'radio' && n.props.value === 'B').props.onChange(); await Vue.nextTick()
  assert.ok(!ui.button('Send selected answer').props.disabled); await ui.click(ui.button('Send selected answer'))
  assert.equal(ui.calls[0].action, 'chat_message'); assert.equal(ui.calls[0].data.text, 'B')
  assert.equal(ui.all().filter((n) => n.type === 'textarea').length, 1)
  assert.equal(ui.all().filter((n) => n.props.type === 'radio').length, 0)
 } finally { ui.unmount() }
})
for (const [name, options] of [
 ['duration', [{ value: 'A', label: 'Around 20 minutes' }, { value: 'B', label: 'Around 35 minutes' }]],
 ['educational exit', [{ value: 'A', label: 'Explanation and continue' }, { value: 'B', label: 'Educational resource and finish' }]],
 ['FN validation', 'ABCDE'.split('').map((value) => ({ value, label: `Synthetic validation ${value}` }))],
]) test(`${name} is selectable on a resumed conversation`, async () => {
 const ui = await mount(snapshot(options, true))
 try {
  assert.ok(!ui.button('Continue to the conversation'))
  assert.equal(ui.all().filter((n) => n.props.type === 'radio').length, options.length)
  assert.equal(ui.all().filter((n) => n.type === 'textarea').length, 0)
  assert.equal(ui.button('Answer in my own words'), undefined)
  const value = options.at(-1).value
  ui.all().find((n) => n.props.type === 'radio' && n.props.value === value).props.onChange()
  await Vue.nextTick(); await ui.click(ui.button('Send selected answer')); assert.equal(ui.calls[0].data.text, value)
 } finally { ui.unmount() }
})
test('choice questions offer selection only, then restore open questions', async () => {
 const ui = await mount(snapshot(roles, true))
 try {
  assert.equal(ui.button('Answer in my own words'), undefined)
  assert.equal(ui.button('Hide text reply'), undefined)
  assert.equal(ui.all().filter((n) => n.type === 'textarea' || n.type === 'form').length, 0)
  ui.all().find((n) => n.props.type === 'radio' && n.props.value === 'A').props.onChange()
  await Vue.nextTick(); await ui.click(ui.button('Send selected answer'))
  const input = ui.all().find((n) => n.type === 'textarea')
  input.value = 'Madrid'; input.listeners.input({ target: input }); await Vue.nextTick()
  await ui.all().find((n) => n.type === 'form').props.onSubmit({ preventDefault() {} }); await Vue.nextTick()
  assert.equal(ui.calls[0].data.text, 'A')
  assert.equal(ui.calls[1].data.text, 'Madrid')
 } finally { ui.unmount() }
})
for (const [depth, command, target] of [
 ['short', 'extended conversation', 'Use extended citizen interview (~35 min)'],
 ['extended', 'keep it short', 'Use short citizen interview (~20 min)'],
]) test(`citizen ${depth} style has a working depth control until result review`, async () => {
 const initial = snapshot([], true)
 Object.assign(initial.chat, { profile: 'citizen', depth, depth_selection: { depth } })
 const ui = await mount(initial)
 try {
  await ui.click(ui.button(target))
  assert.equal(ui.calls[0].action, 'chat_message'); assert.equal(ui.calls[0].data.text, command)
  ui.flow.session.value = { ...ui.flow.session.value, chat: { ...ui.flow.session.value.chat, stage: 'review' } }
  await Vue.nextTick(); assert.equal(ui.button(target), undefined)
 } finally { ui.unmount() }
})
test('ordinary questions stay open-form and New conversation restores introduction', async () => {
 const ui = await mount(snapshot([], true))
 try {
  assert.equal(ui.all().filter((n) => n.type === 'textarea').length, 1)
  assert.equal(ui.all().filter((n) => n.props.type === 'radio').length, 0)
  await ui.click(ui.button('New conversation')); assert.ok(ui.text().includes(intro)); assert.ok(!ui.text().includes('Which point of view'))
 } finally { ui.unmount() }
})
test('a new question clears the previous selection', async () => {
 const ui = await mount(snapshot(roles, true))
 try {
  ui.all().find((n) => n.props.type === 'radio' && n.props.value === 'B').props.onChange()
  await Vue.nextTick(); await ui.click(ui.button('Send selected answer'))
  ui.flow.session.value = { ...ui.flow.session.value, chat: { ...ui.flow.session.value.chat,
   response_options: [{ value: 'A', label: 'Around 20 minutes' }, { value: 'B', label: 'Around 35 minutes' }],
   messages: [...ui.flow.session.value.chat.messages, { id: 'm6', role: 'assistant', act: 'question', text: 'How much time?' }] } }
  await Vue.nextTick()
  assert.ok(ui.all().filter((n) => n.props.type === 'radio').every((n) => !n.props.checked))
  assert.ok(ui.button('Send selected answer').props.disabled)
 } finally { ui.unmount() }
})
test('a selection cannot submit twice while an operation is running', async () => {
 const ui = await mount(snapshot(roles, true))
 try {
  ui.all().find((n) => n.props.type === 'radio' && n.props.value === 'A').props.onChange(); await Vue.nextTick()
  ui.flow.working.value = true; await Vue.nextTick()
  await ui.click(ui.button('Send selected answer'))
  assert.equal(ui.calls.length, 0)
 } finally { ui.unmount() }
})
test('welcome-screen session-clear errors remain visible', async () => {
 const ui = await mount()
 try {
  ui.flow.operation.error.value = { userMessage: 'Synthetic session-clear error' }; await Vue.nextTick()
  assert.ok(ui.text().includes('Synthetic session-clear error'))
 } finally { ui.unmount() }
})
test('profile labels and explanatory descriptions appear once, inside selectable cards', async () => {
 const initial = snapshot(roles, true)
 const guidance = 'If more than one applies, choose the perspective you prefer today.'
 initial.chat.messages.at(-1).text = 'Which perspective?\n\nA. Citizen\nA resident answering personally.\n\nB. Organisation or institution\nAn organisation representative.\n\nC. Technology expert or researcher\nSomeone developing drone technology.\n\n' + guidance
 const ui = await mount(initial)
 try {
  for (const value of ['Citizen', 'Organisation or institution', 'Technology expert or researcher',
   'A resident answering personally.', 'An organisation representative.', 'Someone developing drone technology.', guidance]) {
   assert.equal(ui.text().split(value).length - 1, 1, value)
  }
  const cards = ui.all().filter((n) => n.type === 'label' && n.props.class?.includes('answer-option'))
  assert.equal(cards.length, 3)
  assert.ok(ui.text(cards[0]).includes('A resident answering personally.'))
  assert.ok(ui.text().includes('Which perspective?'))
  ui.all().find((n) => n.props.type === 'radio' && n.props.value === 'A').props.onChange()
  await Vue.nextTick(); await ui.click(ui.button('Send selected answer'))
  // The original history remains complete once the active choice controls disappear.
  assert.equal(ui.text().split('A resident answering personally.').length - 1, 1)
 } finally { ui.unmount() }
})
for (const separator of ['. ', ' — ']) test(`lettered answers using ${separator.trim()} are not repeated in the question`, async () => {
 const options = [{ value: 'A', label: 'Short conversation' }, { value: 'B', label: 'Detailed conversation' }]
 const initial = snapshot(options, true)
 initial.chat.messages.at(-1).text = 'How much detail?\n\nA' + separator + options[0].label + '\n\nB' + separator + options[1].label + '\n\nYou may change later.'
 const ui = await mount(initial)
 try {
  for (const option of options) assert.equal(ui.text().split(option.label).length - 1, 1)
  assert.ok(ui.text().includes('How much detail?')); assert.ok(ui.text().includes('You may change later.'))
  assert.equal(ui.all().filter((n) => n.props.type === 'radio').length, 2)
 } finally { ui.unmount() }
})
test('contiguous A–E validation candidates appear only in their selectable cards', async () => {
 const options = 'ABCDE'.split('').map((value) => ({ value, label: `Unique validation choice ${value}` }))
 const initial = snapshot(options, true)
 initial.chat.messages.at(-1).text = 'Does the result fit?\n\n' + options.map((o) => `${o.value}. ${o.label}`).join('\n')
 const ui = await mount(initial)
 try {
  for (const option of options) assert.equal(ui.text().split(option.label).length - 1, 1)
  assert.ok(ui.text().includes('Does the result fit?'))
  assert.equal(ui.all().filter((n) => n.props.type === 'radio').length, 5)
 } finally { ui.unmount() }
})
test('open questions retain their original text even when it includes lettered examples', async () => {
 const initial = snapshot([], true), question = 'Compare these examples:\nA. Noise\nB. Privacy\nWhat matters to you?'
 initial.chat.messages.at(-1).text = question
 const ui = await mount(initial)
 try {
  assert.ok(ui.text().includes(question))
  assert.equal(ui.all().filter((n) => n.type === 'textarea').length, 1)
 } finally { ui.unmount() }
})
test('compact profile clarification does not repeat candidates beside the cards', async () => {
 const initial = snapshot(roles, true)
 initial.chat.messages.at(-1).text = 'Please choose your perspective: A. Citizen, B. Organisation or institution, or C. Technology expert or researcher. A profession alone does not select a perspective.'
 const ui = await mount(initial)
 try {
  for (const option of roles) assert.equal(ui.text().split(option.label).length - 1, 1)
  assert.ok(ui.text().includes('Please choose your perspective.'))
  assert.ok(ui.text().includes('A profession alone does not select a perspective.'))
 } finally { ui.unmount() }
})
