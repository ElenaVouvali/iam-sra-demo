import { readFileSync } from 'node:fs'
const CASE = JSON.parse(readFileSync(new URL('../../../eval/conversation_meeting_cases_v2.json', import.meta.url))).cases[0]
const AUTHORED_SCENARIO = JSON.parse(readFileSync(new URL('../../../configs/scenario.json', import.meta.url))).id
export const pages = ['/tools/sra-assessment', '/tools/sra-assessment/app']
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
async function select(page, label, value, root = 'body') {
  const id = await page.$$eval(`${root} label`, (els, text) => els.find((el) => el.textContent.trim().startsWith(text))?.htmlFor, label)
  if (!id) throw new Error(`Missing label: ${label}`)
  await page.select(`#${CSSescape(id)}`, value)
}
const CSSescape = (id) => id.replace(/([^a-zA-Z0-9_-])/g, '\\$1')
async function fill(page, selector, text) { await page.$eval(selector, (el) => { el.value = ''; el.dispatchEvent(new Event('input', { bubbles: true })) }); await page.type(selector, text) }
async function disclosure(page, title, root = 'body') {
  await page.$$eval(`${root} details`, (els, text) => { const el = els.find((e) => e.querySelector(':scope > summary')?.textContent.trim() === text); if (!el) throw new Error('Missing disclosure'); el.open = true }, title)
}
async function waitUntil(fn, message) {
  const end = Date.now() + 15000
  while (Date.now() < end) { if (await fn()) return; await wait(80) }
  throw new Error(message)
}
function monitor(page) {
  const state = { view: null, exports: [], requests: [] }
  page.on('request', (r) => { if (/^https?:/.test(r.url())) state.requests.push(r.url()) })
  page.on('response', async (r) => {
    if (!r.url().includes('/api/sra-assessment/') || !r.ok()) return
    if (r.url().includes('/export?')) {
      state.exports.push({ header: r.headers()['content-disposition'], mime: r.headers()['content-type'] })
      return
    }
    try {
      const data = await r.json()
      if (data.session) state.view = data.session
    } catch { /* non-JSON */ }
  })
  return state
}

