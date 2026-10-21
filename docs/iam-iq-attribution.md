# IAM-IQ source attribution

The IAM-SRA Vue application adapts reusable frontend source from
https://codeberg.org/IAM-CC/IAM-IQ.git at
`bb1ff04913c32f3a0d85ee6b6a34d38c1dd00f2e`.

The catalogue/detail/working-page structure, chrome, router, API wrapper,
composables, form/state components, production proxy, Docker build and browser
harness derive from that checkout. `docs/iam-iq-provenance.json` records each
copied file, its donor path and its original SHA-256. Authored SRA files and
adaptations are identified by the integration diff.

Generated `app/src/styles/tokens.css` and `components.css` are byte-identical to
the donor. IAM-CC logo and EU emblem remain intact. The offline Google Sans font
CSS retains its upstream generated notice and SIL OFL attribution. Reference
skills, design notes, playground and deployment example are retained under
`docs/vendor/iam-iq/`; their IAM-IQ endpoint descriptions are donor references,
not the IAM-SRA API contract.

No repository-wide licence file was present in the inspected donor checkout.
This attribution does not invent a licence grant or change ownership. Confirm
redistribution terms with the donor owners as part of any public onboarding.
No partner datasets, credentials, donor runtime files or donor tool pages were
copied into the application. The separate donor checkout was left unchanged.
