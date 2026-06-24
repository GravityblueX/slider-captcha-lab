# Authorized Evidence Pack - Local Demo

Generated: 2026-06-24T01:39:12.786216+00:00
Scope: `local_owned_or_explicitly_authorized_pages_only`
Result: `OK`

## Boundary

- Local, owned, or explicitly authorized pages only.
- Does not solve CAPTCHA challenges.
- Does not record cookie values or third-party secrets.
- Default profile stays on the bundled local demo page.

## Profile

- Name: `local-authorized-deep-page-example`
- URL: `demo/index.html`
- Authorized only: `True`
- Manual navigation: `False`
- Existing Chrome attach: `False`

## Evidence Summary

- Authorized profile: passed `2`, failed `0`, total `2`
- Page probe: frames `1`, visible candidates `2`
- CDP diagnostics: targets `1`, frames `1`

## Best Selector Candidates

| Selector | Frame | Score | Reasons |
|---|---:|---:|---|
| `#knob` | 0 | 89 | visible, slider_or_drag_named, button_like, knob_shaped, has_label |
| `#slider` | 0 | 79 | visible, slider_or_drag_named, track_shaped, has_label |
