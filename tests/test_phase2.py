import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

from complaints_analyzer.phase2 import (ROOT, months, score_point, score_panel,
                                       load_counts, top_k, validate_config, injection_experiment)


class Phase2Tests(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads((ROOT / "configs/phase2.json").read_text(encoding="utf-8"))
        self.cfg["products"] = ["A"]
        self.counts = {(m, "A"): 100 for m in months("2017-05", "2025-12")}

    def test_hand_calculation_constant_history(self):
        score = score_point(130, [100] * 12)
        self.assertEqual((score["baseline"], score["score"]), (100, 30))
        self.assertTrue(score["scale_floored"])
        self.assertTrue(score["zero_mad"])

    def test_first_scored_month_and_window(self):
        rows = score_panel(self.counts, self.cfg)
        self.assertEqual((rows[0]["month"], rows[0]["history_start"], rows[0]["history_end"]),
                         ("2018-05", "2017-05", "2018-04"))

    def test_future_change_cannot_change_past(self):
        before = score_panel(self.counts, self.cfg)
        self.counts[("2024-12", "A")] = 100000000
        after = score_panel(self.counts, self.cfg)
        self.assertEqual(before[:-1], after[:-1])

    def test_current_month_excluded_from_baseline(self):
        self.counts[("2018-05", "A")] = 100000
        row = score_panel(self.counts, self.cfg)[0]
        self.assertEqual(row["baseline"], 100)
        self.assertEqual(row["score"], 99900)

    def test_missing_month_fails_no_zero_fill(self):
        del self.counts[("2018-04", "A")]
        with self.assertRaisesRegex(ValueError, "Missing"):
            score_panel(self.counts, self.cfg)

    def test_zero_counts_are_distinct_from_missing(self):
        self.counts[("2018-04", "A")] = 0
        self.assertEqual(score_panel(self.counts, self.cfg)[0]["baseline"], 100)

    def test_ties_are_deterministic_and_nonpositive_excluded(self):
        rows = [{"score": 3, "month": "2024-01", "product": p} for p in ("B", "A")]
        rows.append({"score": 0, "month": "2023-01", "product": "C"})
        self.assertEqual([r["product"] for r in top_k(rows, 20)], ["A", "B"])
        self.assertEqual(top_k(rows[::-1], 1), top_k(rows, 1))

    def test_invalid_dates_and_reverse_range(self):
        for left, right in [("2024-13", "2024-13"), ("2024-2", "2024-12"), ("2025-01", "2024-01")]:
            with self.assertRaises(ValueError):
                months(left, right)

    def test_temporal_boundary_configuration_validation(self):
        validate_config(self.cfg)
        self.cfg["validation_end"] = "2020-01"
        with self.assertRaises(ValueError):
            validate_config(self.cfg)

    def test_injection_pairing_reproducibility_and_no_mutation(self):
        self.cfg.update(seeds=[7], trials_per_seed=2, growth_fractions=[0.25, 1])
        original = copy.deepcopy(self.counts)
        trials, summary = injection_experiment(self.counts, self.cfg)
        self.assertEqual(self.counts, original)
        self.assertEqual((trials, summary), injection_experiment(self.counts, self.cfg))
        for a, b in zip(trials[::2], trials[1::2]):
            self.assertEqual((a["month"], a["product"]), (b["month"], b["product"]))
            self.assertGreater(b["added"], a["added"])

    def test_bad_aggregate_rejected(self):
        for values in [("-1",), ("2", "3")]:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "cross.csv"
                with path.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["table", "key_1", "key_2", "count"])
                    for value in values:
                        writer.writerow(["month_product", "2024-01", "A", value])
                with self.assertRaises(ValueError):
                    load_counts(path)

    def test_phase_two_does_not_score_test_period(self):
        self.counts[("2025-01", "A")] = 1000000
        rows = score_panel(self.counts, self.cfg)
        self.assertTrue(all(row["month"] <= "2024-12" for row in rows))


if __name__ == "__main__":
    unittest.main()
