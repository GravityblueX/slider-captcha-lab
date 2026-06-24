# Safety Contract

Generated: 2026-06-24T03:25:42.020463+00:00
Scope: `local_owned_or_explicitly_authorized_pages_only`
Status: `OK`

## Gates

| Gate | Result | Detail |
|---|---|---|
| README states non-bypass boundary | OK | README.md + DISCLAIMER.md |
| profile policy ok | OK | True |
| target surface registry ok | OK | True |
| evidence manifest ok | OK | True |
| evidence pack does not solve CAPTCHA | OK | True |
| all default targets local | OK | 2 profile(s) |
| all profiles authorized only | OK | 2 profile(s) |
| all CDP endpoints local | OK | 2 profile(s) |
| no cookie values in generated evidence | OK | cookie keys absent |

## Boundary

- This contract is for local, owned, or explicitly authorized browser diagnostics.
- It rejects third-party default targets, CAPTCHA solving claims, and stored cookie values.
