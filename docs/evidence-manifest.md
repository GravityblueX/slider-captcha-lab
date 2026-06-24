# Authorized Evidence Manifest

Generated: 2026-06-24T03:13:27.993220+00:00
Scope: `local_owned_or_explicitly_authorized_pages_only`
Status: `OK`

## Evidence Items

| Artifact | Result | Purpose |
|---|---|---|
| `docs/authorized-evidence-pack-local-demo.json` | OK | local demo browser evidence pack |
| `docs/authorized-evidence-pack-local-demo.md` | OK | human-readable authorized evidence summary |
| `docs/profile-policy-report.json` | OK | profile authorization and local-default policy |
| `docs/profile-policy-report.md` | OK | human-readable profile policy report |
| `docs/target-surface-registry.json` | OK | authorized browser target and surface registry |
| `docs/target-surface-registry.md` | OK | human-readable authorized target surface registry |
| `docs/cdp-authorized-diagnostics.md` | OK | authorized Chrome DevTools Protocol diagnostics notes |
| `docs/deep-page-map.md` | OK | deep page and frame mapping notes |
| `docs/trace-artifacts/local-demo-trace.json` | OK | local screenshot and selector visibility trace |
| `docs/trace-artifacts/local-demo-trace.md` | OK | human-readable local trace artifact summary |
| `docs/trace-artifacts/local-demo.png` | OK | local demo screenshot evidence |

## Reference Patterns

- Playwright Trace Viewer: inspectable artifacts instead of opaque automation claims
- Chrome DevTools Protocol Page domain: frame/page state is explicit evidence
- OpenSSF Scorecard: local gates make project health reviewable

## Boundary

- This manifest is for local, owned, or explicitly authorized browser diagnostics.
- It does not solve CAPTCHA challenges, evade bot defenses, or store cookie values.
