# Profile Policy Report

Status: `OK`
Profiles checked: `2`

## Policy

- Profiles must set `authorized_only: true`.
- Default URLs must be bundled demo files or localhost.
- CDP attach endpoints must be localhost.
- Profiles must not store cookie values.

## Profiles

| Profile | Authorized | URL | Issues |
|---|---|---|---|
| `examples\attached_chrome_profile.json` | `True` | `demo/index.html` | none |
| `examples\authorized_deep_page_profile.json` | `True` | `demo/index.html` | none |