export const flows = {
  'catalogue, detail, keyboard and Back': async (page, _errors, { go, back, expect, clickText }) => {
    await go(page, '/')
    await page.keyboard.press('Tab')
    const focus = await page.evaluate(() => ({ text: document.activeElement.textContent, outline: getComputedStyle(document.activeElement).outlineStyle }))
    expect(focus.text.includes('Skip to content') && focus.outline !== 'none', 'Skip link needs visible keyboard focus')
    await fill(page, 'input[type=search]', 'IAM-SRA2')
    await clickText(page, 'a', 'Open tool')
    await page.waitForSelector('h1')
    expect((await page.title()).includes('IAM-SRA2 · IAM-SRA'), 'Detail branding')
    await back(page)
    await page.waitForSelector('input[type=search]')
    expect(await page.$eval('input[type=search]', (el) => el.value) === 'IAM-SRA2', 'Catalogue search was not restored')
  },
  'complete authored synthetic interview, correction, information and exports': async (page, _errors, { go, expect, clickText }) => {
    const seen = await monitor(page)
    await go(page, '/legacy')
    await page.waitForSelector('[data-testid=assessment] .empty button')
    await clickText(page, 'button', 'Start assessment')
    await waitUntil(() => seen.view?.state === 'general_welcome', 'New session missing')
    async function act(title) {
      const before = seen.view?.version ?? -1
      await clickText(page, 'button', title)
      await waitUntil(() => seen.view && seen.view.version > before && !seen.view.busy_job, `Action did not complete: ${title}`)
      await wait(100)
    }
    await disclosure(page, 'Prefer to begin with a general conversation?')
    await select(page, 'Are you answering', CASE.context.perspective)
    await disclosure(page, 'More about your context—optional', '[data-testid=general-onboarding]')
    await select(page, 'Which role', CASE.context.role, '[data-testid=general-onboarding]')
    await select(page, 'Which city', CASE.context.city, '[data-testid=general-onboarding]')
    await act('Begin interview')
    await page.reload({ waitUntil: 'networkidle0' })
    expect(await page.$('[data-testid=question]'), 'Refresh did not restore the interview')
    let corrected = false, information = false, reflection = false
    for (let i = 0; i < 65; i++) {
      const view = seen.view
      if (view.state === 'final') break
      if (view.state.endsWith('_interview')) {
        if (view.stage === 'scenario' && !information) {
          await disclosure(page, 'Optional information and sources')
          await fill(page, '#information-question', CASE.information_question)
          await act('Show sourced information')
          while (seen.view.information.some((entry) => !entry.acknowledged)) await act('I have read this')
          information = true
        }
        if (seen.view.stage === 'scenario' && information && !reflection && seen.view.allowed_actions.includes('start_reflection') && seen.view.answers.some((row) => row.stage === 'scenario')) {
          await disclosure(page, 'Optional information and sources')
          await act('Reflect on information'); reflection = true
        }
        const q = seen.view.question
        const ref = Object.values(CASE.bindings[q.id] || {})[0]
        const answer = CASE.answers[ref]
        expect(answer, `No authored fixture for ${q.id}`)
        if (q.format === 'selection') await select(page, 'Your answer', answer.text)
        else await fill(page, '#answer', answer.text)
        await act('Submit answer')
      } else if (view.pending) {
        if (!corrected) {
          await act('Back one step')
          const ref = Object.values(CASE.bindings[seen.view.question.id])[0]
          await fill(page, '#answer', CASE.answers[ref].text)
          await act('Submit answer')
          await disclosure(page, 'Correct the interpretation')
          await fill(page, '#correction', 'Please preserve the exact meaning of my original answer.')
          await act('Apply correction')
          corrected = true
        }
        await act('Confirm interpretation')
      } else if (view.state === 'general_baseline_review') await act('Confirm general summary')
      else if (view.state === 'offer') {
        if (view.scenarios.length > 1) {
          const alternate = view.scenarios.find((row) => row.id !== view.scenario.id)
          await select(page, 'Choose an illustrative', alternate.id)
          await act('Show example')
        }
        // This frozen interview's answers/reflection target its authored example;
        // expanded scenario options must not make it depend on the default sort.
        if (seen.view.scenario?.id !== AUTHORED_SCENARIO) {
          await select(page, 'Choose an illustrative', AUTHORED_SCENARIO)
          await act('Show example')
        }
        expect(seen.view.scenario?.id === AUTHORED_SCENARIO, 'Wrong example for the frozen authored interview')
        await act('Discuss example')
      } else if (view.allowed_actions.includes('confirm_final')) await act('Confirm final summary')
      else throw new Error('Unexpected interview state: ' + view.state)
    }
    expect(seen.view.state === 'final' && corrected && information && reflection, 'Full authored journey incomplete')
    expect(['crl', 'trl', 'orl', 'srl'].every((key) => seen.view.results[key] === null), 'Unavailable scores must remain null')
    expect(!await page.$eval('[data-testid=results]', (el) => el.textContent.includes('Request provisional estimate')), 'Historical global estimate competes with v4 journey')
    await page.click('[data-testid=indicator-assessment] input[type=checkbox][value="indicator-07"]')
    await act('Begin selected indicators')
    expect(seen.view.indicator_assessment.current.scale.length === 9, 'Nine source statements missing')
    await fill(page, '#indicator-answer', 'I propose safeguards to protect rest.')
    await act('Continue')
    await page.reload({ waitUntil: 'networkidle0' })
    await page.waitForSelector('[data-testid=indicator-interpretation]', { timeout: 15000 })
    expect(await page.$('[data-testid=indicator-interpretation]'), 'Indicator interpretation did not restore after reload')
    expect(await page.$eval('[data-testid=indicator-interpretation]', (el) => el.textContent.includes('Proposed condition or safeguard') && el.textContent.includes('your own reasoning or action')), 'Interpretation hides the classifications used for matching')
    await act("Yes, that’s what I meant")
    if (seen.view.indicator_assessment.current.state==='collecting') await act('Finish indicator questions')
    await act('Request draft indicator suggestion')
    expect(seen.view.indicator_assessment.current.participant === null, 'Tool suggestion prepopulated participant result')
    await select(page, 'Your own statement selection', 'indicator-07-crl-3')
    await fill(page, '#indicator-review-explanation', 'The description of understanding fits better.')
    await act('Record my selected statement')
    expect(seen.view.indicator_assessment.current.participant.statement.level === 3, 'Alternative participant statement missing')
    expect(seen.view.indicator_assessment.current.tool.statement.level === 5, 'Participant choice overwrote tool suggestion')
    await page.reload({ waitUntil: 'networkidle0' })
    await page.waitForSelector('[data-testid=participant-indicator-result]', { timeout: 15000 })
    expect(await page.$('[data-testid=participant-indicator-result]'), 'Participant review did not restore')
    expect(await page.$eval('[data-testid=indicator-review] select', (el) => el.value) === '', 'Review was prepopulated on reload')
    const priorRevision = seen.view.indicator_assessment.revision
    await disclosure(page, 'Indicator answers, barriers and corrections')
    await act('Review indicator interpretation')
    expect(seen.view.indicator_assessment.current.tool === null && seen.view.indicator_assessment.current.participant === null, 'Reopening interpretation did not invalidate judgments')
    await page.evaluate(async (revision) => {
      const cap = await (await fetch('/api/sra-assessment/v1/capabilities')).json()
      const active = (await (await fetch('/api/sra-assessment/v1/sessions/' + cap.sessions.at(-1).id)).json()).session
      const response = await fetch('/api/sra-assessment/v1/sessions/' + active.id + '/actions', { method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':cap.csrf_token}, body:JSON.stringify({action:'indicator_review', data:{choice:'endorse',revision}, expected_version:active.version, request_id:crypto.randomUUID()}) })
      if (response.status !== 409) throw new Error('Stale assessment review was not rejected')
    }, priorRevision)
    await act("Yes, that’s what I meant"); if (seen.view.indicator_assessment.current.state==='collecting') await act('Finish indicator questions'); await act('Request draft indicator suggestion'); await act('Confirm suggested statement')
    await clickText(page, 'button', 'Download JSON')
    await waitUntil(() => seen.exports.length === 1, 'JSON download missing')
    await waitUntil(() => page.$$eval('button', (els) => !els.find((el) => el.textContent.trim() === 'Download JSONL')?.disabled), 'Export controls stayed disabled')
    await clickText(page, 'button', 'Download JSONL')
    await waitUntil(() => seen.exports.length === 2, 'JSONL download missing')
    expect(seen.exports.every((row) => row.header.includes('attachment') && /application\/(json|x-ndjson)/.test(row.mime)), 'Export headers/profile')
    const stored = await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }))
    expect(!stored.includes(CASE.answers.concept.text) && !stored.includes('csrf') && !page.url().includes('session'), 'Sensitive state leaked to storage or URL')
    expect(seen.requests.every((url) => new URL(url).origin === new URL(page.url()).origin), 'Browser requested a raw backend or model origin')
    await clickText(page, 'button', 'Reset interview')
    await act('Confirm reset')
    expect(seen.view.state === 'general_welcome' && seen.view.answers.length === 0, 'Reset did not clear interview')
  },
  'mobile privacy preview, blocked input, recoverable model failure and decline': async (page, _errors, { go, expect, clickText }) => {
    await page.setViewport({ width: 360, height: 900 })
    const seen = await monitor(page)
    await go(page, '/legacy')
    await waitUntil(() => seen.view?.state === 'general_welcome', 'Resume after reset missing')
    async function act(title, failure = false) {
      const version = seen.view.version
      await clickText(page, 'button', title)
      await waitUntil(async () => !seen.view.busy_job && (seen.view.version > version || (failure && await page.$('[role=alert]'))), title)
      await wait(100)
    }
    await disclosure(page, 'Prefer to begin with a general conversation?')
    await select(page, 'Are you answering', 'personal'); await disclosure(page, 'More about your context—optional', '[data-testid=general-onboarding]')
    await select(page, 'Which role', 'citizen', '[data-testid=general-onboarding]'); await select(page, 'Which city', 'madrid', '[data-testid=general-onboarding]')
    await act('Begin interview')
    await select(page, 'Your answer', 'little'); await act('Submit answer')
    await fill(page, '#answer', 'password=synthetic-sensitive-value')
    await act('Submit answer', true)
    expect(!await page.$eval('#answer', (el) => el.value), 'Blocked original retained in input')
    await fill(page, '#answer', 'Alice Example has concerns about noise.')
    await act('Submit answer')
    expect(await page.$('[data-testid=cleaned-preview]'), 'Cleaned preview missing')
    expect(!(await page.$eval('[data-testid=assessment]', (el) => el.textContent)).includes('Alice Example'), 'Original private name is visible')
    await act('Confirm cleaned text')
    await act('Back one step')
    await fill(page, '#answer', 'simulate model failure')
    await act('Submit answer')
    await page.waitForSelector('[role=alert]')
    expect(seen.view.retry_draft && seen.view.question, 'Failed model action advanced the question')
    await fill(page, '#answer', CASE.answers.concept.text); await act('Submit answer'); await act('Confirm interpretation')
    await act('Finish here'); await act('Confirm general summary'); await act('Decline example'); await act('Confirm final summary')
    expect(seen.view.state === 'final', 'Decline path incomplete')
    await clickText(page, 'button', 'End session')
    await clickText(page, 'button', 'Confirm end')
    await page.waitForFunction(() => document.body.textContent.includes('Your server session has ended'))
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)
    expect(!overflow, 'Mobile interview overflows')
  },
}

