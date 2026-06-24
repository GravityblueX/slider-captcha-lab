# Target Surface Registry

Generated: 2026-06-24T03:13:27.842051+00:00
Scope: `local_owned_or_explicitly_authorized_pages_only`
Status: `OK`

## Summary

| Metric | Value |
|---|---:|
| Profiles | 2 |
| Persistent profile surfaces | 1 |
| CDP attach surfaces | 1 |
| Extension-configured profiles | 0 |
| Manual-navigation profiles | 0 |

## Gates

| Gate | Result | Detail |
|---|---|---|
| profiles discovered | OK | 2 profile(s) |
| all profiles authorized | OK | authorized_only=true |
| all default urls local | OK | demo/file/localhost defaults only |
| all CDP endpoints local | OK | localhost CDP only |
| no profile cookie values | OK | no stored cookie values |
| persistent profile surface documented | OK | 1 profile(s) |
| CDP attach surface documented | OK | 1 profile(s) |
| local demo target present | OK | 2 local profile(s) |
| deep page map exists | OK | docs/deep-page-map.md |
| local trace screenshot exists | OK | docs/trace-artifacts/local-demo.png |
| profile policy report ok | OK | True |
| evidence manifest ok | OK | True |
| anti-abuse boundary documented | OK | README.md + DISCLAIMER.md |

## Profiles

| Profile | URL | Browser Surface | Selectors | Frame Depth |
|---|---|---|---|---:|
| `examples\attached_chrome_profile.json` | `demo/index.html` | cdp-attach | slider=0; knob=0; success=0 | 0 |
| `examples\authorized_deep_page_profile.json` | `demo/index.html` | persistent-profile | slider=1; knob=1; success=1 | 0 |

## Boundary

- This registry is for local, owned, or explicitly authorized browser diagnostics.
- It does not solve CAPTCHA challenges, evade bot defenses, or store cookie values.
- Third-party sites must not be added as default targets.
