# Deep Page Map

`src/page_probe.py` now exports a safer deep-page map for local, owned, or explicitly authorized pages.

It is meant for cases where the real target UI is buried behind manual login, browser extensions, tabs, or nested frames.

## What It Adds

- `depth` and `parent_index` for every frame.
- `frame_chain` hints that can be translated into an authorized `target.frame_chain` profile.
- `target_hint` for frame selection by `name` or `url_contains`.
- Per-candidate `score` and `reasons`.
- `summary.best_candidates`, a short list of visible controls worth manually reviewing.

## Run

```bash
python src/page_probe.py examples/attached_chrome_profile.json --out page-probe-result.json
```

Then import `page-probe-result.json` into `report_center.py` to get an HTML report with a candidate-control table.

## Safety Boundary

This report does not solve CAPTCHA challenges and does not generate third-party bypass logic.

Use it only for:

- local demo pages;
- owned applications;
- pages where you have explicit permission to test;
- QA documentation and selector discovery.