flows['processing reset, navigation cancellation and organisation scope'] = async (page, _errors, { go, expect, clickText }) => {
  const seen = await monitor(page)
  await go(page, '/legacy')
  await page.waitForSelector('.sra-assessment .empty button')
  async function act(title) {
    const before = seen.view?.version ?? -1
    await clickText(page, 'button', title)
    await waitUntil(() => seen.view && seen.view.version > before && !seen.view.busy_job, title)
    await wait(100)
  }
  async function context(perspective = 'personal') {
    await disclosure(page, 'Prefer to begin with a general conversation?')
    await select(page, 'Are you answering', perspective); await disclosure(page, 'More about your context—optional', '[data-testid=general-onboarding]')
    await select(page, 'Which role', 'citizen', '[data-testid=general-onboarding]'); await select(page, 'Which city', 'madrid', '[data-testid=general-onboarding]')
    await act('Begin interview')
  }
  await clickText(page, 'button', 'Start assessment')
  await waitUntil(() => seen.view?.state === 'general_welcome', 'Create session')
  await context()
  await select(page, 'Your answer', 'little'); await act('Submit answer')
  await fill(page, '#answer', 'simulate slow model')
  await clickText(page, 'button', 'Submit answer')
  await waitUntil(() => seen.view.busy_job, 'Queued action not visible')
  await clickText(page, 'button', 'Reset interview'); await act('Confirm reset')
  await wait(2200)
  expect(seen.view.state === 'general_welcome' && !seen.view.pending, 'Late result applied after reset')
  await context()
  await select(page, 'Your answer', 'little'); await act('Submit answer')
  await fill(page, '#answer', 'simulate slow model')
  await clickText(page, 'button', 'Submit answer')
  await waitUntil(() => seen.view.busy_job, 'Second queued action missing')
  await page.click('a[aria-label="IAM-SRA home"] svg')
  await page.waitForSelector('input[type=search]')
  await wait(700)
  const count = seen.requests.filter((url) => url.includes('/jobs/')).length
  await wait(1600)
  expect(seen.requests.filter((url) => url.includes('/jobs/')).length === count, 'Polling continued after navigation')
  await go(page, '/legacy')
  await waitUntil(() => seen.view?.pending && !seen.view.busy_job, 'Session did not resume after background work')
  await clickText(page, 'button', 'Reset interview'); await act('Confirm reset')
  await context('organisation')
  await act('Finish here'); await act('Confirm general summary'); await act('Decline example'); await act('Confirm final summary')
  expect(!seen.view.allowed_actions.includes('provisional_estimate'), 'Organisation estimate was offered')
  expect(!(await page.$eval('[data-testid=results]', (el) => el.textContent)).includes('Optional provisional'), 'Organisation estimate control visible')
  if (process.env.SHOTS) await page.screenshot({ path: process.env.SHOTS + '/organisation-final.png', fullPage: true })
  await clickText(page, 'button', 'End session'); await clickText(page, 'button', 'Confirm end')
  await page.waitForFunction(() => document.body.textContent.includes('Your server session has ended'))
}

