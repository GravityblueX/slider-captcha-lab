from __future__ import annotations

import json
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
