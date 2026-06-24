from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.evidence_pack import build_evidence_pack, render_markdown
from scripts.profile_policy import build_report, check_profile
from src.analyzer import analyze
from src.trajectory import generate_trajectory

ROOT = Path(__file__).resolve().parents[1]


class LocalContractTests(unittest.TestCase):
    def test_generated_trajectory_has_analyzable_human_like_shape(self) -> None:
        points = generate_trajectory((0, 0), (320, 0), duration_ms=900, steps=90)
        metrics = analyze(points)

        self.assertGreaterEqual(len(points), 8)
        self.assertEqual(points[0].t, 0)
        self.assertGreaterEqual(points[-1].t, 900)
        self.assertGreater(metrics["score"], 0)
        self.assertIn(metrics["verdict"], {"natural_like_for_local_lab", "needs_review"})

    def test_authorized_example_profile_stays_on_local_demo_page(self) -> None:
        profile = json.loads((ROOT / "examples" / "authorized_deep_page_profile.json").read_text(encoding="utf-8"))

        self.assertTrue(profile.get("authorized_only"))
        self.assertIn("demo/index.html", profile["url"])
        self.assertNotIn("http://", profile["url"])
        self.assertNotIn("https://", profile["url"])

    def test_documentation_keeps_explicit_authorized_use_boundary(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        disclaimer = (ROOT / "DISCLAIMER.md").read_text(encoding="utf-8")
        combined = f"{readme}\n{disclaimer}"

        for required in ["明确授权", "请勿用于", "验证码", "风控"]:
            self.assertIn(required, combined)

    def test_evidence_pack_preserves_authorized_boundary(self) -> None:
        profile = {
            "name": "local-authorized-deep-page-example",
            "url": "demo/index.html",
            "authorized_only": True,
            "browser": {"manual_navigation": False, "connect_existing_chrome": False},
        }
        authorized_result = {"summary": {"passed": 2, "failed": 0, "total": 2}}
        probe = {
            "summary": {
                "frame_count": 1,
                "deep_frame_count": 0,
                "candidate_count": 2,
                "visible_candidate_count": 2,
                "best_candidates": [
                    {"selector": "#knob", "frame_index": 0, "frame_depth": 0, "score": 89, "reasons": ["visible"]}
                ],
            }
        }
        cdp = {"scope": "local_owned_or_explicitly_authorized_pages_only", "cdp": {"target_count": 1}, "page": {"frame_count": 1}}

        pack = build_evidence_pack(ROOT / "examples" / "authorized_deep_page_profile.json", profile, authorized_result, probe, cdp)
        markdown = render_markdown(pack)

        self.assertTrue(pack["ok"])
        self.assertTrue(pack["safety"]["does_not_solve_captcha"])
        self.assertIn("Does not solve CAPTCHA", markdown)
        self.assertIn("#knob", markdown)

    def test_profile_policy_accepts_bundled_authorized_examples(self) -> None:
        report = build_report([ROOT / "examples"])

        self.assertTrue(report["ok"])
        self.assertEqual(report["issues"], [])

    def test_profile_policy_rejects_third_party_defaults(self) -> None:
        issues = check_profile(
            ROOT / "examples" / "bad.json",
            {"name": "bad", "url": "https://example.com", "authorized_only": False},
        )

        messages = [issue.message for issue in issues]
        self.assertIn("authorized_only must be true", messages)
        self.assertTrue(any("default url must be local" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