for (const [profile,scale] of [['citizen','crl'],['organisational','orl'],['technical','trl']]) {
 flows[`direct ${profile} questionnaire, continuation, restoration and report`] = async (page,_errors,{go,expect,clickText}) => {
  const seen=monitor(page);await go(page,'/legacy')
  await waitUntil(()=>seen.view || page.$('[data-testid=assessment] .empty button'),'Assessment not ready')
  if(!seen.view){await clickText(page,'button','Start assessment');await waitUntil(()=>seen.view,'New session missing')}
  async function act(title){const v=seen.view.version;await clickText(page,'button',title);await waitUntil(()=>seen.view.version>v && !seen.view.busy_job,title);await wait(100)}
  if(seen.view.state!=='general_welcome'){await clickText(page,'button','Reset interview');await act('Confirm reset')}
  await select(page,'Who are you answering for?',profile);await select(page,'What would you like to discuss?','service');await fill(page,'#assessment-use-case','Synthetic proposed service')
  await act('Start assessment')
  expect(seen.view.answers.length===0,'Direct route required baseline answers')
  expect(seen.view.indicator_assessment.selected_indicator_ids.length===15,'Assessment was limited to a batch')
  if(profile!=='citizen'){
   if(profile==='organisational'){await fill(page,'#indicator-unit','Planning unit');await fill(page,'#indicator-responsibilities','Planning and coordination')}
   else{await fill(page,'#indicator-object','Test model');await fill(page,'#indicator-version','A');await fill(page,'#indicator-environment','Laboratory')}
   await act('Confirm indicator scope')
  }
  await fill(page,'#indicator-answer','I propose safeguards because repeated disruption matters.');await act('Continue')
  await page.reload({waitUntil:'networkidle0'});await page.waitForSelector('[data-testid=indicator-interpretation]')
  await act("Yes, that’s what I meant");await act('Request draft indicator suggestion')
  const tool=seen.view.indicator_assessment.current.tool
  expect(tool.statement.profile===profile && tool.statement.scale===scale.toUpperCase(),'Wrong profile statement')
  await act('Read all nine source statements')
  expect(await page.$$eval('[data-testid=indicator-review] ol > li',els=>els.length)===9,'Complete source scale inaccessible')
  await select(page,'Your own statement selection',`indicator-01-${scale}-3`);await act('Record my selected statement')
  expect(seen.view.indicator_assessment.current.participant.statement.level===3,'Participant selection missing')
  expect(seen.view.indicator_assessment.current.tool.selected_statement_id===tool.selected_statement_id,'Tool judgment overwritten')
  await disclosure(page,'Choose or review topics')
  for(const n of [6,11])await act(`Continue Synthetic indicator ${n}`)
  await act('Return to Synthetic indicator 1')
  expect(seen.view.indicator_assessment.current.participant.statement.level===3,'Navigation restarted completed indicator')
  await act('Finish for now');await page.reload({waitUntil:'networkidle0'})
  await page.waitForSelector('[data-testid=individual-profile-report]')
  expect(seen.view.indicator_assessment.report_finished,'Partial report did not restore')
  await clickText(page,'button','Download JSON');await waitUntil(()=>seen.exports.length===1,'JSON missing')
  await waitUntil(()=>page.$$eval('button',els=>!els.find(e=>e.textContent.trim()==='Download JSONL')?.disabled),'Download still busy')
  await clickText(page,'button','Download JSONL');await waitUntil(()=>seen.exports.length===2,'JSONL missing')
 }
}

