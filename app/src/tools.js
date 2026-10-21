// Adapted from IAM-IQ: id controls the route, component and same-origin proxy prefix.
export const TOOLS = [{
  id: 'sra-assessment', name: 'IAM-SRA2', suite: 'IAM-SRA', partner: 'IAM-SRA',
  domains: ['societal readiness'], tags: ['Citizens', 'Researchers'], status: 'live', hasApp: true,
  lead: 'Explore your understanding and participation in innovative air mobility.',
  does: [
    'Guides a general interview with interpretation review and correction',
    'Offers an optional illustrative scenario and source-grounded information',
    'Exports confirmed evidence with an optional provisional citizen estimate',
  ],
  audience: 'Citizens and organisational respondents taking part in an internal, draft assessment demonstration.',
  data: 'Reviewed sources are provisioned privately by the operator. Answers remain in server memory until expiry, reset or restart; downloads remain with their recipients.',
}]
export const toolById = (id) => TOOLS.find((tool) => tool.id === id)
export const SUITES = ['IAM-SRA']
export const DOMAINS = ['societal readiness']
export const AUDIENCES = [
  { id: 'citizens', label: 'For citizens', tag: 'Citizens' },
  { id: 'researchers', label: 'For researchers', tag: 'Researchers' },
]
