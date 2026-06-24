# Authorized Boundary Audit

Generated: 2026-06-24T03:59:37.330819+00:00
Scope: `local_owned_or_explicitly_authorized_pages_only`
Status: `OK`

## Summary

| Metric | Value |
|---|---:|
| Profiles | 2 |
| CDP attach profiles | 1 |
| Persistent profiles | 1 |
| Extension profiles | 0 |
| Blocked default-target markers | 0 |

## Gates

| Gate | Result | Detail |
|---|---|---|
| scope recorded | OK | local_owned_or_explicitly_authorized_pages_only |
| target surface registry ok | OK | True |
| safety contract ok | OK | True |
| all profiles authorized only | OK | 2 profile(s) |
| all default URLs local | OK | 2 profile(s) |
| all CDP endpoints local | OK | 2 profile(s) |
| CDP attach uses existing local browser only | OK | 1 CDP profile(s) |
| default profiles do not load extensions | OK | 0 extension profile(s) |
| blocked real-site markers absent from profile defaults | OK | none |
| no cookie values in generated audit inputs | OK | profile registry storesCookieValues=false |
| README and disclaimer keep non-bypass language | OK | README.md + DISCLAIMER.md |

## Boundary

- Defaults must remain local, owned, or explicitly authorized.
- Real third-party challenge providers and site-specific bypass targets are not allowed as defaults.
- CDP attach is limited to local browser diagnostics and must not store cookie values.