flows['unavailable tool suggestion preserves explicit participant assessment'] = async (page,_errors,{go,expect,clickText}) => {
 const seen=monitor(page);await go(page,'/legacy')
 await page.waitForSelector('[data-testid=assessment] .empty button');await clickText(page,'button','Start assessment');await waitUntil(()=>seen.view,'Session missing')
 async function act(title){const v=seen.view.version;await clickText(page,'button',title);await waitUntil(()=>seen.view.version>v && !seen.view.busy_job,title);await wait(100)}
 await select(page,'Who are you answering for?','citizen');await select(page,'What would you like to discuss?','service');await fill(page,'#assessment-use-case','Synthetic service');await act('Start assessment')
 await fill(page,'#indicator-answer','simulate indicator failure; I propose safeguards.');await act('Continue');await act("Yes, that’s what I meant");await act('Request draft indicator suggestion')
 expect(seen.view.indicator_assessment.current.tool===null,'Rejected matching became a suggestion or abstention')
 expect(seen.view.indicator_assessment.current.suggestion_error.status==='unavailable','Unavailable status missing')
 await page.reload({waitUntil:'networkidle0'});await page.waitForSelector('[data-testid=indicator-review]')
 expect(await page.$eval('[data-testid=indicator-assessment]',el=>el.textContent.includes('No valid tool suggestion is available')),'Failure notice did not restore')
 await select(page,'Your own statement selection','indicator-01-crl-1');await act('Record my selected statement');await act('Finish for now')
 expect(seen.view.indicator_assessment.current.participant.statement.level===1 && seen.view.indicator_assessment.current.tool===null,'Participant selection fabricated a tool score')
 await clickText(page,'button','Download JSON');await waitUntil(()=>seen.exports.length===1,'Export missing after model rejection')
}

