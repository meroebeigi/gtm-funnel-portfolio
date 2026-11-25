import csv
import json
import tempfile
import unittest
from pathlib import Path

from build_powerbi import generate
from run_demo import ROOT, build


class DemoTest(unittest.TestCase):
    def test_reconciles_and_preserves_attribution(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            root = Path(folder)
            crm, funnel = build(ROOT / "demo-exports", root)
            self.assertEqual(len(crm), 16)
            self.assertEqual(len({r["Account"] for r in funnel if r["Attempted"]}), 14)
            self.assertEqual(sum(r["Meetings"] for r in funnel), 3)
            self.assertEqual(sum(r["Overdue"] for r in crm if r["Channel"] == "Email"), 1)
            a03 = {r["Channel"]: r["Meetings"] for r in funnel if r["Account"] == "A03"}
            self.assertEqual(a03, {"LinkedIn": 1, "Email": 0})
            with (root / "validation.csv").open(encoding="utf-8") as file:
                issues = [r["Reason"] for r in csv.DictReader(file)]
            self.assertTrue(any("invalid" in reason for reason in issues))
            self.assertIn("Duplicate meeting observation", issues)
            generate(root / "power-bi", crm, funnel)
            first = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            crm, funnel = build(ROOT / "demo-exports", root)
            generate(root / "power-bi", crm, funnel)
            self.assertEqual(first, {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()})
            for path in root.rglob("*.json"):
                json.loads(path.read_text(encoding="utf-8"))
