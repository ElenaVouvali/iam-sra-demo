# Opening IAM-SRA from an IAM-CC tool tile

The central IAM-CC tools page is a web catalogue. IAM-IQ is a separate web
application with its own catalogue. This repository builds a standalone IAM-SRA
application; it does not modify either running catalogue.

The catalogue owner needs an approved shared IAM-SRA address, then a tile/link
with the name **IAM-SRA2**, description **Explore understanding and participation
in innovative air mobility**, and the destination
`https://<approved-sra-host>/tools/sra-assessment/app`. The actual host is a
platform decision; localhost is only for the current machine or an SSH tunnel.
No central registry schema or API is assumed.

Clicking that link opens the Vue interface served from IAM-SRA's `app/dist/`.
Vue runs in the visitor's browser. It sends same-origin `/api/sra-assessment/v1/`
requests to the UI server, which proxies them to the Python API. The API runs the
existing assessment controller on server CPU/RAM, reads the privately provisioned
corpus and calls the existing local Qwen/vLLM GPU service when inference is
needed. Session state is temporary API-server memory. Private sources, model
addresses and GPU weights are never downloaded into the browser.

Simply pasting an IAM-SRA registry entry into the IAM-IQ donor would not complete
that connection: IAM-IQ's current registry assumes local working-page components
and proxy entries. The platform owner must select the supported external-link or
shared-host arrangement. The separate donor checkout is unchanged.

The standalone application is locally available at
`http://127.0.0.1:5001/tools/sra-assessment/app` after the documented launch.
See [launch, networking and rollback](iamcc-integration.md). Central publication,
SSO integration and catalogue registration have not been performed.