for(const profile of ['citizen','organisational','technical']) {
 flows[`optional scenario context in ${profile} assessment`] = async(page,_errors,{go,expect,clickText})=>{
  if(profile==='citizen')await page.setViewport({width:360,height:900})
  const seen=monitor(page);await go(page,'/legacy')
  await waitUntil(()=>seen.view || page.$('[data-testid=assessment] .empty button'),'Ready state missing')
  if(!seen.view){await clickText(page,'button','Start assessment');await waitUntil(()=>seen.view,'Session missing')}
  async function act(title){const v=seen.view.version;await clickText(page,'button',title);await waitUntil(()=>seen.view.version>v && !seen.view.busy_job,title);await wait(100)}
  if(seen.view.state!=='general_welcome'){await clickText(page,'button','Reset interview');await act('Confirm reset')}
  await select(page,'Who are you answering for?',profile);await select(page,'What would you like to discuss?','service');await fill(page,'#assessment-use-case','Confirmed local proposal');await act('Start assessment')
  if(profile!=='citizen'){if(profile==='organisational'){await fill(page,'#indicator-unit','Planning unit');await fill(page,'#indicator-responsibilities','Planning')}else await fill(page,'#indicator-object','Test model');await act('Confirm indicator scope')}
  await disclosure(page,'About this topic and optional examples');await disclosure(page,'Optional illustrative case for this indicator');await select(page,'Optional case','expansion-04');await act('Use optional case for this indicator')
  expect(seen.view.indicator_assessment.current.scope.use_case==='Confirmed local proposal','Case replaced primary local use case')
  expect(await page.$eval('[data-testid=indicator-case]',el=>el.textContent.includes('unverified_draft_adaptation')),'Case verification status hidden')
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Scenario context scrolls sideways')
  await fill(page,'#indicator-answer','I propose safeguards.');await act('Continue');await act("Yes, that’s what I meant");await act('Request draft indicator suggestion');await act('Remain unsure about my level')
  await page.reload({waitUntil:'networkidle0'});await page.waitForSelector('[data-testid=indicator-case]')
  expect(seen.view.indicator_assessment.current.scope.illustrative_case.id==='expansion-04','Reload lost exact selected case')
  await act('Finish for now');await clickText(page,'button','Download JSON');await waitUntil(()=>seen.exports.length===1,'Case export missing')
  await act('Return to Synthetic indicator 1');await disclosure(page,'About this topic and optional examples');await disclosure(page,'Optional illustrative case for this indicator');await act('Continue without an optional case')
  expect(!seen.view.indicator_assessment.current.scope.illustrative_case && seen.view.indicator_assessment.current.participant===null,'Case decline did not invalidate dependent review')
  await act('Finish for now')
 }
}

flows['simple onboarding general, service, example, privacy and back'] = async (page,_errors,{go,expect,clickText}) => {
 const seen=monitor(page);await go(page,'/legacy')
 await waitUntil(()=>seen.view || page.$('[data-testid=assessment] .empty button'),'Onboarding unavailable')
 if(!seen.view){await clickText(page,'button','Start assessment');await waitUntil(()=>seen.view,'Session missing')}
 async function act(title){const v=seen.view.version;await clickText(page,'button',title);await waitUntil(()=>seen.view.version>v && !seen.view.busy_job,title);await wait(100)}
 async function reset(){if(seen.view.state!=='general_welcome'){await clickText(page,'button','Reset interview');await act('Confirm reset')}}
 await reset()
 expect(await page.$$eval('h2',els=>els.some(e=>e.textContent==='Let’s get started')),'Simple introduction missing')
 expect(await page.$$eval('.sra-task-head',els=>els.every(e=>!e.textContent.includes('General interview'))),'Setup called general interview')
 expect(await page.$$eval('details',els=>els.filter(e=>['How this assessment works','Prefer to begin with a general conversation?','More about your context—optional'].includes(e.querySelector(':scope > summary')?.textContent.trim())).every(e=>!e.open)),'Help or duplicate setup opened by default')
 expect(!await page.$('#assessment-use-case') && !await page.$('#assessment-object'),'General citizen setup requires service or object')
 await page.setViewport({width:360,height:900})
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Onboarding scrolls sideways on mobile')
 if(process.env.SHOTS)await page.screenshot({path:`${process.env.SHOTS}/onboarding-mobile.png`,fullPage:true})
 await page.setViewport({width:1200,height:900})
 for(const profile of ['citizen','organisational','technical']){
  await select(page,'Who are you answering for?',profile);await act('Start assessment')
  const a=seen.view.indicator_assessment
  expect(a.scope.context==='general_understanding' && a.scope.discussion_choice==='general','General context misclassified')
  expect(a.scope.use_case_card.origin==='tool_derived_general_context','Tool label attributed to respondent')
  expect(a.current.state===(profile==='citizen'?'collecting':'scope'),'Scope confirmation bypassed')
  if(profile==='technical'){
   await select(page,'Scope availability','no_technical_object_identified');await act('Confirm indicator scope')
   expect(seen.view.indicator_assessment.current.disposition==='no_technical_object_identified','Unknown object became a number')
  }
  await page.reload({waitUntil:'networkidle0'});await page.waitForSelector('[data-testid=indicator-assessment]')
  expect(seen.view.indicator_assessment.scope.discussion_choice==='general','Reload lost explicit general choice')
  await reset()
 }
 for(const stage of ['proposal','operational']){
  await select(page,'Who are you answering for?','citizen');await select(page,'What would you like to discuss?','service')
  await fill(page,'#assessment-use-case',stage==='proposal'?'Alice Example described hospital supplies transport':'Hospital supplies transport')
  await select(page,'What stage is the service at?',stage);await act('Start assessment')
  if(stage==='proposal'){
   expect(seen.view.preview.fields.discussion_choice==='service' && seen.view.preview.fields.discussion_status==='proposal','Privacy preview lost selected choices')
   await act('Confirm cleaned text')
  }
  expect(seen.view.indicator_assessment.scope.discussion_status===stage,'Reported service stage lost')
  expect(seen.view.indicator_assessment.scope.use_case_card.origin==='participant_described_service','Service origin wrong')
  await reset()
 }
 await select(page,'Who are you answering for?','citizen');await select(page,'What would you like to discuss?','example')
 await select(page,'Choose an illustrative example','expansion-04')
 expect(await page.$eval('[data-testid=onboarding-example]',e=>e.textContent.includes('unverified_draft_adaptation') && e.textContent.includes('Unknown:') && e.textContent.includes('Illustrative example')),'Example source status/unknowns hidden before confirmation')
 expect(!await page.$('#assessment-use-case'),'Example requires invented service description')
 await act('Start assessment')
 expect(seen.view.indicator_assessment.scope.context==='illustrative_proposal','Example treated as actual experience')
 expect(seen.view.indicator_assessment.current.information.some(e=>e.kind==='case'),'Example exposure lost')
 await reset()
 expect(!await page.$('[data-testid=general-onboarding]'),'Removed alternative setup is still visible')
 expect(await page.$$eval('summary',els=>!els.some(e=>e.textContent.includes('More about your context'))),'Removed context disclosure is still visible')
 await select(page,'Who are you answering for?','citizen');await act('Start assessment')
 await clickText(page,'button','Back')
 await page.waitForSelector('[data-testid=assessment-onboarding]')
 expect(await page.$eval('#assessment-use-case',()=>true).catch(()=>false)===false,'Back to general setup requires a service')
 await clickText(page,'button','Back')
 expect(!await page.$('[data-testid=assessment-onboarding]'),'Back did not cancel scope editing')

}

flows['simple second screen, skip and partial results'] = async (page,_errors,{go,expect,clickText}) => {
 const seen=monitor(page);await go(page,'/legacy')
 await waitUntil(()=>seen.view || page.$('[data-testid=assessment] .empty button'),'Assessment unavailable')
 if(!seen.view){await clickText(page,'button','Start assessment');await waitUntil(()=>seen.view,'Session missing')}
 async function act(title){const v=seen.view.version;await clickText(page,'button',title);await waitUntil(()=>seen.view.version>v && !seen.view.busy_job,title);await wait(100)}
 if(seen.view.state!=='general_welcome'){await clickText(page,'button','Reset interview');await act('Confirm reset')}
 await select(page,'Who are you answering for?','citizen');await act('Start assessment')
 expect(await page.$eval('[data-testid=topic-progress]',e=>e.textContent.includes('Topic 1 of 15 available')),'Topic progress missing')
 expect(!await page.$eval('[data-testid=indicator-coverage]',e=>e.open),'Full topic list distracts from question')
 expect(!await page.$eval('[data-testid=topic-help]',e=>e.open),'Technical methodology displayed by default')
 expect(await page.$('[data-testid=indicator-question]'),'Question missing')
 const visible=await page.$$eval('button',els=>els.filter(e=>e.getClientRects().length).map(e=>e.textContent.trim()))
 expect(visible.includes('Continue') && visible.includes('Skip') && !visible.includes('Download JSON'),'Question-first controls missing')
 await act('Skip');await act('Finish for now')
 expect(await page.$('[data-testid=individual-profile-report]'),'Partial result missing')
 expect(await page.$eval('[data-testid=indicator-coverage]',e=>e.open),'Completed report hides coverage')
}

flows['free chat direct entry, all profiles, privacy and keyboard'] = async (page,_errors,{go,expect,clickText}) => {
 const seen=monitor(page)
 await go(page,'/chat');await waitUntil(()=>seen.view?.chat,'Chat did not open')
 async function send(text){const version=seen.view.version;await fill(page,'#chat-message',text);await clickText(page,'button','Send');await waitUntil(()=>seen.view.version>version && !seen.view.busy_job,text);await wait(100)}
 expect(await page.$eval('h1',e=>e.textContent)==="Let's talk about drones",'Wrong title')
 expect(!await page.$('[data-testid=indicator-assessment]'),'Indicator form exposed')
 expect(!await page.$$eval('button',els=>els.some(e=>['Skip','I’m not sure','Confirm interpretation'].includes(e.textContent.trim()))),'Legacy controls exposed')
 await send('My personal views');await send('Madrid, no known local service');await send('I have no idea what a drone is')
 expect(seen.view.chat.messages.at(-1).text.includes('Would you like'),'No explanation permission')
 await send('yes please');await send('Noise and privacy concern me')
 await send('show two ways of asking that');expect(seen.view.chat.pending_comparison,'No comparison state')
 await send('2. Sleep disturbance matters.');expect(!seen.view.chat.pending_comparison,'Comparison did not resolve')
 await send('stop');expect(seen.view.chat.stage==='summary','Natural finish missing')
 await send('looks right');expect(seen.view.chat.stage==='review','No result review')
 expect(await page.$('section[aria-label="Scale disclosure"]'),'No scale disclosure')
 await page.setViewport({width:360,height:900});await page.evaluate(()=>document.documentElement.style.fontSize='200%')
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Scale overflow at large text')
 await page.evaluate(()=>document.documentElement.style.fontSize='');await page.setViewport({width:1200,height:900})
 await send('I prefer level 7, something is missing');expect(seen.view.chat.participant_review.preferred_level===7,'Review mixed with suggestion')
 await page.reload({waitUntil:'networkidle0'});await page.waitForSelector('#chat-message')
 expect(seen.view.chat.stage==='review_addition','Reload did not preserve stage')
 for(const profile of ['organisational','technical']){
  await disclosure(page,'Privacy, help and conversation options');await clickText(page,'button','New conversation');await waitUntil(()=>seen.view.chat.profile===null,'Reset failed')
  await send(profile==='organisational'?'Our organisation responsibilities':'A technology subsystem')
  await send('Madrid');await send('Test unit, safety subsystem v1, laboratory; healthcare logistics remit only')
  expect(seen.view.chat.profile===profile,'Wrong profile')
  expect(seen.view.chat.messages.at(-1).text.includes(profile==='organisational'?'team':'object'),'Scope-specific questions missing')
 }
 await send('My contact is demo@example.com and I discuss a laboratory system')
 expect(seen.view.preview && !JSON.stringify(seen.view).includes('demo@example.com'),'Privacy repair bypassed')
 await clickText(page,'button','Return to editing');await waitUntil(()=>!seen.view.preview,'Preview not discarded')
 expect(await page.$eval('#chat-message',e=>e.value.includes('demo@example.com')),'Unsent draft cleared')
 await page.setViewport({width:360,height:900})
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Mobile overflow')
 await page.evaluate(()=>document.documentElement.style.fontSize='200%')
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Large-text mobile overflow')
 await page.evaluate(()=>document.documentElement.style.fontSize='')
 await page.focus('#chat-message');await page.keyboard.press('Enter');expect(await page.$eval('#chat-message',e=>e.value.includes('\n')),'Enter must allow multiline input')
 await go(page,'/tools/sra-assessment/app');expect(new URL(page.url()).pathname==='/chat','Tool alias did not reach chat')
}
